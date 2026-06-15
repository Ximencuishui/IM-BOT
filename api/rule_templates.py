"""
规则模板库API
提供云端规则模板的浏览、下载、上传功能
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.rule_template_service import RuleTemplateService

rule_template_bp = Blueprint('rule_template', __name__, url_prefix='/api/rule-templates')


@rule_template_bp.route('/', methods=['GET'])
def list_templates():
    """
    获取规则模板列表（公开接口，无需登录）
    Query: industry=xxx, source_type=xxx, featured_only=true
    """
    industry = request.args.get('industry')
    source_type = request.args.get('source_type')
    featured_only = request.args.get('featured_only', 'false').lower() == 'true'

    db: Session = get_db_session()
    try:
        templates = RuleTemplateService.get_templates(db, industry, source_type, featured_only)

        return jsonify({
            'success': True,
            'templates': templates,
            'count': len(templates)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_template_bp.route('/industries', methods=['GET'])
def list_industries():
    """获取所有行业分类（公开接口）"""
    db: Session = get_db_session()
    try:
        industries = RuleTemplateService.get_industries(db)

        return jsonify({
            'success': True,
            'industries': industries
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_template_bp.route('/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """获取单个模板详情（公开接口）"""
    db: Session = get_db_session()
    try:
        template = RuleTemplateService.get_template(db, template_id)

        if not template:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        return jsonify({
            'success': True,
            'template': template
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_template_bp.route('/<int:template_id>/download', methods=['POST'])
def download_template(template_id):
    """
    下载模板（公开接口，但建议登录后使用以记录用户历史）
    返回完整的规则内容供桌面端导入
    """
    db: Session = get_db_session()
    try:
        result = RuleTemplateService.download_template(db, template_id)

        if not result:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        return jsonify({
            'success': True,
            'template': result
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_template_bp.route('/upload', methods=['POST'])
@login_required
def upload_template():
    """
    用户上传规则模板（分享自己的规则到云端）
    Body: {
        "template_name": "我的沙县小吃规则",
        "industry": "沙县小吃",
        "description": "适用于沙县小吃店的食材配送统计",
        "parse_rules": [...],
        "stat_rules": [...],
        "reply_rules": [...],
        "is_public": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RuleTemplateService.upload_template(db, user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 用户规则备份 ====================

@rule_template_bp.route('/backups', methods=['GET'])
@login_required
def get_backups():
    """获取用户的规则备份列表"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        backups = RuleTemplateService.get_user_backups(db, user.id)

        return jsonify({
            'success': True,
            'backups': backups
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@rule_template_bp.route('/backups', methods=['POST'])
@login_required
def save_backup():
    """
    保存规则备份到云端
    Body: {
        "backup_name": "2024-01-15备份",
        "parse_rules": [...],
        "stat_rules": [...],
        "reply_rules": [...],
        "template_id": 1,  // 可选，来源模板
        "version": "1.0"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RuleTemplateService.save_user_backup(db, user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
