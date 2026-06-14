"""
消息处理服务
- 消息去重
- RabbitMQ推送
- Elasticsearch写入
"""
import json
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional, Tuple
import pika
import redis
from elasticsearch import Elasticsearch
from config.settings import settings

logger = logging.getLogger(__name__)
# 降低第三方库重试日志噪音（连接失败时避免滚屏）
logging.getLogger("elastic_transport").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)


class MessageDeduplicator:
    """消息去重器 - 基于Redis SET"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.ttl = settings.MESSAGE_DEDUP_TTL
        self._degraded = False

    def generate_message_hash(self, group_id: str, sender: str, content: str, timestamp: int) -> str:
        """生成消息指纹"""
        raw = f"{group_id}:{sender}:{content}:{timestamp}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def is_duplicate(self, message_hash: str) -> bool:
        """检查消息是否重复"""
        if self.redis_client is None:
            return False

        try:
            return not self.redis_client.set(message_hash, "1", nx=True, ex=self.ttl)
        except Exception as e:
            if not self._degraded:
                logger.warning(f"Redis去重不可用，已降级跳过去重: {e}")
            self._degraded = True
            self.redis_client = None
            return False  # Redis失败时允许通过,避免阻塞

    def mark_processed(self, message_hash: str):
        """标记消息已处理"""
        if self.redis_client is None:
            return

        try:
            self.redis_client.set(message_hash, "processed", ex=self.ttl)
        except Exception as e:
            if not self._degraded:
                logger.warning(f"Redis标记不可用，已降级: {e}")
            self._degraded = True
            self.redis_client = None


class RabbitMQProducer:
    """RabbitMQ生产者"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        """建立RabbitMQ连接"""
        try:
            credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # 声明队列
            self.channel.queue_declare(queue=settings.QUEUE_RAW_ORDER, durable=True)
            self.channel.queue_declare(queue=settings.QUEUE_PARSE_FAILURE, durable=True)

            logger.info("RabbitMQ连接成功")
        except Exception as e:
            logger.error(f"RabbitMQ连接失败: {e}")
            raise

    def publish(self, message: dict, routing_key: str = None) -> bool:
        """发布消息到队列"""
        if routing_key is None:
            routing_key = settings.QUEUE_RAW_ORDER

        try:
            if not self.connection or self.connection.is_closed:
                self._connect()

            self.channel.basic_publish(
                exchange='',
                routing_key=routing_key,
                body=json.dumps(message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # 持久化
                    content_type='application/json'
                )
            )
            logger.debug(f"消息已发布到队列: {routing_key}")
            return True
        except Exception as e:
            logger.error(f"发布消息失败: {e}")
            try:
                self._connect()
            except:
                pass
            return False

    def close(self):
        """关闭连接"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()


class ElasticsearchWriter:
    """Elasticsearch写入器"""

    def __init__(self):
        if settings.ES_USER and settings.ES_PASSWORD:
            self.es = Elasticsearch(
                [settings.ES_URL],
                basic_auth=(settings.ES_USER, settings.ES_PASSWORD),
                request_timeout=1,
                max_retries=0,
                retry_on_timeout=False
            )
        else:
            self.es = Elasticsearch(
                [settings.ES_URL],
                request_timeout=1,
                max_retries=0,
                retry_on_timeout=False
            )

        self.index = settings.ES_INDEX
        self._degraded = False
        self._ensure_index()

    def _ensure_index(self):
        """确保索引存在"""
        if self.es is None:
            return

        try:
            if not self.es.indices.exists(index=self.index):
                self.es.indices.create(index=self.index)
                logger.info(f"Elasticsearch索引创建成功: {self.index}")
        except Exception as e:
            if not self._degraded:
                logger.warning(f"Elasticsearch不可用，已降级跳过存储: {e}")
            self._degraded = True
            self.es = None

    def write(self, document: dict) -> bool:
        """写入文档"""
        if self.es is None:
            return False

        try:
            result = self.es.index(index=self.index, document=document)
            logger.debug(f"ES写入成功: {result['_id']}")
            return True
        except Exception as e:
            if not self._degraded:
                logger.warning(f"ES写入不可用，已降级停止写入: {e}")
            self._degraded = True
            self.es = None
            return False


# 全局单例（懒加载）
_deduplicator = None
_rabbitmq_producer = None
_es_writer = None


def get_deduplicator():
    """获取消息去重器实例（懒加载）"""
    global _deduplicator
    if _deduplicator is None:
        try:
            _deduplicator = MessageDeduplicator()
        except Exception as e:
            logger.warning(f"Redis连接失败，去重功能将不可用: {e}")
            _deduplicator = MessageDeduplicator.__new__(MessageDeduplicator)
            _deduplicator.redis_client = None
    return _deduplicator


