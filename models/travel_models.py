"""
旅行社服务数据模型
"""
import json
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class TravelRoute(Base):
    """旅游线路表"""
    __tablename__ = 't_travel_route'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='线路ID')
    route_name = Column(String(200), nullable=False, comment='线路名称')
    price = Column(Numeric(10, 2), default=0.00, comment='价格')
    start_date = Column(Date, comment='出发时间')
    group_size = Column(Integer, default=10, comment='成团人数要求')
    duration = Column(Integer, default=1, comment='行程天数')
    route_details = Column(Text, comment='具体线路描述')
    highlights = Column(JSON, comment='特色亮点列表')
    source_url = Column(String(500), comment='来源链接')
    status = Column(String(20), default='draft', comment='状态：draft/published/closed')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """旅游群配置表"""
    __tablename__ = 't_travel_group'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='群ID')
    platform = Column(String(20), default='wechat', comment='平台：wechat/feishu')
    group_id = Column(String(100), comment='平台群ID')
    group_name = Column(String(100), comment='群名称')
    boss_wxid = Column(String(100), comment='老板微信/飞书ID')
    is_active = Column(TinyInteger, default=1, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """报名记录表"""
    __tablename__ = 't_travel_registration'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='报名ID')
    route_id = Column(Integer, ForeignKey('t_travel_route.id'), nullable=False, comment='线路ID')
    user_id = Column(String(100), comment='用户微信/飞书ID')
    user_name = Column(String(100), comment='用户姓名')
    phone = Column(String(20), comment='联系电话')
    people_count = Column(Integer, default=1, comment='报名人数')
    status = Column(String(20), default='pending', comment='状态：pending/confirmed/payed/cancelled')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """群反馈表"""
    __tablename__ = 't_travel_feedback'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='反馈ID')
    group_id = Column(Integer, ForeignKey('t_travel_group.id'), comment='群ID')
    user_id = Column(String(100), comment='用户ID')
    user_name = Column(String(100), comment='用户姓名')
    content = Column(Text, comment='反馈内容')
    response = Column(Text, comment='回复内容')
    route_id = Column(Integer, ForeignKey('t_travel_route.id'), comment='关联线路ID')
    intent = Column(String(20), default='other', comment='意图：inquiry/complaint/registration/other')
    status = Column(String(20), default='pending', comment='状态：pending/responded/escalated')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """自动回复规则表"""
    __tablename__ = 't_travel_reply_rule'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='规则ID')
    rule_name = Column(String(100), nullable=False, comment='规则名称')
    keyword = Column(String(200), comment='触发关键词')
    pattern = Column(String(500), comment='正则表达式')
    response = Column(Text, comment='回复内容')
    route_id = Column(Integer, ForeignKey('t_travel_route.id'), comment='关联线路ID(可选)')
    priority = Column(Integer, default=0, comment='优先级')
    is_active = Column(TinyInteger, default=1, comment='是否启用')
    match_count = Column(Integer, default=0, comment='匹配次数')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
