import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.fooddelivery.models import (
    FoodProduct, FoodOrder, FoodOrderItem, FoodCategory, FoodTable,
    FoodStaff, FoodSalesRecord, FoodPromotion
)

logger = logging.getLogger(__name__)


class FoodDeliveryService(BaseService):

    def create_product(self, product_data: Dict) -> Dict:
        try:
            product = FoodProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                price=product_data.get('price', 0.00),
                cost_price=product_data.get('cost_price', 0.00),
                unit=product_data.get('unit', '份'),
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

    def list_products(self, category: Optional[str] = None, is_available: Optional[int] = None) -> List[Dict]:
        query = self.db.query(FoodProduct)
        if category:
            query = query.filter(FoodProduct.category == category)
        if is_available is not None:
            query = query.filter(FoodProduct.is_available == is_available)
        return [p.to_dict() for p in query.order_by(FoodProduct.sort_order).all()]

    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        product = self.db.query(FoodProduct).filter(FoodProduct.id == product_id).first()
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
        product = self.db.query(FoodProduct).filter(FoodProduct.id == product_id).first()
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
            order_no = f"FOOD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = 0
            items = order_data.get('items', [])

            for item in items:
                product = self.db.query(FoodProduct).filter(FoodProduct.id == item['product_id']).first()
                if product:
                    item['unit_price'] = float(product.price)
                    item['product_name'] = product.product_name
                    total_amount += float(product.price) * item.get('quantity', 1)

            discount = order_data.get('discount', 0)
            pay_amount = total_amount - discount

            order = FoodOrder(
                order_no=order_no,
                customer_name=order_data.get('customer_name', ''),
                phone=order_data.get('phone', ''),
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
                order_item = FoodOrderItem(
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

    def list_orders(self, status: Optional[str] = None, order_type: Optional[str] = None) -> List[Dict]:
        query = self.db.query(FoodOrder)
        if status:
            query = query.filter(FoodOrder.status == status)
        if order_type:
            query = query.filter(FoodOrder.order_type == order_type)
        return [o.to_dict() for o in query.order_by(FoodOrder.created_at.desc()).all()]

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(FoodOrder).filter(FoodOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        items = self.db.query(FoodOrderItem).filter(FoodOrderItem.order_id == order_id).all()
        order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(FoodOrder).filter(FoodOrder.id == order_id).first()
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
            category = FoodCategory(
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
        return [c.to_dict() for c in self.db.query(FoodCategory).filter(
            FoodCategory.is_active == 1
        ).order_by(FoodCategory.sort_order).all()]

    def create_table(self, table_data: Dict) -> Dict:
        try:
            table = FoodTable(
                table_no=table_data['table_no'],
                table_name=table_data.get('table_name', ''),
                seats=table_data.get('seats', 4),
                area=table_data.get('area', ''),
            )
            self.db.add(table)
            self.db.commit()
            self.db.refresh(table)
            return {'success': True, 'data': table.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_tables(self, area: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        query = self.db.query(FoodTable)
        if area:
            query = query.filter(FoodTable.area == area)
        if status:
            query = query.filter(FoodTable.status == status)
        return [t.to_dict() for t in query.all()]

    def occupy_table(self, table_id: int, order_id: int) -> Dict:
        table = self.db.query(FoodTable).filter(FoodTable.id == table_id).first()
        if not table:
            return {'success': False, 'error': '桌台不存在'}

        try:
            table.status = 'occupied'
            table.current_order_id = order_id
            self.db.commit()
            self.db.refresh(table)
            return {'success': True, 'data': table.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def free_table(self, table_id: int) -> Dict:
        table = self.db.query(FoodTable).filter(FoodTable.id == table_id).first()
        if not table:
            return {'success': False, 'error': '桌台不存在'}

        try:
            table.status = 'free'
            table.current_order_id = None
            self.db.commit()
            self.db.refresh(table)
            return {'success': True, 'data': table.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_staff(self, staff_data: Dict) -> Dict:
        try:
            staff = FoodStaff(
                name=staff_data['name'],
                phone=staff_data.get('phone', ''),
                position=staff_data.get('position', ''),
                status=staff_data.get('status', 'active'),
            )
            self.db.add(staff)
            self.db.commit()
            self.db.refresh(staff)
            return {'success': True, 'data': staff.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_staff(self) -> List[Dict]:
        return [s.to_dict() for s in self.db.query(FoodStaff).filter(
            FoodStaff.status == 'active'
        ).all()]

    def create_promotion(self, promotion_data: Dict) -> Dict:
        try:
            promotion = FoodPromotion(
                promotion_name=promotion_data['promotion_name'],
                promotion_type=promotion_data.get('promotion_type', 'discount'),
                discount_rate=promotion_data.get('discount_rate', 0),
                min_amount=promotion_data.get('min_amount', 0),
                max_discount=promotion_data.get('max_discount', 0),
                start_date=promotion_data.get('start_date'),
                end_date=promotion_data.get('end_date'),
                product_ids=json.dumps(promotion_data.get('product_ids', [])),
                is_active=promotion_data.get('is_active', 1),
            )
            self.db.add(promotion)
            self.db.commit()
            self.db.refresh(promotion)
            return {'success': True, 'data': promotion.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_promotions(self) -> List[Dict]:
        return [p.to_dict() for p in self.db.query(FoodPromotion).filter(
            FoodPromotion.is_active == 1
        ).all()]

    def calculate_discount(self, order_data: Dict) -> float:
        total_amount = order_data.get('total_amount', 0)
        discount = 0

        promotions = self.list_promotions()
        for promotion in promotions:
            if promotion['min_amount'] <= total_amount:
                promo_discount = total_amount * promotion['discount_rate']
                if promotion['max_discount'] > 0:
                    promo_discount = min(promo_discount, promotion['max_discount'])
                discount = max(discount, promo_discount)

        return discount

    def generate_sales_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        orders = self.db.query(FoodOrder).filter(
            FoodOrder.created_at >= date_str
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.pay_amount) for o in orders)
        dine_in_orders = len([o for o in orders if o.order_type == 'dine_in'])
        takeout_orders = len([o for o in orders if o.order_type == 'takeout'])
        delivery_orders = len([o for o in orders if o.order_type == 'delivery'])

        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0

        report = {
            'date': date_str,
            'total_orders': total_orders,
            'total_amount': round(total_amount, 2),
            'dine_in_orders': dine_in_orders,
            'takeout_orders': takeout_orders,
            'delivery_orders': delivery_orders,
            'avg_order_amount': round(avg_order_amount, 2),
        }

        return {'success': True, 'data': report}

    def parse_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'order_type': 'dine_in',
            'items': [],
            'customer_name': '',
            'phone': '',
            'address': '',
            'remark': '',
            'confidence': 0.7,
        }

        phone_match = re.search(r'(\d{11})', message_text)
        if phone_match:
            result['phone'] = phone_match.group(1)

        address_keywords = ['地址', '送到', '外卖', '配送']
        if any(keyword in message_text for keyword in address_keywords):
            result['order_type'] = 'delivery'

        return result

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(FoodOrder).filter(
            FoodOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.pay_amount) for o in orders)
        pending_orders = len([o for o in orders if o.status == 'pending'])

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'pending_orders': pending_orders,
            'active_tables': len(self.db.query(FoodTable).filter(FoodTable.status == 'occupied').all()),
            'total_tables': len(self.db.query(FoodTable).all()),
        }