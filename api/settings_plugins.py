"""
旧版前端兼容 API - 插件管理端点
为 frontend/settings.html 提供向后兼容的插件管理接口
内部映射到新的插件商店 API 服务
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.plugin_service import plugin_service

logger = logging.getLogger(__name__)

settings_plugin_bp = Blueprint('settings_plugins', __name__, url_prefix='/api/settings')


def _resolve_plugin_id(db: Session, plugin_id):
    """
    解析插件标识符：支持整数 ID 或字符串 plugin_code
    返回 (package_id, plugin_code) 元组，或 (None, None)
    """
    from models.plugin_models import PluginPackage

    if isinstance(plugin_id, int) or (isinstance(plugin_id, str) and plugin_id.isdigit()):
        pkg = db.query(PluginPackage).filter(PluginPackage.id == int(plugin_id)).first()
        if pkg:
            return pkg.id, pkg.plugin_code
    elif isinstance(plugin_id, str):
        pkg = db.query(PluginPackage).filter(PluginPackage.plugin_code == plugin_id).first()
        if pkg:
            return pkg.id, pkg.plugin_code
    return None, None


def _plugin_to_settings_format(plugin_dict, installed_version=None):
    """
    将插件商店格式转换为 settings.html 期望的旧版格式
    """
    category_map = {
        'industry': '行业插件',
        'knowledge': '知识库',
        'qa': '问答库',
        'algorithm': '解析算法',
        'tool': '工具插件',
        'core': '核心插件',
        'desktop': 'IM平台',
        'platform': 'IM平台',
    }

    type_map = {
        'industry': 'utility',
        'knowledge': 'utility',
        'qa': 'utility',
        'algorithm': 'utility',
        'tool': 'utility',
        'core': 'core',
        'desktop': 'platform',
        'platform': 'platform',
    }

    icon_map = {
        'seafood': '🦐',
        'fooddelivery': '🍽️',
        'education': '📚',
        'realestate': '🏠',
        'travel': '✈️',
        'construction': '🏗️',
        'fleet': '🚛',
        'studio': '🎵',
        'hotpot': '🍲',
        'teacoffee': '🧋',
        'bakery': '🍞',
        'hardware': '🔧',
        'japanesefood': '🍱',
        'evparts': '⚡',
        'phoneparts': '📱',
        'partswholesale': '🏍️',
        'core': '⚙️',
        'wechat': '💬',
        'excel': '📊',
        'feishu': '📧',
        'dingtalk': '💼',
    }

    industry = plugin_dict.get('industry', '') or ''
    plugin_code = plugin_dict.get('plugin_code', '')
    category = plugin_dict.get('category', '')

    return {
        'id': plugin_code,
        'name': plugin_dict.get('plugin_name', ''),
        'description': plugin_dict.get('description', ''),
        'category': category_map.get(category, category),
        'version': installed_version or plugin_dict.get('latest_version', '1.0.0'),
        'installed': installed_version is not None,
        'tags': plugin_dict.get('tags', []) if isinstance(plugin_dict.get('tags'), list) else [],
        'type': type_map.get(category, 'utility'),
        'icon': icon_map.get(plugin_code) or icon_map.get(industry.lower()) or '🧩',
        'industry': industry,
        'rating': plugin_dict.get('rating', 0),
        'downloads': str(plugin_dict.get('download_count', 0)),
    }


@settings_plugin_bp.route('/plugins', methods=['GET'])
@login_required
def list_plugins():
    """
    获取插件列表（旧版兼容）
    返回 { installed_plugins, recommended_plugins }
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)

        # 获取已安装插件
        installed = plugin_service.list_installed_plugins(db, user.id)
        installed_map = {}
        for inst in installed:
            plugin_info = inst.get('plugin', {}) or {}
            plugin_code = plugin_info.get('plugin_code', '')
            installed_map[plugin_code] = inst

        # 获取所有公开插件
        all_plugins = plugin_service.list_plugins(db)

        installed_list = []
        recommended_list = []

        for p in all_plugins:
            pc = p.get('plugin_code', '')
            if pc in installed_map:
                inst = installed_map[pc]
                installed_list.append(
                    _plugin_to_settings_format(p, inst.get('installed_version'))
                )
            else:
                recommended_list.append(_plugin_to_settings_format(p))

        # 确保核心插件始终显示
        core_codes = {p.get('plugin_code') for p in all_plugins}
        for code in ['core', 'wechat', 'excel']:
            if code not in core_codes:
                installed_list.insert(0, {
                    'id': code,
                    'name': {'core': '核心功能插件', 'wechat': '微信插件', 'excel': 'Excel报表插件'}.get(code, code),
                    'description': {'core': '订单解析、消息捕获、规则引擎、报表生成等核心功能',
                                    'wechat': '微信消息捕获、自动回复、群管理等',
                                    'excel': '多格式报表导出、邮件自动发送'}.get(code, ''),
                    'category': '核心插件' if code == 'core' else '工具插件',
                    'version': '2.0.0',
                    'installed': True,
                    'tags': ['核心', '必需'] if code == 'core' else (['微信', '消息'] if code == 'wechat' else ['报表', 'Excel']),
                    'type': 'core' if code == 'core' else 'utility',
                    'icon': {'core': '⚙️', 'wechat': '💬', 'excel': '📊'}.get(code, '🧩'),
                    'industry': '',
                    'rating': 4.9,
                    'downloads': '10,000+',
                })

        return jsonify({
            'success': True,
            'installed_plugins': installed_list,
            'recommended_plugins': recommended_list,
        }), 200
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@settings_plugin_bp.route('/plugins/install', methods=['POST'])
@login_required
def install_plugin():
    """
    安装插件（旧版兼容）
    Body: { "plugin_id": "core" }  # 支持 plugin_code 或 数字 ID
    """
    data = request.get_json() or {}
    raw_id = data.get('plugin_id')
    if not raw_id:
        return jsonify({'success': False, 'error': '缺少插件ID'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)

        pkg_id, pkg_code = _resolve_plugin_id(db, raw_id)
        if pkg_id is None:
            # 尝试将 plugin_code 作为回退，动态创建最小记录
            logger.warning(f"插件未找到，尝试回退: plugin_id={raw_id}")
            return jsonify({'success': False, 'error': f'插件不存在: {raw_id}'}), 404

        result = plugin_service.install_plugin(db, user.id, pkg_id)
        db.commit()

        if result['success']:
            return jsonify({
                'success': True,
                'message': f'插件安装成功',
                'plugin_id': pkg_code or raw_id,
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error', '安装失败')}), 400
    except Exception as e:
        db.rollback()
        logger.error(f"安装插件失败: plugin_id={raw_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@settings_plugin_bp.route('/plugins/uninstall', methods=['POST'])
@login_required
def uninstall_plugin():
    """
    卸载插件（旧版兼容）
    Body: { "plugin_id": "core" }  # 支持 plugin_code 或 数字 ID
    """
    data = request.get_json() or {}
    raw_id = data.get('plugin_id')
    if not raw_id:
        return jsonify({'success': False, 'error': '缺少插件ID'}), 400

    # 核心插件不允许卸载
    if raw_id in ('core',):
        return jsonify({'success': False, 'error': '核心插件无法卸载'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)

        pkg_id, pkg_code = _resolve_plugin_id(db, raw_id)
        if pkg_id is None:
            return jsonify({'success': False, 'error': f'插件不存在: {raw_id}'}), 404

        result = plugin_service.uninstall_plugin(db, user.id, pkg_id)
        db.commit()

        if result['success']:
            return jsonify({
                'success': True,
                'message': f'插件已卸载',
                'plugin_id': pkg_code or raw_id,
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error', '卸载失败')}), 400
    except Exception as e:
        db.rollback()
        logger.error(f"卸载插件失败: plugin_id={raw_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()