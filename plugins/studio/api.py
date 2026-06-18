"""
歌曲分离工作室 - REST API
提供服务配置、订单管理、工作流、知识库、问候语、统计等接口
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.studio.service import StudioService

logger = logging.getLogger(__name__)

studio_bp = Blueprint('studio', __name__, url_prefix='/api/studio')


def get_service() -> StudioService:
    """获取StudioService实例"""
    db: Session = get_db_session()
    return StudioService(db)


def close_db(service):
    """关闭数据库会话"""
    if service and service.db:
        service.db.close()


# ==================== 服务配置管理 ====================

@studio_bp.route('/services', methods=['GET', 'POST'])
@login_required
def services():
    svc = get_service()
    try:
        if request.method == 'GET':
            is_active = request.args.get('is_active', None)
            if is_active is not None:
                is_active = int(is_active)
            configs = svc.list_service_configs(is_active)
            return jsonify({'success': True, 'count': len(configs), 'services': configs}), 200

        data = request.get_json()
        if not data or 'service_name' not in data or 'service_code' not in data:
            return jsonify({'success': False, 'error': '缺少服务名称或编码'}), 400

        result = svc.create_service_config(data)
        return jsonify(result), 201 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/services/<int:config_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def service_detail(config_id):
    svc = get_service()
    try:
        if request.method == 'GET':
            config = svc.get_service_config(config_id)
            if not config:
                return jsonify({'success': False, 'error': '服务配置不存在'}), 404
            return jsonify({'success': True, 'service': config}), 200

        if request.method == 'PUT':
            data = request.get_json()
            result = svc.update_service_config(config_id, data)
            return jsonify(result), 200 if result['success'] else 400

        if request.method == 'DELETE':
            result = svc.delete_service_config(config_id)
            return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


# ==================== 订单管理 ====================

@studio_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    svc = get_service()
    try:
        if request.method == 'GET':
            status = request.args.get('status')
            service_code = request.args.get('service_code')
            customer_wx_id = request.args.get('customer_wx_id')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            result = svc.list_orders(status, service_code, customer_wx_id,
                                     start_date, end_date, page, page_size)
            return jsonify(result), 200

        data = request.get_json()
        if not data or 'service_code' not in data:
            return jsonify({'success': False, 'error': '缺少服务编码'}), 400

        result = svc.create_order(data)
        return jsonify(result), 201 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/orders/<int:order_id>', methods=['GET', 'PUT'])
@login_required
def order_detail(order_id):
    svc = get_service()
    try:
        if request.method == 'GET':
            order = svc.get_order(order_id)
            if not order:
                return jsonify({'success': False, 'error': '订单不存在'}), 404
            return jsonify({'success': True, 'order': order}), 200

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '缺少更新数据'}), 400

        # 如果包含status字段，使用状态机更新
        if 'status' in data:
            extra = {k: v for k, v in data.items() if k != 'status'}
            result = svc.update_order_status(order_id, data['status'], **extra)
        else:
            result = svc.update_order(order_id, data)
        return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/orders/<int:order_id>/notify-boss', methods=['POST'])
@login_required
def notify_boss(order_id):
    """通知老板有新订单"""
    svc = get_service()
    try:
        order = svc.get_order(order_id)
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404

        notification = svc.generate_boss_notification(order)
        # TODO: 实际发送微信消息给老板
        logger.info(f"老板通知: {notification}")

        return jsonify({'success': True, 'notification': notification}), 200
    finally:
        close_db(svc)


@studio_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@login_required
def update_order_status(order_id):
    """更新订单状态"""
    svc = get_service()
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': '缺少订单状态'}), 400

        extra = {k: v for k, v in data.items() if k != 'status'}
        result = svc.update_order_status(order_id, data['status'], **extra)
        return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


# ==================== 工作流配置 ====================

@studio_bp.route('/workflows', methods=['GET', 'POST'])
@login_required
def workflows():
    svc = get_service()
    try:
        if request.method == 'GET':
            service_code = request.args.get('service_code')
            configs = svc.list_workflow_configs(service_code)
            return jsonify({'success': True, 'count': len(configs), 'workflows': configs}), 200

        data = request.get_json()
        if not data or 'service_code' not in data or 'workflow_name' not in data:
            return jsonify({'success': False, 'error': '缺少服务编码或工作流名称'}), 400

        result = svc.create_workflow_config(data)
        return jsonify(result), 201 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/workflows/<int:wf_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def workflow_detail(wf_id):
    svc = get_service()
    try:
        if request.method == 'GET':
            config = svc.get_workflow_config(wf_id)
            if not config:
                return jsonify({'success': False, 'error': '工作流配置不存在'}), 404
            return jsonify({'success': True, 'workflow': config}), 200

        if request.method == 'PUT':
            data = request.get_json()
            result = svc.update_workflow_config(wf_id, data)
            return jsonify(result), 200 if result['success'] else 400

        if request.method == 'DELETE':
            result = svc.delete_workflow_config(wf_id)
            return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/workflows/<int:wf_id>/execute', methods=['POST'])
@login_required
def execute_workflow(wf_id):
    """触发工作流执行"""
    svc = get_service()
    try:
        data = request.get_json()
        if not data or 'order_id' not in data:
            return jsonify({'success': False, 'error': '缺少订单ID'}), 400

        # 验证工作流存在
        wf = svc.get_workflow_config(wf_id)
        if not wf:
            return jsonify({'success': False, 'error': '工作流配置不存在'}), 404

        file_path = data.get('file_path')
        result = svc.start_workflow(data['order_id'], file_path=file_path)
        return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/workflows/executions/<int:execution_id>', methods=['GET'])
@login_required
def workflow_execution(execution_id):
    """获取工作流执行进度"""
    svc = get_service()
    try:
        execution = svc.get_workflow_execution(execution_id)
        if not execution:
            return jsonify({'success': False, 'error': '执行记录不存在'}), 404
        return jsonify({'success': True, 'execution': execution}), 200
    finally:
        close_db(svc)


# ==================== 知识库管理 ====================

@studio_bp.route('/knowledge', methods=['GET', 'POST'])
@login_required
def knowledge():
    svc = get_service()
    try:
        if request.method == 'GET':
            category = request.args.get('category')
            is_resolved = request.args.get('is_resolved')
            if is_resolved is not None:
                is_resolved = int(is_resolved)
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            result = svc.list_knowledge(category, is_resolved, page, page_size)
            return jsonify(result), 200

        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'success': False, 'error': '缺少问题内容'}), 400

        result = svc.add_knowledge(data)
        return jsonify(result), 201 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/knowledge/unresolved', methods=['GET'])
@login_required
def unresolved_questions():
    """列出未解答问题"""
    svc = get_service()
    try:
        questions = svc.list_unresolved_questions()
        return jsonify({'success': True, 'count': len(questions), 'questions': questions}), 200
    finally:
        close_db(svc)


@studio_bp.route('/knowledge/<int:entry_id>/answer', methods=['POST'])
@login_required
def answer_question(entry_id):
    """老板回答问题"""
    svc = get_service()
    try:
        data = request.get_json()
        if not data or 'answer' not in data:
            return jsonify({'success': False, 'error': '缺少答案内容'}), 400

        result = svc.answer_knowledge(entry_id, data['answer'])
        return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/knowledge/search', methods=['POST'])
@login_required
def search_knowledge():
    """搜索知识库"""
    svc = get_service()
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'success': False, 'error': '缺少查询问题'}), 400

        result = svc.search_knowledge(data['question'])
        if result:
            return jsonify({'success': True, 'matched': True, 'entry': result}), 200
        return jsonify({'success': True, 'matched': False, 'entry': None}), 200
    finally:
        close_db(svc)


# ==================== 问候语管理 ====================

@studio_bp.route('/greetings', methods=['GET', 'POST'])
@login_required
def greetings():
    svc = get_service()
    try:
        if request.method == 'GET':
            greeting_type = request.args.get('greeting_type')
            configs = svc.list_greetings(greeting_type)
            return jsonify({'success': True, 'count': len(configs), 'greetings': configs}), 200

        data = request.get_json()
        if not data or 'greeting_text' not in data:
            return jsonify({'success': False, 'error': '缺少问候内容'}), 400

        result = svc.create_greeting(data)
        return jsonify(result), 201 if result['success'] else 400
    finally:
        close_db(svc)


@studio_bp.route('/greetings/<int:greeting_id>', methods=['PUT', 'DELETE'])
@login_required
def greeting_detail(greeting_id):
    svc = get_service()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            result = svc.update_greeting(greeting_id, data)
            return jsonify(result), 200 if result['success'] else 400

        if request.method == 'DELETE':
            result = svc.delete_greeting(greeting_id)
            return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


# ==================== 统计与概览 ====================

@studio_bp.route('/stats/dashboard', methods=['GET'])
@login_required
def dashboard_stats():
    """获取概览统计"""
    svc = get_service()
    try:
        stats = svc.get_dashboard_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    finally:
        close_db(svc)


@studio_bp.route('/stats', methods=['GET'])
@login_required
def statistics():
    """获取详细统计"""
    svc = get_service()
    try:
        stat_type = request.args.get('stat_type', 'daily')
        service_code = request.args.get('service_code')
        days = int(request.args.get('days', 30))
        result = svc.get_statistics(stat_type, service_code, days)
        return jsonify(result), 200
    finally:
        close_db(svc)


@studio_bp.route('/stats/refresh', methods=['POST'])
@login_required
def refresh_stats():
    """刷新统计数据"""
    svc = get_service()
    try:
        data = request.get_json() or {}
        stat_type = data.get('stat_type', 'daily')
        result = svc.refresh_statistics(stat_type=stat_type)
        return jsonify(result), 200 if result['success'] else 400
    finally:
        close_db(svc)


# ==================== NLP/消息解析 ====================

@studio_bp.route('/parse-message', methods=['POST'])
@login_required
def parse_message():
    """解析客户消息"""
    svc = get_service()
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': '缺少消息内容'}), 400

        parse_result = svc.parse_requirement(data['message'])
        response = svc.generate_consultation_response(parse_result)
        return jsonify({
            'success': True,
            'parse_result': parse_result,
            'response': response,
        }), 200
    finally:
        close_db(svc)