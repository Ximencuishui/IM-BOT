"""
规则配置API
提供消息解析规则和统计规则的CRUD接口
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.rule_service import ParseRuleService, StatRuleService

rule_bp = Blueprint('rule', __name__, url_prefix='/api/rules')


# ==================== 消息解析规则 ====================

@rule_bp.route('/parse', methods=['GET'])
@login_required
def list_parse_rules():
    """
    获取解析规则列表
    Query: active_only=true/false
    """
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        rules = ParseRuleService.get_rules(db, user.id, active_only)

        return jsonify({
            'success': True,
            'rules': rules,
            'count': len(rules)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_bp.route('/parse', methods=['POST'])
@login_required
def create_parse_rule():
    """
    创建解析规则
    Body: {
        "rule_name": "特殊格式解析",
        "rule_type": "regex",  // regex/keyword/custom
        "pattern": "(\\d+)斤(.+)",
        "extract_fields": "{\"quantity\": 1, \"product\": 2}",
        "priority": 10,
        "is_active": true,
        "description": "匹配'10斤土豆'格式"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ParseRuleService.create_rule(db, user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_bp.route('/parse/<int:rule_id>', methods=['PUT'])
@login_required
def update_parse_rule(rule_id):
    """更新解析规则"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ParseRuleService.update_rule(db, rule_id, user.id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_bp.route('/parse/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_parse_rule(rule_id):
    """删除解析规则"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ParseRuleService.delete_rule(db, rule_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 统计规则 ====================

@rule_bp.route('/stat', methods=['GET'])
@login_required
def list_stat_rules():
    """
    获取统计规则列表
    Query: active_only=true/false
    """
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        rules = StatRuleService.get_rules(db, user.id, active_only)

        return jsonify({
            'success': True,
            'rules': rules,
            'count': len(rules)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_bp.route('/stat', methods=['POST'])
@login_required
def create_stat_rule():
    """
    创建统计规则
    Body: {
        "rule_name": "每日销售汇总",
        "stat_type": "daily",  // daily/weekly/monthly/custom
        "dimensions": "[\"product\", \"customer\"]",
        "filters": "{\"min_amount\": 100}",
        "chart_type": "bar",  // bar/line/pie
        "refresh_interval": 3600,
        "is_active": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = StatRuleService.create_rule(db, user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_bp.route('/stat/<int:rule_id>', methods=['PUT'])
@login_required
def update_stat_rule(rule_id):
    """更新统计规则"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = StatRuleService.update_rule(db, rule_id, user.id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_bp.route('/stat/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_stat_rule(rule_id):
    """删除统计规则"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = StatRuleService.delete_rule(db, rule_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
