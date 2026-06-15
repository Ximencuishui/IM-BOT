"""
SQLAlchemy ORM 模型定义
"""
import json
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, Date, Text, ForeignKey, Index, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from sqlalchemy.orm import relationship
from database.db_config import Base


class DeliveryRoute(Base):
    """配送线路表"""
    __tablename__ = 't_delivery_route'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='线路ID')
    route_name = Column(String(100), nullable=False, comment='线路名称')
    route_code = Column(String(50), unique=True, comment='线路编码')
    description = Column(String(255), comment='线路描述')
    is_active = Column(TinyInteger, default=1, comment='是否启用: 1-启用, 0-禁用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    customers = relationship('Customer', back_populates='route')

    def to_dict(self):
        return {
            'id': self.id,
            'route_name': self.route_name,
            'route_code': self.route_code,
            'description': self.description,
            'is_active': self.is_active
        }


class Product(Base):
    """商品表"""
    __tablename__ = 't_product'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='商品ID')
    product_name = Column(String(100), nullable=False, unique=True, comment='商品名称')
    product_code = Column(String(50), comment='商品编码')
    shortcut_codes = Column(String(255), comment='快捷码列表,逗号分隔')
    unit = Column(String(20), default='斤', comment='默认单位')
    price = Column(Numeric(10, 2), default=0.00, comment='参考单价(元)')
    category = Column(String(50), comment='商品分类')
    attributes = Column(JSON, comment='商品属性JSON数组,最多10个属性')
    commission = Column(Numeric(10, 2), default=0.00, comment='佣金(元)')
    points = Column(Integer, default=0, comment='积分')
    is_active = Column(TinyInteger, default=1, comment='是否启用')
    sort_order = Column(Integer, default=0, comment='排序权重')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    order_items = relationship('OrderItem', back_populates='product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_code': self.product_code,
            'shortcut_codes': self.shortcut_codes.split(',') if self.shortcut_codes else [],
            'unit': self.unit,
            'price': float(self.price),
            'category': self.category,
            'attributes': json.loads(self.attributes) if self.attributes else [],
            'commission': float(self.commission) if self.commission else 0.0,
            'points': self.points or 0,
            'is_active': self.is_active
        }

    def match_shortcut(self, text):
        """检查文本是否匹配商品快捷码"""
        if not self.shortcut_codes:
            return False
        codes = [code.strip() for code in self.shortcut_codes.split(',')]
        return any(code in text for code in codes)


class Customer(Base):
    """客户表"""
    __tablename__ = 't_user'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='客户ID')
    customer_name = Column(String(100), nullable=False, comment='客户姓名/店铺名')
    phone = Column(String(20), comment='联系电话')
    address = Column(String(255), comment='配送地址')
    wx_group_id = Column(String(64), unique=True, comment='微信群ID')
    wx_alias = Column(String(64), comment='微信昵称')
    route_id = Column(Integer, ForeignKey('t_delivery_route.id'), comment='所属配送线路ID')
    sales_person = Column(String(50), comment='负责销售')
    is_active = Column(TinyInteger, default=1, comment='是否启用')
    remark = Column(String(255), comment='备注信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    route = relationship('DeliveryRoute', back_populates='customers')
    orders = relationship('Order', back_populates='customer')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'address': self.address,
            'wx_group_id': self.wx_group_id,
            'wx_alias': self.wx_alias,
            'route_id': self.route_id,
            'sales_person': self.sales_person,
            'is_active': self.is_active
        }


class Order(Base):
    """订单表"""
    __tablename__ = 't_order'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='订单ID')
    order_uuid = Column(String(64), unique=True, nullable=False, comment='订单唯一标识')
    customer_id = Column(Integer, ForeignKey('t_user.id'), nullable=False, comment='客户ID')
    order_date = Column(Date, nullable=False, comment='订单日期')
    status = Column(String(20), default='pending', comment='订单状态')
    total_amount = Column(Numeric(10, 2), default=0.00, comment='订单总金额')
    remark = Column(String(500), comment='订单备注')
    source_type = Column(String(20), default='wechat', comment='订单来源')
    confirmed_by = Column(String(50), comment='确认人')
    confirmed_at = Column(DateTime, comment='确认时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    customer = relationship('Customer', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'order_uuid': self.order_uuid,
            'customer_id': self.customer_id,
            'customer_name': self.customer.customer_name if self.customer else None,
            'order_date': self.order_date.isoformat() if isinstance(self.order_date, date) else str(self.order_date),
            'status': self.status,
            'total_amount': float(self.total_amount),
            'remark': self.remark,
            'source_type': self.source_type,
            'confirmed_by': self.confirmed_by,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(Base):
    """订单明细表"""
    __tablename__ = 't_order_item'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='明细ID')
    order_id = Column(Integer, ForeignKey('t_order.id'), nullable=False, comment='订单ID')
    product_id = Column(Integer, ForeignKey('t_product.id'), nullable=False, comment='商品ID')
    product_name = Column(String(100), comment='商品名称快照')
    quantity = Column(Numeric(10, 2), nullable=False, comment='数量')
    unit = Column(String(20), default='斤', comment='单位')
    unit_price = Column(Numeric(10, 2), default=0.00, comment='单价')
    subtotal = Column(Numeric(10, 2), default=0.00, comment='小计金额')
    remark = Column(String(255), comment='商品备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    order = relationship('Order', back_populates='items')
    product = relationship('Product', back_populates='order_items')

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': float(self.quantity),
            'unit': self.unit,
            'unit_price': float(self.unit_price),
            'subtotal': float(self.subtotal),
            'remark': self.remark
        }


