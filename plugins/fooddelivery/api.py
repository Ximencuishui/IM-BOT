import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.fooddelivery.service import FoodDeliveryService

logger = logging.getLogger(__name__)

fooddelivery_bp = Blueprint('fooddelivery', __name__, url_prefix='/api/fooddelivery')


@fooddelivery_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    if request.method == 'GET':
        category = request.args.get('category', None)
        is_available = request.args.get('is_available', None)
        if is_available is not None:
            is_available = int(is_available)
        products = service.list_products(category, is_available)
        db.close()
        return jsonify({'success': True, 'count': len(products), 'products': products}), 200

    data = request.get_json()
    if not data or 'product_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少商品名称'}), 400

    result = service.create_product(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@fooddelivery_bp.route('/products/<int:product_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def product_detail(product_id):
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

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


@fooddelivery_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    if request.method == 'GET':
        status = request.args.get('status', None)
        order_type = request.args.get('order_type', None)
        orders = service.list_orders(status, order_type)
        db.close()
        return jsonify({'success': True, 'count': len(orders), 'orders': orders}), 200

    data = request.get_json()
    if not data or 'items' not in data or not data['items']:
        db.close()
        return jsonify({'success': False, 'error': '缺少订单商品'}), 400

    result = service.create_order(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@fooddelivery_bp.route('/orders/<int:order_id>', methods=['GET', 'PUT'])
@login_required
def order_detail(order_id):
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

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


@fooddelivery_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

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


@fooddelivery_bp.route('/tables', methods=['GET', 'POST'])
@login_required
def tables():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    if request.method == 'GET':
        area = request.args.get('area', None)
        status = request.args.get('status', None)
        tables = service.list_tables(area, status)
        db.close()
        return jsonify({'success': True, 'count': len(tables), 'tables': tables}), 200

    data = request.get_json()
    if not data or 'table_no' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少桌台编号'}), 400

    result = service.create_table(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@fooddelivery_bp.route('/tables/<int:table_id>/occupy', methods=['POST'])
@login_required
def occupy_table(table_id):
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    data = request.get_json()
    if not data or 'order_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少订单ID'}), 400

    result = service.occupy_table(table_id, data['order_id'])
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@fooddelivery_bp.route('/tables/<int:table_id>/free', methods=['POST'])
@login_required
def free_table(table_id):
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    result = service.free_table(table_id)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@fooddelivery_bp.route('/staff', methods=['GET', 'POST'])
@login_required
def staff():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    if request.method == 'GET':
        staff_list = service.list_staff()
        db.close()
        return jsonify({'success': True, 'count': len(staff_list), 'staff': staff_list}), 200

    data = request.get_json()
    if not data or 'name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少员工姓名'}), 400

    result = service.create_staff(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@fooddelivery_bp.route('/promotions', methods=['GET', 'POST'])
@login_required
def promotions():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    if request.method == 'GET':
        promotions = service.list_promotions()
        db.close()
        return jsonify({'success': True, 'count': len(promotions), 'promotions': promotions}), 200

    data = request.get_json()
    if not data or 'promotion_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少促销活动名称'}), 400

    result = service.create_promotion(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@fooddelivery_bp.route('/report', methods=['GET'])
@login_required
def report():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    date_range = request.args.get('date', None)
    result = service.generate_sales_report(date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@fooddelivery_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    db: Session = get_db_session()
    service = FoodDeliveryService(db)

    period = request.args.get('period', 'today')
    stats = service.get_stats(period)
    db.close()
    return jsonify({'success': True, 'stats': stats}), 200