"""
自动续费API
提供授权码自动续费的管理接口
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.auto_renew_service import AutoRenewService

auto_renew_bp = Blueprint('auto_renew', __name__, url_prefix='/api/auto-renew')


@auto_renew_bp.route('/enable', methods=['POST'])
@login_required
def enable_auto_renew():
    """
    启用授权码自动续费
    Body: {
        "license_id": 1,
        "renew_period": "1m" | "3m" | "6m" | "1y"
    }
    """
    data = request.get_json()
    if not data or not data.get('license_id'):
        return jsonify({'success': False, 'error': '请提供授权码ID'}), 400
    
    renew_period = data.get('renew_period', '1m')
    if renew_period not in ['1m', '3m', '6m', '1y']:
        return jsonify({'success': False, 'error': '无效的续费周期'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = AutoRenewService.enable_auto_renew(
            db, 
            data['license_id'], 
            user.id, 
            renew_period
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auto_renew_bp.route('/disable', methods=['POST'])
@login_required
def disable_auto_renew():
    """
    禁用授权码自动续费
    Body: {
        "license_id": 1
    }
    """
    data = request.get_json()
    if not data or not data.get('license_id'):
        return jsonify({'success': False, 'error': '请提供授权码ID'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = AutoRenewService.disable_auto_renew(
            db, 
            data['license_id'], 
            user.id
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auto_renew_bp.route('/status', methods=['GET'])
@login_required
def get_auto_renew_status():
    """获取当前用户的自动续费状态"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = AutoRenewService.get_auto_renew_status(db, user.id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auto_renew_bp.route('/calculate-price', methods=['POST'])
@login_required
def calculate_renew_price():
    """
    计算续费价格
    Body: {
        "license_ids": [1, 2, 3],
        "period": "1m" | "3m" | "6m" | "1y"
    }
    """
    data = request.get_json()
    if not data or not data.get('license_ids') or not data.get('period'):
        return jsonify({'success': False, 'error': '请提供授权码ID列表和续费周期'}), 400
    
    db: Session = get_db_session()
    try:
        result = AutoRenewService.calculate_renew_price(
            db, 
            len(data['license_ids']), 
            data['period']
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auto_renew_bp.route('/batch-enable', methods=['POST'])
@login_required
def batch_enable_auto_renew():
    """
    批量启用自动续费
    Body: {
        "license_ids": [1, 2, 3],
        "renew_period": "1m" | "3m" | "6m" | "1y"
    }
    """
    data = request.get_json()
    if not data or not data.get('license_ids') or not data.get('renew_period'):
        return jsonify({'success': False, 'error': '请提供授权码ID列表和续费周期'}), 400
    
    renew_period = data['renew_period']
    if renew_period not in ['1m', '3m', '6m', '1y']:
        return jsonify({'success': False, 'error': '无效的续费周期'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        success_count = 0
        failed_count = 0
        errors = []
        
        for license_id in data['license_ids']:
            result = AutoRenewService.enable_auto_renew(
                db, license_id, user.id, renew_period
            )
            
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
                errors.append(f"授权码 {license_id}: {result.get('error', '未知错误')}")
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功启用 {success_count} 个，失败 {failed_count} 个',
            'success_count': success_count,
            'failed_count': failed_count,
            'errors': errors if errors else None
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
