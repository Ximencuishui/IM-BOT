import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.partswholesale.models import (
    PartsProduct, PartsOrder, PartsOrderItem, PartsCategory,
    PartsCustomer, PartsPriceLevel, PartsSalesRecord
)

logger = logging.getLogger(__name__)


class PartsWholesaleService(BaseService):

    def create_product(self, product_data: Dict) -> Dict:
        try:
            product = PartsProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                sub_category=product_data.get('sub_category', ''),
                brand=product_data.get('brand', ''),
                spec=product_data.get('spec', ''),
                unit=product_data.get('unit', '件'),
                price=product_data.get('price', 0.00),
                wholesale_price=product_data.get('wholesale_price', 0.00),
                cost_price=product_data.get('cost_price', 0.00),
                min_order_qty=product_data.get('min_order_qty', 1),
                description=product_data.get('description', ''),
                image_url=product_data.get('image_url', ''),
                is_available=product_data.get('is_available', 1),
                stock=product_data.get('stock', 0),
                sort_order=product_data.get('sort_order', 0),
            )
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            return {'success': True, 'data': product.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_products(self, category: Optional[str] = None, brand: Optional[str] = None, is_available: Optional[int] = None) -> List[Dict]:
        query = self.db.query(PartsProduct)
        if category:
            query = query.filter(PartsProduct.category == category)
        if brand:
            query = query.filter(PartsProduct.brand == brand)
        if is_available is not None:
            query = query.filter(PartsProduct.is_available == is_available)
        return [p.to_dict() for p in query.order_by(PartsProduct.sort_order).all()]

    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        product = self.db.query(PartsProduct).filter(PartsProduct.id == product_id).first()
        if not product:
            return {'success': False, 'error': '商品不存在'}

        try:
            for key, value in product_data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            self.db.commit()
            self.db.refresh(product)
            return {'success': True, 'data': product.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_product(self, product_id: int) -> Dict:
        product = self.db.query(PartsProduct).filter(PartsProduct.id == product_id).first()
        if not product:
            return {'success': False, 'error': '商品不存在'}

        try:
            self.db.delete(product)
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def calculate_wholesale_price(self, product_id: int, quantity: int) -> float:
        product = self.db.query(PartsProduct).filter(PartsProduct.id == product_id).first()
        if not product:
            return 0

        base_price = float(product.wholesale_price) if product.wholesale_price > 0 else float(product.price)

        price_levels = self.db.query(PartsPriceLevel).filter(
            PartsPriceLevel.is_active == 1
        ).order_by(PartsPriceLevel.min_qty).all()

        discount_rate = 1.0
        for level in price_levels:
            if quantity >= level.min_qty and (level.max_qty is None or quantity <= level.max_qty):
                discount_rate = float(level.discount_rate)

        return base_price * discount_rate

    def create_order(self, order_data: Dict) -> Dict:
        try:
            order_no = f"PARTS{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = 0
            items = order_data.get('items', [])

            for item in items:
                product = self.db.query(PartsProduct).filter(
                    PartsProduct.id == item['product_id']
                ).first()
                if product:
                    qty = item.get('quantity', 1)
                    unit_price = self.calculate_wholesale_price(product.id, qty)
                    item['unit_price'] = unit_price
                    item['product_name'] = product.product_name
                    item['product_code'] = product.product_code
                    total_amount += unit_price * qty

            customer_id = order_data.get('customer_id')
            customer_name = order_data.get('customer_name', '')
            if customer_id:
                customer = self.db.query(PartsCustomer).filter(PartsCustomer.id == customer_id).first()
                if customer:
                    customer_name = customer.customer_name
                    customer.total_purchases += total_amount
                    customer.last_purchase_date = date.today()

            discount = order_data.get('discount', 0)
            pay_amount = total_amount - discount

            order = PartsOrder(
                order_no=order_no,
                customer_id=customer_id,
                customer_name=customer_name,
                phone=order_data.get('phone', ''),
                address=order_data.get('address', ''),
                total_amount=total_amount,
                discount=discount,
                pay_amount=pay_amount,
                status=order_data.get('status', 'pending'),
                order_type=order_data.get('order_type', 'wholesale'),
                remark=order_data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            for item in items:
                order_item = PartsOrderItem(
                    order_id=order.id,
                    product_id=item['product_id'],
                    product_name=item.get('product_name', ''),
                    product_code=item.get('product_code', ''),
                    quantity=item.get('quantity', 1),
                    unit_price=item.get('unit_price', 0),
                    total_price=item.get('quantity', 1) * item.get('unit_price', 0),
                    remark=item.get('remark', ''),
                )
                self.db.add(order_item)

            self.db.commit()

            return {'success': True, 'data': order.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_orders(self, status: Optional[str] = None, order_type: Optional[str] = None, customer_id: Optional[int] = None) -> List[Dict]:
        query = self.db.query(PartsOrder)
        if status:
            query = query.filter(PartsOrder.status == status)
        if order_type:
            query = query.filter(PartsOrder.order_type == order_type)
        if customer_id:
            query = query.filter(PartsOrder.customer_id == customer_id)
        return [o.to_dict() for o in query.order_by(PartsOrder.created_at.desc()).all()]

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(PartsOrder).filter(PartsOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        items = self.db.query(PartsOrderItem).filter(PartsOrderItem.order_id == order_id).all()
        order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(PartsOrder).filter(PartsOrder.id == order_id).first()
        if not order:
            return {'success': False, 'error': '订单不存在'}

        try:
            order.status = status
            self.db.commit()
            self.db.refresh(order)
            return {'success': True, 'data': order.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_category(self, category_data: Dict) -> Dict:
        try:
            category = PartsCategory(
                category_name=category_data['category_name'],
                category_code=category_data.get('category_code', ''),
                parent_id=category_data.get('parent_id'),
                sort_order=category_data.get('sort_order', 0),
                is_active=category_data.get('is_active', 1),
            )
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            return {'success': True, 'data': category.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_categories(self) -> List[Dict]:
        return [c.to_dict() for c in self.db.query(PartsCategory).filter(
            PartsCategory.is_active == 1
        ).order_by(PartsCategory.sort_order).all()]

    def create_customer(self, customer_data: Dict) -> Dict:
        try:
            customer = PartsCustomer(
                customer_name=customer_data['customer_name'],
                phone=customer_data.get('phone', ''),
                company_name=customer_data.get('company_name', ''),
                address=customer_data.get('address', ''),
                customer_level=customer_data.get('customer_level', 'normal'),
                total_purchases=customer_data.get('total_purchases', 0.00),
                last_purchase_date=customer_data.get('last_purchase_date'),
                status=customer_data.get('status', 'active'),
            )
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            return {'success': True, 'data': customer.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_customers(self, customer_level: Optional[str] = None) -> List[Dict]:
        query = self.db.query(PartsCustomer).filter(PartsCustomer.status == 'active')
        if customer_level:
            query = query.filter(PartsCustomer.customer_level == customer_level)
        return [c.to_dict() for c in query.order_by(PartsCustomer.total_purchases.desc()).all()]

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        customer = self.db.query(PartsCustomer).filter(PartsCustomer.phone == phone).first()
        return customer.to_dict() if customer else None

    def create_price_level(self, level_data: Dict) -> Dict:
        try:
            level = PartsPriceLevel(
                level_name=level_data['level_name'],
                min_qty=level_data.get('min_qty', 1),
                max_qty=level_data.get('max_qty'),
                discount_rate=level_data.get('discount_rate', 1.00),
                sort_order=level_data.get('sort_order', 0),
                is_active=level_data.get('is_active', 1),
            )
            self.db.add(level)
            self.db.commit()
            self.db.refresh(level)
            return {'success': True, 'data': level.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_price_levels(self) -> List[Dict]:
        return [p.to_dict() for p in self.db.query(PartsPriceLevel).filter(
            PartsPriceLevel.is_active == 1
        ).order_by(PartsPriceLevel.min_qty).all()]

    def parse_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'order_type': 'wholesale',
            'items': [],
            'customer_name': '',
            'phone': '',
            'customer_id': None,
            'address': '',
            'remark': '',
            'confidence': 0.75,
        }

        phone_match = re.search(r'(\d{11})', message_text)
        if phone_match:
            result['phone'] = phone_match.group(1)
            customer = self.get_customer_by_phone(result['phone'])
            if customer:
                result['customer_id'] = customer['id']
                result['customer_name'] = customer['customer_name']

        retail_keywords = ['零售', '散卖']
        if any(keyword in message_text for keyword in retail_keywords):
            result['order_type'] = 'retail'

        return result

    def generate_sales_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        orders = self.db.query(PartsOrder).filter(
            PartsOrder.created_at >= date_str
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.pay_amount) for o in orders)
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0

        total_qty = 0
        customer_sales = {}
        for order in orders:
            items = self.db.query(PartsOrderItem).filter(PartsOrderItem.order_id == order.id).all()
            total_qty += sum(item.quantity for item in items)
            customer_name = order.customer_name or '未知'
            customer_sales[customer_name] = customer_sales.get(customer_name, 0) + float(order.pay_amount)

        top_customer = max(customer_sales, key=customer_sales.get) if customer_sales else ''

        return {'success': True, 'data': {
            'date': date_str,
            'total_orders': total_orders,
            'total_amount': round(total_amount, 2),
            'avg_order_amount': round(avg_order_amount, 2),
            'total_qty': total_qty,
            'top_customer': top_customer,
        }}

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(PartsOrder).filter(
            PartsOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.pay_amount) for o in orders)
        pending_orders = len([o for o in orders if o.status == 'pending'])

        total_qty = 0
        for order in orders:
            items = self.db.query(PartsOrderItem).filter(PartsOrderItem.order_id == order.id).all()
            total_qty += sum(item.quantity for item in items)

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'pending_orders': pending_orders,
            'total_qty': total_qty,
            'total_customers': len(self.db.query(PartsCustomer).filter(PartsCustomer.status == 'active').all()),
            'total_products': len(self.db.query(PartsProduct).filter(PartsProduct.is_available == 1).all()),
        }