import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.seafood.models import (
    SeafoodCustomer, SeafoodSupplier, SeafoodProduct,
    SeafoodOrder, SeafoodOrderItem, SeafoodStock,
    SeafoodConfig, SeafoodOrderReminder
)

logger = logging.getLogger(__name__)


class SeafoodService(BaseService):

    DEFAULT_CUTOFF_TIME = '21:00'
    REMINDER_MESSAGE = "老板需要备明天的货吗？"

    def get_config(self, config_key: str, default_value: str = '') -> str:
        config = self.db.query(SeafoodConfig).filter(
            SeafoodConfig.config_key == config_key
        ).first()
        return config.config_value if config else default_value

    def set_config(self, config_key: str, config_value: str, config_type: str = 'string', description: str = '') -> Dict:
        try:
            config = self.db.query(SeafoodConfig).filter(
                SeafoodConfig.config_key == config_key
            ).first()
            if config:
                config.config_value = config_value
                config.config_type = config_type
                config.description = description
            else:
                config = SeafoodConfig(
                    config_key=config_key,
                    config_value=config_value,
                    config_type=config_type,
                    description=description
                )
                self.db.add(config)
            self.db.commit()
            return {'success': True, 'data': config.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_customer(self, customer_data: Dict) -> Dict:
        try:
            customer = SeafoodCustomer(
                customer_name=customer_data['customer_name'],
                phone=customer_data.get('phone', ''),
                wechat_id=customer_data.get('wechat_id', ''),
                customer_type=customer_data.get('customer_type', 'B'),
                address=customer_data.get('address', ''),
                remark=customer_data.get('remark', ''),
                is_active=customer_data.get('is_active', 1),
            )
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            return {'success': True, 'data': customer.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_customers(self, customer_type: Optional[str] = None) -> List[Dict]:
        query = self.db.query(SeafoodCustomer).filter(SeafoodCustomer.is_active == 1)
        if customer_type:
            query = query.filter(SeafoodCustomer.customer_type == customer_type)
        return [c.to_dict() for c in query.order_by(SeafoodCustomer.created_at.desc()).all()]

    def update_customer(self, customer_id: int, customer_data: Dict) -> Dict:
        customer = self.db.query(SeafoodCustomer).filter(SeafoodCustomer.id == customer_id).first()
        if not customer:
            return {'success': False, 'error': '客户不存在'}

        try:
            for key, value in customer_data.items():
                if hasattr(customer, key):
                    setattr(customer, key, value)
            self.db.commit()
            self.db.refresh(customer)
            return {'success': True, 'data': customer.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_customer(self, customer_id: int) -> Dict:
        customer = self.db.query(SeafoodCustomer).filter(SeafoodCustomer.id == customer_id).first()
        if not customer:
            return {'success': False, 'error': '客户不存在'}

        try:
            customer.is_active = 0
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_supplier(self, supplier_data: Dict) -> Dict:
        try:
            supplier = SeafoodSupplier(
                supplier_name=supplier_data['supplier_name'],
                phone=supplier_data.get('phone', ''),
                wechat_id=supplier_data.get('wechat_id', ''),
                supplier_type=supplier_data.get('supplier_type', ''),
                address=supplier_data.get('address', ''),
                contact_person=supplier_data.get('contact_person', ''),
                remark=supplier_data.get('remark', ''),
                is_active=supplier_data.get('is_active', 1),
            )
            self.db.add(supplier)
            self.db.commit()
            self.db.refresh(supplier)
            return {'success': True, 'data': supplier.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_suppliers(self) -> List[Dict]:
        return [s.to_dict() for s in self.db.query(SeafoodSupplier).filter(
            SeafoodSupplier.is_active == 1
        ).order_by(SeafoodSupplier.created_at.desc()).all()]

    def update_supplier(self, supplier_id: int, supplier_data: Dict) -> Dict:
        supplier = self.db.query(SeafoodSupplier).filter(SeafoodSupplier.id == supplier_id).first()
        if not supplier:
            return {'success': False, 'error': '供应商不存在'}

        try:
            for key, value in supplier_data.items():
                if hasattr(supplier, key):
                    setattr(supplier, key, value)
            self.db.commit()
            self.db.refresh(supplier)
            return {'success': True, 'data': supplier.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_product(self, product_data: Dict) -> Dict:
        try:
            product = SeafoodProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                unit=product_data.get('unit', '斤'),
                price=product_data.get('price', 0.00),
                cost_price=product_data.get('cost_price', 0.00),
                stock=product_data.get('stock', 0),
                min_stock=product_data.get('min_stock', 0),
                description=product_data.get('description', ''),
                image_url=product_data.get('image_url', ''),
                is_available=product_data.get('is_available', 1),
                supplier_id=product_data.get('supplier_id'),
            )
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            return {'success': True, 'data': product.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_products(self, category: Optional[str] = None) -> List[Dict]:
        query = self.db.query(SeafoodProduct).filter(SeafoodProduct.is_available == 1)
        if category:
            query = query.filter(SeafoodProduct.category == category)
        return [p.to_dict() for p in query.order_by(SeafoodProduct.product_name).all()]

    def create_order(self, order_data: Dict) -> Dict:
        try:
            customer = self.db.query(SeafoodCustomer).filter(
                SeafoodCustomer.id == order_data['customer_id']
            ).first()
            if not customer:
                return {'success': False, 'error': '客户不存在'}

            order_no = f"SEA{datetime.now().strftime('%Y%m%d%H%M%S')}"
            delivery_date = order_data.get('delivery_date')
            if not delivery_date:
                delivery_date = (date.today() + timedelta(days=1)).isoformat()

            total_amount = 0
            items = order_data.get('items', [])
            for item in items:
                product = self.db.query(SeafoodProduct).filter(
                    SeafoodProduct.id == item['product_id']
                ).first()
                if product:
                    item['unit_price'] = float(product.price)
                    item['product_name'] = product.product_name
                    total_amount += float(product.price) * item.get('quantity', 1)

            is_urgent = order_data.get('is_urgent', 0)
            order_type = 'urgent' if is_urgent else 'normal'

            order = SeafoodOrder(
                order_no=order_no,
                customer_id=order_data['customer_id'],
                customer_name=customer.customer_name,
                customer_type=customer.customer_type,
                delivery_date=delivery_date,
                order_type=order_type,
                is_urgent=is_urgent,
                status='pending',
                total_amount=total_amount,
                remark=order_data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            for item in items:
                order_item = SeafoodOrderItem(
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

            if is_urgent:
                order.boss_notified = 1
                self.db.commit()

            return {
                'success': True,
                'data': order.to_dict(),
                'need_boss_notify': bool(is_urgent),
                'order_items': items
            }
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_orders(self, customer_id: Optional[int] = None, status: Optional[str] = None,
                    is_urgent: Optional[int] = None, delivery_date: Optional[str] = None) -> List[Dict]:
        query = self.db.query(SeafoodOrder)
        if customer_id:
            query = query.filter(SeafoodOrder.customer_id == customer_id)
        if status:
            query = query.filter(SeafoodOrder.status == status)
        if is_urgent is not None:
            query = query.filter(SeafoodOrder.is_urgent == is_urgent)
        if delivery_date:
            query = query.filter(SeafoodOrder.delivery_date == delivery_date)

        orders = query.order_by(SeafoodOrder.created_at.desc()).all()
        result = []
        for order in orders:
            order_dict = order.to_dict()
            items = self.db.query(SeafoodOrderItem).filter(
                SeafoodOrderItem.order_id == order.id
            ).all()
            order_dict['items'] = [item.to_dict() for item in items]
            result.append(order_dict)
        return result

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(SeafoodOrder).filter(SeafoodOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        items = self.db.query(SeafoodOrderItem).filter(
            SeafoodOrderItem.order_id == order_id
        ).all()
        order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(SeafoodOrder).filter(SeafoodOrder.id == order_id).first()
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

    def get_customers_needing_reminder(self) -> List[Dict]:
        cutoff_time = self.get_config('cutoff_time', self.DEFAULT_CUTOFF_TIME)
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        b_customers = self.db.query(SeafoodCustomer).filter(
            SeafoodCustomer.customer_type == 'B',
            SeafoodCustomer.is_active == 1
        ).all()

        customers_needing_reminder = []
        for customer in b_customers:
            has_order = self.db.query(SeafoodOrder).filter(
                SeafoodOrder.customer_id == customer.id,
                SeafoodOrder.delivery_date == tomorrow,
                SeafoodOrder.status != 'cancelled'
            ).first()
            if not has_order:
                customers_needing_reminder.append(customer.to_dict())

        return customers_needing_reminder

    def send_reminder(self, customer_id: int) -> Dict:
        customer = self.db.query(SeafoodCustomer).filter(SeafoodCustomer.id == customer_id).first()
        if not customer:
            return {'success': False, 'error': '客户不存在'}

        cutoff_time = self.get_config('cutoff_time', self.DEFAULT_CUTOFF_TIME)
        tomorrow = date.today() + timedelta(days=1)

        try:
            reminder = SeafoodOrderReminder(
                customer_id=customer_id,
                customer_name=customer.customer_name,
                reminder_date=tomorrow,
                reminder_time=cutoff_time,
                sent_at=datetime.now(),
                status='sent'
            )
            self.db.add(reminder)
            self.db.commit()

            return {
                'success': True,
                'message': self.REMINDER_MESSAGE,
                'customer': customer.to_dict(),
                'reminder': reminder.to_dict()
            }
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def parse_order_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'items': [],
            'is_urgent': False,
            'remark': '',
            'confidence': 0.6,
            'needs_confirmation': False,
            'confirmation_question': '请问这是急单还是常规备货单？'
        }

        urgent_keywords = ['急', '加急', '马上', '立刻', '紧急']
        if any(keyword in message_text for keyword in urgent_keywords):
            result['is_urgent'] = True

        product_pattern = r'([\u4e00-\u9fa5]+)\s*(\d+(?:\.\d+)?)\s*(斤|公斤|条|只|份|盒|袋)?'
        matches = re.findall(product_pattern, message_text)
        for match in matches:
            product_name = match[0].strip()
            quantity = float(match[1])
            unit = match[2] if match[2] else '斤'
            result['items'].append({
                'product_name': product_name,
                'quantity': quantity,
                'unit': unit
            })

        if result['items']:
            result['confidence'] = min(0.8 + len(result['items']) * 0.05, 0.95)

        return result

    def generate_order_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            start_date = date.today().replace(day=1)
            end_date = date.today()
        else:
            dates = date_range.split('~')
            start_date = datetime.strptime(dates[0].strip(), '%Y-%m-%d').date()
            end_date = datetime.strptime(dates[1].strip(), '%Y-%m-%d').date()

        orders = self.db.query(SeafoodOrder).filter(
            SeafoodOrder.created_at >= start_date,
            SeafoodOrder.created_at <= end_date,
            SeafoodOrder.status != 'cancelled'
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.total_amount) for o in orders)
        urgent_orders = len([o for o in orders if o.is_urgent == 1])
        pending_orders = len([o for o in orders if o.status == 'pending'])

        customer_type_stats = {}
        for order in orders:
            c_type = order.customer_type or '未知'
            if c_type not in customer_type_stats:
                customer_type_stats[c_type] = {'count': 0, 'amount': 0}
            customer_type_stats[c_type]['count'] += 1
            customer_type_stats[c_type]['amount'] += float(order.total_amount)

        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0

        return {
            'success': True,
            'data': {
                'date_range': f"{start_date.isoformat()} ~ {end_date.isoformat()}",
                'total_orders': total_orders,
                'total_amount': round(total_amount, 2),
                'avg_order_amount': round(avg_order_amount, 2),
                'urgent_orders': urgent_orders,
                'pending_orders': pending_orders,
                'customer_type_stats': customer_type_stats
            }
        }

    def generate_customer_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            start_date = date.today().replace(day=1)
            end_date = date.today()
        else:
            dates = date_range.split('~')
            start_date = datetime.strptime(dates[0].strip(), '%Y-%m-%d').date()
            end_date = datetime.strptime(dates[1].strip(), '%Y-%m-%d').date()

        orders = self.db.query(SeafoodOrder).filter(
            SeafoodOrder.created_at >= start_date,
            SeafoodOrder.created_at <= end_date,
            SeafoodOrder.status != 'cancelled'
        ).all()

        customer_stats = {}
        for order in orders:
            c_id = order.customer_id
            c_name = order.customer_name or f'客户{c_id}'
            c_type = order.customer_type or '未知'

            if c_id not in customer_stats:
                customer_stats[c_id] = {
                    'customer_id': c_id,
                    'customer_name': c_name,
                    'customer_type': c_type,
                    'order_count': 0,
                    'total_amount': 0,
                    'avg_order_amount': 0
                }
            customer_stats[c_id]['order_count'] += 1
            customer_stats[c_id]['total_amount'] += float(order.total_amount)

        for c_id in customer_stats:
            stats = customer_stats[c_id]
            stats['avg_order_amount'] = round(
                stats['total_amount'] / stats['order_count'], 2
            ) if stats['order_count'] > 0 else 0

        sorted_customers = sorted(
            customer_stats.values(),
            key=lambda x: x['total_amount'],
            reverse=True
        )

        return {
            'success': True,
            'data': {
                'date_range': f"{start_date.isoformat()} ~ {end_date.isoformat()}",
                'total_customers': len(customer_stats),
                'customers': sorted_customers
            }
        }

    def generate_stock_report(self) -> Dict:
        products = self.db.query(SeafoodProduct).filter(SeafoodProduct.is_available == 1).all()

        stock_list = []
        low_stock_count = 0
        total_stock_value = 0

        for product in products:
            current_stock = product.stock or 0
            min_stock = product.min_stock or 0
            is_low = current_stock <= min_stock and min_stock > 0
            if is_low:
                low_stock_count += 1

            stock_value = current_stock * float(product.price) if product.price else 0
            total_stock_value += stock_value

            stock_list.append({
                'product_id': product.id,
                'product_name': product.product_name,
                'category': product.category,
                'unit': product.unit,
                'price': float(product.price) if product.price else 0,
                'current_stock': current_stock,
                'min_stock': min_stock,
                'is_low_stock': is_low,
                'stock_value': round(stock_value, 2)
            })

        return {
            'success': True,
            'data': {
                'total_products': len(products),
                'low_stock_count': low_stock_count,
                'total_stock_value': round(total_stock_value, 2),
                'stock_list': stock_list
            }
        }

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(SeafoodOrder).filter(
            SeafoodOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.total_amount) for o in orders)
        urgent_orders = len([o for o in orders if o.is_urgent == 1])
        pending_orders = len([o for o in orders if o.status == 'pending'])
        b_customers = len(self.db.query(SeafoodCustomer).filter(
            SeafoodCustomer.customer_type == 'B',
            SeafoodCustomer.is_active == 1
        ).all())

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'urgent_orders': urgent_orders,
            'pending_orders': pending_orders,
            'b_customers': b_customers
        }