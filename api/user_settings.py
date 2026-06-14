"""
用户设置API
提供个人资料管理、行业配置、通知设置、插件管理等功能
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.plugin_service import plugin_service

logger = logging.getLogger(__name__)

user_settings_bp = Blueprint('user_settings', __name__, url_prefix='/api/settings')


# ==================== 个人资料 ====================

@user_settings_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取用户个人资料"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        return jsonify({
            'success': True,
            'profile': {
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'company_name': user.company_name,
                'industry': user.industry
            }
        }), 200
    except Exception as e:
        logger.error(f"获取个人资料失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@user_settings_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户个人资料"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        if 'username' in data:
            user.username = data['username']
        if 'phone' in data:
            user.phone = data['phone']
        if 'company_name' in data:
            user.company_name = data['company_name']
        if 'industry' in data:
            user.industry = data['industry']

        db.commit()

        return jsonify({
            'success': True,
            'message': '个人资料更新成功',
            'profile': {
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'company_name': user.company_name,
                'industry': user.industry
            }
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"更新个人资料失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 行业配置 ====================

@user_settings_bp.route('/industry', methods=['GET'])
@login_required
def get_industry_config():
    """获取用户行业配置"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        industry_plugins = []
        if user.industry:
            industry_plugins = plugin_service.list_plugins(db, industry=user.industry)

        installed_plugins = plugin_service.list_installed_plugins(db, user.id)

        return jsonify({
            'success': True,
            'current_industry': user.industry,
            'industry_plugins': industry_plugins,
            'installed_plugins': installed_plugins
        }), 200
    except Exception as e:
        logger.error(f"获取行业配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@user_settings_bp.route('/industry', methods=['PUT'])
@login_required
def update_industry():
    """切换用户行业"""
    data = request.get_json()
    if not data or 'industry' not in data:
        return jsonify({'success': False, 'error': '缺少行业参数'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        user.industry = data['industry']
        db.commit()

        logger.info(f"用户 {user.email} 切换行业为: {data['industry']}")

        industry_plugins = plugin_service.list_plugins(db, industry=data['industry'])

        return jsonify({
            'success': True,
            'message': f'行业已切换为 {data["industry"]}',
            'current_industry': data['industry'],
            'recommended_plugins': industry_plugins
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"切换行业失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 通知设置 ====================

@user_settings_bp.route('/notifications', methods=['GET'])
@login_required
def get_notification_settings():
    """获取通知设置"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        from services.system_config_service import get_system_config_value

        notification_settings = {
            'order_notification': get_system_config_value(f'user_{user.id}_order_notification', 'true') == 'true',
            'daily_report': get_system_config_value(f'user_{user.id}_daily_report', 'true') == 'true',
            'report_time': get_system_config_value(f'user_{user.id}_report_time', '09:00'),
            'cutoff_reminder': get_system_config_value(f'user_{user.id}_cutoff_reminder', 'true') == 'true',
            'cutoff_time': get_system_config_value(f'user_{user.id}_cutoff_time', '20:00')
        }

        return jsonify({
            'success': True,
            'notifications': notification_settings
        }), 200
    except Exception as e:
        logger.error(f"获取通知设置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@user_settings_bp.route('/notifications', methods=['PUT'])
@login_required
def update_notification_settings():
    """更新通知设置"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        from services.system_config_service import set_system_config_value

        if 'order_notification' in data:
            set_system_config_value(
                f'user_{user.id}_order_notification',
                'true' if data['order_notification'] else 'false',
                '订单通知开关'
            )
        if 'daily_report' in data:
            set_system_config_value(
                f'user_{user.id}_daily_report',
                'true' if data['daily_report'] else 'false',
                '日报发送开关'
            )
        if 'report_time' in data:
            set_system_config_value(
                f'user_{user.id}_report_time',
                data['report_time'],
                '日报发送时间'
            )
        if 'cutoff_reminder' in data:
            set_system_config_value(
                f'user_{user.id}_cutoff_reminder',
                'true' if data['cutoff_reminder'] else 'false',
                '截单提醒开关'
            )
        if 'cutoff_time' in data:
            set_system_config_value(
                f'user_{user.id}_cutoff_time',
                data['cutoff_time'],
                '截单时间'
            )

        logger.info(f"用户 {user.email} 更新了通知设置")

        return jsonify({
            'success': True,
            'message': '通知设置更新成功',
            'notifications': data
        }), 200
    except Exception as e:
        logger.error(f"更新通知设置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 插件管理 ====================

@user_settings_bp.route('/plugins', methods=['GET'])
@login_required
def get_user_plugins():
    """获取用户插件列表（已安装 + 推荐）"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        installed = plugin_service.list_installed_plugins(db, user.id)
        recommended = []

        if user.industry:
            recommended = plugin_service.list_plugins(db, industry=user.industry)

        return jsonify({
            'success': True,
            'installed_plugins': installed,
            'recommended_plugins': recommended
        }), 200
    except Exception as e:
        logger.error(f"获取用户插件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@user_settings_bp.route('/plugins/install', methods=['POST'])
@login_required
def install_plugin():
    """安装插件"""
    data = request.get_json()
    if not data or 'plugin_id' not in data:
        return jsonify({'success': False, 'error': '缺少插件ID'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        result = plugin_service.install_plugin(db, user.id, data['plugin_id'], data.get('version'))
        db.close()

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.close()
        logger.error(f"安装插件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@user_settings_bp.route('/plugins/uninstall', methods=['POST'])
@login_required
def uninstall_plugin():
    """卸载插件"""
    data = request.get_json()
    if not data or 'plugin_id' not in data:
        return jsonify({'success': False, 'error': '缺少插件ID'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        result = plugin_service.uninstall_plugin(db, user.id, data['plugin_id'])
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        db.close()
        logger.error(f"卸载插件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 系统信息 ====================

@user_settings_bp.route('/system-info', methods=['GET'])
@login_required
def get_system_info():
    """获取系统信息"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        from config.settings import settings

        system_info = {
            'app_version': getattr(settings, 'APP_VERSION', '1.0.0'),
            'system_status': 'running',
            'current_user': user.to_dict()
        }

        return jsonify({
            'success': True,
            'system_info': system_info
        }), 200
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()