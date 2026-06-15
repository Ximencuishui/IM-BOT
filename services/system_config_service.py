"""
系统配置服务
用于读取和写入通用系统配置项，支持运行时保存 AI 解析配置等。
"""
from typing import Any, Dict, Optional
import logging

from database.db_config import get_db_session
from models.models import SystemConfig

logger = logging.getLogger(__name__)


def get_system_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """从系统配置表中读取单个配置值。"""
    db = get_db_session()
    try:
        config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        return config.config_value if config else default
    except Exception as exc:
        logger.warning(f"读取系统配置 {key} 失败: {exc}")
        return default
    finally:
        db.close()


def set_system_config_value(key: str, value: str, description: Optional[str] = None) -> Dict[str, Any]:
    """保存或更新系统配置项。"""
    db = get_db_session()
    try:
        config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if config:
            config.config_value = value
            if description is not None:
                config.description = description
        else:
            config = SystemConfig(
                config_key=key,
                config_value=value,
                description=description or key
            )
            db.add(config)
            db.flush()
        db.commit()
        db.refresh(config)
        return config.to_dict()
    except Exception as exc:
        db.rollback()
        logger.error(f"保存系统配置 {key} 失败: {exc}")
        raise
    finally:
        db.close()


def get_system_config_dict(prefix: Optional[str] = None) -> Dict[str, str]:
    """读取系统配置表中以 prefix 开头的配置项。"""
    db = get_db_session()
    try:
        query = db.query(SystemConfig)
        if prefix:
            query = query.filter(SystemConfig.config_key.like(f"{prefix}%"))
        configs = query.all()
        return {config.config_key: config.config_value for config in configs}
    except Exception as exc:
        logger.warning(f"读取系统配置字典失败: {exc}")
        return {}
    finally:
        db.close()
