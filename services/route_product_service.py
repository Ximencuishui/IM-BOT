"""
线路产品服务
管理配送线路与商品的关联关系
"""
from typing import List, Dict, Optional
from decimal import Decimal
import logging
from sqlalchemy.orm import Session

from models.models import RouteProduct, Product, DeliveryRoute
from database.db_config import get_db

logger = logging.getLogger(__name__)


class RouteProductService:
    """线路产品服务"""

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """获取数据库会话"""
        return next(get_db())

    def get_route_products(self, route_id: int, active_only: bool = True) -> List[Dict]:
        """
        获取线路产品清单(带序号)

        参数:
        - route_id: 线路ID
        - active_only: 是否只返回启用的商品

        返回:
        [{
            'id': 1,
            'route_id': 1,
            'product_id': 1,
            'product_name': '土豆',
            'unit': '斤',
            'sort_order': 1,
            'price': 2.50,
            'custom_price': None,
            'is_active': 1
        }]
        """
        db = self._get_db()
        try:
            query = db.query(RouteProduct).filter(
                RouteProduct.route_id == route_id
            )

            if active_only:
                query = query.filter(RouteProduct.is_active == 1)

            # 按排序序号排序
            route_products = query.order_by(
                RouteProduct.sort_order,
                RouteProduct.product_id
            ).all()

            return [rp.to_dict() for rp in route_products]

        except Exception as e:
            logger.error(f"获取线路产品失败: route_id={route_id}, error={e}", exc_info=True)
            return []

    def assign_products_to_route(self, route_id: int, product_ids: List[int],
                                  custom_prices: Dict[int, float] = None) -> Dict:
        """
        为线路分配商品

        参数:
        - route_id: 线路ID
        - product_ids: 商品ID列表
        - custom_prices: 自定义价格字典 {product_id: price}

        返回:
        {'success': True, 'assigned_count': 10}
        """
        db = self._get_db()
        try:
            # 验证线路是否存在
            route = db.query(DeliveryRoute).filter(
                DeliveryRoute.id == route_id
            ).first()
            if not route:
                return {'success': False, 'error': f'线路不存在: {route_id}'}

            assigned_count = 0
            for idx, product_id in enumerate(product_ids, start=1):
                # 检查商品是否存在
                product = db.query(Product).filter(
                    Product.id == product_id
                ).first()
                if not product:
                    logger.warning(f"商品不存在: {product_id}, 跳过")
                    continue

                # 检查是否已存在关联
                existing = db.query(RouteProduct).filter(
                    RouteProduct.route_id == route_id,
                    RouteProduct.product_id == product_id
                ).first()

                if existing:
                    # 更新现有记录
                    existing.sort_order = idx
                    existing.is_active = 1
                    if custom_prices and product_id in custom_prices:
                        existing.custom_price = Decimal(str(custom_prices[product_id]))
                    assigned_count += 1
                else:
                    # 创建新记录
                    custom_price = None
                    if custom_prices and product_id in custom_prices:
                        custom_price = Decimal(str(custom_prices[product_id]))

                    route_product = RouteProduct(
                        route_id=route_id,
                        product_id=product_id,
                        sort_order=idx,
                        custom_price=custom_price,
                        is_active=1
                    )
                    db.add(route_product)
                    assigned_count += 1

            db.commit()
            logger.info(f"线路{route_id}分配商品成功: {assigned_count}个")
            return {'success': True, 'assigned_count': assigned_count}

        except Exception as e:
            db.rollback()
            logger.error(f"分配商品失败: route_id={route_id}, error={e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def update_route_product_sort(self, route_id: int, product_id: int,
                                   sort_order: int) -> Dict:
        """
        更新线路产品排序

        参数:
        - route_id: 线路ID
        - product_id: 商品ID
        - sort_order: 新排序序号

        返回:
        {'success': True}
        """
        db = self._get_db()
        try:
            route_product = db.query(RouteProduct).filter(
                RouteProduct.route_id == route_id,
                RouteProduct.product_id == product_id
            ).first()

            if not route_product:
                return {'success': False, 'error': '线路产品关联不存在'}

            route_product.sort_order = sort_order
            db.commit()

            logger.info(f"更新线路产品排序: route={route_id}, product={product_id}, sort={sort_order}")
            return {'success': True}

        except Exception as e:
            db.rollback()
            logger.error(f"更新排序失败: error={e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def remove_product_from_route(self, route_id: int, product_id: int) -> Dict:
        """
        从线路移除商品(软删除)

        参数:
        - route_id: 线路ID
        - product_id: 商品ID

        返回:
        {'success': True}
        """
        db = self._get_db()
        try:
            route_product = db.query(RouteProduct).filter(
                RouteProduct.route_id == route_id,
                RouteProduct.product_id == product_id
            ).first()

            if not route_product:
                return {'success': False, 'error': '线路产品关联不存在'}

            route_product.is_active = 0
            db.commit()

            logger.info(f"从线路移除商品: route={route_id}, product={product_id}")
            return {'success': True}

        except Exception as e:
            db.rollback()
            logger.error(f"移除商品失败: error={e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def generate_numbered_list(self, route_id: int) -> str:
        """
        生成带序号的清单文本(用于客户圈选)

        返回:
        "1. 土豆 2.5元/斤\n2. 鸡蛋 6.5元/斤\n3. 白菜 1.8元/斤"
        """
        products = self.get_route_products(route_id, active_only=True)

        if not products:
            return "该线路暂无商品"

        lines = []
        for product in products:
            price = product['price']
            unit = product['unit']
            lines.append(f"{product['sort_order']}. {product['product_name']} {price}元/{unit}")

        return "\n".join(lines)

    def get_product_by_index(self, route_id: int, index: int) -> Optional[Dict]:
        """
        根据序号获取线路中的商品

        参数:
        - route_id: 线路ID
        - index: 序号(从1开始)

        返回:
        商品字典或None
        """
        products = self.get_route_products(route_id, active_only=True)

        for product in products:
            if product['sort_order'] == index:
                return product

        return None
