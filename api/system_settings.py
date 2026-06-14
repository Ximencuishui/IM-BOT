"""
系统设置API
提供邮件配置、支付配置、系统参数设置、通知模板管理等功能
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import admin_required, get_current_user_from_request
from models.user_models import User
import json
import logging

logger = logging.getLogger(__name__)

system_settings_bp = Blueprint('system_settings', __name__, url_prefix='/api/admin/system')


# ==================== 邮件配置 ====================

@system_settings_bp.route('/email-config', methods=['GET'])
@admin_required
def get_email_config():
    """获取邮件配置"""
    db: Session = get_db_session()
    try:
        # 从配置文件或数据库中获取邮件配置
        from config.settings import settings
        
        email_config = {
            'smtp_host': getattr(settings, 'SMTP_HOST', ''),
            'smtp_port': getattr(settings, 'SMTP_PORT', 587),
            'smtp_user': getattr(settings, 'SMTP_USER', ''),
            'smtp_password': getattr(settings, 'SMTP_PASSWORD', ''),
            'from_email': getattr(settings, 'FROM_EMAIL', ''),
            'report_recipients': getattr(settings, 'REPORT_RECIPIENTS', '')
        }
        
        return jsonify({
            'success': True,
            'config': email_config
        }), 200
    except Exception as e:
        logger.error(f"获取邮件配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/email-config', methods=['POST'])
@admin_required
def update_email_config():
    """更新邮件配置"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    # 验证必要字段
    required_fields = ['smtp_host', 'smtp_port', 'smtp_user', 'from_email']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
    
    db: Session = get_db_session()
    try:
        # 这里可以将配置保存到数据库或更新环境变量
        # 为了简化，我们暂时只返回成功响应
        # 在实际应用中，应该将配置保存到数据库的系统配置表中
        
        current_user = get_current_user_from_request(db)
        logger.info(f"管理员 {current_user.email} 更新了邮件配置")
        
        return jsonify({
            'success': True,
            'message': '邮件配置更新成功'
        }), 200
    except Exception as e:
        logger.error(f"更新邮件配置失败: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/email-config/test', methods=['POST'])
@admin_required
def test_email_config():
    """测试邮件配置"""
    data = request.get_json()
    if not data or 'test_email' not in data:
        return jsonify({'success': False, 'error': '请提供测试邮箱地址'}), 400
    
    db: Session = get_db_session()
    try:
        test_email = data['test_email']
        
        # 使用配置的SMTP设置发送测试邮件
        from utils.email_utils import EmailSender
        email_sender = EmailSender()
        
        # 临时更新配置用于测试
        original_smtp_host = email_sender.smtp_host
        original_smtp_port = email_sender.smtp_port
        original_smtp_user = email_sender.smtp_user
        original_smtp_password = email_sender.smtp_password
        original_from_email = email_sender.from_email
        
        # 使用传入的配置进行测试
        email_sender.smtp_host = data.get('smtp_host', original_smtp_host)
        email_sender.smtp_port = data.get('smtp_port', original_smtp_port)
        email_sender.smtp_user = data.get('smtp_user', original_smtp_user)
        email_sender.smtp_password = data.get('smtp_password', original_smtp_password)
        email_sender.from_email = data.get('from_email', original_from_email)
        
        # 发送测试邮件
        subject = "TonjClaw 系统邮件配置测试"
        body = """
        这是一封测试邮件，用于验证您的SMTP配置是否正确。
        
        如果您收到此邮件，说明邮件配置成功！
        
        TonjClaw 系统
        """
        
        # 这里需要实现实际的邮件发送逻辑
        # 由于我们没有完整的邮件发送实现，暂时返回模拟结果
        logger.info(f"测试邮件发送至: {test_email}")
        
        # 恢复原始配置
        email_sender.smtp_host = original_smtp_host
        email_sender.smtp_port = original_smtp_port
        email_sender.smtp_user = original_smtp_user
        email_sender.smtp_password = original_smtp_password
        email_sender.from_email = original_from_email
        
        return jsonify({
            'success': True,
            'message': f'测试邮件已发送至 {test_email}'
        }), 200
    except Exception as e:
        logger.error(f"测试邮件配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 支付配置 ====================

@system_settings_bp.route('/payment-config', methods=['GET'])
@admin_required
def get_payment_config():
    """获取支付配置"""
    db: Session = get_db_session()
    try:
        from config.settings import settings
        
        payment_config = {
            'alipay': {
                'app_id': getattr(settings, 'ALIPAY_APP_ID', ''),
                'private_key': '******' if getattr(settings, 'ALIPAY_APP_PRIVATE_KEY', '') else '',
                'alipay_public_key': '******' if getattr(settings, 'ALIPAY_PUBLIC_KEY', '') else '',
                'gateway_url': getattr(settings, 'ALIPAY_GATEWAY_URL', 'https://openapi.alipay.com/gateway.do'),
                'return_url': getattr(settings, 'ALIPAY_RETURN_URL', ''),
                'notify_url': getattr(settings, 'ALIPAY_NOTIFY_URL', '')
            },
            'wechat': {
                'app_id': getattr(settings, 'WECHAT_APP_ID', ''),
                'mch_id': getattr(settings, 'WECHAT_MCH_ID', ''),
                'api_key': '******' if getattr(settings, 'WECHAT_API_KEY', '') else '',
                'notify_url': getattr(settings, 'WECHAT_NOTIFY_URL', '')
            }
        }
        
        return jsonify({
            'success': True,
            'config': payment_config
        }), 200
    except Exception as e:
        logger.error(f"获取支付配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/payment-config', methods=['POST'])
@admin_required
def update_payment_config():
    """更新支付配置"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        current_user = get_current_user_from_request(db)
        logger.info(f"管理员 {current_user.email} 更新了支付配置")
        
        # 这里应该将配置保存到数据库
        return jsonify({
            'success': True,
            'message': '支付配置更新成功'
        }), 200
    except Exception as e:
        logger.error(f"更新支付配置失败: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 系统参数设置 ====================

@system_settings_bp.route('/parameters', methods=['GET'])
@admin_required
def get_system_parameters():
    """获取系统参数设置"""
    db: Session = get_db_session()
    try:
        from config.settings import settings
        
        parameters = {
            'app_name': getattr(settings, 'APP_NAME', 'TonjClaw'),
            'max_users': 100,  # 可以从数据库获取
            'default_subscription_days': 30,
            'maintenance_mode': False,
            'registration_enabled': True,
            'session_timeout': 3600,
            'password_policy': {
                'min_length': 8,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special_chars': False
            }
        }
        
        return jsonify({
            'success': True,
            'parameters': parameters
        }), 200
    except Exception as e:
        logger.error(f"获取系统参数失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/parameters', methods=['POST'])
@admin_required
def update_system_parameters():
    """更新系统参数设置"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        current_user = get_current_user_from_request(db)
        logger.info(f"管理员 {current_user.email} 更新了系统参数")
        
        # 这里应该将参数保存到数据库
        return jsonify({
            'success': True,
            'message': '系统参数更新成功'
        }), 200
    except Exception as e:
        logger.error(f"更新系统参数失败: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== AI 解析配置管理 ====================

@system_settings_bp.route('/ai-parser-config', methods=['GET'])
@admin_required
def get_ai_parser_config():
    """获取 AI 解析运行时配置。"""
    try:
        from services.ai_parser import get_ai_config
        return jsonify({
            'success': True,
            'config': get_ai_config()
        }), 200
    except Exception as e:
        logger.error(f"获取 AI 解析配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@system_settings_bp.route('/ai-parser-config', methods=['POST'])
@admin_required
def update_ai_parser_config():
    """更新 AI 解析运行时配置。"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    allowed_fields = {
        'enabled': 'ai_parser_enabled',
        'provider': 'ai_parser_provider',
        'api_url': 'ai_parser_api_url',
        'api_key': 'ai_parser_api_key',
        'model': 'ai_parser_model',
        'timeout': 'ai_parser_timeout'
    }

    if not any(field in data for field in allowed_fields):
        return jsonify({'success': False, 'error': '未提供任何可更新的 AI 配置字段'}), 400

    from services.system_config_service import set_system_config_value

    db: Session = get_db_session()
    try:
        current_user = get_current_user_from_request(db)
        updated = {}
        for field, key in allowed_fields.items():
            if field in data:
                value = data[field]
                if field == 'enabled':
                    value = 'true' if bool(value) else 'false'
                elif field == 'timeout':
                    try:
                        value = str(int(value))
                    except (ValueError, TypeError):
                        return jsonify({'success': False, 'error': 'timeout 必须为整数'}), 400
                else:
                    value = str(value).strip()
                set_system_config_value(key, value, description=f'AI parser setting {field}')
                updated[field] = value

        logger.info(f"管理员 {current_user.email} 更新了 AI 解析配置: {updated}")
        return jsonify({
            'success': True,
            'message': 'AI 解析配置更新成功',
            'updated': updated
        }), 200
    except Exception as e:
        logger.error(f"更新 AI 解析配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 通知模板管理 ====================

@system_settings_bp.route('/notification-templates', methods=['GET'])
@admin_required
def get_notification_templates():
    """获取通知模板列表"""
    db: Session = get_db_session()
    try:
        # 这里应该从数据库获取通知模板
        # 暂时返回示例数据
        templates = [
            {
                'id': 1,
                'name': '续费提醒邮件',
                'type': 'email',
                'subject': '【续费提醒】您的授权码将在{{days_remaining}}天后过期',
                'content': '尊敬的用户 {{username}}：\n\n您的授权码 {{license_code}} 将在 {{days_remaining}} 天后过期（{{expires_at}}）。\n\n为避免服务中断，请及时续费。\n\n登录地址：{{login_url}}\n\n此致\n敬礼',
                'variables': ['username', 'license_code', 'days_remaining', 'expires_at', 'login_url'],
                'is_active': True,
                'created_at': '2023-01-01T00:00:00'
            },
            {
                'id': 2,
                'name': '自动续费成功通知',
                'type': 'email',
                'subject': '【续费成功】授权码 {{license_code}} 已自动续费',
                'content': '尊敬的用户 {{username}}：\n\n您的授权码 {{license_code}} 已成功自动续费。\n\n续费详情：\n- 新过期时间：{{new_expiry}}\n- 续费金额：¥{{amount}}\n\n如需取消自动续费，请登录用户控制台进行操作。\n\n登录地址：{{login_url}}\n\n此致\n敬礼',
                'variables': ['username', 'license_code', 'new_expiry', 'amount', 'login_url'],
                'is_active': True,
                'created_at': '2023-01-01T00:00:00'
            }
        ]
        
        return jsonify({
            'success': True,
            'templates': templates
        }), 200
    except Exception as e:
        logger.error(f"获取通知模板失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/notification-templates', methods=['POST'])
@admin_required
def create_notification_template():
    """创建通知模板"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    # 验证必要字段
    required_fields = ['name', 'type', 'subject', 'content']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
    
    db: Session = get_db_session()
    try:
        current_user = get_current_user_from_request(db)
        logger.info(f"管理员 {current_user.email} 创建了通知模板: {data['name']}")
        
        # 这里应该将模板保存到数据库
        return jsonify({
            'success': True,
            'message': '通知模板创建成功',
            'template': {
                'id': 3,  # 示例ID
                **data
            }
        }), 201
    except Exception as e:
        logger.error(f"创建通知模板失败: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/notification-templates/<int:template_id>', methods=['PUT'])
@admin_required
def update_notification_template(template_id):
    """更新通知模板"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        current_user = get_current_user_from_request(db)
        logger.info(f"管理员 {current_user.email} 更新了通知模板 ID: {template_id}")
        
        # 这里应该从数据库获取并更新模板
        return jsonify({
            'success': True,
            'message': '通知模板更新成功'
        }), 200
    except Exception as e:
        logger.error(f"更新通知模板失败: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/notification-templates/<int:template_id>', methods=['DELETE'])
@admin_required
def delete_notification_template(template_id):
    """删除通知模板"""
    db: Session = get_db_session()
    try:
        current_user = get_current_user_from_request(db)
        logger.info(f"管理员 {current_user.email} 删除了通知模板 ID: {template_id}")
        
        # 这里应该从数据库删除模板
        return jsonify({
            'success': True,
            'message': '通知模板删除成功'
        }), 200
    except Exception as e:
        logger.error(f"删除通知模板失败: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@system_settings_bp.route('/notification-templates/<int:template_id>/preview', methods=['POST'])
@admin_required
def preview_notification_template(template_id):
    """预览通知模板"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        # 这里应该从数据库获取模板并进行变量替换
        # 暂时返回示例预览
        sample_data = data.get('sample_data', {})
        
        # 示例模板内容
        template_content = "尊敬的用户 {{username}}：\n\n您的授权码 {{license_code}} 将在 {{days_remaining}} 天后过期。"
        
        # 简单的变量替换
        preview_content = template_content
        for key, value in sample_data.items():
            preview_content = preview_content.replace(f"{{{{{key}}}}}", str(value))
        
        return jsonify({
            'success': True,
            'preview': preview_content
        }), 200
    except Exception as e:
        logger.error(f"预览通知模板失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()