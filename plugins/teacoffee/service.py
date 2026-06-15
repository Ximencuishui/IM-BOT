import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.teacoffee.models import (
    TeaProduct, TeaOrder, TeaOrderItem, TeaCategory,
    TeaMember, TeaIngredient, TeaSalesRecord
)

logger = logging.getLogger(__name__)


class TeaCoffeeService(BaseService):

    def create_product(self, product_data: Dict) -> Dict:
        try:
            product = TeaProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                sub_category=product_data.get('sub_category', ''),
                price=product_data.get('price', 0.00),
                cost_price=product_data.get('cost_price', 0.00),
                unit=product_data.get('unit', '杯'),
                description=product_data.get('description', ''),
                image_url=product_data.get('image_url', ''),
                is_available=product_data.get('is_available', 1),
                stock=product_data.get('stock', 0),
                sort_order=product_data.get('sort_order', 0),
                sugar_levels=json.dumps(product_data.get('sugar_levels', [])),
                ice_levels=json.dumps(product_data.get('ice_levels', [])),
                size_options=json.dumps(product_data.get('size_options', [])),
            )
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            return {'success': True, 'data': product.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_products(self, category: Optional[str] = None, sub_category: Optional[str] = None, is_available: Optional[int] = None) -> List[Dict]:
        query = self.db.query(TeaProduct)
        if category:
            query = query.filter(TeaProduct.category == category)
        if sub_category:
            query = query.filter(TeaProduct.sub_category == sub_category)
        if is_available is not None:
            query = query.filter(TeaProduct.is_available == is_available)
        return [p.to_dict() for p in query.order_by(TeaProduct.sort_order).all()]

    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        product = self.db.query(TeaProduct).filter(TeaProduct.id == product_id).first()
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
        product = self.db.query(TeaProduct).filter(TeaProduct.id == product_id).first()
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
            order_no = f"TEA{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = 0
            items = order_data.get('items', [])

            for item in items:
                product = self.db.query(TeaProduct).filter(TeaProduct.id == item['product_id']).first()
                if product:
                    base_price = float(product.price)
                    size = item.get('size', '')
                    if size in ['大杯', 'large']:
                        base_price *= 1.3
                    elif size in ['中杯', 'medium']:
                        base_price *= 1.1
                    item['unit_price'] = base_price
                    item['product_name'] = product.product_name
                    total_amount += base_price * item.get('quantity', 1)

            member_id = order_data.get('member_id')
            discount = 0
            if member_id:
                member = self.db.query(TeaMember).filter(TeaMember.id == member_id).first()
                if member:
                    if member.member_level == 'vip':
                        discount = total_amount * 0.85
                    elif member.member_level == 'gold':
                        discount = total_amount * 0.9
                    points = int(total_amount)
                    member.points += points
                    member.total_consumption += total_amount

            pay_amount = total_amount - discount

            order = TeaOrder(
                order_no=order_no,
                customer_name=order_data.get('customer_name', ''),
                phone=order_data.get('phone', ''),
                member_id=member_id,
                address=order_data.get('address', ''),
                total_amount=total_amount,
                discount=discount,
                pay_amount=pay_amount,
                status=order_data.get('status', 'pending'),
                order_type=order_data.get('order_type', 'dine_in'),
                remark=order_data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            for item in items:
                order_item = TeaOrderItem(
                    order_id=order.id,
                    product_id=item['product_id'],
                    product_name=item.get('product_name', ''),
                    quantity=item.get('quantity', 1),
                    unit_price=item.get('unit_price', 0),
                    total_price=item.get('quantity', 1) * item.get('unit_price', 0),
                    sugar_level=item.get('sugar_level', ''),
                    ice_level=item.get('ice_level', ''),
                    size=item.get('size', ''),
                    remark=item.get('remark', ''),
                )
                self.db.add(order_item)

            self.db.commit()

            return {'success': True, 'data': order.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_orders(self, status: Optional[str] = None, order_type: Optional[str] = None, member_id: Optional[int] = None) -> List[Dict]:
        query = self.db.query(TeaOrder)
        if status:
            query = query.filter(TeaOrder.status == status)
        if order_type:
            query = query.filter(TeaOrder.order_type == order_type)
        if member_id:
            query = query.filter(TeaOrder.member_id == member_id)
        return [o.to_dict() for o in query.order_by(TeaOrder.created_at.desc()).all()]

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(TeaOrder).filter(TeaOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        items = self.db.query(TeaOrderItem).filter(TeaOrderItem.order_id == order_id).all()
        order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(TeaOrder).filter(TeaOrder.id == order_id).first()
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
            category = TeaCategory(
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
        return [c.to_dict() for c in self.db.query(TeaCategory).filter(
            TeaCategory.is_active == 1
        ).order_by(TeaCategory.sort_order).all()]

    def create_member(self, member_data: Dict) -> Dict:
        try:
            member = TeaMember(
                member_name=member_data['member_name'],
                phone=member_data.get('phone', ''),
                email=member_data.get('email', ''),
                member_level=member_data.get('member_level', 'normal'),
                points=member_data.get('points', 0),
                total_consumption=member_data.get('total_consumption', 0.00),
                birthday=member_data.get('birthday'),
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
        query = self.db.query(TeaMember).filter(TeaMember.status == 'active')
        if member_level:
            query = query.filter(TeaMember.member_level == member_level)
        return [m.to_dict() for m in query.order_by(TeaMember.total_consumption.desc()).all()]

    def get_member_by_phone(self, phone: str) -> Optional[Dict]:
        member = self.db.query(TeaMember).filter(TeaMember.phone == phone).first()
        return member.to_dict() if member else None

    def create_ingredient(self, ingredient_data: Dict) -> Dict:
        try:
            ingredient = TeaIngredient(
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
        query = self.db.query(TeaIngredient).filter(TeaIngredient.is_active == 1)
        if low_stock:
            query = query.filter(TeaIngredient.stock <= TeaIngredient.min_stock)
        return [i.to_dict() for i in query.all()]

    def recommend_product(self, preferences: Dict = None) -> List[Dict]:
        products = self.list_products(is_available=1)
        if not preferences:
            return products[:6]

        preferred_categories = preferences.get('categories', [])
        preferred_sugar = preferences.get('sugar_level', '')
        preferred_ice = preferences.get('ice_level', '')

        filtered = []
        for p in products:
            match_score = 0
            if p['category'] in preferred_categories:
                match_score += 2
            if preferred_sugar and p['sugar_levels'] and preferred_sugar in p['sugar_levels']:
                match_score += 1
            if preferred_ice and p['ice_levels'] and preferred_ice in p['ice_levels']:
                match_score += 1
            if match_score > 0:
                p['match_score'] = match_score
                filtered.append(p)

        filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        return filtered[:6]

    def parse_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'order_type': 'dine_in',
            'items': [],
            'customer_name': '',
            'phone': '',
            'member_id': None,
            'address': '',
            'sugar_level': '',
            'ice_level': '',
            'size': '',
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

        sugar_keywords = {'少糖': '少糖', '半糖': '半糖', '全糖': '全糖', '无糖': '无糖'}
        for keyword, level in sugar_keywords.items():
            if keyword in message_text:
                result['sugar_level'] = level
                break

        ice_keywords = {'少冰': '少冰', '多冰': '多冰', '正常冰': '正常冰', '不加冰': '不加冰'}
        for keyword, level in ice_keywords.items():
            if keyword in message_text:
                result['ice_level'] = level
                break

        size_keywords = {'大杯': '大杯', '中杯': '中杯', '小杯': '小杯'}
        for keyword, size in size_keywords.items():
            if keyword in message_text:
                result['size'] = size
                break

        return result

    def generate_sales_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        orders = self.db.query(TeaOrder).filter(
            TeaOrder.created_at >= date_str
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.pay_amount) for o in orders)
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0
        member_orders = len([o for o in orders if o.member_id])

        product_counts = {}
        for order in orders:
            items = self.db.query(TeaOrderItem).filter(TeaOrderItem.order_id == order.id).all()
            for item in items:
                product_name = item.product_name or '未知'
                product_counts[product_name] = product_counts.get(product_name, 0) + item.quantity
        popular_product = max(product_counts, key=product_counts.get) if product_counts else ''

        return {'success': True, 'data': {
            'date': date_str,
            'total_orders': total_orders,
            'total_amount': round(total_amount, 2),
            'avg_order_amount': round(avg_order_amount, 2),
            'popular_product': popular_product,
            'member_orders': member_orders,
        }}

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(TeaOrder).filter(
            TeaOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.pay_amount) for o in orders)
        pending_orders = len([o for o in orders if o.status == 'pending'])
        member_orders = len([o for o in orders if o.member_id])

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'pending_orders': pending_orders,
            'member_orders': member_orders,
            'total_members': len(self.db.query(TeaMember).filter(TeaMember.status == 'active').all()),
            'total_products': len(self.db.query(TeaProduct).filter(TeaProduct.is_available == 1).all()),
        }