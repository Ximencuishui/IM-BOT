import json
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class TravelRoute(Base):
    __tablename__ = 't_travel_route'

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), default=0.00)
    start_date = Column(Date)
    group_size = Column(Integer, default=10)
    duration = Column(Integer, default=1)
    route_details = Column(Text)
    highlights = Column(JSON)
    source_url = Column(String(500))
    status = Column(String(20), default='draft')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'route_name': self.route_name,
            'price': float(self.price) if self.price else 0.00,
            'start_date': self.start_date.isoformat() if isinstance(self.start_date, date) else str(self.start_date),
            'group_size': self.group_size or 0,
            'duration': self.duration or 0,
            'route_details': self.route_details,
            'highlights': json.loads(self.highlights) if self.highlights else [],
            'source_url': self.source_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TravelGroup(Base):
    __tablename__ = 't_travel_group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), default='wechat')
    group_id = Column(String(100))
    group_name = Column(String(100))
    boss_wxid = Column(String(100))
    is_active = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'group_id': self.group_id,
            'group_name': self.group_name,
            'boss_wxid': self.boss_wxid,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TravelRegistration(Base):
    __tablename__ = 't_travel_registration'

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey('t_travel_route.id'), nullable=False)
    user_id = Column(String(100))
    user_name = Column(String(100))
    phone = Column(String(20))
    people_count = Column(Integer, default=1)
    status = Column(String(20), default='pending')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'phone': self.phone,
            'people_count': self.people_count or 1,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TravelFeedback(Base):
    __tablename__ = 't_travel_feedback'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('t_travel_group.id'))
    user_id = Column(String(100))
    user_name = Column(String(100))
    content = Column(Text)
    response = Column(Text)
    route_id = Column(Integer, ForeignKey('t_travel_route.id'))
    intent = Column(String(20), default='other')
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'content': self.content,
            'response': self.response,
            'route_id': self.route_id,
            'intent': self.intent,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TravelReplyRule(Base):
    __tablename__ = 't_travel_reply_rule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), nullable=False)
    keyword = Column(String(200))
    pattern = Column(String(500))
    response = Column(Text)
    route_id = Column(Integer, ForeignKey('t_travel_route.id'))
    priority = Column(Integer, default=0)
    is_active = Column(TinyInteger, default=1)
    match_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'keyword': self.keyword,
            'pattern': self.pattern,
            'response': self.response,
            'route_id': self.route_id,
            'priority': self.priority,
            'is_active': self.is_active,
            'match_count': self.match_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }