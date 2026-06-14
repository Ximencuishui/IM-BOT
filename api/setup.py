"""
安装引导API
提供安装流程中的行业选择、插件配置、配置完成标记等功能
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.plugin_service import plugin_service

logger = logging.getLogger(__name__)

setup_bp = Blueprint('setup', __name__, url_prefix='/api/setup')


@setup_bp.route('/status', methods=['GET'])
@login_required
def get_setup_status():
    """获取安装引导状态"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        installed_plugins = plugin_service.list_installed_plugins(db, user.id)

        return jsonify({
            'success': True,
            'status': {
                'completed': user.setup_completed,
                'industry': user.industry,
                'installed_plugin_count': len(installed_plugins)
            }
        }), 200
    except Exception as e:
        logger.error(f"获取安装状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@setup_bp.route('/select-industry', methods=['POST'])
@login_required
def select_industry():
    """选择行业"""
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

        recommended_plugins = plugin_service.list_plugins(db, industry=data['industry'])

        logger.info(f"用户 {user.email} 选择行业: {data['industry']}")

        return jsonify({
            'success': True,
            'industry': data['industry'],
            'recommended_plugins': recommended_plugins,
            'message': f'已选择行业: {data["industry"]}'
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"选择行业失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@setup_bp.route('/install-plugins', methods=['POST'])
@login_required
def install_plugins_batch():
    """批量安装插件"""
    data = request.get_json()
    if not data or 'plugin_ids' not in data:
        return jsonify({'success': False, 'error': '缺少插件ID列表'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        plugin_ids = data['plugin_ids']
        results = []

        for plugin_id in plugin_ids:
            try:
                result = plugin_service.install_plugin(db, user.id, plugin_id)
                results.append({
                    'plugin_id': plugin_id,
                    'success': result.get('success', False),
                    'message': result.get('message', '')
                })
            except Exception as e:
                results.append({
                    'plugin_id': plugin_id,
                    'success': False,
                    'message': str(e)
                })

        db.commit()

        success_count = sum(1 for r in results if r['success'])

        return jsonify({
            'success': True,
            'message': f'批量安装完成，成功 {success_count}/{len(results)}',
            'results': results,
            'success_count': success_count,
            'total_count': len(results)
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"批量安装插件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@setup_bp.route('/complete', methods=['POST'])
@login_required
def complete_setup():
    """标记安装引导完成"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        user.setup_completed = True
        db.commit()

        logger.info(f"用户 {user.email} 完成安装引导")

        return jsonify({
            'success': True,
            'message': '安装引导已完成',
            'redirect_url': '/index.html'
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"标记安装完成失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@setup_bp.route('/reset', methods=['POST'])
@login_required
def reset_setup():
    """重置安装引导状态"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        user.setup_completed = False
        db.commit()

        logger.info(f"用户 {user.email} 重置安装引导")

        return jsonify({
            'success': True,
            'message': '安装引导已重置'
        }), 200
    except Exception as e:
        db.rollback()
        logger.error(f"重置安装引导失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@setup_bp.route('/industries', methods=['GET'])
def list_industries():
    """获取行业列表"""
    industries = [
        {'code': 'seafood', 'name': '海鲜批发', 'description': '海鲜批发行业解决方案', 'icon': '🦐'},
        {'code': 'food_delivery', 'name': '餐饮配送', 'description': '餐饮配送行业解决方案', 'icon': '🍜'},
        {'code': 'construction', 'name': '工地管理', 'description': '工地管理行业解决方案', 'icon': '🏗️'},
        {'code': 'travel', 'name': '旅行社', 'description': '旅行社行业解决方案', 'icon': '✈️'},
        {'code': 'retail', 'name': '零售超市', 'description': '零售超市行业解决方案', 'icon': '🏪'},
        {'code': 'wholesale', 'name': '综合批发', 'description': '综合批发行业解决方案', 'icon': '📦'}
    ]

    return jsonify({
        'success': True,
        'industries': industries
    }), 200