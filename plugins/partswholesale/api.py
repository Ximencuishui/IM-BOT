import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.partswholesale.service import PartsWholesaleService

logger = logging.getLogger(__name__)

partswholesale_bp = Blueprint('partswholesale', __name__, url_prefix='/api/partswholesale')


@partswholesale_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    if request.method == 'GET':
        category = request.args.get('category', None)
        brand = request.args.get('brand', None)
        is_available = request.args.get('is_available', None)
        if is_available is not None:
            is_available = int(is_available)
        products = service.list_products(category, brand, is_available)
        db.close()
        return jsonify({'success': True, 'count': len(products), 'products': products}), 200

    data = request.get_json()
    if not data or 'product_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少商品名称'}), 400

    result = service.create_product(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@partswholesale_bp.route('/products/<int:product_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def product_detail(product_id):
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    if request.method == 'GET':
        products = service.list_products()
        product = next((p for p in products if p['id'] == product_id), None)
        db.close()
        if not product:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        return jsonify({'success': True, 'product': product}), 200

    if request.method == 'PUT':
        data = request.get_json()
        result = service.update_product(product_id, data)
        db.close()
        return jsonify(result), 200 if result['success'] else 400

    if request.method == 'DELETE':
        result = service.delete_product(product_id)
        db.close()
        return jsonify(result), 200 if result['success'] else 400


@partswholesale_bp.route('/products/<int:product_id>/wholesale_price', methods=['GET'])
@login_required
def wholesale_price(product_id):
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    quantity = request.args.get('quantity', 1)
    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    price = service.calculate_wholesale_price(product_id, quantity)
    db.close()
    return jsonify({'success': True, 'product_id': product_id, 'quantity': quantity, 'price': price}), 200


@partswholesale_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    if request.method == 'GET':
        status = request.args.get('status', None)
        order_type = request.args.get('order_type', None)
        customer_id = request.args.get('customer_id', None)
        if customer_id:
            customer_id = int(customer_id)
        orders = service.list_orders(status, order_type, customer_id)
        db.close()
        return jsonify({'success': True, 'count': len(orders), 'orders': orders}), 200

    data = request.get_json()
    if not data or 'items' not in data or not data['items']:
        db.close()
        return jsonify({'success': False, 'error': '缺少订单商品'}), 400

    result = service.create_order(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@partswholesale_bp.route('/orders/<int:order_id>', methods=['GET', 'PUT'])
@login_required
def order_detail(order_id):
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

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


@partswholesale_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    if request.method == 'GET':
        categories = service.list_categories()
        db.close()
        return jsonify({'success': True, 'count': len(categories), 'categories': categories}), 200

    data = request.get_json()
    if not data or 'category_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少分类名称'}), 400

    result = service.create_category(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@partswholesale_bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    if request.method == 'GET':
        customer_level = request.args.get('customer_level', None)
        customers = service.list_customers(customer_level)
        db.close()
        return jsonify({'success': True, 'count': len(customers), 'customers': customers}), 200

    data = request.get_json()
    if not data or 'customer_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少客户名称'}), 400

    result = service.create_customer(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@partswholesale_bp.route('/customers/phone/<phone>', methods=['GET'])
@login_required
def customer_by_phone(phone):
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    customer = service.get_customer_by_phone(phone)
    db.close()
    if not customer:
        return jsonify({'success': False, 'error': '客户不存在'}), 404
    return jsonify({'success': True, 'customer': customer}), 200


@partswholesale_bp.route('/price_levels', methods=['GET', 'POST'])
@login_required
def price_levels():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    if request.method == 'GET':
        levels = service.list_price_levels()
        db.close()
        return jsonify({'success': True, 'count': len(levels), 'price_levels': levels}), 200

    data = request.get_json()
    if not data or 'level_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少价格等级名称'}), 400

    result = service.create_price_level(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@partswholesale_bp.route('/parse_message', methods=['POST'])
@login_required
def parse_message():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    data = request.get_json()
    if not data or 'message' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少消息内容'}), 400

    result = service.parse_message(data['message'])
    db.close()
    return jsonify(result), 200


@partswholesale_bp.route('/report', methods=['GET'])
@login_required
def report():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    date_range = request.args.get('date', None)
    result = service.generate_sales_report(date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@partswholesale_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    db: Session = get_db_session()
    service = PartsWholesaleService(db)

    period = request.args.get('period', 'today')
    stats = service.get_stats(period)
    db.close()
    return jsonify({'success': True, 'stats': stats}), 200