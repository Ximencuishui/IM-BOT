"""
授权检查API
为桌面端提供在线授权验证和定期同步接口
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request

license_check_bp = Blueprint('license_check', __name__, url_prefix='/api/license')


@license_check_bp.route('/check', methods=['GET'])
@login_required
def check_license():
    """
    桌面端定期检查授权状态
    返回当前授权的有效性和到期时间
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        return jsonify({
            'success': True,
            'license': {
                'expires_at': user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                'subscription_type': user.subscription_type,
                'max_groups': user.max_groups,
                'is_valid': user.is_subscription_valid
            }
        }), 200
    finally:
        db.close()


@license_check_bp.route('/info', methods=['GET'])
@login_required
def get_license_detail():
    """
    获取完整的授权详情
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        from datetime import datetime
        now = datetime.now()
        remaining_days = 0
        if user.subscription_expires_at and user.subscription_expires_at > now:
            delta = user.subscription_expires_at - now
            remaining_days = delta.days

        return jsonify({
            'success': True,
            'license': {
                'expires_at': user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                'subscription_type': user.subscription_type,
                'max_groups': user.max_groups,
                'is_valid': user.is_subscription_valid,
                'remaining_days': remaining_days,
                'is_active': user.is_active
            }
        }), 200
    finally:
        db.close()