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


_ICON_MAP = {
    'seafood': '🦐', 'fooddelivery': '🍽️', 'education': '📚',
    'realestate': '🏠', 'travel': '✈️', 'construction': '🏗️',
    'fleet': '🚛', 'studio': '🎵', 'hotpot': '🍲',
    'teacoffee': '🧋', 'bakery': '🍞', 'hardware': '🔧',
    'japanesefood': '🍱', 'evparts': '⚡', 'phoneparts': '📱',
    'partswholesale': '🏍️', 'core': '⚙️',
}

_INDUSTRY_NAMES = {
    'seafood': '海鲜批发', 'fooddelivery': '餐饮配送', 'education': '教育培训',
    'realestate': '房产中介', 'travel': '旅行社', 'construction': '工地管理',
    'fleet': '车队调度', 'studio': '录音棚/工作室', 'hotpot': '火锅食材',
    'teacoffee': '茶饮咖啡', 'bakery': '烘焙甜品', 'hardware': '水电五金',
    'japanesefood': '日料寿司', 'evparts': '电动车配件', 'phoneparts': '手机零配件',
    'partswholesale': '配件批发',
}

_INDUSTRY_DESCRIPTIONS = {
    'seafood': '客户订单管理、急单处理、截单提醒、报表统计',
    'fooddelivery': '商品管理、订单处理、促销活动、配送调度',
    'education': '课程管理、学员管理、学习进度、教师管理',
    'realestate': '房源管理、客户管理、智能匹配、交易管理',
    'travel': '线路管理、群配置、报名处理、自动回复',
    'construction': '工人打卡、工期管理、安全检查、材料管理',
    'fleet': '车辆调度、路线优化、油费管理、司机管理',
    'studio': '预约管理、项目跟踪、客户管理、计费统计',
    'hotpot': '食材管理、订单处理、库存管理、供应商管理',
    'teacoffee': '原料管理、配方管理、订单处理、库存跟踪',
    'bakery': '配方管理、订单管理、库存管理、生产计划',
    'hardware': '商品管理、订单处理、库存预警、客户报价',
    'japanesefood': '食材管理、菜品管理、订单处理、库存跟踪',
    'evparts': '配件管理、车型匹配、订单处理、库存管理',
    'phoneparts': '配件管理、机型适配、订单处理、供应商管理',
    'partswholesale': '商品管理、批量报价、订单处理、物流跟踪',
}


def _resolve_plugin_ids(db: Session, plugin_ids: list):
    """将 plugin_codes（字符串）或数字 ID 解析为数字 ID"""
    from models.plugin_models import PluginPackage

    resolved = []
    for pid in plugin_ids:
        if isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit()):
            resolved.append(int(pid))
        elif isinstance(pid, str):
            pkg = db.query(PluginPackage).filter(PluginPackage.plugin_code == pid).first()
            if pkg:
                resolved.append(pkg.id)
            else:
                resolved.append(pid)  # 保留原值，让 service 层报错
        else:
            resolved.append(pid)
    return resolved


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

        plugin_ids = _resolve_plugin_ids(db, data['plugin_ids'])
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
    """获取行业列表（动态生成，基于已知行业和插件商店数据）"""
    db: Session = get_db_session()
    try:
        from models.plugin_models import PluginPackage

        # 从数据库获取有对应插件的行业
        db_industries = db.query(PluginPackage.industry).filter(
            PluginPackage.industry.isnot(None),
            PluginPackage.industry != ''
        ).distinct().all()

        db_industry_codes = {row[0] for row in db_industries}

        # 合并已知行业列表和数据库中的行业
        all_codes = set(_INDUSTRY_NAMES.keys()) | db_industry_codes

        # 获取每个行业对应的插件
        industry_plugins_map = {}
        for code in all_codes:
            plugins = db.query(PluginPackage).filter(
                PluginPackage.industry == code,
                PluginPackage.status == 'active'
            ).all()
            industry_plugins_map[code] = [
                {'code': p.plugin_code, 'name': p.plugin_name, 'icon': _ICON_MAP.get(p.plugin_code, '🧩')}
                for p in plugins
            ]

        industries = []
        for code in sorted(all_codes):
            industries.append({
                'code': code,
                'name': _INDUSTRY_NAMES.get(code, code),
                'description': _INDUSTRY_DESCRIPTIONS.get(code, f'{code}行业解决方案'),
                'icon': _ICON_MAP.get(code, '🧩'),
                'plugins': [p['code'] for p in industry_plugins_map.get(code, [])],
                'plugin_details': industry_plugins_map.get(code, []),
            })

        return jsonify({
            'success': True,
            'industries': industries
        }), 200
    except Exception as e:
        logger.error(f"获取行业列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()