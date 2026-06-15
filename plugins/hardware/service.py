import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.hardware.models import (
    HardwareProduct, HardwareOrder, HardwareOrderItem, HardwareCategory,
    HardwareCustomer, HardwareInstallService, HardwareSalesRecord
)

logger = logging.getLogger(__name__)


class HardwareService(BaseService):

    def create_product(self, product_data: Dict) -> Dict:
        try:
            product = HardwareProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                sub_category=product_data.get('sub_category', ''),
                brand=product_data.get('brand', ''),
                spec=product_data.get('spec', ''),
                unit=product_data.get('unit', '件'),
                price=product_data.get('price', 0.00),
                cost_price=product_data.get('cost_price', 0.00),
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
        query = self.db.query(HardwareProduct)
        if category:
            query = query.filter(HardwareProduct.category == category)
        if brand:
            query = query.filter(HardwareProduct.brand == brand)
        if is_available is not None:
            query = query.filter(HardwareProduct.is_available == is_available)
        return [p.to_dict() for p in query.order_by(HardwareProduct.sort_order).all()]

    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        product = self.db.query(HardwareProduct).filter(HardwareProduct.id == product_id).first()
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
        product = self.db.query(HardwareProduct).filter(HardwareProduct.id == product_id).first()
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
            order_no = f"HARD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = 0
            items = order_data.get('items', [])

            for item in items:
                product = self.db.query(HardwareProduct).filter(
                    HardwareProduct.id == item['product_id']
                ).first()
                if product:
                    qty = item.get('quantity', 1)
                    unit_price = float(product.price)
                    item['unit_price'] = unit_price
                    item['product_name'] = product.product_name
                    item['product_code'] = product.product_code
                    total_amount += unit_price * qty

            install_required = order_data.get('install_required', 0)
            if install_required:
                install_service_id = order_data.get('install_service_id')
                if install_service_id:
                    service = self.db.query(HardwareInstallService).filter(
                        HardwareInstallService.id == install_service_id
                    ).first()
                    if service:
                        total_amount += float(service.base_price)

            customer_id = order_data.get('customer_id')
            customer_name = order_data.get('customer_name', '')
            if customer_id:
                customer = self.db.query(HardwareCustomer).filter(HardwareCustomer.id == customer_id).first()
                if customer:
                    customer_name = customer.customer_name
                    customer.total_purchases += total_amount
                    customer.last_purchase_date = date.today()

            discount = order_data.get('discount', 0)
            pay_amount = total_amount - discount

            order = HardwareOrder(
                order_no=order_no,
                customer_id=customer_id,
                customer_name=customer_name,
                phone=order_data.get('phone', ''),
                address=order_data.get('address', ''),
                total_amount=total_amount,
                discount=discount,
                pay_amount=pay_amount,
                status=order_data.get('status', 'pending'),
                order_type=order_data.get('order_type', 'retail'),
                install_required=install_required,
                install_date=order_data.get('install_date'),
                remark=order_data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            for item in items:
                order_item = HardwareOrderItem(
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

    def list_orders(self, status: Optional[str] = None, order_type: Optional[str] = None, install_required: Optional[int] = None) -> List[Dict]:
        query = self.db.query(HardwareOrder)
        if status:
            query = query.filter(HardwareOrder.status == status)
        if order_type:
            query = query.filter(HardwareOrder.order_type == order_type)
        if install_required is not None:
            query = query.filter(HardwareOrder.install_required == install_required)
        return [o.to_dict() for o in query.order_by(HardwareOrder.created_at.desc()).all()]

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(HardwareOrder).filter(HardwareOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        items = self.db.query(HardwareOrderItem).filter(HardwareOrderItem.order_id == order_id).all()
        order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(HardwareOrder).filter(HardwareOrder.id == order_id).first()
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
            category = HardwareCategory(
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
        return [c.to_dict() for c in self.db.query(HardwareCategory).filter(
            HardwareCategory.is_active == 1
        ).order_by(HardwareCategory.sort_order).all()]

    def create_customer(self, customer_data: Dict) -> Dict:
        try:
            customer = HardwareCustomer(
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
        query = self.db.query(HardwareCustomer).filter(HardwareCustomer.status == 'active')
        if customer_level:
            query = query.filter(HardwareCustomer.customer_level == customer_level)
        return [c.to_dict() for c in query.order_by(HardwareCustomer.total_purchases.desc()).all()]

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        customer = self.db.query(HardwareCustomer).filter(HardwareCustomer.phone == phone).first()
        return customer.to_dict() if customer else None

    def create_install_service(self, service_data: Dict) -> Dict:
        try:
            service = HardwareInstallService(
                service_name=service_data['service_name'],
                service_code=service_data.get('service_code', ''),
                base_price=service_data.get('base_price', 0.00),
                description=service_data.get('description', ''),
                duration=service_data.get('duration', 60),
                is_active=service_data.get('is_active', 1),
                sort_order=service_data.get('sort_order', 0),
            )
            self.db.add(service)
            self.db.commit()
            self.db.refresh(service)
            return {'success': True, 'data': service.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_install_services(self) -> List[Dict]:
        return [s.to_dict() for s in self.db.query(HardwareInstallService).filter(
            HardwareInstallService.is_active == 1
        ).order_by(HardwareInstallService.sort_order).all()]

    def parse_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'order_type': 'retail',
            'items': [],
            'customer_name': '',
            'phone': '',
            'customer_id': None,
            'address': '',
            'install_required': 0,
            'remark': '',
            'confidence': 0.7,
        }

        phone_match = re.search(r'(\d{11})', message_text)
        if phone_match:
            result['phone'] = phone_match.group(1)
            customer = self.get_customer_by_phone(result['phone'])
            if customer:
                result['customer_id'] = customer['id']
                result['customer_name'] = customer['customer_name']

        install_keywords = ['安装', '上门', '师傅']
        if any(keyword in message_text for keyword in install_keywords):
            result['install_required'] = 1

        wholesale_keywords = ['批发', '批量']
        if any(keyword in message_text for keyword in wholesale_keywords):
            result['order_type'] = 'wholesale'

        return result

    def generate_sales_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        orders = self.db.query(HardwareOrder).filter(
            HardwareOrder.created_at >= date_str
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.pay_amount) for o in orders)
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0

        install_orders = len([o for o in orders if o.install_required == 1])
        install_amount = sum(float(o.pay_amount) for o in orders if o.install_required == 1)

        return {'success': True, 'data': {
            'date': date_str,
            'total_orders': total_orders,
            'total_amount': round(total_amount, 2),
            'avg_order_amount': round(avg_order_amount, 2),
            'install_orders': install_orders,
            'install_amount': round(install_amount, 2),
        }}

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(HardwareOrder).filter(
            HardwareOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.pay_amount) for o in orders)
        pending_orders = len([o for o in orders if o.status == 'pending'])
        install_orders = len([o for o in orders if o.install_required == 1])

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'pending_orders': pending_orders,
            'install_orders': install_orders,
            'total_customers': len(self.db.query(HardwareCustomer).filter(HardwareCustomer.status == 'active').all()),
            'total_products': len(self.db.query(HardwareProduct).filter(HardwareProduct.is_available == 1).all()),
        }