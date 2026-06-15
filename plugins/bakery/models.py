import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class BakeryProduct(Base):
    __tablename__ = 't_bakery_product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    product_code = Column(String(50))
    category = Column(String(50))
    sub_category = Column(String(50))
    price = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    unit = Column(String(20), default='个')
    description = Column(Text)
    image_url = Column(String(500))
    is_available = Column(TinyInteger, default=1)
    stock = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    is_customizable = Column(TinyInteger, default=0)
    shelf_life_hours = Column(Integer, default=24)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_code': self.product_code,
            'category': self.category,
            'sub_category': self.sub_category,
            'price': float(self.price) if self.price else 0.00,
            'cost_price': float(self.cost_price) if self.cost_price else 0.00,
            'unit': self.unit,
            'description': self.description,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'stock': self.stock or 0,
            'sort_order': self.sort_order or 0,
            'is_customizable': self.is_customizable,
            'shelf_life_hours': self.shelf_life_hours or 24,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BakeryOrder(Base):
    __tablename__ = 't_bakery_order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_name = Column(String(100))
    phone = Column(String(20))
    member_id = Column(Integer)
    address = Column(String(500))
    delivery_date = Column(Date)
    delivery_time = Column(String(50))
    total_amount = Column(Numeric(10, 2), default=0.00)
    discount = Column(Numeric(10, 2), default=0.00)
    pay_amount = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default='pending')
    order_type = Column(String(20), default='dine_in')
    is_custom_order = Column(TinyInteger, default=0)
    customization = Column(JSON)
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'member_id': self.member_id,
            'address': self.address,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'delivery_time': self.delivery_time,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'discount': float(self.discount) if self.discount else 0.00,
            'pay_amount': float(self.pay_amount) if self.pay_amount else 0.00,
            'status': self.status,
            'order_type': self.order_type,
            'is_custom_order': self.is_custom_order,
            'customization': json.loads(self.customization) if self.customization else {},
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BakeryOrderItem(Base):
    __tablename__ = 't_bakery_order_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('t_bakery_order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('t_bakery_product.id'), nullable=False)
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


class BakeryCategory(Base):
    __tablename__ = 't_bakery_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50))
    parent_id = Column(Integer, ForeignKey('t_bakery_category.id'))
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


class BakeryMember(Base):
    __tablename__ = 't_bakery_member'

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True)
    email = Column(String(100))
    member_level = Column(String(20), default='normal')
    points = Column(Integer, default=0)
    total_consumption = Column(Numeric(12, 2), default=0.00)
    birthday = Column(Date)
    preferred_flavors = Column(JSON)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'member_name': self.member_name,
            'phone': self.phone,
            'email': self.email,
            'member_level': self.member_level,
            'points': self.points or 0,
            'total_consumption': float(self.total_consumption) if self.total_consumption else 0.00,
            'birthday': self.birthday.isoformat() if self.birthday else None,
            'preferred_flavors': json.loads(self.preferred_flavors) if self.preferred_flavors else [],
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BakeryIngredient(Base):
    __tablename__ = 't_bakery_ingredient'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_name = Column(String(200), nullable=False)
    ingredient_code = Column(String(50))
    unit = Column(String(20), default='g')
    stock = Column(Numeric(10, 2), default=0.00)
    min_stock = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    is_active = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'ingredient_name': self.ingredient_name,
            'ingredient_code': self.ingredient_code,
            'unit': self.unit,
            'stock': float(self.stock) if self.stock else 0.00,
            'min_stock': float(self.min_stock) if self.min_stock else 0.00,
            'cost_price': float(self.cost_price) if self.cost_price else 0.00,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BakerySalesRecord(Base):
    __tablename__ = 't_bakery_sales_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    total_orders = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0.00)
    avg_order_amount = Column(Numeric(10, 2), default=0.00)
    custom_orders = Column(Integer, default=0)
    member_orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_orders': self.total_orders or 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'avg_order_amount': float(self.avg_order_amount) if self.avg_order_amount else 0.00,
            'custom_orders': self.custom_orders or 0,
            'member_orders': self.member_orders or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }