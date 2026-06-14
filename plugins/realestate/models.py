"""
房产中介行业插件数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.db_config import Base


class RealEstateProperty(Base):
    """房源表"""
    __tablename__ = 't_realestate_property'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_name = Column(String(100), nullable=False, index=True)
    property_type = Column(String(20), index=True)
    area = Column(Float, comment='面积(平米)')
    price = Column(Float, comment='价格(万)')
    location = Column(String(200))
    district = Column(String(50), index=True)
    bedroom_count = Column(Integer, comment='卧室数')
    bathroom_count = Column(Integer, comment='卫生间数')
    floor = Column(String(20))
    total_floor = Column(Integer)
    orientation = Column(String(20), comment='朝向')
    decoration = Column(String(20), comment='装修情况')
    age = Column(Integer, comment='房龄(年)')
    description = Column(String(500))
    images = Column(Text, comment='图片URL列表JSON')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    matches = relationship('RealEstateMatch', back_populates='property')
    viewings = relationship('RealEstateViewing', back_populates='property')
    transactions = relationship('RealEstateTransaction', back_populates='property')

    def to_dict(self):
        return {
            'id': self.id,
            'property_name': self.property_name,
            'property_type': self.property_type,
            'area': float(self.area) if self.area else 0.0,
            'price': float(self.price) if self.price else 0.0,
            'location': self.location,
            'district': self.district,
            'bedroom_count': self.bedroom_count,
            'bathroom_count': self.bathroom_count,
            'floor': self.floor,
            'total_floor': self.total_floor,
            'orientation': self.orientation,
            'decoration': self.decoration,
            'age': self.age,
            'description': self.description,
            'images': self.images,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RealEstateCustomer(Base):
    """客户表"""
    __tablename__ = 't_realestate_customer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    wechat_id = Column(String(100))
    demand = Column(String(500), comment='需求描述')
    budget_min = Column(Float, comment='预算下限(万)')
    budget_max = Column(Float, comment='预算上限(万)')
    preferred_area = Column(String(200), comment='偏好区域')
    preferred_type = Column(String(20), comment='偏好房型')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    matches = relationship('RealEstateMatch', back_populates='customer')
    viewings = relationship('RealEstateViewing', back_populates='customer')
    transactions = relationship('RealEstateTransaction', back_populates='customer')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'wechat_id': self.wechat_id,
            'demand': self.demand,
            'budget_min': float(self.budget_min) if self.budget_min else 0.0,
            'budget_max': float(self.budget_max) if self.budget_max else 0.0,
            'preferred_area': self.preferred_area,
            'preferred_type': self.preferred_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RealEstateAgent(Base):
    """经纪人表"""
    __tablename__ = 't_realestate_agent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    department = Column(String(50))
    team = Column(String(50))
    avatar = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'agent_name': self.agent_name,
            'phone': self.phone,
            'department': self.department,
            'team': self.team,
            'avatar': self.avatar,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RealEstateMatch(Base):
    """匹配记录表"""
    __tablename__ = 't_realestate_match'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('t_realestate_customer.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('t_realestate_property.id'), nullable=False, index=True)
    match_score = Column(Float, comment='匹配分数(0-100)')
    matched_at = Column(DateTime, default=datetime.now)

    customer = relationship('RealEstateCustomer', back_populates='matches')
    property = relationship('RealEstateProperty', back_populates='matches')

    __table_args__ = (Index('idx_customer_property', 'customer_id', 'property_id', unique=True),)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'property_id': self.property_id,
            'match_score': float(self.match_score) if self.match_score else 0.0,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None
        }


class RealEstateViewing(Base):
    """带看记录表"""
    __tablename__ = 't_realestate_viewing'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('t_realestate_customer.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('t_realestate_property.id'), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey('t_realestate_agent.id'), index=True)
    viewing_date = Column(DateTime, default=datetime.now)
    feedback = Column(String(500), comment='客户反馈')
    rating = Column(Integer, comment='满意度(1-5)')

    customer = relationship('RealEstateCustomer', back_populates='viewings')
    property = relationship('RealEstateProperty', back_populates='viewings')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'property_id': self.property_id,
            'agent_id': self.agent_id,
            'viewing_date': self.viewing_date.isoformat() if self.viewing_date else None,
            'feedback': self.feedback,
            'rating': self.rating
        }


class RealEstateTransaction(Base):
    """交易表"""
    __tablename__ = 't_realestate_transaction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('t_realestate_customer.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('t_realestate_property.id'), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey('t_realestate_agent.id'), index=True)
    amount = Column(Float, comment='交易金额(万)')
    status = Column(String(20), default='pending')
    contract_date = Column(DateTime)
    completion_date = Column(DateTime)

    customer = relationship('RealEstateCustomer', back_populates='transactions')
    property = relationship('RealEstateProperty', back_populates='transactions')
    contracts = relationship('RealEstateContract', back_populates='transaction')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'property_id': self.property_id,
            'agent_id': self.agent_id,
            'amount': float(self.amount) if self.amount else 0.0,
            'status': self.status,
            'contract_date': self.contract_date.isoformat() if self.contract_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None
        }


class RealEstateContract(Base):
    """合同表"""
    __tablename__ = 't_realestate_contract'

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey('t_realestate_transaction.id'), nullable=False, index=True)
    contract_number = Column(String(50), unique=True, index=True)
    content = Column(Text)
    sign_date = Column(DateTime)
    expires_date = Column(DateTime)

    transaction = relationship('RealEstateTransaction', back_populates='contracts')

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'contract_number': self.contract_number,
            'content': self.content,
            'sign_date': self.sign_date.isoformat() if self.sign_date else None,
            'expires_date': self.expires_date.isoformat() if self.expires_date else None
        }