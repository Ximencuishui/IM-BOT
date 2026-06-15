from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from models.base_model import Base


class AuditLog(Base):
    """审计日志模型 - 记录管理员的所有重要操作"""
    
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(50), nullable=True)
    action_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action_type': self.action_type,
            'description': self.description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }