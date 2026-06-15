"""
线路产品管理API
提供线路与商品关联关系的CRUD操作
"""
import logging
from flask import Blueprint, request, jsonify
from database.db_config import get_db_session
from models.models import DeliveryRoute
from services.route_product_service import RouteProductService

logger = logging.getLogger(__name__)

routes_bp = Blueprint('routes', __name__, url_prefix='/api/routes')
route_product_service = RouteProductService()


@routes_bp.route('/', methods=['GET'])
def get_all_routes():
    """获取所有线路列表"""
    db = get_db_session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        route_name = request.args.get('route_name', '')
        is_active = request.args.get('is_active', None)
        
        query = db.query(DeliveryRoute)
        
        # 筛选条件
        if active_only:
            query = query.filter(DeliveryRoute.is_active == 1)
        
        if is_active is not None:
            query = query.filter(DeliveryRoute.is_active == int(is_active))
        
        if route_name:
            query = query.filter(DeliveryRoute.route_name.like(f'%{route_name}%'))
        
        # 获取总数
        total = query.count()
        
        # 分页
        routes = query.order_by(DeliveryRoute.id).offset((page - 1) * per_page).limit(per_page).all()
        
        # 统计每个线路的商品数量
        from sqlalchemy import func
        from models.models import RouteProduct
        
        route_list = []
        for route in routes:
            product_count = db.query(func.count(RouteProduct.id)).filter(
                RouteProduct.route_id == route.id
            ).scalar() or 0
            
            route_dict = route.to_dict()
            route_dict['product_count'] = product_count
            route_list.append(route_dict)
        
        return jsonify({
            'success': True,
            'count': total,
            'routes': route_list,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }), 200
    except Exception as e:
        logger.error(f"获取线路列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@routes_bp.route('/', methods=['POST'])
def create_route():
    """创建新线路"""
    db = get_db_session()
    try:
        data = request.get_json()
        if not data or 'route_name' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: route_name'}), 400
        
        # 检查线路名称是否已存在
        existing = db.query(DeliveryRoute).filter(
            DeliveryRoute.route_name == data['route_name']
        ).first()
        if existing:
            return jsonify({'success': False, 'error': '线路名称已存在'}), 400
        
        # 创建新线路
        new_route = DeliveryRoute(
            route_name=data['route_name'],
            route_code=data.get('route_code'),
            description=data.get('description', ''),
            is_active=data.get('is_active', 1)
        )
        
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        
        return jsonify({
            'success': True,
            'message': '线路创建成功',
            'route': new_route.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        logger.error(f"创建线路失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@routes_bp.route('/<int:route_id>', methods=['PUT'])
def update_route(route_id):
    """更新线路信息"""
    db = get_db_session()
    try:
        route = db.query(DeliveryRoute).filter(DeliveryRoute.id == route_id).first()
        if not route:
            return jsonify({'success': False, 'error': '线路不存在'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        # 如果修改了线路名称，检查是否重复
        if 'route_name' in data and data['route_name'] != route.route_name:
            existing = db.query(DeliveryRoute).filter(
                DeliveryRoute.route_name == data['route_name'],
                DeliveryRoute.id != route_id
            ).first()
            if existing:
                return jsonify({'success': False, 'error': '线路名称已存在'}), 400
        
        # 更新字段
        if 'route_name' in data:
            route.route_name = data['route_name']
        if 'route_code' in data:
            route.route_code = data['route_code']
        if 'description' in data:
            route.description = data['description']
        if 'is_active' in data:
            route.is_active = data['is_active']
        
        db.commit()
        db.refresh(route)
        
        return jsonify({
            'success': True,
            'message': '线路更新成功',
            'route': route.to_dict()
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"更新线路失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@routes_bp.route('/<int:route_id>', methods=['DELETE'])
def delete_route(route_id):
    """删除线路"""
    db = get_db_session()
    try:
        route = db.query(DeliveryRoute).filter(DeliveryRoute.id == route_id).first()
        if not route:
            return jsonify({'success': False, 'error': '线路不存在'}), 404
        
        # 检查是否有关联的商品
        from models.models import RouteProduct
        product_count = db.query(RouteProduct).filter(
            RouteProduct.route_id == route_id
        ).count()
        
        if product_count > 0:
            return jsonify({
                'success': False,
                'error': f'该线路下还有{product_count}个商品，请先移除所有商品后再删除'
            }), 400
        
        db.delete(route)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': '线路删除成功'
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"删除线路失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@routes_bp.route('/<int:route_id>/products', methods=['GET'])
def get_route_products(route_id):
    """获取线路产品清单"""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        products = route_product_service.get_route_products(route_id, active_only)

        return jsonify({
            'success': True,
            'count': len(products),
            'products': products
        }), 200

    except Exception as e:
        logger.error(f"获取线路产品失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@routes_bp.route('/<int:route_id>/products', methods=['POST'])
def assign_products_to_route(route_id):
    """为线路分配商品"""
    try:
        data = request.get_json()
        if not data or 'product_ids' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: product_ids'}), 400

        product_ids = data['product_ids']
        custom_prices = data.get('custom_prices', {})

        result = route_product_service.assign_products_to_route(
            route_id, product_ids, custom_prices
        )

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"分配商品失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@routes_bp.route('/<int:route_id>/products/<int:product_id>', methods=['PUT'])
def update_route_product_sort(route_id, product_id):
    """更新线路产品排序"""
    try:
        data = request.get_json()
        if not data or 'sort_order' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: sort_order'}), 400

        sort_order = data['sort_order']

        result = route_product_service.update_route_product_sort(
            route_id, product_id, sort_order
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"更新排序失败: route_id={route_id}, product_id={product_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@routes_bp.route('/<int:route_id>/products/<int:product_id>', methods=['DELETE'])
def remove_product_from_route(route_id, product_id):
    """从线路移除商品"""
    try:
        result = route_product_service.remove_product_from_route(route_id, product_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"移除商品失败: route_id={route_id}, product_id={product_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@routes_bp.route('/<int:route_id>/products/<int:product_id>/price', methods=['PUT'])
def update_route_product_price(route_id, product_id):
    """更新线路产品自定义价格"""
    db = get_db_session()
    try:
        from models.models import RouteProduct
        from decimal import Decimal
        
        data = request.get_json()
        if not data or 'custom_price' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: custom_price'}), 400
        
        custom_price = data['custom_price']
        
        # 查找线路产品关联
        route_product = db.query(RouteProduct).filter(
            RouteProduct.route_id == route_id,
            RouteProduct.product_id == product_id
        ).first()
        
        if not route_product:
            return jsonify({'success': False, 'error': '线路产品关联不存在'}), 404
        
        # 更新自定义价格（None表示使用基础价格）
        route_product.custom_price = Decimal(str(custom_price)) if custom_price is not None else None
        db.commit()
        
        return jsonify({
            'success': True,
            'message': '价格更新成功',
            'custom_price': float(route_product.custom_price) if route_product.custom_price else None
        }), 200
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新价格失败: route_id={route_id}, product_id={product_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@routes_bp.route('/<int:route_id>/numbered-list', methods=['GET'])
def generate_numbered_list(route_id):
    """生成带序号的清单文本"""
    try:
        text = route_product_service.generate_numbered_list(route_id)

        return jsonify({
            'success': True,
            'route_id': route_id,
            'list_text': text
        }), 200

    except Exception as e:
        logger.error(f"生成清单失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@routes_bp.route('/<int:route_id>/product-by-index/<int:index>', methods=['GET'])
def get_product_by_index(route_id, index):
    """根据序号获取线路中的商品"""
    try:
        product = route_product_service.get_product_by_index(route_id, index)

        if product:
            return jsonify({
                'success': True,
                'product': product
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'未找到序号为{index}的商品'
            }), 404

    except Exception as e:
        logger.error(f"获取商品失败: route_id={route_id}, index={index}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
