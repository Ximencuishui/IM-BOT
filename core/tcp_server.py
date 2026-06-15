import socket
import struct


def handle_client(client_socket):
    try:
        while True:
            # 读取消息长度（前4个字节）
            header = client_socket.recv(4)
            if not header:
                print("客户端断开连接")
                break

            print(f"收到头部: {header.hex()}")  # 打印16进制

            if len(header) < 4:
                print(f"头部不完整，只有 {len(header)} 字节")
                break

            # 修正：使用大端序解包（网络字节序）
            try:
                msg_length = struct.unpack('>I', header)[0]  # 改为大端序
                print(f"解析消息长度: {msg_length}")

            except Exception as e:
                print(f"解包头部失败: {e}")
                break

            # 限制最大消息长度防止攻击
            if msg_length > 10 * 1024 * 1024:  # 10MB
                print(f"消息过长: {msg_length}，断开连接")
                break

            print(f"开始接收消息体，长度: {msg_length}")

            # 读取消息内容
            chunks = []
            bytes_received = 0
            while bytes_received < msg_length:
                remaining = msg_length - bytes_received
                chunk = client_socket.recv(min(remaining, 4096))
                if not chunk:
                    print("客户端在发送完整消息前断开连接")
                    break
                chunks.append(chunk)
                bytes_received += len(chunk)
                print(f"已接收 {bytes_received}/{msg_length} 字节")

            if bytes_received < msg_length:
                print(f"消息不完整，期望 {msg_length}，实际收到 {bytes_received}")
                break

            message = b''.join(chunks)
            print(f"完整消息内容: {message.decode('utf-8', errors='replace')}")
            print("-" * 50)

    except Exception as e:
        print(f"处理客户端时出错: {e}")
    finally:
        client_socket.close()

def start_server(host='0.0.0.0', port=61108):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"服务器启动，监听 {host}:{port}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"接受来自 {addr} 的连接")
            handle_client(client_socket)

    except KeyboardInterrupt:
        print("服务器关闭")
    except Exception as e:
        print(f"服务器错误: {e}")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_server()