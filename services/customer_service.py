"""
客户管理服务
- 客户查询
- 微信群ID绑定
- 客户CRUD
"""
import logging
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from models.models import Customer, DeliveryRoute
from database.db_config import SessionLocal

logger = logging.getLogger(__name__)


class CustomerService:
    """客户服务类"""

    def _get_db(self) -> Session:
        """获取数据库会话（每次调用创建新session，避免线程安全问题）"""
        return SessionLocal()

    def get_customer_by_wx_group(self, wx_group_id: str) -> Optional[Dict]:
        """
        根据微信群ID查找客户

        Args:
            wx_group_id: 微信群ID

        Returns:
            客户信息字典,未找到返回None
        """
        db = self._get_db()
        try:
            customer = db.query(Customer).filter(
                Customer.wx_group_id == wx_group_id,
                Customer.is_active == 1
            ).first()

            if customer:
                return customer.to_dict()
            return None
        finally:
            db.close()

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict]:
        """根据ID获取客户信息"""
        db = self._get_db()
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()

            if customer:
                return customer.to_dict()
            return None
        finally:
            db.close()

    def bind_wx_group(self, customer_id: int, wx_group_id: str, wx_alias: str = None) -> Dict:
        """
        绑定微信群ID到客户

        Args:
            customer_id: 客户ID
            wx_group_id: 微信群ID
            wx_alias: 微信昵称

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {'success': False, 'error': f'客户不存在: {customer_id}'}

            # 检查群ID是否已被其他客户绑定
            existing = db.query(Customer).filter(
                Customer.wx_group_id == wx_group_id,
                Customer.id != customer_id
            ).first()

            if existing:
                return {
                    'success': False,
                    'error': f'该微信群已绑定给客户: {existing.customer_name}'
                }

            # 更新绑定
            customer.wx_group_id = wx_group_id
            if wx_alias:
                customer.wx_alias = wx_alias

            db.commit()
            logger.info(f"微信绑定成功: customer_id={customer_id}, group_id={wx_group_id}")

            return {
                'success': True,
                'customer_id': customer_id,
                'wx_group_id': wx_group_id
            }

        except Exception as e:
            db.rollback()
            logger.error(f"绑定微信失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def create_customer(self, customer_data: Dict) -> Dict:
        """
        创建新客户

        Args:
            customer_data: 客户数据 {
                "customer_name": "张三",
                "phone": "13800138000",
                "address": "xx路xx号",
                "route_id": 1,
                "sales_person": "李四"
            }

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            # 验证必填字段
            if not customer_data.get('customer_name'):
                return {'success': False, 'error': '客户名称不能为空'}

            # 检查重名
            existing = db.query(Customer).filter(
                Customer.customer_name == customer_data['customer_name']
            ).first()

            if existing:
                return {'success': False, 'error': '客户名称已存在'}

            # 创建客户
            customer = Customer(
                customer_name=customer_data['customer_name'],
                phone=customer_data.get('phone'),
                address=customer_data.get('address'),
                route_id=customer_data.get('route_id'),
                sales_person=customer_data.get('sales_person'),
                remark=customer_data.get('remark'),
                is_active=1
            )

            db.add(customer)
            db.commit()
            db.refresh(customer)

            logger.info(f"客户创建成功: customer_id={customer.id}")

            return {
                'success': True,
                'customer_id': customer.id,
                'customer_name': customer.customer_name
            }

        except Exception as e:
            db.rollback()
            logger.error(f"创建客户失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def list_customers(self, page: int = 1, page_size: int = 20,
                        route_id: int = None, sales_person: str = None,
                        is_active: bool = None) -> Dict:
        """
        获取客户列表（支持分页）

        Args:
            page: 页码(默认1)
            page_size: 每页数量(默认20)
            route_id: 线路ID筛选
            sales_person: 销售筛选
            is_active: 启用状态筛选

        Returns:
            {
                'total': 总数,
                'page': 当前页,
                'page_size': 每页数量,
                'customers': 客户列表
            }
        """
        db = self._get_db()

        query = db.query(Customer)

        if route_id:
            query = query.filter(Customer.route_id == route_id)

        if sales_person:
            query = query.filter(Customer.sales_person == sales_person)

        if is_active is not None:
            query = query.filter(Customer.is_active == (1 if is_active else 0))

        # 总数
        total = query.count()

        # 分页
        customers = query.order_by(Customer.customer_name)\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'customers': [c.to_dict() for c in customers]
        }

    def update_customer(self, customer_id: int, update_data: Dict) -> Dict:
        """
        更新客户信息

        Args:
            customer_id: 客户ID
            update_data: 更新数据

        Returns:
            操作结果
        """
        db = self._get_db()

        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {'success': False, 'error': f'客户不存在: {customer_id}'}

            # 更新允许修改的字段
            allowed_fields = ['customer_name', 'phone', 'address', 'route_id',
                            'sales_person', 'remark', 'is_active']

            for field in allowed_fields:
                if field in update_data:
                    setattr(customer, field, update_data[field])

            db.commit()
            logger.info(f"客户信息更新成功: customer_id={customer_id}")

            return {'success': True, 'customer_id': customer_id}

        except Exception as e:
            db.rollback()
            logger.error(f"更新客户失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


# 全局单例
customer_service = CustomerService()
