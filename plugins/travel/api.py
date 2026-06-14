import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.travel.service import TravelService

logger = logging.getLogger(__name__)

travel_bp = Blueprint('travel', __name__, url_prefix='/api/travel')


@travel_bp.route('/routes', methods=['GET', 'POST'])
@login_required
def routes():
    db: Session = get_db_session()
    service = TravelService(db)

    if request.method == 'GET':
        status = request.args.get('status', None)
        routes = service.list_routes(status)
        db.close()
        return jsonify({'success': True, 'count': len(routes), 'routes': routes}), 200

    data = request.get_json()
    if not data or 'route_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少线路名称'}), 400

    result = service.create_route(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@travel_bp.route('/routes/<int:route_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def route_detail(route_id):
    db: Session = get_db_session()
    service = TravelService(db)

    if request.method == 'GET':
        route = service.get_route(route_id)
        db.close()
        if not route:
            return jsonify({'success': False, 'error': '线路不存在'}), 404
        return jsonify({'success': True, 'route': route}), 200

    if request.method == 'PUT':
        data = request.get_json()
        result = service.update_route(route_id, data)
        db.close()
        return jsonify(result), 200 if result['success'] else 400

    if request.method == 'DELETE':
        result = service.delete_route(route_id)
        db.close()
        return jsonify(result), 200 if result['success'] else 400


@travel_bp.route('/groups', methods=['GET', 'POST'])
@login_required
def groups():
    db: Session = get_db_session()
    service = TravelService(db)

    if request.method == 'GET':
        groups = service.list_groups()
        db.close()
        return jsonify({'success': True, 'count': len(groups), 'groups': groups}), 200

    data = request.get_json()
    if not data or 'group_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少群ID'}), 400

    result = service.create_group(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@travel_bp.route('/registrations', methods=['GET', 'POST'])
@login_required
def registrations():
    db: Session = get_db_session()
    service = TravelService(db)

    if request.method == 'GET':
        route_id = request.args.get('route_id', None)
        status = request.args.get('status', None)
        registrations = service.list_registrations(route_id, status)
        db.close()
        return jsonify({'success': True, 'count': len(registrations), 'registrations': registrations}), 200

    data = request.get_json()
    if not data or 'route_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少线路ID'}), 400

    result = service.create_registration(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@travel_bp.route('/registrations/<int:registration_id>', methods=['PUT'])
@login_required
def update_registration(registration_id):
    db: Session = get_db_session()
    service = TravelService(db)

    data = request.get_json()
    result = service.update_registration(registration_id, data)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@travel_bp.route('/feedbacks', methods=['GET', 'POST'])
@login_required
def feedbacks():
    db: Session = get_db_session()
    service = TravelService(db)

    if request.method == 'GET':
        group_id = request.args.get('group_id', None)
        status = request.args.get('status', None)
        feedbacks = service.list_feedbacks(group_id, status)
        db.close()
        return jsonify({'success': True, 'count': len(feedbacks), 'feedbacks': feedbacks}), 200

    data = request.get_json()
    if not data or 'group_id' not in data or 'content' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少群ID或内容'}), 400

    result = service.create_feedback(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@travel_bp.route('/feedbacks/<int:feedback_id>/reply', methods=['POST'])
@login_required
def reply_feedback(feedback_id):
    db: Session = get_db_session()
    service = TravelService(db)

    data = request.get_json()
    if not data or 'response' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少回复内容'}), 400

    result = service.reply_feedback(feedback_id, data['response'])
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@travel_bp.route('/reply_rules', methods=['GET', 'POST'])
@login_required
def reply_rules():
    db: Session = get_db_session()
    service = TravelService(db)

    if request.method == 'GET':
        route_id = request.args.get('route_id', None)
        rules = service.list_reply_rules(route_id)
        db.close()
        return jsonify({'success': True, 'count': len(rules), 'rules': rules}), 200

    data = request.get_json()
    if not data or 'rule_name' not in data or 'response' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少规则名称或回复内容'}), 400

    result = service.create_reply_rule(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@travel_bp.route('/report', methods=['GET'])
@login_required
def report():
    db: Session = get_db_session()
    service = TravelService(db)

    report_type = request.args.get('type', 'daily')
    date_range = request.args.get('date', None)
    result = service.generate_report(report_type, date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@travel_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    db: Session = get_db_session()
    service = TravelService(db)

    period = request.args.get('period', 'today')
    stats = service.get_stats(period)
    db.close()
    return jsonify({'success': True, 'stats': stats}), 200