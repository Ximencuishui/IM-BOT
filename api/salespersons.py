"""
销售人员管理API
提供销售人员的增删改查、线路配置、授权码关联等功能
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from models.models import Salesperson, DeliveryRoute
from models.user_models import License
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

salespersons_bp = Blueprint('salespersons', __name__, url_prefix='/api/salespersons')


# ==================== 销售人员管理 ====================

@salespersons_bp.route('', methods=['GET'])
@login_required
def list_salespersons():
    """
    获取销售人员列表
    
    Query Params:
    - keyword: 搜索关键词（姓名/电话）
    - route_id: 线路ID筛选
    - is_active: 状态筛选
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 基础查询
        query = db.query(Salesperson).filter(Salesperson.user_id == user.id)
        
        # 搜索筛选
        keyword = request.args.get('keyword')
        if keyword:
            query = query.filter(
                (Salesperson.name.like(f'%{keyword}%')) |
                (Salesperson.phone.like(f'%{keyword}%'))
            )
        
        # 线路筛选
        route_id = request.args.get('route_id', type=int)
        if route_id:
            query = query.filter(Salesperson.route_id == route_id)
        
        # 状态筛选
        is_active = request.args.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true' or is_active == '1'
            query = query.filter(Salesperson.is_active == is_active_bool)
        
        salespersons = query.order_by(Salesperson.created_at.desc()).all()
        
        # 转换为字典
        result = []
        for sp in salespersons:
            result.append({
                'id': sp.id,
                'name': sp.name,
                'phone': sp.phone,
                'region': sp.region,
                'route_id': sp.route_id,
                'route_name': sp.route.route_name if sp.route else None,
                'license_codes': sp.license_codes or [],
                'total_sales': sp.total_sales or 0,
                'total_amount': float(sp.total_amount or 0),
                'is_active': sp.is_active,
                'remark': sp.remark,
                'created_at': sp.created_at.isoformat() if sp.created_at else None
            })
        
        return jsonify({
            'success': True,
            'count': len(result),
            'salespersons': result
        }), 200
        
    except Exception as e:
        logger.error(f"查询销售人员列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@salespersons_bp.route('/<int:salesperson_id>', methods=['GET'])
@login_required
def get_salesperson(salesperson_id):
    """获取销售人员详情"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        salesperson = db.query(Salesperson).filter(
            Salesperson.id == salesperson_id,
            Salesperson.user_id == user.id
        ).first()
        
        if not salesperson:
            return jsonify({'success': False, 'error': '销售人员不存在'}), 404
        
        return jsonify({
            'success': True,
            'salesperson': {
                'id': salesperson.id,
                'name': salesperson.name,
                'phone': salesperson.phone,
                'region': salesperson.region,
                'route_id': salesperson.route_id,
                'route_name': salesperson.route.route_name if salesperson.route else None,
                'license_codes': salesperson.license_codes or [],
                'total_sales': salesperson.total_sales or 0,
                'total_amount': float(salesperson.total_amount or 0),
                'is_active': salesperson.is_active,
                'remark': salesperson.remark,
                'created_at': salesperson.created_at.isoformat() if salesperson.created_at else None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"查询销售人员详情失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@salespersons_bp.route('', methods=['POST'])
@login_required
def create_salesperson():
    """
    创建销售人员
    
    Request Body:
    {
        "name": "张三",
        "phone": "13800138000",
        "region": "朝阳区",
        "route_id": 1,
        "license_codes": ["LIC001", "LIC002"],
        "remark": "备注信息"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'error': '姓名不能为空'}), 400
        
        # 检查手机号是否已存在
        if data.get('phone'):
            existing = db.query(Salesperson).filter(
                Salesperson.user_id == user.id,
                Salesperson.phone == data['phone']
            ).first()
            if existing:
                return jsonify({'success': False, 'error': '该手机号已被使用'}), 400
        
        # 验证线路是否存在
        if data.get('route_id'):
            route = db.query(DeliveryRoute).filter(
                DeliveryRoute.id == data['route_id']
            ).first()
            if not route:
                return jsonify({'success': False, 'error': '线路不存在'}), 400
        
        # 创建销售人员
        salesperson = Salesperson(
            user_id=user.id,
            name=data['name'],
            phone=data.get('phone'),
            region=data.get('region'),
            route_id=data.get('route_id'),
            license_codes=data.get('license_codes', []),
            remark=data.get('remark'),
            is_active=True
        )
        
        db.add(salesperson)
        db.commit()
        db.refresh(salesperson)
        
        return jsonify({
            'success': True,
            'salesperson': {
                'id': salesperson.id,
                'name': salesperson.name
            }
        }), 201
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建销售人员失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@salespersons_bp.route('/<int:salesperson_id>', methods=['PUT'])
@login_required
def update_salesperson(salesperson_id):
    """
    更新销售人员信息
    
    Request Body:
    {
        "name": "张三",
        "phone": "13800138000",
        "region": "朝阳区",
        "route_id": 1,
        "license_codes": ["LIC001", "LIC002"],
        "is_active": true,
        "remark": "备注信息"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        salesperson = db.query(Salesperson).filter(
            Salesperson.id == salesperson_id,
            Salesperson.user_id == user.id
        ).first()
        
        if not salesperson:
            return jsonify({'success': False, 'error': '销售人员不存在'}), 404
        
        # 检查手机号唯一性
        if data.get('phone') and data['phone'] != salesperson.phone:
            existing = db.query(Salesperson).filter(
                Salesperson.user_id == user.id,
                Salesperson.phone == data['phone'],
                Salesperson.id != salesperson_id
            ).first()
            if existing:
                return jsonify({'success': False, 'error': '该手机号已被使用'}), 400
        
        # 验证线路
        if data.get('route_id'):
            route = db.query(DeliveryRoute).filter(
                DeliveryRoute.id == data['route_id']
            ).first()
            if not route:
                return jsonify({'success': False, 'error': '线路不存在'}), 400
        
        # 更新字段
        if 'name' in data:
            salesperson.name = data['name']
        if 'phone' in data:
            salesperson.phone = data['phone']
        if 'region' in data:
            salesperson.region = data['region']
        if 'route_id' in data:
            salesperson.route_id = data['route_id']
        if 'license_codes' in data:
            salesperson.license_codes = data['license_codes']
        if 'is_active' in data:
            salesperson.is_active = data['is_active']
        if 'remark' in data:
            salesperson.remark = data['remark']
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': '更新成功'
        }), 200
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新销售人员失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@salespersons_bp.route('/<int:salesperson_id>', methods=['DELETE'])
@login_required
def delete_salesperson(salesperson_id):
    """删除销售人员"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        salesperson = db.query(Salesperson).filter(
            Salesperson.id == salesperson_id,
            Salesperson.user_id == user.id
        ).first()
        
        if not salesperson:
            return jsonify({'success': False, 'error': '销售人员不存在'}), 404
        
        db.delete(salesperson)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        }), 200
        
    except Exception as e:
        db.rollback()
        logger.error(f"删除销售人员失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 统计接口 ====================

@salespersons_bp.route('/stats', methods=['GET'])
@login_required
def get_salesperson_stats():
    """
    获取销售人员统计数据
    
    Query Params:
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - route_id: 线路ID
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 基础查询
        query = db.query(Salesperson).filter(Salesperson.user_id == user.id)
        
        # 日期筛选
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 线路筛选
        route_id = request.args.get('route_id', type=int)
        if route_id:
            query = query.filter(Salesperson.route_id == route_id)
        
        salespersons = query.all()
        
        # 统计数据
        total_count = len(salespersons)
        active_count = sum(1 for sp in salespersons if sp.is_active)
        total_sales = sum(sp.total_sales or 0 for sp in salespersons)
        total_amount = sum(float(sp.total_amount or 0) for sp in salespersons)
        
        # 按线路分组统计
        route_stats = {}
        for sp in salespersons:
            route_name = sp.route.route_name if sp.route else '未分配'
            if route_name not in route_stats:
                route_stats[route_name] = {
                    'route_name': route_name,
                    'salesperson_count': 0,
                    'total_sales': 0,
                    'total_amount': 0
                }
            route_stats[route_name]['salesperson_count'] += 1
            route_stats[route_name]['total_sales'] += sp.total_sales or 0
            route_stats[route_name]['total_amount'] += float(sp.total_amount or 0)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_count': total_count,
                'active_count': active_count,
                'inactive_count': total_count - active_count,
                'total_sales': total_sales,
                'total_amount': total_amount,
                'route_stats': list(route_stats.values())
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 授权码关联 ====================

@salespersons_bp.route('/<int:salesperson_id>/licenses', methods=['PUT'])
@login_required
def assign_licenses(salesperson_id):
    """
    为销售人员分配授权码
    
    Request Body:
    {
        "license_codes": ["LIC001", "LIC002"]
    }
    """
    data = request.get_json()
    if not data or 'license_codes' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        salesperson = db.query(Salesperson).filter(
            Salesperson.id == salesperson_id,
            Salesperson.user_id == user.id
        ).first()
        
        if not salesperson:
            return jsonify({'success': False, 'error': '销售人员不存在'}), 404
        
        # 验证授权码是否存在
        license_codes = data['license_codes']
        valid_codes = []
        for code in license_codes:
            license = db.query(License).filter(
                License.license_code == code,
                License.user_id == user.id
            ).first()
            if license:
                valid_codes.append(code)
        
        # 更新授权码列表
        salesperson.license_codes = valid_codes
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功分配 {len(valid_codes)} 个授权码',
            'assigned_count': len(valid_codes)
        }), 200
        
    except Exception as e:
        db.rollback()
        logger.error(f"分配授权码失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
