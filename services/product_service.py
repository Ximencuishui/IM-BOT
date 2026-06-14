"""
商品管理服务
- 商品CRUD
- 快捷码管理
"""
import logging
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from models.models import Product
from database.db_config import SessionLocal

logger = logging.getLogger(__name__)


class ProductService:
    """商品服务类"""

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

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """根据ID获取商品信息"""
        db = self._get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if product:
            return product.to_dict()
        return None

    def list_products(self, category: str = None, is_active: bool = None) -> List[Dict]:
        """
        获取商品列表

        Args:
            category: 分类筛选
            is_active: 启用状态筛选

        Returns:
            商品列表
        """
        db = self._get_db()

        query = db.query(Product)

        if category:
            query = query.filter(Product.category == category)

        if is_active is not None:
            query = query.filter(Product.is_active == (1 if is_active else 0))

        products = query.order_by(Product.sort_order, Product.product_name).all()
        return [p.to_dict() for p in products]

    def create_product(self, product_data: Dict) -> Dict:
        """
        创建新商品

        Args:
            product_data: 商品数据 {
                "product_name": "土豆",
                "product_code": "PROD_001",
                "shortcut_codes": ["TD", "土", "土豆"],
                "unit": "斤",
                "price": 2.50,
                "category": "蔬菜"
            }

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            # 验证必填字段
            if not product_data.get('product_name'):
                return {'success': False, 'error': '商品名称不能为空'}

            # 检查重名
            existing = db.query(Product).filter(
                Product.product_name == product_data['product_name']
            ).first()

            if existing:
                return {'success': False, 'error': '商品名称已存在'}

            # 处理快捷码
            shortcut_codes = product_data.get('shortcut_codes', [])
            if isinstance(shortcut_codes, list):
                shortcut_str = ','.join(shortcut_codes)
            else:
                shortcut_str = str(shortcut_codes)

            # 创建商品
            product = Product(
                product_name=product_data['product_name'],
                product_code=product_data.get('product_code'),
                shortcut_codes=shortcut_str,
                unit=product_data.get('unit', '斤'),
                price=product_data.get('price', 0.00),
                category=product_data.get('category', '其他'),
                sort_order=product_data.get('sort_order', 0),
                is_active=1
            )

            db.add(product)
            db.commit()
            db.refresh(product)

            logger.info(f"商品创建成功: product_id={product.id}")

            return {
                'success': True,
                'product_id': product.id,
                'product_name': product.product_name
            }

        except Exception as e:
            db.rollback()
            logger.error(f"创建商品失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def update_product(self, product_id: int, update_data: Dict) -> Dict:
        """
        更新商品信息

        Args:
            product_id: 商品ID
            update_data: 更新数据

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return {'success': False, 'error': f'商品不存在: {product_id}'}

            # 更新允许修改的字段
            allowed_fields = ['product_name', 'product_code', 'unit', 'price',
                            'category', 'sort_order', 'is_active']

            for field in allowed_fields:
                if field in update_data:
                    setattr(product, field, update_data[field])

            # 特殊处理快捷码
            if 'shortcut_codes' in update_data:
                codes = update_data['shortcut_codes']
                if isinstance(codes, list):
                    product.shortcut_codes = ','.join(codes)
                else:
                    product.shortcut_codes = str(codes)

            db.commit()
            logger.info(f"商品信息更新成功: product_id={product_id}")

            return {'success': True, 'product_id': product_id}

        except Exception as e:
            db.rollback()
            logger.error(f"更新商品失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def delete_product(self, product_id: int) -> Dict:
        """
        删除商品(软删除,设置为禁用)

        Args:
            product_id: 商品ID

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return {'success': False, 'error': f'商品不存在: {product_id}'}

            product.is_active = 0
            db.commit()

            logger.info(f"商品已禁用: product_id={product_id}")

            return {'success': True, 'product_id': product_id}

        except Exception as e:
            db.rollback()
            logger.error(f"禁用商品失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def search_products(self, keyword: str) -> List[Dict]:
        """
        搜索商品(支持名称/快捷码模糊搜索)

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的商品列表
        """
        db = self._get_db()

        products = db.query(Product).filter(
            Product.is_active == 1,
            (
                Product.product_name.like(f'%{keyword}%') |
                Product.shortcut_codes.like(f'%{keyword}%')
            )
        ).order_by(Product.product_name).all()

        return [p.to_dict() for p in products]


# 全局单例
product_service = ProductService()
