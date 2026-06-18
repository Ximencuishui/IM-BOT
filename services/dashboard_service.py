"""
数据统计服务
提供多维度统计数据，支持图表展示

优化: 高频查询使用本地缓存，减少数据库压力
"""
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import Order, OrderItem, Product, Customer
from models.user_models import User
from utils.cache import cached


class DashboardService:
    """数据看板服务"""

    @staticmethod
    @cached(ttl=30, key_prefix='overview', ignore_args=(0,))
    def get_overview_stats(db: Session, user_id: int, period: str = 'today') -> Dict:
        """
        获取概览统计数据
        :param period: today/week/month/custom
        :return: 统计数据
        """
        now = datetime.now()

        # 计算时间范围
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0).date()
            end_date = start_date + timedelta(days=1)
        elif period == 'week':
            start_date = (now - timedelta(days=now.weekday())).date()
            end_date = start_date + timedelta(days=7)
        elif period == 'month':
            start_date = now.replace(day=1).date()
            next_month = now.replace(day=28) + timedelta(days=4)
            end_date = next_month.replace(day=1).date()
        else:
            # custom需要额外参数
            start_date = now.date() - timedelta(days=7)
            end_date = now.date() + timedelta(days=1)

        # 查询订单统计
        orders_query = db.query(Order).filter(
            Order.order_date >= start_date,
            Order.order_date < end_date
        )

        total_orders = orders_query.count()
        total_amount = orders_query.with_entities(func.sum(Order.total_amount)).scalar() or 0

        # 按状态统计
        status_stats = orders_query.with_entities(
            Order.status,
            func.count(Order.id)
        ).group_by(Order.status).all()

        # 商品种类统计
        products_count = db.query(Product).count()

        # 客户数量统计
        customers_count = db.query(Customer).count()

        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_orders': total_orders,
            'total_amount': float(total_amount),
            'avg_order_amount': float(total_amount / total_orders) if total_orders > 0 else 0,
            'status_breakdown': dict(status_stats),
            'products_count': products_count,
            'customers_count': customers_count
        }

    @staticmethod
    @cached(ttl=60, key_prefix='sales_chart', ignore_args=(0,))
    def get_sales_chart_data(db: Session, user_id: int, days: int = 7) -> Dict:
        """
        获取销售趋势图表数据（折线图）
        :param days: 天数
        :return: 图表数据
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # 按日期分组统计
        daily_stats = db.query(
            Order.order_date,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('daily_amount')
        ).filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).group_by(Order.order_date).order_by(Order.order_date).all()

        dates = []
        order_counts = []
        amounts = []

        # 填充所有日期（包括没有订单的日期）
        current_date = start_date
        stats_dict = {str(row.order_date): row for row in daily_stats}

        while current_date <= end_date:
            dates.append(current_date.isoformat())
            if str(current_date) in stats_dict:
                row = stats_dict[str(current_date)]
                order_counts.append(row.order_count)
                amounts.append(float(row.daily_amount))
            else:
                order_counts.append(0)
                amounts.append(0.0)
            current_date += timedelta(days=1)

        return {
            'dates': dates,
            'order_counts': order_counts,
            'amounts': amounts
        }

    @staticmethod
    @cached(ttl=120, key_prefix='product_ranking', ignore_args=(0,))
    def get_product_ranking(db: Session, user_id: int, limit: int = 10,
                            period: str = 'week') -> Dict:
        """
        获取商品销量排行（柱状图）
        :param limit: 返回数量
        :param period: 统计周期
        :return: 排行数据
        """
        now = datetime.now()

        if period == 'week':
            start_date = (now - timedelta(days=now.weekday())).date()
        elif period == 'month':
            start_date = now.replace(day=1).date()
        else:
            start_date = now.date() - timedelta(days=7)

        # 按商品统计销量
        product_stats = db.query(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.subtotal).label('total_amount'),
            func.count(OrderItem.id).label('order_times')
        ).join(Order).filter(
            Order.order_date >= start_date
        ).group_by(
            OrderItem.product_name
        ).order_by(
            func.sum(OrderItem.quantity).desc()
        ).limit(limit).all()

        products = []
        quantities = []
        amounts = []

        for stat in product_stats:
            products.append(stat.product_name)
            quantities.append(float(stat.total_quantity))
            amounts.append(float(stat.total_amount))

        return {
            'products': products,
            'quantities': quantities,
            'amounts': amounts
        }

    @staticmethod
    def get_customer_distribution(db: Session, user_id: int) -> Dict:
        """
        获取客户分布统计（饼图）
        :return: 分布数据
        """
        # 按销售人员统计客户数
        sales_stats = db.query(
            Customer.sales_person,
            func.count(Customer.id).label('customer_count')
        ).filter(
            Customer.is_active == 1
        ).group_by(
            Customer.sales_person
        ).all()

        labels = []
        values = []

        for stat in sales_stats:
            name = stat.sales_person or '未分配'
            labels.append(name)
            values.append(stat.customer_count)

        return {
            'labels': labels,
            'values': values
        }

    @staticmethod
    def get_route_summary(db: Session, user_id: int, date: str = None) -> Dict:
        """
        获取线路汇总统计
        :param date: 指定日期，默认今天
        :return: 线路汇总
        """
        if not date:
            date = datetime.now().date().isoformat()

        # 按线路统计
        route_stats = db.query(
            Customer.sales_person,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_amount')
        ).join(Order).filter(
            Order.order_date == date
        ).group_by(
            Customer.sales_person
        ).all()

        routes = []
        for stat in route_stats:
            routes.append({
                'name': stat.sales_person or '未分配',
                'order_count': stat.order_count,
                'total_amount': float(stat.total_amount or 0)
            })

        return {
            'date': date,
            'routes': routes,
            'total_orders': sum(r['order_count'] for r in routes),
            'total_amount': sum(r['total_amount'] for r in routes)
        }

    @staticmethod
    def get_dashboard_widgets(db: Session, user_id: int) -> List[Dict]:
        """获取用户的看板组件配置"""
        from models.user_models import DashboardWidget

        widgets = db.query(DashboardWidget).filter(
            DashboardWidget.user_id == user_id,
            DashboardWidget.is_visible == True
        ).order_by(DashboardWidget.position_y, DashboardWidget.position_x).all()

        return [w.to_dict() for w in widgets]

    @staticmethod
    def save_widget_config(db: Session, user_id: int, **kwargs) -> Dict:
        """保存看板组件配置"""
        from models.user_models import DashboardWidget

        widget_id = kwargs.get('id')

        if widget_id:
            # 更新
            widget = db.query(DashboardWidget).filter(
                DashboardWidget.id == widget_id,
                DashboardWidget.user_id == user_id
            ).first()

            if not widget:
                return {'success': False, 'error': '组件不存在'}

            updatable_fields = [
                'widget_name', 'widget_type', 'data_source', 'stat_period',
                'position_x', 'position_y', 'width', 'height', 'is_visible'
            ]
            for field in updatable_fields:
                if field in kwargs:
                    setattr(widget, field, kwargs[field])
        else:
            # 创建
            widget = DashboardWidget(
                user_id=user_id,
                widget_name=kwargs.get('widget_name', '新组件'),
                widget_type=kwargs.get('widget_type', 'stat_card'),
                data_source=kwargs.get('data_source'),
                stat_period=kwargs.get('stat_period', 'today'),
                position_x=kwargs.get('position_x', 0),
                position_y=kwargs.get('position_y', 0),
                width=kwargs.get('width', 1),
                height=kwargs.get('height', 1),
                is_visible=kwargs.get('is_visible', True)
            )
            db.add(widget)

        db.commit()
        db.refresh(widget)

        return {
            'success': True,
            'widget': widget.to_dict()
        }
