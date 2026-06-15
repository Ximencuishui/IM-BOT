import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.teacoffee.service import TeaCoffeeService

logger = logging.getLogger(__name__)

teacoffee_bp = Blueprint('teacoffee', __name__, url_prefix='/api/teacoffee')


@teacoffee_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    if request.method == 'GET':
        category = request.args.get('category', None)
        sub_category = request.args.get('sub_category', None)
        is_available = request.args.get('is_available', None)
        if is_available is not None:
            is_available = int(is_available)
        products = service.list_products(category, sub_category, is_available)
        db.close()
        return jsonify({'success': True, 'count': len(products), 'products': products}), 200

    data = request.get_json()
    if not data or 'product_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少商品名称'}), 400

    result = service.create_product(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@teacoffee_bp.route('/products/<int:product_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def product_detail(product_id):
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

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


@teacoffee_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    if request.method == 'GET':
        status = request.args.get('status', None)
        order_type = request.args.get('order_type', None)
        member_id = request.args.get('member_id', None)
        if member_id:
            member_id = int(member_id)
        orders = service.list_orders(status, order_type, member_id)
        db.close()
        return jsonify({'success': True, 'count': len(orders), 'orders': orders}), 200

    data = request.get_json()
    if not data or 'items' not in data or not data['items']:
        db.close()
        return jsonify({'success': False, 'error': '缺少订单商品'}), 400

    result = service.create_order(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@teacoffee_bp.route('/orders/<int:order_id>', methods=['GET', 'PUT'])
@login_required
def order_detail(order_id):
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

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


@teacoffee_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

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


@teacoffee_bp.route('/members', methods=['GET', 'POST'])
@login_required
def members():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    if request.method == 'GET':
        member_level = request.args.get('member_level', None)
        members = service.list_members(member_level)
        db.close()
        return jsonify({'success': True, 'count': len(members), 'members': members}), 200

    data = request.get_json()
    if not data or 'member_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少会员姓名'}), 400

    result = service.create_member(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@teacoffee_bp.route('/members/phone/<phone>', methods=['GET'])
@login_required
def member_by_phone(phone):
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    member = service.get_member_by_phone(phone)
    db.close()
    if not member:
        return jsonify({'success': False, 'error': '会员不存在'}), 404
    return jsonify({'success': True, 'member': member}), 200


@teacoffee_bp.route('/ingredients', methods=['GET', 'POST'])
@login_required
def ingredients():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    if request.method == 'GET':
        low_stock = request.args.get('low_stock', 'false').lower() == 'true'
        ingredients = service.list_ingredients(low_stock)
        db.close()
        return jsonify({'success': True, 'count': len(ingredients), 'ingredients': ingredients}), 200

    data = request.get_json()
    if not data or 'ingredient_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少原料名称'}), 400

    result = service.create_ingredient(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@teacoffee_bp.route('/recommend', methods=['POST'])
@login_required
def recommend():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    data = request.get_json() or {}
    recommendations = service.recommend_product(data)
    db.close()
    return jsonify({'success': True, 'recommendations': recommendations}), 200


@teacoffee_bp.route('/parse_message', methods=['POST'])
@login_required
def parse_message():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    data = request.get_json()
    if not data or 'message' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少消息内容'}), 400

    result = service.parse_message(data['message'])
    db.close()
    return jsonify(result), 200


@teacoffee_bp.route('/report', methods=['GET'])
@login_required
def report():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    date_range = request.args.get('date', None)
    result = service.generate_sales_report(date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@teacoffee_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    db: Session = get_db_session()
    service = TeaCoffeeService(db)

    period = request.args.get('period', 'today')
    stats = service.get_stats(period)
    db.close()
    return jsonify({'success': True, 'stats': stats}), 200