def get_rabbitmq_producer():
    """获取RabbitMQ生产者实例（懒加载）"""
    global _rabbitmq_producer
    if _rabbitmq_producer is None:
        try:
            _rabbitmq_producer = RabbitMQProducer()
        except Exception as e:
            logger.warning(f"RabbitMQ连接失败，消息推送功能将不可用: {e}")
            _rabbitmq_producer = RabbitMQProducer.__new__(RabbitMQProducer)
            _rabbitmq_producer.connection = None
            _rabbitmq_producer.channel = None
    return _rabbitmq_producer


def get_es_writer():
    """获取Elasticsearch写入器实例（懒加载）"""
    global _es_writer
    if _es_writer is None:
        try:
            _es_writer = ElasticsearchWriter()
        except Exception as e:
            logger.warning(f"Elasticsearch连接失败，日志存储功能将不可用: {e}")
            _es_writer = ElasticsearchWriter.__new__(ElasticsearchWriter)
            _es_writer.es = None
    return _es_writer


def _desktop_inbound_allowed() -> bool:
    try:
        from database.db_config import get_db_session
        from services.bot_runtime_store import get_bot_inbound_enabled
        from services.desktop_robot_store import is_robot_license_valid

        db = get_db_session()
        try:
            if not get_bot_inbound_enabled(db):
                return False
            return is_robot_license_valid(db)
        finally:
            db.close()
    except Exception:
        return settings.BOT_INBOUND_ENABLED


def process_incoming_message(raw_data: dict) -> dict:
    """
    处理接收到的Hook消息

    Args:
        raw_data: Hook发送的原始JSON数据，支持两种格式:
                 1. 直接包含 group_id, sender, content 等字段
                 2. 包含 JsApiResponse 的复杂结构
                 3. sim-bot 风格原始字段（fromUserName / real_content 等，经归一化）

    Returns:
        处理结果字典
    """
    from utils.hook_recv_normalize import normalize_hook_inbound_payload

    result = {
        'status': 'success',
        'duplicated': False,
        'queued': False,
        'stored': False,
        'rule_applied': False,
        'order_created': False,
        'handled': False,
        'skipped': False
    }

    try:
        if not _desktop_inbound_allowed():
            result['status'] = 'skipped'
            result['skipped'] = True
            result['skip_reason'] = 'inbound_disabled_or_license_invalid'
            return result

        if not raw_data:
            result['status'] = 'skipped'
            result['skipped'] = True
            result['skip_reason'] = 'empty_payload'
            return result

        normalized_payload = normalize_hook_inbound_payload(raw_data)
        if normalized_payload is not None:
            raw_data = normalized_payload

        # 检查是否是简单的消息格式（来自 hook_callback）
        if 'group_id' in raw_data and 'sender' in raw_data and 'content' in raw_data:
            # 简单格式，直接处理
            _process_single_message(raw_data, result)
        elif 'JsApiResponse' in raw_data:
            # JsApiResponse 复杂结构
            msg_list = []
            try:
                resp_json = json.loads(raw_data['JsApiResponse']['RespJson'])
                msg_list = resp_json.get('msg_list', [])
            except Exception:
                msg_list = []

            if msg_list:
                for msg in msg_list:
                    _process_single_message(msg, result)
            else:
                result['skipped'] = True
                result['skip_reason'] = 'empty_msg_list'
        elif isinstance(raw_data.get('msg_list'), list):
            # 直接包含 msg_list 的结构
            msg_list = raw_data.get('msg_list', [])
            if msg_list:
                for msg in msg_list:
                    _process_single_message(msg, result)
            else:
                result['skipped'] = True
                result['skip_reason'] = 'empty_msg_list'
        else:
            # 其他结构按单条消息处理
            _process_single_message(raw_data, result)

        if not result.get('handled') and result.get('skipped'):
            result['status'] = 'skipped'

        return result

    except Exception as e:
        logger.error(f"处理消息异常: {e}", exc_info=True)
        result['status'] = 'error'
        result['error'] = str(e)
        return result


