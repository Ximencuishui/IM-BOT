"""
授权码管理API
提供授权码的生成、查询、激活、撤销、续期等接口
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.license_service_v2 import LicenseServiceV2

license_bp = Blueprint('license_v2', __name__, url_prefix='/api/license')


@license_bp.route('/generate', methods=['POST'])
@login_required
def generate_license():
    """
    生成新的授权码（仅管理员或付费用户）
    Body: {
        "license_type": "monthly",  // monthly 或 yearly
        "bound_to": "group_xxx"     // 可选，绑定群ID
    }
    """
    data = request.get_json() or {}
    license_type = data.get('license_type', 'monthly')
    bound_to = data.get('bound_to')

    if license_type not in ['monthly', 'yearly']:
        return jsonify({'success': False, 'error': '授权类型必须为monthly或yearly'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = LicenseServiceV2.create_license(
            db,
            user_id=user.id,
            license_type=license_type,
            bound_to=bound_to
        )

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/activate', methods=['POST'])
def activate_license():
    """
    激活授权码（桌面端直接调用）
    Body: {
        "license_code": "XXXX-XXXX-XXXX",
        "machine_id": "xxx",      // 可选
        "bound_to": "group_xxx"   // 可选
    }
    """
    data = request.get_json()
    if not data or not data.get('license_code'):
        return jsonify({'success': False, 'error': '请提供授权码'}), 400

    db: Session = get_db_session()
    try:
        result = LicenseServiceV2.activate_license(
            db,
            license_code=data['license_code'],
            machine_id=data.get('machine_id'),
            bound_to=data.get('bound_to')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/list', methods=['GET'])
@login_required
def list_licenses():
    """
    获取授权列表
    Query: active_only=true/false
    """
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        licenses = LicenseServiceV2.get_user_licenses(db, user.id, active_only)

        return jsonify({
            'success': True,
            'licenses': licenses,
            'count': len(licenses)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/stats', methods=['GET'])
@login_required
def license_stats():
    """获取授权统计信息"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        stats = LicenseServiceV2.get_license_stats(db, user.id)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/<int:license_id>/revoke', methods=['POST'])
@login_required
def revoke_license(license_id):
    """撤销授权"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = LicenseServiceV2.revoke_license(db, license_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/<int:license_id>/renew', methods=['POST'])
@login_required
def renew_license(license_id):
    """
    续期授权
    Body: {
        "extend_days": 30  // 可选，默认根据授权类型
    }
    """
    data = request.get_json() or {}
    extend_days = data.get('extend_days')

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = LicenseServiceV2.renew_license(db, license_id, user.id, extend_days)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/<int:license_id>/extend', methods=['POST'])
@login_required
def extend_license(license_id):
    """
    展期授权（按月）
    Body: {
        "months": 3  // 展期月数
    }
    """
    data = request.get_json() or {}
    months = data.get('months', 1)
    
    if months not in [1, 3, 6, 12]:
        return jsonify({'success': False, 'error': '展期时长必须为1、3、6或12个月'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = LicenseServiceV2.extend_license_by_months(db, license_id, user.id, months)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/<int:license_id>/auto-renew', methods=['POST'])
@login_required
def toggle_auto_renew(license_id):
    """
    切换自动续费
    Body: {
        "auto_renew": true  // 是否启用自动续费
    }
    """
    data = request.get_json() or {}
    auto_renew = data.get('auto_renew', False)

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = LicenseServiceV2.toggle_auto_renew(db, license_id, user.id, auto_renew)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_bp.route('/assign', methods=['POST'])
@login_required
def assign_license():
    """
    将授权分配给团队成员
    Body: {
        "license_id": 1,
        "member_id": 2
    }
    """
    data = request.get_json()
    if not data or not data.get('license_id') or not data.get('member_id'):
        return jsonify({'success': False, 'error': '请提供授权ID和成员ID'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = LicenseServiceV2.assign_to_team_member(
            db,
            license_id=data['license_id'],
            user_id=user.id,
            member_id=data['member_id']
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
