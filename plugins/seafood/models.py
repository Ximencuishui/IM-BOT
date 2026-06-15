import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, Boolean, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class SeafoodCustomer(Base):
    __tablename__ = 't_seafood_customer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    wechat_id = Column(String(200))
    customer_type = Column(String(20), default='B')
    address = Column(String(500))
    remark = Column(Text)
    is_active = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'wechat_id': self.wechat_id,
            'customer_type': self.customer_type,
            'address': self.address,
            'remark': self.remark,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SeafoodSupplier(Base):
    __tablename__ = 't_seafood_supplier'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    wechat_id = Column(String(200))
    supplier_type = Column(String(50))
    address = Column(String(500))
    contact_person = Column(String(100))
    remark = Column(Text)
    is_active = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_name': self.supplier_name,
            'phone': self.phone,
            'wechat_id': self.wechat_id,
            'supplier_type': self.supplier_type,
            'address': self.address,
            'contact_person': self.contact_person,
            'remark': self.remark,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SeafoodProduct(Base):
    __tablename__ = 't_seafood_product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    product_code = Column(String(50))
    category = Column(String(50))
    unit = Column(String(20), default='斤')
    price = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    stock = Column(Integer, default=0)
    min_stock = Column(Integer, default=0)
    description = Column(Text)
    image_url = Column(String(500))
    is_available = Column(TinyInteger, default=1)
    supplier_id = Column(Integer, ForeignKey('t_seafood_supplier.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_code': self.product_code,
            'category': self.category,
            'unit': self.unit,
            'price': float(self.price) if self.price else 0.00,
            'cost_price': float(self.cost_price) if self.cost_price else 0.00,
            'stock': self.stock or 0,
            'min_stock': self.min_stock or 0,
            'description': self.description,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'supplier_id': self.supplier_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SeafoodOrder(Base):
    __tablename__ = 't_seafood_order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey('t_seafood_customer.id'), nullable=False)
    customer_name = Column(String(100))
    customer_type = Column(String(20))
    delivery_date = Column(Date)
    order_type = Column(String(20), default='normal')
    is_urgent = Column(TinyInteger, default=0)
    status = Column(String(20), default='pending')
    total_amount = Column(Numeric(12, 2), default=0.00)
    remark = Column(Text)
    boss_notified = Column(TinyInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_type': self.customer_type,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'order_type': self.order_type,
            'is_urgent': self.is_urgent,
            'status': self.status,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'remark': self.remark,
            'boss_notified': self.boss_notified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SeafoodOrderItem(Base):
    __tablename__ = 't_seafood_order_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('t_seafood_order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('t_seafood_product.id'), nullable=False)
    product_name = Column(String(200))
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
            'quantity': self.quantity or 1,
            'unit_price': float(self.unit_price) if self.unit_price else 0.00,
            'total_price': float(self.total_price) if self.total_price else 0.00,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SeafoodStock(Base):
    __tablename__ = 't_seafood_stock'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('t_seafood_product.id'), nullable=False)
    product_name = Column(String(200))
    stock_in = Column(Integer, default=0)
    stock_out = Column(Integer, default=0)
    balance = Column(Integer, default=0)
    stock_date = Column(Date, nullable=False)
    supplier_id = Column(Integer, ForeignKey('t_seafood_supplier.id'))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'stock_in': self.stock_in or 0,
            'stock_out': self.stock_out or 0,
            'balance': self.balance or 0,
            'stock_date': self.stock_date.isoformat() if self.stock_date else None,
            'supplier_id': self.supplier_id,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SeafoodConfig(Base):
    __tablename__ = 't_seafood_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(String(500))
    config_type = Column(String(50), default='string')
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SeafoodOrderReminder(Base):
    __tablename__ = 't_seafood_order_reminder'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('t_seafood_customer.id'), nullable=False)
    customer_name = Column(String(100))
    reminder_date = Column(Date, nullable=False)
    reminder_time = Column(String(20))
    sent_at = Column(DateTime)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'reminder_date': self.reminder_date.isoformat() if self.reminder_date else None,
            'reminder_time': self.reminder_time,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }