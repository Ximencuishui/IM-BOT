"""
订单管理API路由
"""
from flask import Blueprint, request, jsonify
from datetime import date, datetime
import logging

from services.order_service import order_service
from services.customer_service import customer_service
from services.order_parser import parse_order_message

logger = logging.getLogger(__name__)

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')


@orders_bp.route('', methods=['GET', 'POST'])
def handle_orders():
    """
    GET: 获取订单列表
    POST: 创建/更新订单
    """
    if request.method == 'GET':
        return list_orders()
    elif request.method == 'POST':
        return create_order()


def list_orders():
    """
    获取订单列表

    Query Params:
    - page: 页码(默认1)
    - page_size: 每页数量(默认20)
    - customer: 客户名称/电话模糊搜索
    - status: 订单状态筛选
    - start_date: 开始日期
    - end_date: 结束日期
    """
    try:
        from database.db_config import get_db_session
        from models.models import Order, Customer
        from sqlalchemy import or_

        db = get_db_session()

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        customer = request.args.get('customer', '')
        status = request.args.get('status', '')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        query = db.query(Order).join(Customer, Order.customer_id == Customer.id)

        # 客户搜索
        if customer:
            query = query.filter(
                or_(
                    Customer.customer_name.contains(customer),
                    Customer.phone.contains(customer)
                )
            )

        # 状态筛选
        if status:
            query = query.filter(Order.status == status)

        # 日期范围筛选
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query = query.filter(Order.order_date >= start_date)
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(Order.order_date <= end_date)
            except ValueError:
                pass

        # 总数
        total = query.count()

        # 分页
        orders = query.order_by(Order.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'page_size': page_size,
            'orders': [order.to_dict() for order in orders]
        }), 200

    except Exception as e:
        logger.error(f"获取订单列表异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


def create_order():
    """
    创建/更新订单

    Request Body:
    {
        "customer_id": 1,
        "items": [
            {"product_id": 1, "quantity": 10.0, "remark": "要嫩的"}
        ],
        "order_date": "2025-04-15",  // 可选,默认今天
        "remark": "订单备注",
        "order_uuid": "xxx"  // 可选,用于幂等性
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        # 验证必填字段
        if not data.get('customer_id'):
            return jsonify({'error': 'customer_id不能为空'}), 400

        if not data.get('items') or not isinstance(data['items'], list):
            return jsonify({'error': 'items必须是非空列表'}), 400

        # 解析order_date
        order_date = None
        if data.get('order_date'):
            try:
                order_date = datetime.strptime(data['order_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': '日期格式错误,应为YYYY-MM-DD'}), 400

        # 调用服务
        result = order_service.create_or_update_order(
            customer_id=data['customer_id'],
            items=data['items'],
            order_date=order_date,
            remark=data.get('remark'),
            order_uuid=data.get('order_uuid'),
            source_type=data.get('source_type', 'api')
        )

        if result['success']:
            status_code = 201 if not result.get('is_duplicate') else 200
            return jsonify(result), status_code
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"创建订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/parse', methods=['POST'])
def parse_and_create_order():
    """
    解析消息并创建订单(用于Hook消息自动处理)

    Request Body:
    {
        "group_id": "xxx",
        "sender": "张三",
        "content": "来10斤土豆,要嫩的",
        "auto_add_rule": false  // 新增: 是否自动添加到解析规则
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('content'):
            return jsonify({'error': '消息内容不能为空'}), 400

        group_id = data.get('group_id', '')
        sender = data.get('sender', '')
        content = data.get('content', '')
        auto_add_rule = data.get('auto_add_rule', False)

        # 根据group_id查找客户
        customer = customer_service.get_customer_by_wx_group(group_id)
        if not customer:
            return jsonify({
                'error': f'未找到绑定的客户: group_id={group_id}',
                'hint': '请先在后台绑定微信群ID与客户'
            }), 404

        # 解析消息
        parse_result = parse_order_message(content)

        if not parse_result['success']:
            return jsonify({
                'error': '消息解析失败',
                'details': parse_result.get('error'),
                'confidence': parse_result.get('confidence', 0)
            }), 400

        # 检查置信度
        if parse_result['confidence'] < 0.7:
            return jsonify({
                'error': '解析置信度过低,需要人工审核',
                'confidence': parse_result['confidence'],
                'parsed_items': parse_result['items']
            }), 400

        # 创建订单
        order_result = order_service.create_or_update_order(
            customer_id=customer['id'],
            items=parse_result['items'],
            remark=', '.join(parse_result.get('remarks', [])),
            source_type='wechat'
        )

        # 如果需要自动添加规则
        rule_added = False
        if auto_add_rule and parse_result['success']:
            try:
                from database.db_config import get_db_session
                from services.rule_service import ParseRuleService
                from models.user_models import User
                from sqlalchemy.orm import Session
                
                db: Session = get_db_session()
                try:
                    # 获取默认用户(通常是第一个用户或管理员)
                    user = db.query(User).filter(User.is_active == True).order_by(User.id.asc()).first()
                    
                    if user:
                        # 生成规则名称
                        rule_name = f"解析规则: {content[:20]}"
                        
                        # 从解析结果中提取规则模式
                        # 这里创建一个基于关键词的解析规则
                        pattern_data = {
                            'keywords': [item['product_name'] for item in parse_result['items']],
                            'quantity_pattern': r'(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)',
                        }
                        
                        # 创建解析规则
                        rule_result = ParseRuleService.create_rule(
                            db, user.id,
                            rule_name=rule_name,
                            rule_type='keyword',
                            pattern=json.dumps(pattern_data, ensure_ascii=False),
                            extract_fields=json.dumps({'product': 'keyword_match', 'quantity': 'auto'}, ensure_ascii=False),
                            priority=10,
                            is_active=True,
                            description=f'自动生成的解析规则，来源于消息: {content}'
                        )
                        
                        if rule_result['success']:
                            rule_added = True
                            logger.info(f"自动添加解析规则成功: {rule_name}")
                        else:
                            logger.warning(f"自动添加解析规则失败: {rule_result.get('error')}")
                    else:
                        logger.warning("未找到活跃用户，无法添加解析规则")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"自动添加解析规则异常: {e}", exc_info=True)
                rule_added = False

        if order_result['success']:
            return jsonify({
                'success': True,
                'order_id': order_result['order_id'],
                'order_uuid': order_result['order_uuid'],
                'total_amount': order_result.get('total_amount'),
                'parsed_items': parse_result['items'],
                'confidence': parse_result['confidence'],
                'rule_added': rule_added
            }), 201
        else:
            return jsonify(order_result), 400

    except Exception as e:
        logger.error(f"解析订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/today', methods=['GET'])
def get_today_orders():
    """
    获取今日订单列表

    Query Params:
    - customer_id: 客户ID(可选)
    - status: 订单状态(可选)
    """
    try:
        customer_id = request.args.get('customer_id', type=int)
        status = request.args.get('status')

        orders = order_service.get_today_orders(customer_id=customer_id, status=status)

        return jsonify({
            'success': True,
            'count': len(orders),
            'orders': orders
        }), 200

    except Exception as e:
        logger.error(f"查询今日订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """获取订单详情"""
    try:
        order = order_service.get_order_by_id(order_id)

        if not order:
            return jsonify({'error': f'订单不存在: {order_id}'}), 404

        return jsonify({'success': True, 'order': order}), 200

    except Exception as e:
        logger.error(f"查询订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/<int:order_id>/items', methods=['PUT'])
def update_order_items(order_id):
    """
    修改订单明细

    Request Body:
    {
        "items": [
            {"product_id": 1, "quantity": 15.0, "remark": "要嫩的"}
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('items'):
            return jsonify({'error': 'items不能为空'}), 400

        result = order_service.modify_order_items(order_id, data['items'])

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"修改订单明细API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/<int:order_id>/confirm', methods=['POST'])
def confirm_order(order_id):
    """确认订单"""
    try:
        confirmed_by = request.get_json().get('confirmed_by', 'system') if request.get_json() else 'system'
        result = order_service.confirm_order(order_id, confirmed_by)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"确认订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    """
    取消订单

    Request Body:
    {
        "reason": "取消原因"
    }
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', '未说明')

        result = order_service.cancel_order(order_id, reason)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"取消订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/range', methods=['GET'])
def get_orders_by_range():
    """
    按日期范围查询订单

    Query Params:
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - customer_id: 客户ID(可选)
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        customer_id = request.args.get('customer_id', type=int)

        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date和end_date不能为空'}), 400

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        orders = order_service.get_orders_by_date_range(start_date, end_date, customer_id)

        return jsonify({
            'success': True,
            'count': len(orders),
            'orders': orders
        }), 200

    except ValueError:
        return jsonify({'error': '日期格式错误,应为YYYY-MM-DD'}), 400
    except Exception as e:
        logger.error(f"查询订单范围API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/parse-enhanced', methods=['POST'])
def parse_and_create_order_enhanced():
    """
    解析消息并创建订单(增强版,支持批量圈选)

    Request Body:
    {
        "content": "下单 1-10 5斤",
        "customer_id": 1,
        "route_id": 2,  // 新增: 用于批量圈选时获取线路产品
        "order_uuid": "optional-uuid"
    }
    """
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        customer_id = data.get('customer_id')
        route_id = data.get('route_id')  # 新增
        order_uuid = data.get('order_uuid')

        if not content or not customer_id:
            return jsonify({'error': '缺少必要参数'}), 400

        # 解析消息(自动检测批量圈选语法)
        from services.order_parser import OrderParser
        parser = OrderParser()
        parse_result = parser.parse_message(content, route_id=route_id)

        if not parse_result['success']:
            return jsonify({
                'error': '解析失败',
                'details': parse_result.get('error')
            }), 400

        # 检查置信度
        confidence = parse_result.get('confidence', 0)
        if confidence < 0.7:
            return jsonify({
                'error': '置信度过低,请确认订单内容',
                'confidence': confidence,
                'parsed_items': parse_result.get('items', [])
            }), 400

        # 创建订单
        result = order_service.create_or_update_order(
            customer_id=customer_id,
            items=parse_result['items'],
            order_uuid=order_uuid
        )

        if result['success']:
            status_code = 201 if not result.get('is_duplicate') else 200
            return jsonify({
                **result,
                'parse_confidence': confidence,
                'is_batch': parse_result.get('is_batch', False)
            }), status_code
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"解析订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/incremental', methods=['POST'])
def create_incremental_order():
    """
    创建增量订单

    Request Body:
    {
        "customer_id": 1,
        "product_id": 2,
        "operation": "add",  // add/subtract/replace
        "quantity": 5.0,
        "order_date": "2026-04-15",  // 可选,默认今天
        "remark": "客户临时追加"
    }
    """
    try:
        data = request.get_json()

        required_fields = ['customer_id', 'product_id', 'operation', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必要参数: {field}'}), 400

        # 解析order_date
        order_date = None
        if data.get('order_date'):
            try:
                order_date = datetime.strptime(data['order_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': '日期格式错误,应为YYYY-MM-DD'}), 400

        result = order_service.apply_incremental_order(
            customer_id=data['customer_id'],
            product_id=data['product_id'],
            operation=data['operation'],
            quantity=data['quantity'],
            order_date=order_date,
            remark=data.get('remark')
        )

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"增量订单API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@orders_bp.route('/customers/<int:customer_id>/daily-summary', methods=['GET'])
def get_customer_daily_summary(customer_id):
    """获取客户当日订单汇总"""
    try:
        order_date_str = request.args.get('date')
        order_date = None
        if order_date_str:
            try:
                order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': '日期格式错误,应为YYYY-MM-DD'}), 400

        summary = order_service.get_customer_daily_summary(customer_id, order_date)

        return jsonify({
            'success': True,
            'summary': summary
        }), 200

    except Exception as e:
        logger.error(f"查询客户日报异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
