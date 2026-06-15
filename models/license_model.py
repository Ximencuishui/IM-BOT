"""
授权码(License)数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from database.db_config import Base


class LegacyLicense(Base):
    """授权码表(旧版)"""
    __tablename__ = 't_license'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='授权ID')
    
    # 授权码信息
    license_code = Column(String(64), unique=True, nullable=False, index=True, comment='授权码(唯一)')
    license_type = Column(String(20), default='monthly', comment='授权类型: monthly-月付, yearly-年付')
    
    # 绑定信息
    bound_to = Column(String(100), comment='绑定对象(微信群ID/销售员ID)')
    machine_id = Column(String(64), comment='绑定机器指纹')
    
    # 有效期
    activated_at = Column(DateTime, comment='激活时间')
    expires_at = Column(DateTime, comment='过期时间')
    
    # 状态
    is_active = Column(Boolean, default=False, comment='是否已激活')
    is_expired = Column(Boolean, default=False, comment='是否已过期')
    is_revoked = Column(Boolean, default=False, comment='是否已撤销')
    
    # 云端同步
    last_sync_at = Column(DateTime, comment='最后同步时间')
    sync_status = Column(String(20), default='pending', comment='同步状态: pending/synced/failed')
    
    # 元数据
    metadata_json = Column(Text, comment='额外元数据JSON')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'license_code': self.license_code,
            'license_type': self.license_type,
            'bound_to': self.bound_to,
            'machine_id': self.machine_id,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired,
            'is_revoked': self.is_revoked,
            'days_remaining': self.days_remaining,
            'status': self.status
        }

    @property
    def days_remaining(self):
        """剩余天数"""
        if not self.expires_at or self.is_revoked:
            return 0
        if not self.is_active:
            return 0
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)

    @property
    def status(self):
        """授权状态"""
        if self.is_revoked:
            return 'revoked'
        if not self.is_active:
            return 'inactive'
        if self.is_expired or self.days_remaining <= 0:
            return 'expired'
        if self.days_remaining <= 7:
            return 'expiring_soon'
        return 'active'

    def check_expiry(self):
        """检查并更新过期状态"""
        if self.is_active and self.expires_at and datetime.now() >= self.expires_at:
            self.is_expired = True
            return True
        return False