class RawMessage(Base):
    """原始消息记录表"""
    __tablename__ = 't_raw_message'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='消息ID')
    group_id = Column(String(64), comment='微信群ID')
    sender = Column(String(64), comment='发送者昵称')
    content = Column(Text, comment='消息内容')
    raw_json = Column(Text, comment='原始JSON数据')
    message_hash = Column(String(64), comment='消息指纹(MD5)', index=True)
    received_at = Column(DateTime, comment='接收时间', index=True)
    processed = Column(TinyInteger, default=0, comment='是否已处理: 0-未处理, 1-已处理, 2-处理失败', index=True)
    parse_result = Column(Text, comment='解析结果JSON')
    confidence_score = Column(Numeric(3, 2), comment='解析置信度(0-1)')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'sender': self.sender,
            'content': self.content,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'processed': self.processed,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None
        }


class RouteProduct(Base):
    """线路产品关联表"""
    __tablename__ = 't_route_product'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID')
    route_id = Column(Integer, ForeignKey('t_delivery_route.id'), nullable=False, comment='配送线路ID')
    product_id = Column(Integer, ForeignKey('t_product.id'), nullable=False, comment='商品ID')
    sort_order = Column(Integer, default=0, comment='排序序号(用于圈选时的1-10编号)')
    custom_price = Column(Numeric(10, 2), comment='线路专属价格(NULL则使用商品基础价)')
    is_active = Column(TinyInteger, default=1, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    route = relationship('DeliveryRoute')
    product = relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'product_id': self.product_id,
            'product_name': self.product.product_name if self.product else None,
            'unit': self.product.unit if self.product else '斤',
            'sort_order': self.sort_order,
            'price': float(self.custom_price) if self.custom_price else (float(self.product.price) if self.product else 0.00),
            'custom_price': float(self.custom_price) if self.custom_price else None,
            'is_active': self.is_active
        }


class OrderAdjustmentLog(Base):
    """订单数量调整日志表"""
    __tablename__ = 't_order_adjustment_log'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID')
    order_id = Column(Integer, ForeignKey('t_order.id'), nullable=False, comment='关联订单ID')
    customer_id = Column(Integer, ForeignKey('t_user.id'), nullable=False, comment='客户ID')
    product_id = Column(Integer, ForeignKey('t_product.id'), nullable=False, comment='商品ID')
    adjustment_type = Column(String(20), nullable=False, comment='调整类型: add/subtract/replace')
    quantity_change = Column(Numeric(10, 2), nullable=False, comment='数量变化(+/-)')
    original_quantity = Column(Numeric(10, 2), comment='调整前数量')
    new_quantity = Column(Numeric(10, 2), comment='调整后数量')
    operator = Column(String(50), comment='操作人')
    reason = Column(String(255), comment='调整原因')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 关系
    order = relationship('Order')
    customer = relationship('Customer')
    product = relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'customer_id': self.customer_id,
            'product_id': self.product_id,
            'product_name': self.product.product_name if self.product else None,
            'adjustment_type': self.adjustment_type,
            'quantity_change': float(self.quantity_change),
            'original_quantity': float(self.original_quantity) if self.original_quantity else None,
            'new_quantity': float(self.new_quantity) if self.new_quantity else None,
            'operator': self.operator,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = 't_system_config'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='配置ID')
    config_key = Column(String(100), unique=True, nullable=False, comment='配置键')
    config_value = Column(Text, comment='配置值')
    description = Column(String(255), comment='配置描述')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description
        }


class Salesperson(Base):
    """销售人员表"""
    __tablename__ = 't_salesperson'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='销售人员ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    name = Column(String(100), nullable=False, comment='姓名')
    phone = Column(String(20), comment='联系电话')
    region = Column(String(100), comment='负责区域')
    route_id = Column(Integer, ForeignKey('t_delivery_route.id'), comment='关联线路ID')
    license_codes = Column(JSON, comment='关联授权码列表')
    total_sales = Column(Integer, default=0, comment='累计销售订单数')
    total_amount = Column(Numeric(12, 2), default=0.00, comment='累计销售金额')
    is_active = Column(TinyInteger, default=1, comment='是否启用: 1-启用, 0-禁用')
    remark = Column(Text, comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    route = relationship('DeliveryRoute', backref='salespersons')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'region': self.region,
            'route_id': self.route_id,
            'license_codes': self.license_codes or [],
            'total_sales': self.total_sales,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'is_active': self.is_active,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
