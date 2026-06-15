import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.seafood.service import SeafoodService

logger = logging.getLogger(__name__)

seafood_bp = Blueprint('seafood', __name__, url_prefix='/api/seafood')


@seafood_bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        customer_type = request.args.get('customer_type', None)
        customers = service.list_customers(customer_type)
        db.close()
        return jsonify({'success': True, 'count': len(customers), 'customers': customers}), 200

    data = request.get_json()
    if not data or 'customer_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少客户名称'}), 400

    result = service.create_customer(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@seafood_bp.route('/customers/<int:customer_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def customer_detail(customer_id):
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        customers = service.list_customers()
        customer = next((c for c in customers if c['id'] == customer_id), None)
        db.close()
        if not customer:
            return jsonify({'success': False, 'error': '客户不存在'}), 404
        return jsonify({'success': True, 'customer': customer}), 200

    if request.method == 'PUT':
        data = request.get_json()
        result = service.update_customer(customer_id, data)
        db.close()
        return jsonify(result), 200 if result['success'] else 400

    if request.method == 'DELETE':
        result = service.delete_customer(customer_id)
        db.close()
        return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/suppliers', methods=['GET', 'POST'])
@login_required
def suppliers():
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        suppliers = service.list_suppliers()
        db.close()
        return jsonify({'success': True, 'count': len(suppliers), 'suppliers': suppliers}), 200

    data = request.get_json()
    if not data or 'supplier_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少供应商名称'}), 400

    result = service.create_supplier(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@seafood_bp.route('/suppliers/<int:supplier_id>', methods=['GET', 'PUT'])
@login_required
def supplier_detail(supplier_id):
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        suppliers = service.list_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        db.close()
        if not supplier:
            return jsonify({'success': False, 'error': '供应商不存在'}), 404
        return jsonify({'success': True, 'supplier': supplier}), 200

    if request.method == 'PUT':
        data = request.get_json()
        result = service.update_supplier(supplier_id, data)
        db.close()
        return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        category = request.args.get('category', None)
        products = service.list_products(category)
        db.close()
        return jsonify({'success': True, 'count': len(products), 'products': products}), 200

    data = request.get_json()
    if not data or 'product_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少商品名称'}), 400

    result = service.create_product(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@seafood_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        customer_id = request.args.get('customer_id', None)
        status = request.args.get('status', None)
        is_urgent = request.args.get('is_urgent', None)
        delivery_date = request.args.get('delivery_date', None)

        if customer_id:
            customer_id = int(customer_id)
        if is_urgent is not None:
            is_urgent = int(is_urgent)

        orders = service.list_orders(customer_id, status, is_urgent, delivery_date)
        db.close()
        return jsonify({'success': True, 'count': len(orders), 'orders': orders}), 200

    data = request.get_json()
    if not data or 'customer_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少客户ID'}), 400

    result = service.create_order(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@seafood_bp.route('/orders/<int:order_id>', methods=['GET', 'PUT'])
@login_required
def order_detail(order_id):
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        order = service.get_order(order_id)
        db.close()
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        return jsonify({'success': True, 'order': order}), 200

    if request.method == 'PUT':
        data = request.get_json()
        if not data or 'status' not in data:
            db.close()
            return jsonify({'success': False, 'error': '缺少订单状态'}), 400
        result = service.update_order_status(order_id, data['status'])
        db.close()
        return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    db: Session = get_db_session()
    service = SeafoodService(db)

    if request.method == 'GET':
        cutoff_time = service.get_config('cutoff_time', '21:00')
        db.close()
        return jsonify({'success': True, 'config': {'cutoff_time': cutoff_time}}), 200

    data = request.get_json()
    if not data or 'cutoff_time' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少截单时间配置'}), 400

    result = service.set_config('cutoff_time', data['cutoff_time'], 'string', '截单时间设置')
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/reminders', methods=['GET'])
@login_required
def get_reminders():
    db: Session = get_db_session()
    service = SeafoodService(db)

    customers = service.get_customers_needing_reminder()
    db.close()
    return jsonify({'success': True, 'count': len(customers), 'customers': customers}), 200


@seafood_bp.route('/reminders/send/<int:customer_id>', methods=['POST'])
@login_required
def send_reminder(customer_id):
    db: Session = get_db_session()
    service = SeafoodService(db)

    result = service.send_reminder(customer_id)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/parse-message', methods=['POST'])
@login_required
def parse_message():
    db: Session = get_db_session()
    service = SeafoodService(db)

    data = request.get_json()
    if not data or 'message' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少消息内容'}), 400

    result = service.parse_order_message(data['message'])
    db.close()
    return jsonify(result), 200


@seafood_bp.route('/reports/orders', methods=['GET'])
@login_required
def order_report():
    db: Session = get_db_session()
    service = SeafoodService(db)

    date_range = request.args.get('date_range', None)
    result = service.generate_order_report(date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/reports/customers', methods=['GET'])
@login_required
def customer_report():
    db: Session = get_db_session()
    service = SeafoodService(db)

    date_range = request.args.get('date_range', None)
    result = service.generate_customer_report(date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/reports/stock', methods=['GET'])
@login_required
def stock_report():
    db: Session = get_db_session()
    service = SeafoodService(db)

    result = service.generate_stock_report()
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@seafood_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    db: Session = get_db_session()
    service = SeafoodService(db)

    period = request.args.get('period', 'today')
    stats = service.get_stats(period)
    db.close()
    return jsonify({'success': True, 'stats': stats}), 200