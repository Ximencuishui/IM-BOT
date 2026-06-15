import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class PartsProduct(Base):
    __tablename__ = 't_parts_product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    product_code = Column(String(50), unique=True)
    category = Column(String(50))
    sub_category = Column(String(50))
    brand = Column(String(100))
    spec = Column(String(200))
    unit = Column(String(20), default='件')
    price = Column(Numeric(10, 2), default=0.00)
    wholesale_price = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    min_order_qty = Column(Integer, default=1)
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
            'wholesale_price': float(self.wholesale_price) if self.wholesale_price else 0.00,
            'cost_price': float(self.cost_price) if self.cost_price else 0.00,
            'min_order_qty': self.min_order_qty or 1,
            'description': self.description,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'stock': self.stock or 0,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PartsOrder(Base):
    __tablename__ = 't_parts_order'

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
    order_type = Column(String(20), default='wholesale')
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
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PartsOrderItem(Base):
    __tablename__ = 't_parts_order_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('t_parts_order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('t_parts_product.id'), nullable=False)
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


class PartsCategory(Base):
    __tablename__ = 't_parts_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50))
    parent_id = Column(Integer, ForeignKey('t_parts_category.id'))
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


class PartsCustomer(Base):
    __tablename__ = 't_parts_customer'

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


class PartsPriceLevel(Base):
    __tablename__ = 't_parts_price_level'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level_name = Column(String(100), nullable=False)
    min_qty = Column(Integer, default=1)
    max_qty = Column(Integer)
    discount_rate = Column(Numeric(5, 2), default=1.00)
    sort_order = Column(Integer, default=0)
    is_active = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'level_name': self.level_name,
            'min_qty': self.min_qty or 1,
            'max_qty': self.max_qty,
            'discount_rate': float(self.discount_rate) if self.discount_rate else 1.00,
            'sort_order': self.sort_order or 0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PartsSalesRecord(Base):
    __tablename__ = 't_parts_sales_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    total_orders = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0.00)
    avg_order_amount = Column(Numeric(10, 2), default=0.00)
    total_qty = Column(Integer, default=0)
    top_customer = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_orders': self.total_orders or 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'avg_order_amount': float(self.avg_order_amount) if self.avg_order_amount else 0.00,
            'total_qty': self.total_qty or 0,
            'top_customer': self.top_customer,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }