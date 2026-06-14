"""
订单业务服务
- 订单CRUD
- 幂等性保证
- 状态管理
"""
import uuid
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from models.models import Order, OrderItem, Customer, Product, RawMessage
from database.db_config import SessionLocal

logger = logging.getLogger(__name__)


class OrderService:
    """订单服务类"""

    def __init__(self):
        self.db_session = None

    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self.db_session is None:
            self.db_session = SessionLocal()
        return self.db_session

    def close(self):
        """关闭数据库会话"""
        if self.db_session:
            self.db_session.close()
            self.db_session = None

    def create_or_update_order(self, customer_id: int, items: List[Dict],
                                order_date: date = None, remark: str = None,
                                order_uuid: str = None, source_type: str = 'wechat') -> Dict:
        """
        创建或更新订单(支持幂等性)

        Args:
            customer_id: 客户ID
            items: 商品明细列表 [{"product_id": 1, "quantity": 10.0, "remark": "要嫩的"}]
            order_date: 订单日期(默认今天)
            remark: 订单备注
            order_uuid: 订单唯一标识(用于幂等性,可选)
            source_type: 订单来源

        Returns:
            {"success": bool, "order_id": int, "order_uuid": str, "error": str}
        """
        db = self._get_db()

        try:
            # 生成或使用提供的order_uuid
            if not order_uuid:
                order_uuid = str(uuid.uuid4())

            # 检查是否已存在(幂等性)
            existing_order = db.query(Order).filter(Order.order_uuid == order_uuid).first()
            if existing_order:
                logger.info(f"订单已存在(幂等返回): {order_uuid}")
                return {
                    'success': True,
                    'order_id': existing_order.id,
                    'order_uuid': existing_order.order_uuid,
                    'is_duplicate': True
                }

            # 验证客户
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {'success': False, 'error': f'客户不存在: {customer_id}'}

            if not customer.is_active:
                return {'success': False, 'error': f'客户已禁用: {customer.customer_name}'}

            # 创建订单
            order_date = order_date or date.today()
            order = Order(
                order_uuid=order_uuid,
                customer_id=customer_id,
                order_date=order_date,
                status='pending',
                remark=remark,
                source_type=source_type,
                total_amount=Decimal('0.00')
            )
            db.add(order)
            db.flush()  # 获取order.id

            # 添加订单明细
            total_amount = Decimal('0.00')
            for item_data in items:
                product = db.query(Product).filter(Product.id == item_data['product_id']).first()
                if not product:
                    db.rollback()
                    return {'success': False, 'error': f"商品不存在: {item_data['product_id']}"}

                quantity = Decimal(str(item_data['quantity']))
                unit_price = Decimal(str(product.price))
                subtotal = quantity * unit_price

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.product_name,
                    quantity=quantity,
                    unit=item_data.get('unit', product.unit),
                    unit_price=unit_price,
                    subtotal=subtotal,
                    remark=item_data.get('remark')
                )
                db.add(order_item)
                total_amount += subtotal

            # 更新订单总金额
            order.total_amount = total_amount
            db.commit()
            db.refresh(order)

            logger.info(f"订单创建成功: order_id={order.id}, uuid={order_uuid}, total={total_amount}")

            return {
                'success': True,
                'order_id': order.id,
                'order_uuid': order.order_uuid,
                'total_amount': float(total_amount),
                'is_duplicate': False
            }

        except Exception as e:
            db.rollback()
            logger.error(f"创建订单失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """根据ID获取订单详情"""
        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return None

        return order.to_dict()

    def get_today_orders(self, customer_id: int = None, status: str = None) -> List[Dict]:
        """
        获取今日订单列表

        Args:
            customer_id: 客户ID(可选,筛选特定客户)
            status: 订单状态(可选,筛选特定状态)

        Returns:
            订单列表
        """
        db = self._get_db()
        today = date.today()

        query = db.query(Order).filter(Order.order_date == today)

        if customer_id:
            query = query.filter(Order.customer_id == customer_id)

        if status:
            query = query.filter(Order.status == status)

        orders = query.order_by(Order.created_at.desc()).all()
        return [order.to_dict() for order in orders]

    def modify_order_items(self, order_id: int, items: List[Dict]) -> Dict:
        """
        修改订单明细

        Args:
            order_id: 订单ID
            items: 新的商品明细列表

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {'success': False, 'error': f'订单不存在: {order_id}'}

            # 只有待确认订单可以修改
            if order.status != 'pending':
                return {'success': False, 'error': f'订单状态不允许修改: {order.status}'}

            # 删除原有明细
            db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()

            # 添加新明细
            total_amount = Decimal('0.00')
            for item_data in items:
                product = db.query(Product).filter(Product.id == item_data['product_id']).first()
                if not product:
                    db.rollback()
                    return {'success': False, 'error': f"商品不存在: {item_data['product_id']}"}

                quantity = Decimal(str(item_data['quantity']))
                unit_price = Decimal(str(product.price))
                subtotal = quantity * unit_price

                order_item = OrderItem(
                    order_id=order_id,
                    product_id=product.id,
                    product_name=product.product_name,
                    quantity=quantity,
                    unit=item_data.get('unit', product.unit),
                    unit_price=unit_price,
                    subtotal=subtotal,
                    remark=item_data.get('remark')
                )
                db.add(order_item)
                total_amount += subtotal

            # 更新总金额
            order.total_amount = total_amount
            db.commit()

            logger.info(f"订单明细修改成功: order_id={order_id}")

            return {
                'success': True,
                'order_id': order_id,
                'total_amount': float(total_amount)
            }

        except Exception as e:
            db.rollback()
            logger.error(f"修改订单明细失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def confirm_order(self, order_id: int, confirmed_by: str = 'system') -> Dict:
        """确认订单"""
        db = self._get_db()

        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {'success': False, 'error': f'订单不存在: {order_id}'}

            if order.status != 'pending':
                return {'success': False, 'error': f'订单状态不允许确认: {order.status}'}

            order.status = 'confirmed'
            order.confirmed_by = confirmed_by
            order.confirmed_at = datetime.now()

            db.commit()
            logger.info(f"订单确认成功: order_id={order_id}")

            return {'success': True, 'order_id': order_id, 'status': 'confirmed'}

        except Exception as e:
            db.rollback()
            logger.error(f"确认订单失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def cancel_order(self, order_id: int, reason: str = None) -> Dict:
        """取消订单"""
        db = self._get_db()

        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {'success': False, 'error': f'订单不存在: {order_id}'}

            if order.status in ['completed', 'cancelled']:
                return {'success': False, 'error': f'订单状态不允许取消: {order.status}'}

            order.status = 'cancelled'
            order.remark = f"{order.remark or ''} [取消原因: {reason or '未说明'}]"

            db.commit()
            logger.info(f"订单取消成功: order_id={order_id}")

            return {'success': True, 'order_id': order_id, 'status': 'cancelled'}

        except Exception as e:
            db.rollback()
            logger.error(f"取消订单失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_orders_by_date_range(self, start_date: date, end_date: date,
                                  customer_id: int = None) -> List[Dict]:
        """
        按日期范围查询订单

        Args:
            start_date: 开始日期
            end_date: 结束日期
            customer_id: 客户ID(可选)

        Returns:
            订单列表
        """
        db = self._get_db()

        query = db.query(Order).filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date
        )

        if customer_id:
            query = query.filter(Order.customer_id == customer_id)

        orders = query.order_by(Order.order_date.desc(), Order.created_at.desc()).all()
        return [order.to_dict() for order in orders]

    def get_customer_daily_summary(self, customer_id: int,
                                    order_date: date = None) -> Dict:
        """
        获取客户当日订单汇总(按商品累计)

        返回:
        {
            "customer_id": 1,
            "order_date": "2026-04-15",
            "products": {
                1: {"product_name": "土豆", "total_quantity": 15.0, "unit": "斤"},
                2: {"product_name": "鸡蛋", "total_quantity": 10.0, "unit": "斤"},
                ...
            },
            "total_amount": 102.50
        }
        """
        db = self._get_db()
        order_date = order_date or date.today()

        # 查询当日所有订单
        orders = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.order_date == order_date,
            Order.status != 'cancelled'
        ).all()

        # 按商品累计数量
        product_summary = {}
        total_amount = Decimal('0.00')

        for order in orders:
            total_amount += order.total_amount

            for item in order.items:
                pid = item.product_id
                if pid not in product_summary:
                    product_summary[pid] = {
                        'product_name': item.product_name,
                        'total_quantity': Decimal('0.00'),
                        'unit': item.unit
                    }
                product_summary[pid]['total_quantity'] += item.quantity

        # 转换Decimal为float以便JSON序列化
        products_serializable = {}
        for pid, data in product_summary.items():
            products_serializable[pid] = {
                'product_name': data['product_name'],
                'total_quantity': float(data['total_quantity']),
                'unit': data['unit']
            }

        return {
            'customer_id': customer_id,
            'order_date': order_date.isoformat(),
            'products': products_serializable,
            'total_amount': float(total_amount)
        }

    def apply_incremental_order(self, customer_id: int,
                                 product_id: int,
                                 operation: str,  # add/subtract/replace
                                 quantity: float,
                                 order_date: date = None,
                                 remark: str = None) -> Dict:
        """
        应用增量订单操作

        逻辑:
        1. 查询客户当日该商品的累计数量
        2. 根据操作类型计算新数量
        3. 创建新的订单项(允许负值)
        4. 记录调整日志

        示例:
        - 已有: 鸡蛋10斤
        - 收到: "鸡蛋+5斤" -> 新订单: 鸡蛋5斤 (累计15斤)
        - 收到: "鸡蛋-3斤" -> 新订单: 鸡蛋-3斤 (累计7斤)
        - 收到: "鸡蛋=15斤" -> 新订单: 鸡蛋5斤 (累计15斤, 假设原10斤)
        """
        from models.models import OrderAdjustmentLog

        db = self._get_db()
        order_date = order_date or date.today()

        try:
            # 1. 查询当日累计数量
            summary = self.get_customer_daily_summary(customer_id, order_date)
            current_qty = Decimal('0.00')

            if product_id in summary['products']:
                current_qty = Decimal(str(summary['products'][product_id]['total_quantity']))

            # 2. 计算新订单数量
            qty_decimal = Decimal(str(quantity))
            if operation == 'add':
                order_quantity = qty_decimal
                new_total = current_qty + qty_decimal
            elif operation == 'subtract':
                order_quantity = -qty_decimal  # 负数订单
                new_total = current_qty - qty_decimal
            elif operation == 'replace':
                order_quantity = qty_decimal - current_qty
                new_total = qty_decimal
            else:
                return {'success': False, 'error': f'未知操作类型: {operation}'}

            # 3. 获取商品信息
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return {'success': False, 'error': f'商品不存在: {product_id}'}

            # 4. 创建订单(允许数量为负)
            order_uuid = str(uuid.uuid4())
            items = [{
                'product_id': product_id,
                'quantity': float(order_quantity),
                'unit': product.unit,
                'remark': remark or f'{operation.upper()}操作'
            }]

            result = self.create_or_update_order(
                customer_id=customer_id,
                items=items,
                order_date=order_date,
                order_uuid=order_uuid,
                remark=f'增量操作: {operation} {abs(quantity)}{product.unit}'
            )

            # 5. 记录调整日志
            if result['success']:
                log = OrderAdjustmentLog(
                    order_id=result['order_id'],
                    customer_id=customer_id,
                    product_id=product_id,
                    adjustment_type=operation,
                    quantity_change=float(order_quantity),
                    original_quantity=float(current_qty),
                    new_quantity=float(new_total),
                    reason=remark
                )
                db.add(log)
                db.commit()

                logger.info(f"增量订单成功: customer={customer_id}, "
                           f"product={product_id}, op={operation}, "
                           f"qty={order_quantity}, new_total={new_total}")

            return {
                'success': result['success'],
                'operation': operation,
                'original_quantity': float(current_qty),
                'change': float(order_quantity),
                'new_total': float(new_total),
                'order_id': result.get('order_id')
            }

        except Exception as e:
            db.rollback()
            logger.error(f"增量订单失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def create_batch_selection_order(self, customer_id: int,
                                      product_ids: List[int],
                                      quantity: float,
                                      unit: str = '斤',
                                      order_date: date = None,
                                      remark: str = None) -> Dict:
        """
        创建批量圈选订单

        参数:
        - customer_id: 客户ID
        - product_ids: 商品ID列表 [1,2,3,5,6,7,8,9,10] (已排除3,7)
        - quantity: 每个商品的数量
        - unit: 单位
        - order_date: 订单日期
        - remark: 备注

        返回:
        {
            'success': True,
            'order_id': 123,
            'items_count': 9,
            'total_amount': 225.50
        }
        """
        db = self._get_db()
        order_date = order_date or date.today()

        try:
            # 构建订单项列表
            items = []
            for product_id in product_ids:
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    logger.warning(f"商品不存在: {product_id}, 跳过")
                    continue

                items.append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'unit': unit,
                    'remark': remark
                })

            if not items:
                return {'success': False, 'error': '没有有效的商品'}

            # 创建订单
            order_uuid = str(uuid.uuid4())
            result = self.create_or_update_order(
                customer_id=customer_id,
                items=items,
                order_date=order_date,
                order_uuid=order_uuid,
                remark=f'批量圈选: {len(items)}个商品'
            )

            return result

        except Exception as e:
            db.rollback()
            logger.error(f"批量圈选订单失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


# 全局单例
order_service = OrderService()
