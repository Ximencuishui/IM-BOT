"""
系统配置管理
支持从环境变量和.env文件加载配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """系统配置类"""

    # ==================== 应用基础配置 ====================
    APP_NAME = "本地化配送服务商智能订货统计工具"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # ==================== 数据库配置 ====================
    # 数据库类型: sqlite / mysql (默认sqlite)
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite').lower()

    # SQLite配置 (默认)
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'data/food_delivery.db')

    # MySQL配置 (可选,生产环境使用)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'food_delivery')

    @property
    def DATABASE_URL(self):
        if self.DB_TYPE == 'sqlite':
            # 确保数据目录存在
            import os
            db_dir = os.path.dirname(self.SQLITE_DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            return f"sqlite:///{self.SQLITE_DB_PATH}"
        else:
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # ==================== Redis配置 ====================
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

    @property
    def REDIS_URL(self):
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ==================== RabbitMQ配置 ====================
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
    RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')

    @property
    def RABBITMQ_URL(self):
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"

    # 消息队列名称
    QUEUE_RAW_ORDER = 'order.raw'
    QUEUE_PARSE_FAILURE = 'order.parse.failure'

    # ==================== Elasticsearch配置 ====================
    ES_HOST = os.getenv('ES_HOST', 'localhost')
    ES_PORT = int(os.getenv('ES_PORT', 9200))
    ES_USER = os.getenv('ES_USER', '')
    ES_PASSWORD = os.getenv('ES_PASSWORD', '')

    @property
    def ES_URL(self):
        if self.ES_USER and self.ES_PASSWORD:
            return f"http://{self.ES_USER}:{self.ES_PASSWORD}@{self.ES_HOST}:{self.ES_PORT}"
        return f"http://{self.ES_HOST}:{self.ES_PORT}"

    ES_INDEX = 'raw_messages'

    # ==================== Flask配置 ====================
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

    # ==================== 业务配置 ====================
    # 每日截单时间 (格式: HH:MM)
    CUTOFF_TIME = os.getenv('CUTOFF_TIME', '21:30')

    # 订单解析置信度阈值 (0-1)
    PARSE_CONFIDENCE_THRESHOLD = float(os.getenv('PARSE_CONFIDENCE_THRESHOLD', '0.7'))

    # 消息去重TTL (秒, 默认24小时)
    MESSAGE_DEDUP_TTL = int(os.getenv('MESSAGE_DEDUP_TTL', '86400'))

    # ==================== 日志配置 ====================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # ==================== CORS配置 ====================
    _cors_origins_env = os.getenv('CORS_ORIGINS', '*')
    CORS_ORIGINS = '*' if _cors_origins_env == '*' else [origin.strip() for origin in _cors_origins_env.split(',') if origin.strip()]

    # ==================== 邮件配置 ====================
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL = os.getenv('FROM_EMAIL', '')
    REPORT_RECIPIENTS = os.getenv('REPORT_RECIPIENTS', '')  # 逗号分隔的收件人列表

    # ==================== 授权服务配置 ====================
    LICENSE_API_BASE = os.getenv('LICENSE_API_BASE', 'https://api.fooddelivery.com')

    # ==================== AI 解析配置 (MCP - Model Context Protocol) ====================
    AI_PARSER_ENABLED = os.getenv('AI_PARSER_ENABLED', 'false').lower() == 'true'
    AI_PARSER_PROVIDER = os.getenv('AI_PARSER_PROVIDER', 'none')
    AI_PARSER_API_URL = os.getenv('AI_PARSER_API_URL', '')
    AI_PARSER_API_KEY = os.getenv('AI_PARSER_API_KEY', '')
    AI_PARSER_MODEL = os.getenv('AI_PARSER_MODEL', '')
    AI_PARSER_TIMEOUT = int(os.getenv('AI_PARSER_TIMEOUT', 15))
    AI_PARSER_TEMPERATURE = float(os.getenv('AI_PARSER_TEMPERATURE', 0.3))

    # ==================== VXHook 配置（对齐 sim-bot-node 注入与控制面） ====================
    # 控制面 API（DLL 内置 HTTP，默认 19088）
    HOOK_DLL_HTTP_PORT = int(
        os.getenv('HOOK_DLL_HTTP_PORT', os.getenv('HOOK_HTTP_SERVER_PORT', '19088'))
    )
    HOOK_HTTP_PORT = int(os.getenv('HOOK_HTTP_PORT', str(HOOK_DLL_HTTP_PORT)))
    HOOK_API_TOKEN = os.getenv('HOOK_API_TOKEN', '8888')
    HOOK_BASE_URL = os.getenv(
        'HOOK_API_BASE',
        os.getenv('HOOK_BASE_URL', f'http://127.0.0.1:{HOOK_DLL_HTTP_PORT}')
    ).rstrip('/')

    TCP_HOST = os.getenv('TCP_HOST', '0.0.0.0')
    TCP_PORT = int(os.getenv('TCP_PORT', 61108))
    HOOK_RECEIVE_MODE = os.getenv('HOOK_RECEIVE_MODE', 'http')
    HOOK_CALLBACK_PORT = int(os.getenv('HOOK_CALLBACK_PORT', '0'))
    _default_callback = f'http://127.0.0.1:{FLASK_PORT}/api/recvMsg'
    HOOK_CALLBACK_URL = os.getenv('HOOK_CALLBACK_URL', _default_callback)

    # 旧版 vxhook 推送路径（保留兼容）
    HOOK_CALLBACK_URL_GROUP = os.getenv(
        'HOOK_CALLBACK_URL_GROUP',
        'http://localhost:5000/主动推送的群聊消息'
    )
    HOOK_CALLBACK_URL_PRIVATE = os.getenv(
        'HOOK_CALLBACK_URL_PRIVATE',
        'http://localhost:5000/主动推送的私聊消息'
    )
    HOOK_ENABLED = os.getenv('HOOK_ENABLED', 'true').lower() == 'true'
    BOT_INBOUND_ENABLED = os.getenv('BOT_INBOUND_ENABLED', 'true').lower() == 'true'
    AUTO_WECHAT_INJECT = os.getenv('AUTO_WECHAT_INJECT', '0').lower() == 'true'
    WECHAT_HK_DIR = os.getenv('WECHAT_HK_DIR', '').strip()
    # 桌面端默认冷注入（先关微信再注入，Hook HTTP 服务成功率更高）
    WECHAT_QUIT_BEFORE_INJECT = os.getenv('WECHAT_QUIT_BEFORE_INJECT', '1') == '1'

    # ==================== SimBot 管理平台（桌面端主程序授权） ====================
    SIMBOT_PLATFORM_URL = os.getenv('SIMBOT_PLATFORM_URL', '').strip()
    SIMBOT_PLATFORM_TOKEN = os.getenv('SIMBOT_PLATFORM_TOKEN', '').strip()
    ACTIVATION_PUBLIC_KEY_PATH = os.getenv(
        'ACTIVATION_PUBLIC_KEY',
        os.getenv('ACTIVATION_PUBLIC_KEY_PATH', 'config/activation_public.pem')
    )
    ACTIVATION_CARD_SECRET = os.getenv(
        'ACTIVATION_CARD_SECRET',
        os.getenv('LICENSE_CARD_SECRET', '')
    ).strip()
    SIMBOT_MACHINE_KEY = os.getenv('SIMBOT_MACHINE_KEY', 'tonjclaw-desktop-machine-key')
    SKIP_ROBOT_LICENSE_CHECK = os.getenv('SKIP_ROBOT_LICENSE_CHECK', '0') == '1'

    # Hook 探测超时（秒）：Hook 未启动时避免长时间阻塞请求/重启
    HOOK_PROBE_TIMEOUT = float(os.getenv('HOOK_PROBE_TIMEOUT', '1.5'))
    HOOK_RUNTIME_CACHE_MS = int(os.getenv('HOOK_RUNTIME_CACHE_MS', '5000'))

    # 中间件健康检查超时（秒）
    MIDDLEWARE_HEALTH_TIMEOUT = float(os.getenv('MIDDLEWARE_HEALTH_TIMEOUT', '1.0'))

    # 启动选项：跳过定时任务 / 不打印全部路由（加快桌面端重启）
    SKIP_SCHEDULER = os.getenv('TONJCLAW_SKIP_SCHEDULER', '1') == '1'
    VERBOSE_ROUTE_LOG = os.getenv('TONJCLAW_VERBOSE_ROUTES', '0') == '1'

    # ==================== 飞书API配置 ====================
    FEISHU_APP_ID = os.getenv('FEISHU_APP_ID', '')
    FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')
    FEISHU_BOT_WEBHOOK = os.getenv('FEISHU_BOT_WEBHOOK', '')
    FEISHU_EVENT_SECRET = os.getenv('FEISHU_EVENT_SECRET', '')
    FEISHU_ENCRYPT_KEY = os.getenv('FEISHU_ENCRYPT_KEY', '')
    FEISHU_ENABLED = os.getenv('FEISHU_ENABLED', 'false').lower() == 'true'

    # ==================== 旅行社服务配置 ====================
    TRAVEL_SERVICE_ENABLED = os.getenv('TRAVEL_SERVICE_ENABLED', 'true').lower() == 'true'
    TRAVEL_DAILY_REPORT_TIME = os.getenv('TRAVEL_DAILY_REPORT_TIME', '09:00')
    TRAVEL_AUTO_FORWARD = os.getenv('TRAVEL_AUTO_FORWARD', 'true').lower() == 'true'
    TRAVEL_AUTO_REPLY = os.getenv('TRAVEL_AUTO_REPLY', 'true').lower() == 'true'


# 创建全局配置实例
settings = Settings()
