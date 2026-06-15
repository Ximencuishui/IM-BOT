"""
数据统计API
提供数据看板、图表数据等接口
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.dashboard_service import DashboardService

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/overview', methods=['GET'])
@login_required
def overview():
    """
    获取概览统计数据
    Query: period=today/week/month/custom
    """
    period = request.args.get('period', 'today')

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        stats = DashboardService.get_overview_stats(db, user.id, period)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@dashboard_bp.route('/chart/sales-trend', methods=['GET'])
@login_required
def sales_trend():
    """
    获取销售趋势数据（折线图）
    Query: days=7/30/90
    """
    days = int(request.args.get('days', 7))
    if days not in [7, 14, 30, 60, 90]:
        days = 7

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        data = DashboardService.get_sales_chart_data(db, user.id, days)

        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@dashboard_bp.route('/chart/product-ranking', methods=['GET'])
@login_required
def product_ranking():
    """
    获取商品销量排行（柱状图）
    Query: limit=10, period=week/month
    """
    limit = int(request.args.get('limit', 10))
    period = request.args.get('period', 'week')

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        data = DashboardService.get_product_ranking(db, user.id, limit, period)

        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@dashboard_bp.route('/chart/customer-distribution', methods=['GET'])
@login_required
def customer_distribution():
    """获取客户分布统计（饼图）"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        data = DashboardService.get_customer_distribution(db, user.id)

        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@dashboard_bp.route('/route-summary', methods=['GET'])
@login_required
def route_summary():
    """
    获取线路汇总统计
    Query: date=2024-01-01
    """
    date = request.args.get('date')

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        data = DashboardService.get_route_summary(db, user.id, date)

        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 看板组件管理 ====================

@dashboard_bp.route('/widgets', methods=['GET'])
@login_required
def get_widgets():
    """获取用户的看板组件配置"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        widgets = DashboardService.get_dashboard_widgets(db, user.id)

        return jsonify({
            'success': True,
            'widgets': widgets
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@dashboard_bp.route('/widgets', methods=['POST'])
@login_required
def save_widget():
    """
    保存看板组件配置
    Body: {
        "id": 1,  // 可选，有则更新
        "widget_name": "今日订单",
        "widget_type": "stat_card",  // stat_card/chart/table
        "data_source": "{\"type\": \"orders\", \"status\": \"pending\"}",
        "stat_period": "today",  // today/week/month/custom
        "position_x": 0,
        "position_y": 0,
        "width": 1,
        "height": 1,
        "is_visible": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = DashboardService.save_widget_config(db, user.id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@dashboard_bp.route('/widgets/<int:widget_id>', methods=['DELETE'])
@login_required
def delete_widget(widget_id):
    """删除看板组件"""
    from models.user_models import DashboardWidget

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        widget = db.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id,
            DashboardWidget.user_id == user.id
        ).first()

        if not widget:
            return jsonify({'success': False, 'error': '组件不存在'}), 404

        db.delete(widget)
        db.commit()

        return jsonify({'success': True, 'message': '组件已删除'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
