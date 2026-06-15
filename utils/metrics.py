"""
Prometheus监控指标
- 请求指标(QPS、响应时间、错误率)
- 业务指标(订单数、消息数、解析成功率)
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import threading
import time
import logging

logger = logging.getLogger(__name__)

# ==================== HTTP请求指标 ====================

# 请求总数 (按方法和状态码分类)
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟直方图
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# 当前活跃请求数
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Current number of HTTP requests in progress',
    ['method', 'endpoint']
)


# ==================== 消息处理指标 ====================

# 接收消息总数
messages_received_total = Counter(
    'messages_received_total',
    'Total messages received from WeChat Hook'
)

# 重复消息数
messages_duplicated_total = Counter(
    'messages_duplicated_total',
    'Total duplicated messages skipped'
)

# 消息队列推送成功/失败数
messages_queued_total = Counter(
    'messages_queued_total',
    'Total messages pushed to RabbitMQ',
    ['status']  # success / failure
)

# ES存储成功/失败数
messages_stored_total = Counter(
    'messages_stored_total',
    'Total messages stored to Elasticsearch',
    ['status']  # success / failure
)


# ==================== 订单处理指标 ====================

# 订单创建总数
orders_created_total = Counter(
    'orders_created_total',
    'Total orders created',
    ['source']  # wechat / manual / api
)

# 订单解析成功/失败数
orders_parsed_total = Counter(
    'orders_parsed_total',
    'Total order parsing results',
    ['result']  # success / failure
)

# 解析置信度分布
parse_confidence_histogram = Histogram(
    'parse_confidence_histogram',
    'Distribution of parsing confidence scores',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# 当前待处理订单数
orders_pending_gauge = Gauge(
    'orders_pending_gauge',
    'Current number of pending orders'
)


# ==================== 数据库连接指标 ====================

# 数据库连接池状态
db_connections_active = Gauge(
    'db_connections_active',
    'Current number of active database connections'
)

db_connections_pool_size = Gauge(
    'db_connections_pool_size',
    'Current database connection pool size'
)


# ==================== 中间件健康指标 ====================

# Redis连接状态
redis_connection_status = Gauge(
    'redis_connection_status',
    'Redis connection status (1=connected, 0=disconnected)'
)

# RabbitMQ连接状态
rabbitmq_connection_status = Gauge(
    'rabbitmq_connection_status',
    'RabbitMQ connection status (1=connected, 0=disconnected)'
)

# Elasticsearch连接状态
elasticsearch_connection_status = Gauge(
    'elasticsearch_connection_status',
    'Elasticsearch connection status (1=connected, 0=disconnected)'
)


# ==================== Prometheus Flask中间件 ====================

def prometheus_middleware(f):
    """
    Prometheus监控装饰器
    用于Flask路由,自动记录请求指标
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        endpoint = f.__name__
        method = kwargs.get('method', 'GET')

        # 记录活跃请求
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # 记录请求延迟
        start_time = time.time()

        try:
            response = f(*args, **kwargs)
            status = response[1] if isinstance(response, tuple) else 200
            return response
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time.time() - start_time

            # 记录指标
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()

    return decorated_function


def generate_metrics_response():
    """
    生成Prometheus指标响应
    用于 /metrics 端点
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# ==================== 健康检查辅助函数 ====================

def check_middleware_health() -> dict:
    """
    检查中间件健康状态

    Returns:
        {
            "redis": bool,
            "rabbitmq": bool,
            "elasticsearch": bool,
            "database": bool
        }
    """
    health = {
        'redis': False,
        'rabbitmq': False,
        'elasticsearch': False,
        'database': False
    }

    from config.settings import settings
    timeout = getattr(settings, 'MIDDLEWARE_HEALTH_TIMEOUT', 1.0)

    def _check_redis():
        try:
            import redis
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                socket_connect_timeout=timeout,
                socket_timeout=timeout,
            )
            r.ping()
            health['redis'] = True
            redis_connection_status.set(1)
        except Exception as e:
            logger.warning(f"Redis健康检查失败: {e}")
            redis_connection_status.set(0)

    def _check_rabbitmq():
        try:
            import pika
            credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                connection_attempts=1,
                socket_timeout=timeout,
            )
            connection = pika.BlockingConnection(parameters)
            connection.close()
            health['rabbitmq'] = True
            rabbitmq_connection_status.set(1)
        except Exception as e:
            logger.warning(f"RabbitMQ健康检查失败: {e}")
            rabbitmq_connection_status.set(0)

    def _check_elasticsearch():
        try:
            from elasticsearch import Elasticsearch
            es = Elasticsearch([settings.ES_URL])
            es.cluster.health(request_timeout=timeout)
            health['elasticsearch'] = True
            elasticsearch_connection_status.set(1)
        except Exception as e:
            logger.warning(f"Elasticsearch健康检查失败: {e}")
            elasticsearch_connection_status.set(0)

    def _check_database():
        try:
            from database.db_config import engine
            with engine.connect() as conn:
                conn.execute(__import__('sqlalchemy').text("SELECT 1"))
            health['database'] = True
        except Exception as e:
            logger.warning(f"Database健康检查失败: {e}")

    checks = [_check_redis, _check_rabbitmq, _check_elasticsearch, _check_database]
    threads = []
    for check in checks:
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        threads.append(thread)

    deadline = time.time() + timeout
    for thread in threads:
        remaining = max(0, deadline - time.time())
        thread.join(remaining)

    return health
