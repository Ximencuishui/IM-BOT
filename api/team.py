"""
团队管理API
提供销售人员的增删改查接口
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.team_service import TeamService

team_bp = Blueprint('team', __name__, url_prefix='/api/team')


@team_bp.route('/members', methods=['GET'])
@login_required
def list_members():
    """
    获取团队成员列表
    Query: active_only=true/false
    """
    active_only = request.args.get('active_only', 'true').lower() == 'true'

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        members = TeamService.get_members(db, user.id, active_only)

        return jsonify({
            'success': True,
            'members': members,
            'count': len(members)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@team_bp.route('/members/<int:member_id>', methods=['GET'])
@login_required
def get_member(member_id):
    """获取单个成员详情"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        member = TeamService.get_member(db, member_id, user.id)

        if not member:
            return jsonify({'success': False, 'error': '成员不存在'}), 404

        return jsonify({'success': True, 'member': member}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@team_bp.route('/members', methods=['POST'])
@login_required
def create_member():
    """
    创建团队成员
    Body: {
        "name": "张三",
        "phone": "13800138000",
        "wx_id": "zhangsan123",
        "managed_group_id": "group_xxx",
        "position": "销售经理"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = TeamService.create_member(db, user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@team_bp.route('/members/<int:member_id>', methods=['PUT'])
@login_required
def update_member(member_id):
    """
    更新团队成员
    Body: {
        "name": "新名字",
        "phone": "新电话",
        ...
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = TeamService.update_member(db, member_id, user.id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@team_bp.route('/members/<int:member_id>', methods=['DELETE'])
@login_required
def delete_member(member_id):
    """删除团队成员（软删除）"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = TeamService.delete_member(db, member_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@team_bp.route('/stats', methods=['GET'])
@login_required
def team_stats():
    """获取团队统计信息"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        stats = TeamService.get_team_stats(db, user.id)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
