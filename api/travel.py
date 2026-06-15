"""
旅行社服务API
提供旅游线路、群配置、报名、反馈、日报等CRUD操作
"""
import logging
from flask import Blueprint, request, jsonify

from services.travel_service import travel_service

logger = logging.getLogger(__name__)

travel_bp = Blueprint('travel', __name__, url_prefix='/api/travel')


@travel_bp.route('/routes', methods=['POST'])
def create_route():
    """创建旅游线路"""
    try:
        data = request.get_json()
        if not data or 'route_name' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: route_name'}), 400

        result = travel_service.create_route(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建旅游线路失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/routes', methods=['GET'])
def get_routes():
    """获取旅游线路列表"""
    try:
        status = request.args.get('status', None)
        routes = travel_service.get_routes(status)
        return jsonify({
            'success': True,
            'count': len(routes),
            'routes': [route.to_dict() for route in routes],
        }), 200
    except Exception as e:
        logger.error(f"获取旅游线路列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/routes/<int:route_id>', methods=['GET'])
def get_route(route_id):
    """获取旅游线路详情"""
    try:
        route = travel_service.get_route(route_id)
        if not route:
            return jsonify({'success': False, 'error': '线路不存在'}), 404
        return jsonify({'success': True, 'data': route.to_dict()}), 200
    except Exception as e:
        logger.error(f"获取旅游线路详情失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/routes/<int:route_id>', methods=['PUT'])
def update_route(route_id):
    """更新旅游线路"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        result = travel_service.update_route(route_id, data)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"更新旅游线路失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/routes/<int:route_id>', methods=['DELETE'])
def delete_route(route_id):
    """删除旅游线路"""
    try:
        result = travel_service.delete_route(route_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"删除旅游线路失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/routes/<int:route_id>/forward', methods=['POST'])
def forward_route(route_id):
    """转发线路到旅游群"""
    try:
        result = travel_service.forward_route_to_groups(route_id)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"转发线路失败: route_id={route_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/routes/parse', methods=['POST'])
def parse_route():
    """解析线路信息"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: text'}), 400

        result = travel_service.parse_travel_route(data['text'])
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"解析线路信息失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/groups', methods=['POST'])
def create_group():
    """创建群配置"""
    try:
        data = request.get_json()
        if not data or 'group_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: group_id'}), 400

        result = travel_service.create_group(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建群配置失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/groups', methods=['GET'])
def get_groups():
    """获取群配置列表"""
    try:
        groups = travel_service.get_groups()
        return jsonify({
            'success': True,
            'count': len(groups),
            'groups': [group.to_dict() for group in groups],
        }), 200
    except Exception as e:
        logger.error(f"获取群配置列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """更新群配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        from database.db_config import get_db_session
        from models.travel_models import TravelGroup

        db = get_db_session()
        try:
            group = db.query(TravelGroup).filter(TravelGroup.id == group_id).first()
            if not group:
                return jsonify({'success': False, 'error': '群配置不存在'}), 404

            if 'platform' in data:
                group.platform = data['platform']
            if 'group_id' in data:
                group.group_id = data['group_id']
            if 'group_name' in data:
                group.group_name = data['group_name']
            if 'boss_wxid' in data:
                group.boss_wxid = data['boss_wxid']
            if 'is_active' in data:
                group.is_active = data['is_active']

            db.commit()
            db.refresh(group)
            return jsonify({'success': True, 'data': group.to_dict()}), 200
        finally:
            db.close()
    except Exception as e:
        logger.error(f"更新群配置失败: group_id={group_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """删除群配置"""
    try:
        from database.db_config import get_db_session
        from models.travel_models import TravelGroup

        db = get_db_session()
        try:
            group = db.query(TravelGroup).filter(TravelGroup.id == group_id).first()
            if not group:
                return jsonify({'success': False, 'error': '群配置不存在'}), 404

            db.delete(group)
            db.commit()
            return jsonify({'success': True, 'message': '群配置删除成功'}), 200
        finally:
            db.close()
    except Exception as e:
        logger.error(f"删除群配置失败: group_id={group_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/registrations', methods=['POST'])
def create_registration():
    """创建报名"""
    try:
        data = request.get_json()
        if not data or 'route_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: route_id'}), 400

        result = travel_service.create_registration(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建报名失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/registrations', methods=['GET'])
def get_registrations():
    """获取报名列表"""
    try:
        route_id = request.args.get('route_id', None)
        status = request.args.get('status', None)

        registrations = travel_service.get_registrations(
            int(route_id) if route_id else None,
            status
        )
        return jsonify({
            'success': True,
            'count': len(registrations),
            'registrations': [reg.to_dict() for reg in registrations],
        }), 200
    except Exception as e:
        logger.error(f"获取报名列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/registrations/<int:registration_id>', methods=['PUT'])
def update_registration(registration_id):
    """更新报名状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        result = travel_service.update_registration(registration_id, data)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"更新报名状态失败: registration_id={registration_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/feedback', methods=['POST'])
def process_feedback():
    """处理群反馈"""
    try:
        data = request.get_json()
        required_fields = ['group_id', 'user_id', 'user_name', 'content']
        if not data or any(field not in data for field in required_fields):
            return jsonify({'success': False, 'error': f'缺少必要参数: {", ".join(required_fields)}'}), 400

        result = travel_service.process_group_feedback(
            data['group_id'],
            data['user_id'],
            data['user_name'],
            data['content']
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"处理群反馈失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/feedback', methods=['GET'])
def get_feedbacks():
    """获取反馈列表"""
    try:
        group_id = request.args.get('group_id', None)
        status = request.args.get('status', None)

        feedbacks = travel_service.get_feedbacks(
            int(group_id) if group_id else None,
            status
        )
        return jsonify({
            'success': True,
            'count': len(feedbacks),
            'feedbacks': [f.to_dict() for f in feedbacks],
        }), 200
    except Exception as e:
        logger.error(f"获取反馈列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/feedback/<int:feedback_id>/reply', methods=['POST'])
def reply_feedback(feedback_id):
    """回复反馈"""
    try:
        data = request.get_json()
        if not data or 'response' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: response'}), 400

        result = travel_service.reply_feedback(feedback_id, data['response'])
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"回复反馈失败: feedback_id={feedback_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/daily-report', methods=['GET'])
def get_daily_report():
    """获取日报内容"""
    try:
        date_str = request.args.get('date', None)
        result = travel_service.generate_daily_report(date_str)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"获取日报内容失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/daily-report', methods=['POST'])
def send_daily_report():
    """手动触发发送日报"""
    try:
        travel_service.send_daily_report()
        return jsonify({'success': True, 'message': '日报已发送'}), 200
    except Exception as e:
        logger.error(f"发送日报失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/reply-rules', methods=['POST'])
def create_reply_rule():
    """创建自动回复规则"""
    try:
        data = request.get_json()
        if not data or 'rule_name' not in data or 'response' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: rule_name, response'}), 400

        result = travel_service.create_reply_rule(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建自动回复规则失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@travel_bp.route('/reply-rules', methods=['GET'])
def get_reply_rules():
    """获取自动回复规则列表"""
    try:
        route_id = request.args.get('route_id', None)
        rules = travel_service.get_reply_rules(int(route_id) if route_id else None)
        return jsonify({
            'success': True,
            'count': len(rules),
            'rules': [rule.to_dict() for rule in rules],
        }), 200
    except Exception as e:
        logger.error(f"获取自动回复规则列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
