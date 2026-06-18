"""
插件市场API
提供插件管理、知识库管理、问答库管理、解析算法管理等RESTful接口
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, admin_required, get_current_user_from_request
from services.plugin_service import (
    plugin_service, knowledge_service, faq_service, algorithm_service,
    plugin_admin_service
)

logger = logging.getLogger(__name__)

plugin_bp = Blueprint('plugin', __name__, url_prefix='/api/plugin')


# ==================== 插件管理 ====================

@plugin_bp.route('/market', methods=['GET'])
def list_plugins():
    """
    获取插件市场列表（公开接口）
    Query: category=xxx, industry=xxx, featured_only=true, search=xxx
    """
    try:
        category = request.args.get('category', None)
        industry = request.args.get('industry', None)
        featured_only = request.args.get('featured_only', 'false').lower() == 'true'
        search = request.args.get('search', None)

        db: Session = get_db_session()
        plugins = plugin_service.list_plugins(db, category, industry, featured_only, search)
        db.close()

        return jsonify({
            'success': True,
            'count': len(plugins),
            'plugins': plugins
        }), 200
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/market/<int:plugin_id>', methods=['GET'])
def get_plugin(plugin_id):
    """
    获取插件详情（公开接口）
    """
    try:
        db: Session = get_db_session()
        plugin = plugin_service.get_plugin(db, plugin_id=plugin_id)
        db.close()

        if not plugin:
            return jsonify({'success': False, 'error': '插件不存在'}), 404

        return jsonify({'success': True, 'plugin': plugin}), 200
    except Exception as e:
        logger.error(f"获取插件详情失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/install', methods=['POST'])
@plugin_bp.route('/install/<int:plugin_id>', methods=['POST'])
@login_required
def install_plugin(plugin_id=None):
    """
    安装插件
    支持两种调用方式：
    1. POST /api/plugin/install/<plugin_id>
    2. POST /api/plugin/install  Body: {"plugin_code": "seafood"} 或 {"plugin_id": 1}
    """
    try:
        data = request.get_json() or {}

        # 如果 URL 中未提供 plugin_id，尝试从 body 中获取
        if plugin_id is None:
            body_id = data.get('plugin_id')
            plugin_code = data.get('plugin_code')
            if body_id is not None:
                plugin_id = int(body_id)
            elif plugin_code:
                # 通过 plugin_code 查找
                from models.plugin_models import PluginPackage
                db_lookup: Session = get_db_session()
                try:
                    pkg = db_lookup.query(PluginPackage).filter(
                        PluginPackage.plugin_code == plugin_code
                    ).first()
                    if pkg:
                        plugin_id = pkg.id
                    else:
                        return jsonify({'success': False, 'error': f'插件不存在: {plugin_code}'}), 404
                finally:
                    db_lookup.close()
            else:
                return jsonify({'success': False, 'error': '缺少插件ID或插件代码'}), 400

        version = data.get('version', None)

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = plugin_service.install_plugin(db, user.id, plugin_id, version)
        db.close()

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"安装插件失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/uninstall', methods=['POST'])
@plugin_bp.route('/uninstall/<int:plugin_id>', methods=['POST'])
@login_required
def uninstall_plugin(plugin_id=None):
    """
    卸载插件
    支持两种调用方式：
    1. POST /api/plugin/uninstall/<plugin_id>
    2. POST /api/plugin/uninstall  Body: {"plugin_code": "seafood"} 或 {"plugin_id": 1}
    """
    try:
        data = request.get_json() or {}

        # 如果 URL 中未提供 plugin_id，尝试从 body 中获取
        if plugin_id is None:
            body_id = data.get('plugin_id')
            plugin_code = data.get('plugin_code')
            if body_id is not None:
                plugin_id = int(body_id)
            elif plugin_code:
                from models.plugin_models import PluginPackage
                db_lookup: Session = get_db_session()
                try:
                    pkg = db_lookup.query(PluginPackage).filter(
                        PluginPackage.plugin_code == plugin_code
                    ).first()
                    if pkg:
                        plugin_id = pkg.id
                    else:
                        return jsonify({'success': False, 'error': f'插件不存在: {plugin_code}'}), 404
                finally:
                    db_lookup.close()
            else:
                return jsonify({'success': False, 'error': '缺少插件ID或插件代码'}), 400

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = plugin_service.uninstall_plugin(db, user.id, plugin_id)
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"卸载插件失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/update/<int:plugin_id>', methods=['POST'])
@login_required
def update_plugin(plugin_id):
    """
    更新插件
    Body: {"version": "1.0.1"}
    """
    try:
        data = request.get_json() or {}
        version = data.get('version', None)

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = plugin_service.update_plugin(db, user.id, plugin_id, version)
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"更新插件失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/installed', methods=['GET'])
@login_required
def list_installed_plugins():
    """
    获取已安装插件列表
    """
    try:
        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        plugins = plugin_service.list_installed_plugins(db, user.id)
        db.close()

        return jsonify({
            'success': True,
            'count': len(plugins),
            'plugins': plugins
        }), 200
    except Exception as e:
        logger.error(f"获取已安装插件失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 知识库管理 ====================

@plugin_bp.route('/knowledge', methods=['GET'])
def list_knowledge_bases():
    """
    获取知识库列表（公开接口）
    Query: industry=xxx, category=xxx
    """
    try:
        industry = request.args.get('industry', None)
        category = request.args.get('category', None)

        db: Session = get_db_session()
        kbs = knowledge_service.list_knowledge_bases(db, industry, category)
        db.close()

        return jsonify({
            'success': True,
            'count': len(kbs),
            'knowledge_bases': kbs
        }), 200
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/knowledge/<int:knowledge_id>', methods=['GET'])
def get_knowledge_base(knowledge_id):
    """
    获取知识库详情（公开接口）
    """
    try:
        db: Session = get_db_session()
        kb = knowledge_service.get_knowledge_base(db, knowledge_id)
        db.close()

        if not kb:
            return jsonify({'success': False, 'error': '知识库不存在'}), 404

        return jsonify({'success': True, 'knowledge_base': kb}), 200
    except Exception as e:
        logger.error(f"获取知识库详情失败: knowledge_id={knowledge_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/knowledge', methods=['POST'])
@login_required
def create_knowledge_base():
    """
    创建知识库
    Body: {
        "knowledge_name": "工地管理知识库",
        "description": "工地管理相关知识文档",
        "industry": "工地管理",
        "category": "施工规范"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = knowledge_service.create_knowledge_base(db, user.id, data)
        db.close()

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建知识库失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/knowledge/<int:knowledge_id>/document', methods=['POST'])
@login_required
def add_document(knowledge_id):
    """
    添加文档到知识库
    Body: {
        "doc_title": "施工安全规范",
        "doc_content": "文档内容...",
        "doc_type": "markdown",
        "tags": "安全,施工",
        "summary": "文档摘要"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        result = knowledge_service.add_document(db, knowledge_id, data)
        db.close()

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"添加文档失败: knowledge_id={knowledge_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/knowledge/search', methods=['GET'])
def search_documents():
    """
    搜索知识库文档（公开接口）
    Query: knowledge_id=xxx, query=xxx
    """
    try:
        knowledge_id = request.args.get('knowledge_id', None)
        query = request.args.get('query', None)

        if not query:
            return jsonify({'success': False, 'error': '缺少搜索关键词'}), 400

        try:
            knowledge_id_int = int(knowledge_id) if knowledge_id else None
        except ValueError:
            return jsonify({'success': False, 'error': 'knowledge_id 必须是整数'}), 400

        db: Session = get_db_session()
        docs = knowledge_service.search_documents(
            db,
            knowledge_id_int,
            query
        )
        db.close()

        return jsonify({
            'success': True,
            'count': len(docs),
            'documents': docs
        }), 200
    except Exception as e:
        logger.error(f"搜索文档失败: query={query}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/knowledge/document/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """
    获取文档详情（公开接口）
    """
    try:
        db: Session = get_db_session()
        doc = knowledge_service.get_document(db, doc_id)
        db.close()

        if not doc:
            return jsonify({'success': False, 'error': '文档不存在'}), 404

        return jsonify({'success': True, 'document': doc}), 200
    except Exception as e:
        logger.error(f"获取文档详情失败: doc_id={doc_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 问答库管理 ====================

@plugin_bp.route('/faq', methods=['GET'])
def list_faqs():
    """
    获取FAQ列表（公开接口）
    Query: industry=xxx, category=xxx
    """
    try:
        industry = request.args.get('industry', None)
        category = request.args.get('category', None)

        db: Session = get_db_session()
        faqs = faq_service.list_faqs(db, industry, category)
        db.close()

        return jsonify({
            'success': True,
            'count': len(faqs),
            'faqs': faqs
        }), 200
    except Exception as e:
        logger.error(f"获取FAQ列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/faq', methods=['POST'])
@login_required
def create_faq():
    """
    创建FAQ
    Body: {
        "question": "如何打卡?",
        "answer": "在微信中发送'打卡'即可",
        "industry": "工地管理",
        "category": "考勤",
        "tags": "打卡,考勤",
        "match_keywords": "打卡,上班,签到",
        "match_threshold": 0.7,
        "priority": 10
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = faq_service.create_faq(db, user.id, data)
        db.close()

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建FAQ失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/faq/match', methods=['GET'])
def match_faq():
    """
    智能匹配FAQ（公开接口）
    Query: query=xxx, industry=xxx, top_n=3
    """
    try:
        query = request.args.get('query', None)
        industry = request.args.get('industry', None)

        try:
            top_n = int(request.args.get('top_n', 3))
        except ValueError:
            return jsonify({'success': False, 'error': 'top_n 必须是整数'}), 400

        if not query:
            return jsonify({'success': False, 'error': '缺少查询关键词'}), 400

        db: Session = get_db_session()
        matches = faq_service.match_faq(db, query, industry, top_n)
        db.close()

        return jsonify({
            'success': True,
            'count': len(matches),
            'matches': matches
        }), 200
    except Exception as e:
        logger.error(f"匹配FAQ失败: query={query}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/faq/<int:faq_id>/rate', methods=['POST'])
def rate_faq(faq_id):
    """
    评价FAQ
    Body: {"helpful": true}
    """
    try:
        data = request.get_json()
        if not data or 'helpful' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: helpful'}), 400

        db: Session = get_db_session()
        result = faq_service.rate_faq(db, faq_id, data['helpful'])
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"评价FAQ失败: faq_id={faq_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 解析算法管理 ====================

@plugin_bp.route('/algorithm', methods=['GET'])
def list_algorithms():
    """
    获取算法列表（公开接口）
    Query: industry=xxx, category=xxx
    """
    try:
        industry = request.args.get('industry', None)
        category = request.args.get('category', None)

        db: Session = get_db_session()
        algorithms = algorithm_service.list_algorithms(db, industry, category)
        db.close()

        return jsonify({
            'success': True,
            'count': len(algorithms),
            'algorithms': algorithms
        }), 200
    except Exception as e:
        logger.error(f"获取算法列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/algorithm', methods=['POST'])
@login_required
def register_algorithm():
    """
    注册解析算法
    Body: {
        "algorithm_code": "custom_parser_v1",
        "algorithm_name": "自定义解析器V1",
        "description": "自定义文本解析算法",
        "industry": "餐饮配送",
        "category": "custom",
        "module_path": "plugins.custom_parser",
        "class_name": "CustomParser",
        "function_name": "parse",
        "default_params": "{\"threshold\": 0.8}",
        "param_schema": "{\"type\": \"object\"}"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = algorithm_service.register_algorithm(db, user.id, data)
        db.close()

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"注册算法失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/algorithm/execute', methods=['POST'])
@login_required
def execute_algorithm():
    """
    执行解析算法
    Body: {
        "algorithm_code": "custom_parser_v1",
        "input_data": {"text": "订单内容..."},
        "params": {"threshold": 0.9}
    }
    """
    try:
        data = request.get_json()
        if not data or 'algorithm_code' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: algorithm_code'}), 400

        db: Session = get_db_session()
        result = algorithm_service.execute_algorithm(
            db,
            data['algorithm_code'],
            data.get('input_data', {}),
            data.get('params', None)
        )
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"执行算法失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 插件管理后台 API ====================


@plugin_bp.route('/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """
    获取插件管理后台统计数据（仅管理员）
    """
    try:
        db: Session = get_db_session()
        stats = plugin_admin_service.get_plugin_stats(db)
        db.close()

        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        logger.error(f"获取插件统计数据失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/user-stats', methods=['GET'])
@admin_required
def get_user_plugin_stats():
    """
    获取用户插件使用统计（仅管理员）
    Query: user_id=xxx
    """
    try:
        user_id = request.args.get('user_id', None)
        if user_id:
            user_id = int(user_id)

        db: Session = get_db_session()
        stats = plugin_admin_service.get_user_plugin_stats(db, user_id)
        db.close()

        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        logger.error(f"获取用户插件统计数据失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins', methods=['GET'])
@admin_required
def admin_list_plugins():
    """
    获取全部插件列表（管理后台）
    Query: category=xxx, industry=xxx, search=xxx, status=active|inactive|deprecated
    """
    try:
        category = request.args.get('category')
        industry = request.args.get('industry')
        search = request.args.get('search')
        status = request.args.get('status')

        db: Session = get_db_session()
        plugins = plugin_service.list_admin_plugins(db, category, industry, search, status)
        db.close()

        return jsonify({
            'success': True,
            'count': len(plugins),
            'plugins': plugins
        }), 200
    except Exception as e:
        logger.error(f"获取管理后台插件列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins', methods=['POST'])
@admin_required
def admin_create_plugin():
    """
    创建插件包（仅管理员）
    Body: {
        "plugin_name": "餐饮配送插件",
        "plugin_code": "fooddelivery",
        "description": "餐饮配送行业专业插件",
        "category": "industry",
        "industry": "餐饮配送",
        "icon_url": "https://...",
        "tags": "餐饮,配送,订单",
        "is_public": true,
        "license_type": "free",
        "price": 0,
        "required_permissions": "order_read,order_write"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        user = get_current_user_from_request(db)

        result = plugin_admin_service.create_plugin(db, user.id, data)
        db.close()

        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"创建插件失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins/<int:plugin_id>', methods=['PUT'])
@admin_required
def admin_update_plugin(plugin_id):
    """
    更新插件信息（仅管理员）
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        result = plugin_admin_service.update_plugin(db, plugin_id, data)
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"更新插件失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins/<int:plugin_id>', methods=['DELETE'])
@admin_required
def admin_delete_plugin(plugin_id):
    """
    删除插件（仅管理员，软删除）
    """
    try:
        db: Session = get_db_session()
        result = plugin_admin_service.delete_plugin(db, plugin_id)
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"删除插件失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins/<int:plugin_id>/status', methods=['PUT'])
@admin_required
def admin_update_plugin_status(plugin_id):
    """
    更新插件状态（仅管理员）
    Body: {"is_active": true, "is_public": true, "is_featured": false, "is_deprecated": false}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        db: Session = get_db_session()
        result = plugin_admin_service.update_plugin_status(db, plugin_id, data)
        db.close()

        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"更新插件状态失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins/<int:plugin_id>/versions', methods=['GET'])
@admin_required
def admin_get_plugin_versions(plugin_id):
    """
    获取插件版本历史（仅管理员）
    """
    try:
        db: Session = get_db_session()
        versions = plugin_admin_service.get_plugin_version_history(db, plugin_id)
        db.close()

        return jsonify({
            'success': True,
            'count': len(versions),
            'versions': versions
        }), 200
    except Exception as e:
        logger.error(f"获取插件版本历史失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/plugins/<int:plugin_id>/versions', methods=['POST'])
@admin_required
def admin_create_plugin_version(plugin_id):
    """
    创建插件版本（仅管理员）
    Body: {
        "version": "1.0.0",
        "changelog": "新增功能",
        "download_url": "https://...",
        "file_size": 1024,
        "dependencies": "{\"core\": \"1.0.0\"}",
        "is_stable": true,
        "is_active": true,
        "min_system_version": "1.0",
        "release_notes": "版本说明"
    }
    """
    try:
        data = request.get_json()
        if not data or 'version' not in data:
            return jsonify({'success': False, 'error': '缺少版本号'}), 400

        db: Session = get_db_session()
        result = plugin_admin_service.create_plugin_version(db, plugin_id, data)
        db.close()

        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"创建插件版本失败: plugin_id={plugin_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@plugin_bp.route('/admin/installation-history', methods=['GET'])
@admin_required
def admin_get_installation_history():
    """
    获取安装历史记录（仅管理员）
    Query: plugin_id=xxx, user_id=xxx
    """
    try:
        plugin_id = request.args.get('plugin_id', None)
        user_id = request.args.get('user_id', None)

        if plugin_id:
            plugin_id = int(plugin_id)
        if user_id:
            user_id = int(user_id)

        db: Session = get_db_session()
        history = plugin_admin_service.get_installation_history(db, plugin_id, user_id)
        db.close()

        return jsonify({
            'success': True,
            'count': len(history),
            'history': history
        }), 200
    except Exception as e:
        logger.error(f"获取安装历史失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500