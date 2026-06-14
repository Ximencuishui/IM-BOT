"""
TCP长连接消息接收服务
支持粘包/拆包处理、ACK确认机制、RabbitMQ推送
"""
import socket
import struct
import json
import logging
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from services.message_service import process_incoming_message, rabbitmq_producer

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(settings.LOG_DIR, 'tcp_server.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 确保日志目录存在
os.makedirs(settings.LOG_DIR, exist_ok=True)

# 协议常量
HEADER_SIZE = 4  # 消息头长度(4字节)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 最大消息长度10MB
MAGIC_NUMBER = 0xABCD  # 魔术字,用于协议校验


def _extract_wechat_string(value) -> str:
    """提取微信结构中的字符串字段"""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get('String')
        if isinstance(text, str):
            return text
    return ''


def _build_message_summary(raw_msg: dict, result: dict) -> str:
    """构造单行处理摘要日志，便于联调排查"""
    content = (
        raw_msg.get('real_content')
        or _extract_wechat_string(raw_msg.get('content'))
        or raw_msg.get('msg')
        or ''
    )
    content = str(content).replace('\n', ' ').strip()
    if len(content) > 30:
        content = content[:30] + '...'

    sender_profile = raw_msg.get('sender_profile') if isinstance(raw_msg.get('sender_profile'), dict) else {}
    from_user = _extract_wechat_string(raw_msg.get('fromUserName')) or raw_msg.get('fromUserName') or ''
    sender = (
        _extract_wechat_string(sender_profile.get('nickName'))
        or raw_msg.get('sender_nick')
        or raw_msg.get('nickname')
        or _extract_wechat_string(raw_msg.get('fromUserName'))
        or '未知发送者'
    )
    sender_wxid = (
        _extract_wechat_string(sender_profile.get('userName'))
        or sender_profile.get('friendUserName')
        or _extract_wechat_string(raw_msg.get('fromUserName'))
        or '-'
    )
    from_user = str(from_user or '-')
    event_type = raw_msg.get('event_type')
    msg_type = raw_msg.get('msgType')

    return (
        f"sender={sender} | sender_wxid={sender_wxid} | from_user={from_user} | "
        f"content='{content}' | event_type={event_type} | msgType={msg_type} | "
        f"duplicated={result.get('duplicated', False)} | queued={result.get('queued', False)} | "
        f"rule_applied={result.get('rule_applied', False)} | order_created={result.get('order_created', False)} | "
        f"order_id={result.get('order_id', '-')}" 
        f" | skip_reason={result.get('order_skip_reason', '-')}"
    )


def build_ack(success: bool, message: str = "") -> bytes:
    """
    构建ACK响应包

    协议格式:
    - 4字节: 消息总长度(大端序)
    - 1字节: ACK类型 (0x01=成功, 0x00=失败)
    - N字节: JSON数据
    """
    ack_type = 0x01 if success else 0x00
    ack_data = {
        "type": "ack",
        "success": success,
        "message": message,
        "timestamp": int(datetime.now().timestamp())
    }
    ack_body = json.dumps(ack_data, ensure_ascii=False).encode('utf-8')

    # 构建完整数据包: 长度(4字节) + ACK类型(1字节) + 数据
    body_length = 1 + len(ack_body)
    header = struct.pack('>I', body_length)
    return header + bytes([ack_type]) + ack_body


def parse_message(data: bytes) -> dict:
    """
    解析消息体

    协议格式:
    - 1字节: 消息类型
    - N字节: JSON数据
    """
    if len(data) < 1:
        raise ValueError("消息体过短")

    # 兼容协议A: 纯JSON消息体（无msg_type前缀）
    # 你的VXHook当前推送就是这种格式: { ... }
    try:
        raw_text = data.decode('utf-8', errors='strict').strip()
        if raw_text.startswith('{') or raw_text.startswith('['):
            return {
                'msg_type': 0x01,  # 默认按业务消息处理
                'data': json.loads(raw_text)
            }
    except Exception:
        # 纯JSON解析失败时继续尝试协议B
        pass

    # 兼容协议B: 1字节消息类型 + JSON数据
    msg_type = data[0]
    json_data = data[1:].decode('utf-8', errors='strict').strip()

    return {
        'msg_type': msg_type,
        'data': json.loads(json_data)
    }


def handle_client(client_socket, client_addr):
    """
    处理客户端连接
    支持心跳检测和断线重连
    """
    logger.info(f"客户端连接: {client_addr}")
    buffer = b""

    try:
        while True:
            # 读取消息头(4字节长度)
            while len(buffer) < HEADER_SIZE:
                chunk = client_socket.recv(4096)
                if not chunk:
                    logger.info(f"客户端断开连接: {client_addr}")
                    return
                buffer += chunk

            # 解析消息长度
            header = buffer[:HEADER_SIZE]
            msg_length = struct.unpack('>I', header)[0]

            if msg_length > MAX_MESSAGE_SIZE:
                logger.error(f"消息过长({msg_length}字节),断开连接: {client_addr}")
                return

            # 等待完整消息
            while len(buffer) < HEADER_SIZE + msg_length:
                chunk = client_socket.recv(4096)
                if not chunk:
                    logger.warning(f"客户端在发送完整消息前断开: {client_addr}")
                    return
                buffer += chunk

            # 提取完整消息
            full_message = buffer[HEADER_SIZE:HEADER_SIZE + msg_length]
            buffer = buffer[HEADER_SIZE + msg_length:]

            # 解析消息
            try:
                parsed = parse_message(full_message)
                logger.debug(f"收到消息类型: {parsed['msg_type']}")

                # 处理心跳
                if parsed['msg_type'] == 0xFF:
                    logger.debug(f"收到心跳: {client_addr}")
                    ack = build_ack(True, "pong")
                    client_socket.sendall(ack)
                    continue

                # 处理业务消息
                result = process_incoming_message(parsed['data'])

                # 发送ACK
                if result.get('status') == 'error':
                    ack = build_ack(False, result.get('error', 'Unknown error'))
                    logger.error(f"消息处理失败: {result.get('error')}")
                else:
                    ack = build_ack(True, "Message processed")
                    summary = _build_message_summary(parsed['data'], result)
                    if result.get('status') == 'skipped':
                        logger.debug(f"消息已跳过: {summary}")
                    else:
                        logger.info(f"消息处理成功: {summary}")

                client_socket.sendall(ack)

            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                ack = build_ack(False, f"Invalid JSON: {str(e)}")
                client_socket.sendall(ack)
            except Exception as e:
                logger.error(f"处理消息异常: {e}", exc_info=True)
                ack = build_ack(False, str(e))
                client_socket.sendall(ack)

    except ConnectionResetError:
        logger.warning(f"连接被重置: {client_addr}")
    except Exception as e:
        logger.error(f"处理客户端时出错: {e}", exc_info=True)
    finally:
        client_socket.close()
        logger.info(f"客户端连接关闭: {client_addr}")


def start_server(host='0.0.0.0', port=61108):
    """启动TCP服务器"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 设置TCP KeepAlive
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if hasattr(socket, 'TCP_KEEPIDLE'):
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
    if hasattr(socket, 'TCP_KEEPINTVL'):
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    if hasattr(socket, 'TCP_KEEPCNT'):
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

    try:
        server_socket.bind((host, port))
        server_socket.listen(50)  # 增加监听队列
        logger.info(f"TCP服务器启动,监听 {host}:{port}")
        logger.info(f"协议版本: 1.0 | 最大消息: {MAX_MESSAGE_SIZE}字节")

        while True:
            client_socket, addr = server_socket.accept()
            logger.info(f"接受来自 {addr} 的连接")

            # 可以在这里添加连接数限制等逻辑
            handle_client(client_socket, addr)

    except KeyboardInterrupt:
        logger.info("服务器关闭(Ctrl+C)")
    except Exception as e:
        logger.error(f"服务器错误: {e}", exc_info=True)
    finally:
        server_socket.close()
        rabbitmq_producer.close()
        logger.info("服务器资源已释放")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 61108
    start_server(port=port)
