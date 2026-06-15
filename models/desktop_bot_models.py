"""桌面端机器人运行与 SimBot 风格授权表"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database.db_config import Base


class DesktopRobotConfig(Base):
    __tablename__ = 't_desktop_robot_config'

    wxid = Column(String(128), primary_key=True)
    expire_date = Column(String(8), nullable=False)
    last_card_cipher = Column(Text)
    integrity_hash = Column(String(64), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AppSetting(Base):
    __tablename__ = 't_app_settings'

    setting_key = Column(String(128), primary_key=True)
    setting_value = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BotWorkLog(Base):
    __tablename__ = 't_bot_work_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(16), nullable=False, default='info')
    message = Column(String(2000), nullable=False)
    detail_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class CardHistory(Base):
    __tablename__ = 't_card_history'

    card_no = Column(String(64), primary_key=True)
    target_id = Column(String(128), nullable=False)
    used_at = Column(DateTime, server_default=func.now())