def _process_single_message(msg: dict, result: dict):
    """处理单条消息"""
    try:
        normalized, skip_reason = _normalize_wechat_message(msg)
        if skip_reason:
            result['skipped'] = True
            result['skip_reason'] = skip_reason
            logger.debug(f"跳过消息处理: {skip_reason}")
            return

        group_id = normalized['group_id']
        sender = normalized['sender']
        content = normalized['content']
        timestamp = normalized['timestamp']

        if not content:
            result['skipped'] = True
            result['skip_reason'] = 'empty_content'
            logger.warning("消息内容为空,跳过处理")
            return

        result['handled'] = True

        if normalized.get('is_group') and group_id:
            try:
                from database.db_config import get_db_session
                from services.desktop_group_store import is_group_service_valid

                db = get_db_session()
                try:
                    if not is_group_service_valid(db, group_id):
                        result['skipped'] = True
                        result['skip_reason'] = 'group_not_licensed_or_expired'
                        logger.info('群未绑定或授权已过期，跳过: %s', group_id)
                        return
                finally:
                    db.close()
            except Exception as exc:
                logger.debug('群授权检查跳过: %s', exc)

        matched_rule = _match_parse_rule(content)
        if matched_rule:
            result['rule_applied'] = True

        # 生成消息指纹
        dedup = get_deduplicator()
        if dedup.redis_client:  # 检查Redis是否可用
            message_hash = dedup.generate_message_hash(group_id, sender, content, timestamp)

            # 去重检查
            if dedup.is_duplicate(message_hash):
                logger.info(f"重复消息,跳过: {message_hash[:8]}")
                result['duplicated'] = True
                return
        else:
            message_hash = None

        # 构建标准化消息
        standardized_msg = {
            'group_id': group_id,
            'sender': sender,
            'content': content,
            'timestamp': timestamp,
            'received_at': datetime.now().isoformat(),
            'message_hash': message_hash,
            'sender_wxid': normalized['sender_wxid'],
            'msg_type': normalized['msg_type'],
            'event_type': normalized['event_type'],
            'message_id': normalized['message_id'],
            'is_group': normalized['is_group'],
            'raw_data': msg
        }

        # 推送到RabbitMQ
        producer = get_rabbitmq_producer()
        if producer.connection and producer.publish(standardized_msg):
            result['queued'] = True

        # 写入Elasticsearch
        es_writer = get_es_writer()
        es_doc = {
            **standardized_msg,
            'raw_data': msg,
            '@timestamp': datetime.now().isoformat()
        }
        if es_writer.es and es_writer.write(es_doc):
            result['stored'] = True

        order_result = _try_create_order_from_message(standardized_msg, matched_rule)
        if order_result.get('created'):
            result['order_created'] = True
            result['order_id'] = order_result.get('order_id')
            result['parse_confidence'] = order_result.get('confidence')
        elif order_result.get('reason'):
            result['order_skip_reason'] = order_result.get('reason')

        # 标记为已处理
        if message_hash and dedup.redis_client:
            dedup.mark_processed(message_hash)

        logger.info(f"消息处理成功: {sender} - {content[:50]}")

    except Exception as e:
        logger.error(f"处理单条消息失败: {e}", exc_info=True)


def _extract_wechat_string(value) -> str:
    """提取微信结构中的字符串字段"""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        maybe = value.get('String')
        if isinstance(maybe, str):
            return maybe
    return ''


def _normalize_wechat_message(msg: dict) -> Tuple[Optional[dict], Optional[str]]:
    """
    将Hook消息标准化为统一结构
    返回: (标准化消息, 跳过原因)
    """
    if not isinstance(msg, dict):
        return None, '消息不是JSON对象'

    # 兼容已有标准格式
    if 'group_id' in msg and 'sender' in msg and 'content' in msg:
        content = msg.get('content')
        if isinstance(content, dict):
            content = _extract_wechat_string(content)
        return {
            'group_id': msg.get('group_id') or '',
            'sender': msg.get('sender') or '',
            'sender_wxid': msg.get('sender_wxid') or '',
            'content': str(content or '').strip(),
            'timestamp': int(msg.get('timestamp') or int(datetime.now().timestamp())),
            'msg_type': msg.get('msg_type'),
            'event_type': msg.get('event_type'),
            'message_id': msg.get('new_msg_id') or msg.get('msg_id') or msg.get('msgId') or msg.get('newMsgId'),
            'is_group': bool(msg.get('group_id')),
        }, None

    event_type = msg.get('event_type')
    msg_type = msg.get('msgType')
    recive_type = msg.get('recive_type', '')

    # 只处理文本消息；登录、状态通知等事件直接跳过
    content = msg.get('real_content') or _extract_wechat_string(msg.get('content')) or msg.get('msg') or ''
    content = str(content).strip()
    is_text_message = bool(content) and (msg_type in (1, None) or '文本' in str(recive_type))

    if not is_text_message:
        return None, f'非文本消息 event_type={event_type}, msgType={msg_type}'

    from_user = _extract_wechat_string(msg.get('fromUserName')) or msg.get('fromUserName') or ''
    sender_profile = msg.get('sender_profile') if isinstance(msg.get('sender_profile'), dict) else {}
    sender_nick = (
        _extract_wechat_string(sender_profile.get('nickName'))
        or msg.get('sender_nick')
        or msg.get('nickname')
        or _extract_wechat_string(msg.get('fromUserName'))
    )
    sender_wxid = (
        _extract_wechat_string(sender_profile.get('userName'))
        or sender_profile.get('friendUserName')
        or _extract_wechat_string(msg.get('fromUserName'))
    )

    is_group = str(from_user).endswith('@chatroom') or '群' in str(recive_type)
    group_id = from_user if is_group else (msg.get('group_id') or msg.get('roomid') or '')
    timestamp = int(msg.get('createTime') or msg.get('timestamp') or int(datetime.now().timestamp()))

    return {
        'group_id': str(group_id or ''),
        'sender': str(sender_nick or sender_wxid or '未知发送者'),
        'sender_wxid': str(sender_wxid or ''),
        'content': content,
        'timestamp': timestamp,
        'msg_type': msg_type,
        'event_type': event_type,
        'message_id': msg.get('newMsgId') or msg.get('msgId'),
        'is_group': is_group,
    }, None


