"""
客户管理API路由
"""
from flask import Blueprint, request, jsonify
import logging

from services.customer_service import customer_service

logger = logging.getLogger(__name__)

customers_bp = Blueprint('customers', __name__, url_prefix='/api/customers')


@customers_bp.route('', methods=['GET'])
def list_customers():
    """
    获取客户列表

    Query Params:
    - page: 页码(默认1)
    - page_size: 每页数量(默认20)
    - route_id: 线路ID筛选
    - sales_person: 销售筛选
    - is_active: 启用状态(1/0)
    """
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        route_id = request.args.get('route_id', type=int)
        sales_person = request.args.get('sales_person')
        is_active = request.args.get('is_active')

        if is_active is not None:
            is_active = int(is_active) == 1

        result = customer_service.list_customers(
            page=page,
            page_size=page_size,
            route_id=route_id,
            sales_person=sales_person,
            is_active=is_active
        )

        return jsonify({
            'success': True,
            'count': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'customers': result['customers']
        }), 200

    except Exception as e:
        logger.error(f"查询客户列表API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@customers_bp.route('/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    """获取客户详情"""
    try:
        customer = customer_service.get_customer_by_id(customer_id)

        if not customer:
            return jsonify({'error': f'客户不存在: {customer_id}'}), 404

        return jsonify({'success': True, 'customer': customer}), 200

    except Exception as e:
        logger.error(f"查询客户详情API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@customers_bp.route('', methods=['POST'])
def create_customer():
    """
    创建客户

    Request Body:
    {
        "customer_name": "张三",
        "phone": "13800138000",
        "address": "xx路xx号",
        "route_id": 1,
        "sales_person": "李四",
        "remark": "备注"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        result = customer_service.create_customer(data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"创建客户API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@customers_bp.route('/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """
    更新客户信息

    Request Body:
    {
        "customer_name": "新名称",
        "phone": "新电话",
        "address": "新地址"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        result = customer_service.update_customer(customer_id, data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"更新客户API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@customers_bp.route('/bind', methods=['POST'])
def bind_wx_group():
    """
    绑定微信群ID到客户

    Request Body:
    {
        "customer_id": 1,
        "wx_group_id": "xxx",
        "wx_alias": "张三"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        if not data.get('customer_id') or not data.get('wx_group_id'):
            return jsonify({'error': 'customer_id和wx_group_id不能为空'}), 400

        result = customer_service.bind_wx_group(
            customer_id=data['customer_id'],
            wx_group_id=data['wx_group_id'],
            wx_alias=data.get('wx_alias')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"绑定微信API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@customers_bp.route('/routes', methods=['GET'])
def get_routes():
    """
    获取所有配送线路列表
    
    Returns:
    {
        "success": true,
        "routes": [
            {"id": 1, "route_name": "线路1", ...},
            ...
        ]
    }
    """
    try:
        from database.db_config import get_db_session
        from models.models import DeliveryRoute
        
        db = get_db_session()
        routes = db.query(DeliveryRoute).filter(
            DeliveryRoute.is_active == 1
        ).order_by(DeliveryRoute.id).all()
        
        routes_data = [{
            'id': route.id,
            'route_name': route.route_name,
            'description': getattr(route, 'description', ''),
            'is_active': route.is_active
        } for route in routes]
        
        return jsonify({
            'success': True,
            'count': len(routes_data),
            'routes': routes_data
        }), 200
        
    except Exception as e:
        logger.error(f"获取线路列表API异常: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
