import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.phoneparts.models import (
    PhoneProduct, PhoneOrder, PhoneOrderItem, PhoneCategory,
    PhoneCustomer, PhoneModel, PhoneRepairService, PhoneSalesRecord
)

logger = logging.getLogger(__name__)


class PhonePartsService(BaseService):

    def create_product(self, product_data: Dict) -> Dict:
        try:
            compatible_models = product_data.get('compatible_models', [])
            product = PhoneProduct(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code', ''),
                category=product_data.get('category', ''),
                sub_category=product_data.get('sub_category', ''),
                brand=product_data.get('brand', ''),
                spec=product_data.get('spec', ''),
                compatible_models=json.dumps(compatible_models) if compatible_models else None,
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

    def list_products(self, category: Optional[str] = None, brand: Optional[str] = None, model: Optional[str] = None) -> List[Dict]:
        query = self.db.query(PhoneProduct).filter(PhoneProduct.is_available == 1)
        if category:
            query = query.filter(PhoneProduct.category == category)
        if brand:
            query = query.filter(PhoneProduct.brand == brand)
        products = [p.to_dict() for p in query.order_by(PhoneProduct.sort_order).all()]
        if model:
            products = [p for p in products if model in p['compatible_models']]
        return products

    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        product = self.db.query(PhoneProduct).filter(PhoneProduct.id == product_id).first()
        if not product:
            return {'success': False, 'error': '商品不存在'}

        try:
            if 'compatible_models' in product_data:
                product_data['compatible_models'] = json.dumps(product_data['compatible_models'])
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
        product = self.db.query(PhoneProduct).filter(PhoneProduct.id == product_id).first()
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
            order_no = f"PHONE{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = 0
            items = order_data.get('items', [])

            for item in items:
                product = self.db.query(PhoneProduct).filter(
                    PhoneProduct.id == item['product_id']
                ).first()
                if product:
                    qty = item.get('quantity', 1)
                    unit_price = float(product.price)
                    item['unit_price'] = unit_price
                    item['product_name'] = product.product_name
                    item['product_code'] = product.product_code
                    total_amount += unit_price * qty

            repair_required = order_data.get('repair_required', 0)
            if repair_required:
                repair_service_id = order_data.get('repair_service_id')
                if repair_service_id:
                    service = self.db.query(PhoneRepairService).filter(
                        PhoneRepairService.id == repair_service_id
                    ).first()
                    if service:
                        total_amount += float(service.base_price)

            customer_id = order_data.get('customer_id')
            customer_name = order_data.get('customer_name', '')
            if customer_id:
                customer = self.db.query(PhoneCustomer).filter(PhoneCustomer.id == customer_id).first()
                if customer:
                    customer_name = customer.customer_name
                    customer.total_purchases += total_amount
                    customer.last_purchase_date = date.today()

            discount = order_data.get('discount', 0)
            pay_amount = total_amount - discount

            order = PhoneOrder(
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
                repair_required=repair_required,
                repair_date=order_data.get('repair_date'),
                phone_model=order_data.get('phone_model', ''),
                remark=order_data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            for item in items:
                order_item = PhoneOrderItem(
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

    def list_orders(self, status: Optional[str] = None, order_type: Optional[str] = None, repair_required: Optional[int] = None) -> List[Dict]:
        query = self.db.query(PhoneOrder)
        if status:
            query = query.filter(PhoneOrder.status == status)
        if order_type:
            query = query.filter(PhoneOrder.order_type == order_type)
        if repair_required is not None:
            query = query.filter(PhoneOrder.repair_required == repair_required)
        return [o.to_dict() for o in query.order_by(PhoneOrder.created_at.desc()).all()]

    def get_order(self, order_id: int) -> Optional[Dict]:
        order = self.db.query(PhoneOrder).filter(PhoneOrder.id == order_id).first()
        if not order:
            return None

        order_dict = order.to_dict()
        items = self.db.query(PhoneOrderItem).filter(PhoneOrderItem.order_id == order_id).all()
        order_dict['items'] = [item.to_dict() for item in items]
        return order_dict

    def update_order_status(self, order_id: int, status: str) -> Dict:
        order = self.db.query(PhoneOrder).filter(PhoneOrder.id == order_id).first()
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
            category = PhoneCategory(
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
        return [c.to_dict() for c in self.db.query(PhoneCategory).filter(
            PhoneCategory.is_active == 1
        ).order_by(PhoneCategory.sort_order).all()]

    def create_customer(self, customer_data: Dict) -> Dict:
        try:
            customer = PhoneCustomer(
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
        query = self.db.query(PhoneCustomer).filter(PhoneCustomer.status == 'active')
        if customer_level:
            query = query.filter(PhoneCustomer.customer_level == customer_level)
        return [c.to_dict() for c in query.order_by(PhoneCustomer.total_purchases.desc()).all()]

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        customer = self.db.query(PhoneCustomer).filter(PhoneCustomer.phone == phone).first()
        return customer.to_dict() if customer else None

    def create_phone_model(self, model_data: Dict) -> Dict:
        try:
            model = PhoneModel(
                brand=model_data['brand'],
                model_name=model_data['model_name'],
                model_code=model_data.get('model_code', ''),
                release_date=model_data.get('release_date'),
                screen_size=model_data.get('screen_size', ''),
                image_url=model_data.get('image_url', ''),
                is_active=model_data.get('is_active', 1),
            )
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return {'success': True, 'data': model.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_phone_models(self, brand: Optional[str] = None) -> List[Dict]:
        query = self.db.query(PhoneModel).filter(PhoneModel.is_active == 1)
        if brand:
            query = query.filter(PhoneModel.brand == brand)
        return [m.to_dict() for m in query.order_by(PhoneModel.model_name).all()]

    def create_repair_service(self, service_data: Dict) -> Dict:
        try:
            service = PhoneRepairService(
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

    def list_repair_services(self) -> List[Dict]:
        return [s.to_dict() for s in self.db.query(PhoneRepairService).filter(
            PhoneRepairService.is_active == 1
        ).order_by(PhoneRepairService.sort_order).all()]

    def parse_message(self, message_text: str) -> Dict:
        result = {
            'success': True,
            'order_type': 'retail',
            'items': [],
            'customer_name': '',
            'phone': '',
            'customer_id': None,
            'address': '',
            'repair_required': 0,
            'phone_model': '',
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

        repair_keywords = ['维修', '换屏', '换电池', '修理', '坏了']
        if any(keyword in message_text for keyword in repair_keywords):
            result['repair_required'] = 1

        brand_keywords = {
            '苹果': 'iPhone',
            '华为': 'Huawei',
            '小米': 'Xiaomi',
            '三星': 'Samsung',
            'OPPO': 'OPPO',
            'vivo': 'vivo',
        }
        for keyword, brand in brand_keywords.items():
            if keyword in message_text:
                result['phone_model'] = brand
                break

        wholesale_keywords = ['批发', '批量']
        if any(keyword in message_text for keyword in wholesale_keywords):
            result['order_type'] = 'wholesale'

        return result

    def generate_sales_report(self, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        orders = self.db.query(PhoneOrder).filter(
            PhoneOrder.created_at >= date_str
        ).all()

        total_orders = len(orders)
        total_amount = sum(float(o.pay_amount) for o in orders)
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0

        repair_orders = len([o for o in orders if o.repair_required == 1])
        repair_amount = sum(float(o.pay_amount) for o in orders if o.repair_required == 1)

        return {'success': True, 'data': {
            'date': date_str,
            'total_orders': total_orders,
            'total_amount': round(total_amount, 2),
            'avg_order_amount': round(avg_order_amount, 2),
            'repair_orders': repair_orders,
            'repair_amount': round(repair_amount, 2),
        }}

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        orders = self.db.query(PhoneOrder).filter(
            PhoneOrder.created_at >= start_date
        ).all()

        total_amount = sum(float(o.pay_amount) for o in orders)
        pending_orders = len([o for o in orders if o.status == 'pending'])
        repair_orders = len([o for o in orders if o.repair_required == 1])

        return {
            'period': period,
            'total_orders': len(orders),
            'total_amount': round(total_amount, 2),
            'pending_orders': pending_orders,
            'repair_orders': repair_orders,
            'total_customers': len(self.db.query(PhoneCustomer).filter(PhoneCustomer.status == 'active').all()),
            'total_products': len(self.db.query(PhoneProduct).filter(PhoneProduct.is_available == 1).all()),
            'total_models': len(self.db.query(PhoneModel).filter(PhoneModel.is_active == 1).all()),
        }