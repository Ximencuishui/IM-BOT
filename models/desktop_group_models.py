"""桌面端微信群绑定（多群配置，对齐 sim-bot-node）"""
from sqlalchemy import Column, Integer, String, Text, DateTime, SmallInteger
from sqlalchemy.sql import func
from database.db_config import Base


class WxGroup(Base):
    __tablename__ = 't_wx_groups'

    wx_group_id = Column(String(128), primary_key=True)
    name = Column(String(255))
    manual_owner = Column(String(128))
    group_admin_user_id = Column(Integer)
    expires_at = Column(DateTime)
    last_card_cipher = Column(Text)
    integrity_hash = Column(String(64))
    is_active = Column(SmallInteger, default=1)
    strict_play_routes = Column(SmallInteger, default=0)
    customer_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WxChatroomCache(Base):
    __tablename__ = 't_wx_chatroom_cache'

    room_id = Column(String(128), primary_key=True)
    nick_name = Column(String(255))
    remark = Column(String(255))
    member_count = Column(Integer, default=0)
    owner_wxid = Column(String(128))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
