import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.bakery.models import (
    BakeryProduct, BakeryOrder, BakeryOrderItem, BakeryCategory,
    BakeryMember, BakeryIngredient, BakerySalesRecord
)

logger = logging.getLogger(__name__)


class BakeryService(BaseService):

    def create_product(self, product_data: Dict) -> Dict:
        try:
            product = BakeryProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                sub_category=product_data.get('sub_category', ''),
                price=product_data.get('price', 0.00),
                cost_price=product_data.get('cost_price', 0.00),
                unit=product_data.get('unit', '个'),
                description=product_data.get('description', ''),
                image_url=product_data.get('image_url', ''),
                is_available=product_data.get('is_available', 1),
                stock=product_data.get('stock', 0),
                sort_order=product_data.get('sort_order', 0),
                is_customizable=product_data.get('is_customizable', 0),
                shelf_life_hours=product_data.get('shelf_life_hours', 24),
            )
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            return {'success': True, 'data': product.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_products(self, category: Optional[str] = None, sub_category: Optional[str] = None, is_available: Optional[int] = None) -> List[Dict]:
        query = self.db.query(BakeryProduct)
        if category:
            query = query.filter(BakeryProduct.category == category)
        if sub_category:
            query = query.filter(BakeryProduct.sub_category == sub_category)
        if is_available is not None:
            query = query.filter(BakeryProduct.is_available == is_available)
        return [p.to_dict() for p in query.order_by(BakeryProduct.sort_order).all()]

    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        product = self.db.query(BakeryProduct).filter(BakeryProduct.id == product_id).first()
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
        product = self.db.query(BakeryProduct).filter(BakeryProduct.id == product_id).first()
        if not product:
            return {'success': False, 'error': '商品不存在'}

        try:
            self.db.delete(product)
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_order(self, order_data: Dict) -> Dict:
        try:
            order_no = f"BAKE{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = 0
            items = order_data.get('items', [])
            is_custom_order = order_data.get('is_custom_order', 0)
            customization = order_data.get('customization', {})

            if is_custom_order and customization:
                base_price = customization.get('base_price', 0)
                size_factor = customization.get('size_factor', 1)
                decoration_fee = customization.get('decoration_fee', 0)
                total_amount = base_price * size_factor + decoration_fee
            else:
                for item in items:
                    product = self.db.query(BakeryProduct).filter(
                        BakeryProduct.id == item['product_id']
                    ).first()
                    if product:
                        item['unit_price'] = float(product.price)
                        item['product_name'] = product.product_name
                        total_amount += float(product.price) * item.get('quantity', 1)

            member_id = order_data.get('member_id')
            discount = 0
            if member_id:
                member = self.db.query(BakeryMember).filter(BakeryMember.id == member_id).first()
                if member:
                    if member.member_level == 'vip':
                        discount = total_amount * 0.8
                    elif member.member_level == 'gold':
                        discount = total_amount * 0.9
                    points = int(total_amount)
                    member.points += points
                    member.total_consumption += total_amount

            pay_amount = total_amount - discount

            order = BakeryOrder(
                order_no=order_no,
                customer_name=order_data.get('customer_name', ''),
                phone=order_data.get('phone', ''),
                member_id=member_id,
                address=order_data.get('address', ''),
                delivery_date=order_data.get('delivery_date'),
                delivery_time=order_data.get('delivery_time'),
                total_amount=total_amount,
                discount=discount,
                pay_amount=pay_amount,
                status=order_data.get('status', 'pending'),
                order_type=order_data.get('order_type', 'dine_in'),
                is_custom_order=is_custom_order,
                customization=json.dumps(customization),
                remark=order_data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            if not is_custom_order:
                for item in items:
                    order_item = BakeryOrderItem(
                        order_id=order.id,
                        product_id=item['product_id'],
                        product_name=item.get('product_name', ''),
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

    def list_orders(self, status: Optional[str] = None, order_type: Optional[str] = None, is_custom_order: Optional[int] = None) -> List[Dict]:
        query = self.db.query(BakeryOrder)
        if status:
            query = query.filter(BakeryOrder.status == status)
        if order_type:
            query = query.filter(BakeryOrder.order_type == order_type)
        if is_custom_order is not None:
            query = query.filter(BakeryOrder.is_custom_order == is_custom_order)
        return [o.to_dict() for o in query.order_by(BakeryOrder.created_at.desc()).all()]

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(BakeryOrder).filter(BakeryOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        if not order.is_custom_order:
            items = self.db.query(BakeryOrderItem).filter(BakeryOrderItem.order_id == order_id).all()
            order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(BakeryOrder).filter(BakeryOrder.id == order_id).first()
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
            category = BakeryCategory(
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
        return [c.to_dict() for c in self.db.query(BakeryCategory).filter(
            BakeryCategory.is_active == 1
        ).order_by(BakeryCategory.sort_order).all()]

    def create_member(self, member_data: Dict) -> Dict:
        try:
            member = BakeryMember(
                member_name=member_data['member_name'],
                phone=member_data.get('phone', ''),
                email=member_data.get('email', ''),
                member_level=member_data.get('member_level', 'normal'),
                points=member_data.get('points', 0),
                total_consumption=member_data.get('total_consumption', 0.00),
                birthday=member_data.get('birthday'),
                preferred_flavors=json.dumps(member_data.get('preferred_flavors', [])),
                status=member_data.get('status', 'active'),
            )
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
            return {'success': True, 'data': member.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_members(self, member_level: Optional[str] = None) -> List[Dict]:
        query = self.db.query(BakeryMember).filter(BakeryMember.status == 'active')
        if member_level:
            query = query.filter(BakeryMember.member_level == member_level)
        return [m.to_dict() for m in query.order_by(BakeryMember.total_consumption.desc()).all()]

    def get_member_by_phone(self, phone: str) -> Optional[Dict]:
        member = self.db.query(BakeryMember).filter(BakeryMember.phone == phone).first()
        return member.to_dict() if member else None

    def create_ingredient(self, ingredient_data: Dict) -> Dict:
        try:
            ingredient = BakeryIngredient(
                ingredient_name=ingredient_data['ingredient_name'],
                ingredient_code=ingredient_data.get('ingredient_code', ''),
                unit=ingredient_data.get('unit', 'g'),
                stock=ingredient_data.get('stock', 0.00),
                min_stock=ingredient_data.get('min_stock', 0.00),
                cost_price=ingredient_data.get('cost_price', 0.00),
                is_active=ingredient_data.get('is_active', 1),
            )
            self.db.add(ingredient)
            self.db.commit()
            self.db.refresh(ingredient)
            return {'success': True, 'data': ingredient.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_ingredients(self, low_stock: bool = False) -> List[Dict]:
        query = self.db.query(BakeryIngredient).filter(BakeryIngredient.is_active == 1)
        if low_stock:
            query = query.filter(BakeryIngredient.stock <= BakeryIngredient.min_stock)
        return [i.to_dict() for i in query.all()]

    def parse_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'order_type': 'dine_in',
            'items': [],
            'customer_name': '',
            'phone': '',
            'member_id': None,
            'address': '',
            'is_custom_order': 0,
            'customization': {},
            'remark': '',
            'confidence': 0.75,
        }

        phone_match = re.search(r'(\d{11})', message_text)
        if phone_match:
            result['phone'] = phone_match.group(1)
            member = self.get_member_by_phone(result['phone'])
            if member:
                result['member_id'] = member['id']
                result['customer_name'] = member['member_name']

        address_keywords = ['地址', '送到', '外卖', '配送']
        if any(keyword in message_text for keyword in address_keywords):
            result['order_type'] = 'delivery'

        custom_keywords = ['定制', '定做', '蛋糕', '生日']
        if any(keyword in message_text for keyword in custom_keywords):
            result['is_custom_order'] = 1

        return result

    def generate_sales_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        orders = self.db.query(BakeryOrder).filter(
            BakeryOrder.created_at >= date_str
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.pay_amount) for o in orders)
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0
        custom_orders = len([o for o in orders if o.is_custom_order])
        member_orders = len([o for o in orders if o.member_id])

        return {'success': True, 'data': {
            'date': date_str,
            'total_orders': total_orders,
            'total_amount': round(total_amount, 2),
            'avg_order_amount': round(avg_order_amount, 2),
            'custom_orders': custom_orders,
            'member_orders': member_orders,
        }}

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(BakeryOrder).filter(
            BakeryOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.pay_amount) for o in orders)
        pending_orders = len([o for o in orders if o.status == 'pending'])
        custom_orders = len([o for o in orders if o.is_custom_order])
        member_orders = len([o for o in orders if o.member_id])

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'pending_orders': pending_orders,
            'custom_orders': custom_orders,
            'member_orders': member_orders,
            'total_members': len(self.db.query(BakeryMember).filter(BakeryMember.status == 'active').all()),
            'total_products': len(self.db.query(BakeryProduct).filter(BakeryProduct.is_available == 1).all()),
        }