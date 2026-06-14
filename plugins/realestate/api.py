"""
房产中介行业插件API接口
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from plugins.realestate.service import RealEstateService

logger = logging.getLogger(__name__)

realestate_bp = Blueprint('realestate', __name__, url_prefix='/api/realestate')
realestate_service = RealEstateService()


@realestate_bp.route('/properties', methods=['GET', 'POST'])
@login_required
def properties():
    if request.method == 'GET':
        district = request.args.get('district', None)
        property_type = request.args.get('type', None)
        db: Session = get_db_session()
        properties = realestate_service.list_properties(db, district, property_type)
        db.close()
        return jsonify({'success': True, 'count': len(properties), 'properties': properties}), 200

    data = request.get_json()
    if not data or 'property_name' not in data:
        return jsonify({'success': False, 'error': '缺少房源名称'}), 400

    db: Session = get_db_session()
    result = realestate_service.create_property(db, data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@realestate_bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    if request.method == 'GET':
        db: Session = get_db_session()
        customers = realestate_service.list_customers(db)
        db.close()
        return jsonify({'success': True, 'count': len(customers), 'customers': customers}), 200

    data = request.get_json()
    if not data or 'customer_name' not in data or 'phone' not in data:
        return jsonify({'success': False, 'error': '缺少客户名称或手机号'}), 400

    db: Session = get_db_session()
    result = realestate_service.create_customer(db, data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@realestate_bp.route('/agents', methods=['GET', 'POST'])
@login_required
def agents():
    if request.method == 'GET':
        db: Session = get_db_session()
        agents = realestate_service.list_agents(db)
        db.close()
        return jsonify({'success': True, 'count': len(agents), 'agents': agents}), 200

    data = request.get_json()
    if not data or 'agent_name' not in data or 'phone' not in data:
        return jsonify({'success': False, 'error': '缺少经纪人名称或手机号'}), 400

    db: Session = get_db_session()
    result = realestate_service.create_agent(db, data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@realestate_bp.route('/match', methods=['POST'])
@login_required
def match():
    data = request.get_json()
    if not data or 'customer_id' not in data:
        return jsonify({'success': False, 'error': '缺少客户ID'}), 400

    db: Session = get_db_session()
    result = realestate_service.smart_match(db, data['customer_id'])
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@realestate_bp.route('/viewing', methods=['POST'])
@login_required
def viewing():
    data = request.get_json()
    if not data or 'customer_id' not in data or 'property_id' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    db: Session = get_db_session()
    result = realestate_service.record_viewing(db, data['customer_id'], data['property_id'], data.get('agent_id'), data.get('feedback'))
    db.close()
    return jsonify(result), 200


@realestate_bp.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    if request.method == 'GET':
        db: Session = get_db_session()
        transactions = realestate_service.list_transactions(db)
        db.close()
        return jsonify({'success': True, 'count': len(transactions), 'transactions': transactions}), 200

    data = request.get_json()
    if not data or 'customer_id' not in data or 'property_id' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    db: Session = get_db_session()
    result = realestate_service.create_transaction(db, data['customer_id'], data['property_id'], data.get('agent_id'), data.get('amount'))
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@realestate_bp.route('/transactions/<int:transaction_id>/status', methods=['PUT'])
@login_required
def update_transaction_status(transaction_id):
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'success': False, 'error': '缺少状态'}), 400

    db: Session = get_db_session()
    result = realestate_service.update_transaction_status(db, transaction_id, data['status'])
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@realestate_bp.route('/contract', methods=['POST'])
@login_required
def contract():
    data = request.get_json()
    if not data or 'transaction_id' not in data or 'contract_number' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    db: Session = get_db_session()
    result = realestate_service.create_contract(db, data['transaction_id'], data['contract_number'], data.get('content'))
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@realestate_bp.route('/report', methods=['GET'])
@login_required
def report():
    report_type = request.args.get('type', 'transaction_summary')
    db: Session = get_db_session()
    result = realestate_service.generate_report(db, report_type)
    db.close()
    return jsonify(result), 200 if result['success'] else 400