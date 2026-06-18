"""
歌曲分离工作室 - 数据库模型
包含服务配置、订单、工作流、知识库、问候语、统计等数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, Date, Text, ForeignKey, JSON, Time
from sqlalchemy.dialects.mysql import TINYINT
from database.db_config import Base

__all__ = [
    'StudioServiceConfig', 'StudioOrder', 'StudioWorkflowConfig',
    'StudioWorkflowExecution', 'StudioKnowledgeBase',
    'StudioGreetingConfig', 'StudioStatistics',
]


class StudioServiceConfig(Base):
    """服务类型与定价配置"""
    __tablename__ = 't_studio_service_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    service_name = Column(String(50), nullable=False)
    service_code = Column(String(30), unique=True, nullable=False)
    description = Column(String(500))
    base_price = Column(Numeric(10, 2), default=0.00)
    price_unit = Column(String(20), default='次')
    is_active = Column(TINYINT, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'service_name': self.service_name,
            'service_code': self.service_code,
            'description': self.description,
            'base_price': float(self.base_price) if self.base_price else 0.00,
            'price_unit': self.price_unit,
            'is_active': self.is_active,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class StudioOrder(Base):
    """工作室订单"""
    __tablename__ = 't_studio_order'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False)
    service_code = Column(String(30), nullable=False)
    customer_wx_id = Column(String(100))
    customer_nickname = Column(String(100))
    customer_phone = Column(String(20))
    source_type = Column(String(20), default='group_chat')
    source_group = Column(String(100))
    requirement = Column(Text)
    song_name = Column(String(200))
    song_artist = Column(String(200))
    song_link = Column(String(500))
    file_url = Column(String(500))
    file_name = Column(String(200))
    status = Column(String(30), default='consulting')
    total_amount = Column(Numeric(10, 2), default=0.00)
    paid_amount = Column(Numeric(10, 2), default=0.00)
    result_file_url = Column(String(500))
    remark = Column(String(500))
    workflow_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'service_code': self.service_code,
            'customer_wx_id': self.customer_wx_id,
            'customer_nickname': self.customer_nickname,
            'customer_phone': self.customer_phone,
            'source_type': self.source_type,
            'source_group': self.source_group,
            'requirement': self.requirement,
            'song_name': self.song_name,
            'song_artist': self.song_artist,
            'song_link': self.song_link,
            'file_url': self.file_url,
            'file_name': self.file_name,
            'status': self.status,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0.00,
            'result_file_url': self.result_file_url,
            'remark': self.remark,
            'workflow_id': self.workflow_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class StudioWorkflowConfig(Base):
    """工作流配置"""
    __tablename__ = 't_studio_workflow_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    service_code = Column(String(30), nullable=False)
    workflow_name = Column(String(100), nullable=False)
    workflow_type = Column(String(30), default='auto')
    steps = Column(JSON)
    script_path = Column(String(255))
    is_active = Column(TINYINT, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'service_code': self.service_code,
            'workflow_name': self.workflow_name,
            'workflow_type': self.workflow_type,
            'steps': self.steps,
            'script_path': self.script_path,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class StudioWorkflowExecution(Base):
    """工作流执行记录"""
    __tablename__ = 't_studio_workflow_execution'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey('t_studio_order.id'), nullable=False)
    workflow_id = Column(BigInteger, ForeignKey('t_studio_workflow_config.id'), nullable=False)
    execution_status = Column(String(30), default='pending')
    progress = Column(Integer, default=0)
    log = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'workflow_id': self.workflow_id,
            'execution_status': self.execution_status,
            'progress': self.progress or 0,
            'log': self.log,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StudioKnowledgeBase(Base):
    """知识库"""
    __tablename__ = 't_studio_knowledge_base'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text)
    keywords = Column(JSON)
    category = Column(String(50), default='general')
    source = Column(String(20), default='auto')
    is_resolved = Column(TINYINT, default=0)
    match_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'keywords': self.keywords,
            'category': self.category,
            'source': self.source,
            'is_resolved': self.is_resolved,
            'match_count': self.match_count or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class StudioGreetingConfig(Base):
    """问候语配置"""
    __tablename__ = 't_studio_greeting_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    greeting_text = Column(Text, nullable=False)
    greeting_type = Column(String(20), default='morning')
    send_time = Column(Time)
    target_groups = Column(JSON)
    is_active = Column(TINYINT, default=1)
    is_random = Column(TINYINT, default=0)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'greeting_text': self.greeting_text,
            'greeting_type': self.greeting_type,
            'send_time': self.send_time.strftime('%H:%M:%S') if self.send_time else None,
            'target_groups': self.target_groups,
            'is_active': self.is_active,
            'is_random': self.is_random,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class StudioStatistics(Base):
    """统计汇总"""
    __tablename__ = 't_studio_statistics'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stat_date = Column(Date, nullable=False)
    stat_type = Column(String(20), default='daily')
    service_code = Column(String(30))
    order_count = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0.00)
    completed_count = Column(Integer, default=0)
    cancelled_count = Column(Integer, default=0)
    avg_price = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'stat_date': self.stat_date.isoformat() if self.stat_date else None,
            'stat_type': self.stat_type,
            'service_code': self.service_code,
            'order_count': self.order_count or 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'completed_count': self.completed_count or 0,
            'cancelled_count': self.cancelled_count or 0,
            'avg_price': float(self.avg_price) if self.avg_price else 0.00,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }