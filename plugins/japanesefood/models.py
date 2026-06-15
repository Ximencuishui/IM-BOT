import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class JapaneseProduct(Base):
    __tablename__ = 't_japanese_product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    product_code = Column(String(50))
    category = Column(String(50))
    sub_category = Column(String(50))
    price = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    unit = Column(String(20), default='份')
    description = Column(Text)
    image_url = Column(String(500))
    is_available = Column(TinyInteger, default=1)
    stock = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    is_special = Column(TinyInteger, default=0)
    seasonal = Column(TinyInteger, default=0)
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
            'is_special': self.is_special,
            'seasonal': self.seasonal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JapaneseOrder(Base):
    __tablename__ = 't_japanese_order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_name = Column(String(100))
    phone = Column(String(20))
    address = Column(String(500))
    total_amount = Column(Numeric(10, 2), default=0.00)
    discount = Column(Numeric(10, 2), default=0.00)
    pay_amount = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default='pending')
    order_type = Column(String(20), default='dine_in')
    is_set_menu = Column(TinyInteger, default=0)
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'address': self.address,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'discount': float(self.discount) if self.discount else 0.00,
            'pay_amount': float(self.pay_amount) if self.pay_amount else 0.00,
            'status': self.status,
            'order_type': self.order_type,
            'is_set_menu': self.is_set_menu,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JapaneseOrderItem(Base):
    __tablename__ = 't_japanese_order_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('t_japanese_order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('t_japanese_product.id'), nullable=False)
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


class JapaneseCategory(Base):
    __tablename__ = 't_japanese_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50))
    parent_id = Column(Integer, ForeignKey('t_japanese_category.id'))
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


class JapaneseSetMenu(Base):
    __tablename__ = 't_japanese_set_menu'

    id = Column(Integer, primary_key=True, autoincrement=True)
    set_name = Column(String(200), nullable=False)
    set_code = Column(String(50))
    description = Column(Text)
    original_price = Column(Numeric(10, 2), default=0.00)
    discount_price = Column(Numeric(10, 2), default=0.00)
    product_ids = Column(JSON)
    is_available = Column(TinyInteger, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'set_name': self.set_name,
            'set_code': self.set_code,
            'description': self.description,
            'original_price': float(self.original_price) if self.original_price else 0.00,
            'discount_price': float(self.discount_price) if self.discount_price else 0.00,
            'product_ids': json.loads(self.product_ids) if self.product_ids else [],
            'is_available': self.is_available,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JapaneseIngredient(Base):
    __tablename__ = 't_japanese_ingredient'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_name = Column(String(200), nullable=False)
    ingredient_code = Column(String(50))
    unit = Column(String(20), default='g')
    stock = Column(Numeric(10, 2), default=0.00)
    min_stock = Column(Numeric(10, 2), default=0.00)
    cost_price = Column(Numeric(10, 2), default=0.00)
    freshness_days = Column(Integer, default=1)
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
            'freshness_days': self.freshness_days or 1,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JapaneseSalesRecord(Base):
    __tablename__ = 't_japanese_sales_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    total_orders = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0.00)
    avg_order_amount = Column(Numeric(10, 2), default=0.00)
    set_menu_orders = Column(Integer, default=0)
    popular_category = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_orders': self.total_orders or 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'avg_order_amount': float(self.avg_order_amount) if self.avg_order_amount else 0.00,
            'set_menu_orders': self.set_menu_orders or 0,
            'popular_category': self.popular_category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }