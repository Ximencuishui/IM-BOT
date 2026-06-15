"""
机器人报表查询服务
提供销售员线路汇总、客户订单查询等文本报表生成功能
"""
import logging
from datetime import date, datetime
from typing import List, Dict, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from models.models import Order, OrderItem, Customer, DeliveryRoute, Product
from database.db_config import SessionLocal

logger = logging.getLogger(__name__)


class RobotReportService:
    """机器人报表服务"""

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """获取数据库会话"""
        return SessionLocal()

    def get_sales_route_summary(self, sales_person: str, order_date: date = None) -> Dict:
        """
        获取销售员负责线路的实时汇总

        参数:
        - sales_person: 销售员姓名
        - order_date: 查询日期(默认今天)

        返回:
        {
            "sales_person": "李四",
            "order_date": "2026-04-15",
            "routes": [
                {
                    "route_name": "A线",
                    "order_count": 8,
                    "customer_count": 6,
                    "total_amount": 2350.00,
                    "customers": ["张三餐馆", "李四食堂"]
                }
            ],
            "total_orders": 13,
            "total_amount": 4030.00
        }
        """
        db = self._get_db()
        order_date = order_date or date.today()

        try:
            # 查询该销售员负责的所有客户
            customers = db.query(Customer).filter(
                Customer.sales_person == sales_person,
                Customer.is_active == 1
            ).all()

            if not customers:
                return {
                    'success': False,
                    'error': f'未找到销售员 {sales_person} 负责的客户'
                }

            customer_ids = [c.id for c in customers]

            # 查询当日订单
            orders = db.query(Order).filter(
                Order.customer_id.in_(customer_ids),
                Order.order_date == order_date,
                Order.status != 'cancelled'
            ).all()

            # 按线路分组统计
            route_stats = {}
            total_orders = 0
            total_amount = Decimal('0.00')

            for order in orders:
                customer = order.customer
                if not customer:
                    continue

                route_name = customer.route.route_name if customer.route else '未分配'

                if route_name not in route_stats:
                    route_stats[route_name] = {
                        'route_name': route_name,
                        'order_count': 0,
                        'customers': set(),
                        'total_amount': Decimal('0.00')
                    }

                stats = route_stats[route_name]
                stats['order_count'] += 1
                stats['customers'].add(customer.customer_name)
                stats['total_amount'] += order.total_amount

                total_orders += 1
                total_amount += order.total_amount

            # 转换为可序列化格式
            routes_list = []
            for route_name, stats in sorted(route_stats.items()):
                routes_list.append({
                    'route_name': route_name,
                    'order_count': stats['order_count'],
                    'customer_count': len(stats['customers']),
                    'total_amount': float(stats['total_amount']),
                    'customers': sorted(list(stats['customers']))
                })

            return {
                'success': True,
                'sales_person': sales_person,
                'order_date': order_date.isoformat(),
                'routes': routes_list,
                'total_orders': total_orders,
                'total_amount': float(total_amount)
            }

        except Exception as e:
            logger.error(f"获取销售员汇总失败: sales_person={sales_person}, error={e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_customer_order_detail(self, customer_id: int, order_date: date = None) -> Dict:
        """
        获取客户当日订单详情

        参数:
        - customer_id: 客户ID
        - order_date: 查询日期(默认今天)

        返回:
        {
            "customer_name": "张三餐馆",
            "order_date": "2026-04-15",
            "orders": [
                {
                    "order_id": 123,
                    "items": [
                        {"product_name": "土豆", "quantity": 10.0, "unit": "斤", "subtotal": 25.0}
                    ]
                }
            ],
            "total_amount": 150.00
        }
        """
        db = self._get_db()
        order_date = order_date or date.today()

        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {'success': False, 'error': f'客户不存在: {customer_id}'}

            # 查询当日所有订单
            orders = db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.order_date == order_date,
                Order.status != 'cancelled'
            ).order_by(Order.created_at).all()

            order_details = []
            total_amount = Decimal('0.00')

            for order in orders:
                items = []
                for item in order.items:
                    items.append({
                        'product_name': item.product_name,
                        'quantity': float(item.quantity),
                        'unit': item.unit,
                        'unit_price': float(item.unit_price),
                        'subtotal': float(item.subtotal),
                        'remark': item.remark
                    })

                order_details.append({
                    'order_id': order.id,
                    'created_at': order.created_at.strftime('%H:%M:%S'),
                    'items': items,
                    'order_total': float(order.total_amount)
                })

                total_amount += order.total_amount

            return {
                'success': True,
                'customer_name': customer.customer_name,
                'order_date': order_date.isoformat(),
                'orders': order_details,
                'total_amount': float(total_amount),
                'order_count': len(orders)
            }

        except Exception as e:
            logger.error(f"获取客户订单详情失败: customer_id={customer_id}, error={e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def generate_text_report(self, summary_data: Dict, report_type: str = 'sales') -> str:
        """
        生成适合微信发送的文本报表

        参数:
        - summary_data: 汇总数据(来自get_sales_route_summary或get_customer_order_detail)
        - report_type: 报表类型 (sales/customer)

        返回: 文本格式的报表
        """
        if report_type == 'sales':
            return self._generate_sales_report_text(summary_data)
        elif report_type == 'customer':
            return self._generate_customer_report_text(summary_data)
        else:
            return '未知的报表类型'

    def _generate_sales_report_text(self, data: Dict) -> str:
        """生成销售员线路汇总文本报表"""
        if not data.get('success'):
            return f"❌ 查询失败: {data.get('error', '未知错误')}"

        lines = []
        lines.append(f"📊 【今日订单汇总 - {data['order_date']}】")
        lines.append(f"👤 销售员: {data['sales_person']}")
        lines.append("")

        for route in data['routes']:
            lines.append(f"📍 {route['route_name']}")
            lines.append(f"   ├─ 订单数: {route['order_count']}单")
            lines.append(f"   ├─ 客户数: {route['customer_count']}家")
            lines.append(f"   └─ 总金额: ¥{route['total_amount']:.2f}")
            lines.append("")

        lines.append(f"💰 合计: {data['total_orders']}单 / ¥{data['total_amount']:.2f}")

        return "\n".join(lines)

    def _generate_customer_report_text(self, data: Dict) -> str:
        """生成客户订单详情文本报表"""
        if not data.get('success'):
            return f"❌ 查询失败: {data.get('error', '未知错误')}"

        lines = []
        lines.append(f"📋 【订单详情 - {data['order_date']}】")
        lines.append(f"👤 客户: {data['customer_name']}")
        lines.append("")

        if not data['orders']:
            lines.append("⚠️ 今日暂无订单")
        else:
            for idx, order in enumerate(data['orders'], 1):
                lines.append(f"🛒 订单#{idx} ({order['created_at']})")
                for item in order['items']:
                    remark_text = f" ({item['remark']})" if item.get('remark') else ""
                    lines.append(
                        f"   ├─ {item['product_name']} "
                        f"{item['quantity']}{item['unit']} "
                        f"¥{item['subtotal']:.2f}{remark_text}"
                    )
                lines.append(f"   └─ 小计: ¥{order['order_total']:.2f}")
                lines.append("")

            lines.append(f"💰 总计: ¥{data['total_amount']:.2f} ({data['order_count']}单)")

        return "\n".join(lines)

    def get_today_overview(self) -> Dict:
        """
        获取今日全局概览(所有销售员/线路)

        返回:
        {
            "date": "2026-04-15",
            "total_orders": 50,
            "total_amount": 12500.00,
            "by_sales": [...],
            "by_route": [...]
        }
        """
        db = self._get_db()
        today = date.today()

        try:
            orders = db.query(Order).filter(
                Order.order_date == today,
                Order.status != 'cancelled'
            ).all()

            # 按销售员统计
            sales_stats = {}
            route_stats = {}
            total_amount = Decimal('0.00')

            for order in orders:
                customer = order.customer
                if not customer:
                    continue

                sales_person = customer.sales_person or '未分配'
                route_name = customer.route.route_name if customer.route else '未分配'

                # 销售员统计
                if sales_person not in sales_stats:
                    sales_stats[sales_person] = {
                        'sales_person': sales_person,
                        'order_count': 0,
                        'total_amount': Decimal('0.00')
                    }
                sales_stats[sales_person]['order_count'] += 1
                sales_stats[sales_person]['total_amount'] += order.total_amount

                # 线路统计
                if route_name not in route_stats:
                    route_stats[route_name] = {
                        'route_name': route_name,
                        'order_count': 0,
                        'total_amount': Decimal('0.00')
                    }
                route_stats[route_name]['order_count'] += 1
                route_stats[route_name]['total_amount'] += order.total_amount

                total_amount += order.total_amount

            return {
                'success': True,
                'date': today.isoformat(),
                'total_orders': len(orders),
                'total_amount': float(total_amount),
                'by_sales': [
                    {'sales_person': k, 'order_count': v['order_count'], 'total_amount': float(v['total_amount'])}
                    for k, v in sorted(sales_stats.items())
                ],
                'by_route': [
                    {'route_name': k, 'order_count': v['order_count'], 'total_amount': float(v['total_amount'])}
                    for k, v in sorted(route_stats.items())
                ]
            }

        except Exception as e:
            logger.error(f"获取今日概览失败: error={e}", exc_info=True)
            return {'success': False, 'error': str(e)}


# 全局单例
robot_report_service = RobotReportService()
