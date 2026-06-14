"""
授权管理API路由
- 激活授权
- 查询状态
- 续期授权
"""
from flask import Blueprint, request, jsonify
import logging

from services.license_service import license_service

logger = logging.getLogger(__name__)

license_bp = Blueprint('license', __name__, url_prefix='/api/license')


@license_bp.route('/activate', methods=['POST'])
def activate():
    """
    激活授权码

    Request Body:
    {
        "license_code": "ABC123-DEF456-GHI789",
        "bound_to": "group_id_xxx"  // 可选,绑定的微信群ID
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('license_code'):
            return jsonify({'error': 'license_code不能为空'}), 400

        result = license_service.activate_license(
            license_code=data['license_code'],
            bound_to=data.get('bound_to')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"激活授权API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@license_bp.route('/status', methods=['GET'])
def status():
    """
    查询授权状态

    Query Params:
    - bound_to: 查询特定绑定对象(可选)
    """
    try:
        bound_to = request.args.get('bound_to')
        result = license_service.check_license(bound_to)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"查询授权状态API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@license_bp.route('/renew', methods=['POST'])
def renew():
    """
    续期授权

    Request Body:
    {
        "license_code": "ABC123-DEF456-GHI789"
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('license_code'):
            return jsonify({'error': 'license_code不能为空'}), 400

        result = license_service.renew_license(data['license_code'])

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"续期授权API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@license_bp.route('/groups/count', methods=['GET'])
def groups_count():
    """获取当前授权的群数量"""
    try:
        count = license_service.get_active_groups_count()
        can_add = license_service.can_add_group()

        return jsonify({
            'active_groups': count,
            'can_add_group': can_add
        }), 200

    except Exception as e:
        logger.error(f"查询群数量API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@license_bp.route('/machine-id', methods=['GET'])
def machine_id():
    """获取当前机器指纹(用于购买授权时绑定)"""
    return jsonify({
        'machine_id': license_service.machine_id
    }), 200
