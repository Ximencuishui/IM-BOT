import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class EVProduct(Base):
    __tablename__ = 't_ev_product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    product_code = Column(String(50), unique=True)
    category = Column(String(50))
    sub_category = Column(String(50))
    brand = Column(String(100))
    spec = Column(String(200))
    unit = Column(String(20), default='件')
    price = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    description = Column(Text)
    image_url = Column(String(500))
    is_available = Column(TinyInteger, default=1)
    stock = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_code': self.product_code,
            'category': self.category,
            'sub_category': self.sub_category,
            'brand': self.brand,
            'spec': self.spec,
            'unit': self.unit,
            'price': float(self.price) if self.price else 0.00,
            'cost_price': float(self.cost_price) if self.cost_price else 0.00,
            'description': self.description,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'stock': self.stock or 0,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EVOrder(Base):
    __tablename__ = 't_ev_order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer)
    customer_name = Column(String(100))
    phone = Column(String(20))
    address = Column(String(500))
    total_amount = Column(Numeric(10, 2), default=0.00)
    discount = Column(Numeric(10, 2), default=0.00)
    pay_amount = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default='pending')
    order_type = Column(String(20), default='retail')
    repair_required = Column(TinyInteger, default=0)
    repair_date = Column(Date)
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'address': self.address,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'discount': float(self.discount) if self.discount else 0.00,
            'pay_amount': float(self.pay_amount) if self.pay_amount else 0.00,
            'status': self.status,
            'order_type': self.order_type,
            'repair_required': self.repair_required,
            'repair_date': self.repair_date.isoformat() if self.repair_date else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EVOrderItem(Base):
    __tablename__ = 't_ev_order_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('t_ev_order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('t_ev_product.id'), nullable=False)
    product_name = Column(String(200))
    product_code = Column(String(50))
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), default=0.00)
    total_price = Column(Numeric(10, 2), default=0.00)
    remark = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_code': self.product_code,
            'quantity': self.quantity or 1,
            'unit_price': float(self.unit_price) if self.unit_price else 0.00,
            'total_price': float(self.total_price) if self.total_price else 0.00,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EVCategory(Base):
    __tablename__ = 't_ev_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50))
    parent_id = Column(Integer, ForeignKey('t_ev_category.id'))
    sort_order = Column(Integer, default=0)
    is_active = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'category_name': self.category_name,
            'category_code': self.category_code,
            'parent_id': self.parent_id,
            'sort_order': self.sort_order or 0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EVCustomer(Base):
    __tablename__ = 't_ev_customer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True)
    company_name = Column(String(200))
    address = Column(String(500))
    customer_level = Column(String(20), default='normal')
    total_purchases = Column(Numeric(12, 2), default=0.00)
    last_purchase_date = Column(Date)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'company_name': self.company_name,
            'address': self.address,
            'customer_level': self.customer_level,
            'total_purchases': float(self.total_purchases) if self.total_purchases else 0.00,
            'last_purchase_date': self.last_purchase_date.isoformat() if self.last_purchase_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EVBattery(Base):
    __tablename__ = 't_ev_battery'

    id = Column(Integer, primary_key=True, autoincrement=True)
    battery_code = Column(String(50), unique=True)
    battery_type = Column(String(50))
    voltage = Column(String(20))
    capacity = Column(String(20))
    brand = Column(String(100))
    price = Column(Numeric(10, 2), default=0.00)
    stock = Column(Integer, default=0)
    warranty_period = Column(Integer, default=12)
    description = Column(Text)
    is_available = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'battery_code': self.battery_code,
            'battery_type': self.battery_type,
            'voltage': self.voltage,
            'capacity': self.capacity,
            'brand': self.brand,
            'price': float(self.price) if self.price else 0.00,
            'stock': self.stock or 0,
            'warranty_period': self.warranty_period or 12,
            'description': self.description,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EVRepairService(Base):
    __tablename__ = 't_ev_repair_service'

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(100), nullable=False)
    service_code = Column(String(50))
    base_price = Column(Numeric(10, 2), default=0.00)
    description = Column(Text)
    duration = Column(Integer, default=60)
    is_active = Column(TinyInteger, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'service_name': self.service_name,
            'service_code': self.service_code,
            'base_price': float(self.base_price) if self.base_price else 0.00,
            'description': self.description,
            'duration': self.duration or 60,
            'is_active': self.is_active,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EVSalesRecord(Base):
    __tablename__ = 't_ev_sales_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    total_orders = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0.00)
    avg_order_amount = Column(Numeric(10, 2), default=0.00)
    repair_orders = Column(Integer, default=0)
    repair_amount = Column(Numeric(12, 2), default=0.00)
    battery_sales = Column(Integer, default=0)
    battery_amount = Column(Numeric(12, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_orders': self.total_orders or 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'avg_order_amount': float(self.avg_order_amount) if self.avg_order_amount else 0.00,
            'repair_orders': self.repair_orders or 0,
            'repair_amount': float(self.repair_amount) if self.repair_amount else 0.00,
            'battery_sales': self.battery_sales or 0,
            'battery_amount': float(self.battery_amount) if self.battery_amount else 0.00,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }