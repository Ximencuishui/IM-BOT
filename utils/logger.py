"""
日志配置工具
- 结构化日志
- 日志轮转
- 多级别输出
"""
import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from config.settings import settings


def setup_logger(name: str = None, level: str = None) -> logging.Logger:
    """
    配置日志器

    Args:
        name: 日志器名称
        level: 日志级别

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name or __name__)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    log_level = getattr(logging, level or settings.LOG_LEVEL)
    logger.setLevel(log_level)

    # 日志格式
    detailed_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_format)
    logger.addHandler(console_handler)

    # 确保日志目录存在
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    # 文件处理器 - 所有级别 (按天轮转,保留30天)
    all_log_file = os.path.join(settings.LOG_DIR, 'app.log')
    file_handler = TimedRotatingFileHandler(
        all_log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8',
        delay=True,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_format)
    file_handler.suffix = '%Y%m%d'
    logger.addHandler(file_handler)

    # 错误日志文件 (单独记录ERROR及以上级别)
    error_log_file = os.path.join(settings.LOG_DIR, 'error.log')
    error_handler = TimedRotatingFileHandler(
        error_log_file,
        when='midnight',
        interval=1,
        backupCount=90,  # 错误日志保留更久
        encoding='utf-8',
        delay=True,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    error_handler.suffix = '%Y%m%d'
    logger.addHandler(error_handler)

    # 业务日志文件 (单独记录订单相关业务日志)
    business_log_file = os.path.join(settings.LOG_DIR, 'business.log')
    business_handler = TimedRotatingFileHandler(
        business_log_file,
        when='midnight',
        interval=1,
        backupCount=60,
        encoding='utf-8',
        delay=True,
    )
    business_handler.setLevel(logging.INFO)
    business_handler.setFormatter(detailed_format)
    business_handler.suffix = '%Y%m%d'

    # 创建专门的业务日志器
    business_logger = logging.getLogger('business')
    business_logger.setLevel(logging.INFO)
    business_logger.addHandler(business_handler)
    business_logger.propagate = False  # 不传播到根日志器

    return logger


class BusinessLogger:
    """业务日志助手 - 用于记录关键业务操作"""

    def __init__(self):
        self.logger = logging.getLogger('business')

    def log_order_created(self, order_id: int, customer_id: int, total_amount: float):
        """记录订单创建"""
        self.logger.info(f"ORDER_CREATED | order_id={order_id} | customer_id={customer_id} | amount={total_amount}")

    def log_order_cancelled(self, order_id: int, reason: str):
        """记录订单取消"""
        self.logger.warning(f"ORDER_CANCELLED | order_id={order_id} | reason={reason}")

    def log_message_parsed(self, sender: str, content: str, confidence: float):
        """记录消息解析"""
        self.logger.info(f"MESSAGE_PARSED | sender={sender} | confidence={confidence} | content={content[:50]}")

    def log_parse_failure(self, sender: str, content: str, error: str):
        """记录解析失败"""
        self.logger.error(f"PARSE_FAILURE | sender={sender} | error={error} | content={content[:100]}")


# 全局实例
business_logger = BusinessLogger()