def _match_parse_rule(content: str) -> Optional[dict]:
    """按优先级匹配解析规则（regex / keyword）"""
    try:
        from database.db_config import get_db_session
        from models.user_models import ParseRule

        db = get_db_session()
        try:
            rules = db.query(ParseRule).filter(ParseRule.is_active == True).order_by(ParseRule.priority.desc()).all()
            for rule in rules:
                pattern = (rule.pattern or '').strip()
                if not pattern:
                    continue

                if rule.rule_type == 'regex':
                    if re.search(pattern, content):
                        return rule.to_dict()
                    continue

                if rule.rule_type == 'keyword':
                    keywords = []
                    try:
                        parsed = json.loads(pattern)
                        if isinstance(parsed, dict):
                            keywords = parsed.get('keywords', [])
                        elif isinstance(parsed, list):
                            keywords = parsed
                    except Exception:
                        keywords = [k.strip() for k in pattern.split(',') if k.strip()]

                    if any(str(keyword) in content for keyword in keywords):
                        return rule.to_dict()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"匹配解析规则失败，降级到默认解析: {e}")

    return None


def _try_create_order_from_message(message: dict, matched_rule: Optional[dict]) -> dict:
    """根据消息尝试自动创建订单（规则匹配+解析）"""
    content = message.get('content', '').strip()
    if not content:
        return {'created': False, 'reason': 'empty_content'}

    try:
        from services.order_parser import parse_order_message
        from services.customer_service import customer_service
        from services.order_service import order_service

        parse_result = parse_order_message(content)
        if not parse_result.get('success'):
            return {'created': False, 'reason': f"parse_failed:{parse_result.get('error', 'unknown')}"}

        confidence = float(parse_result.get('confidence') or 0)
        if confidence < settings.PARSE_CONFIDENCE_THRESHOLD:
            return {'created': False, 'reason': f'low_confidence:{confidence}'}

        customer = None
        if message.get('group_id'):
            customer = customer_service.get_customer_by_wx_group(message['group_id'])
        if not customer and message.get('sender_wxid'):
            customer = customer_service.get_customer_by_wx_group(message['sender_wxid'])
        if not customer:
            return {'created': False, 'reason': 'customer_not_bound'}

        remark_parts = []
        if parse_result.get('remarks'):
            remark_parts.append(', '.join(parse_result['remarks']))
        if matched_rule:
            remark_parts.append(f"规则:{matched_rule.get('rule_name')}")

        create_result = order_service.create_or_update_order(
            customer_id=customer['id'],
            items=parse_result['items'],
            remark=' | '.join(remark_parts) if remark_parts else None,
            source_type='wechat'
        )

        if create_result.get('success'):
            return {
                'created': True,
                'order_id': create_result.get('order_id'),
                'confidence': confidence
            }
        return {'created': False, 'reason': f"create_order_failed:{create_result.get('error', 'unknown')}"}
    except Exception as e:
        logger.error(f"自动建单失败: {e}", exc_info=True)
        return {'created': False, 'reason': f'exception:{str(e)}'}


# 兼容旧代码导入方式: from services.message_service import rabbitmq_producer
rabbitmq_producer = get_rabbitmq_producer()
