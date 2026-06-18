"""
本地化配送服务商智能订货统计工具 - 主应用入口
整合所有API路由、定时任务、监控指标

系统架构说明:
    1. 网站端 Admin 管理后台（服务端）- /admin-portal
       功能: 用户管理、授权码销售、系统配置
    
    2. 网站端用户后台（简单功能）- /user-portal
       功能: 个人资料、授权码管理、订阅管理
    
    3. 桌面端用户端（经营者使用）- /app-desktop (本地)
       功能: 订单管理、商品管理、客户管理、机器人配置、报表导出

环境变量:
    APP_MODE: all(默认) | web(仅网站端) | desktop(仅桌面端)

优化说明:
    - 模型和蓝图采用懒加载，减少模块导入耗时
    - 数据库初始化在后台线程执行，HTTP服务先行启动
    - 使用 flask-compress 压缩 API 响应
    - 请求耗时自动记录到 Prometheus 指标
"""
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from flask_compress import Compress
import logging
import os
import sys
import threading
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from utils.logger import setup_logger

# 配置日志目录
os.makedirs(settings.LOG_DIR, exist_ok=True)
logger = setup_logger('main')

# ==================== 应用就绪状态 ====================
_app_ready = threading.Event()
_app_init_error = None


def is_app_ready():
    """检查应用是否已完成初始化"""
    return _app_ready.is_set()


def wait_for_app_ready(timeout=10):
    """等待应用初始化完成（超时秒数）"""
    return _app_ready.wait(timeout)


# ==================== 模型懒加载 ====================

def _import_all_models():
    """导入所有SQLAlchemy模型以确保表被创建（导入模块即触发Base注册）"""
    import models.models
    import models.license_model
    import models.user_models
    import models.desktop_bot_models
    import models.desktop_group_models
    import models.plugin_models


def _import_plugin_models():
    """导入行业插件模型（懒加载）"""
    import plugins.education.models
    import plugins.realestate.models
    import plugins.travel.models
    import plugins.construction.models
    import plugins.fooddelivery.models
    import plugins.seafood.models
    import plugins.fleet.models
    import plugins.studio.models


# ==================== 蓝图懒加载 ====================

def _register_desktop_blueprints(app):
    """注册桌面端业务蓝图"""
    from api.orders import orders_bp
    from api.products import products_bp
    from api.customers import customers_bp
    from api.reports import reports_bp
    from api.salespersons import salespersons_bp
    from api.dashboard import dashboard_bp
    from api.robot import robot_bp
    from api.rules import rule_bp
    from api.rule_templates import rule_template_bp
    from api.rule_import import rule_import_bp
    from api.routes import routes_bp
    from api.plugin import plugin_bp
    from api.settings_plugins import settings_plugin_bp
    from api.hook_callback import hook_callback_bp
    from api.desktop_bot import desktop_bot_bp
    from api.desktop_groups import desktop_groups_bp

    # --- 行业插件API ---
    from plugins.education.api import education_bp
    from plugins.realestate.api import realestate_bp
    from plugins.travel.api import travel_bp
    from plugins.construction.api import construction_bp
    from plugins.fooddelivery.api import fooddelivery_bp
    from plugins.seafood.api import seafood_bp
    from plugins.studio.api import studio_bp

    app.register_blueprint(orders_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(salespersons_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(robot_bp)
    app.register_blueprint(rule_bp)
    app.register_blueprint(rule_template_bp)
    app.register_blueprint(rule_import_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(hook_callback_bp)
    app.register_blueprint(desktop_bot_bp)
    app.register_blueprint(desktop_groups_bp)
    app.register_blueprint(plugin_bp)
    app.register_blueprint(settings_plugin_bp)

    # 行业插件API
    app.register_blueprint(education_bp)
    app.register_blueprint(realestate_bp)
    app.register_blueprint(travel_bp)
    app.register_blueprint(construction_bp)
    app.register_blueprint(fooddelivery_bp)
    app.register_blueprint(seafood_bp)
    app.register_blueprint(studio_bp)


def _register_web_blueprints(app):
    """注册网站端业务蓝图"""
    from api.auth import auth_bp
    from api.admin import admin_bp
    from api.system_settings import system_settings_bp
    from api.affiliate import affiliate_bp
    from api.pricing import pricing_bp
    from api.license_sync import sync_bp
    from api.auto_renew import auto_renew_bp
    from api.renewal_history import renewal_history_bp
    from api.license_stats import license_stats_bp
    from api.team import team_bp
    from api.monitoring import monitoring_bp
    from api.audit_log import audit_log_bp
    from api.user_settings import user_settings_bp
    from api.setup import setup_bp
    from plugins.fleet.api import fleet_bp
    from api.license_check import license_check_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(system_settings_bp)
    app.register_blueprint(affiliate_bp)
    app.register_blueprint(pricing_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(auto_renew_bp)
    app.register_blueprint(renewal_history_bp)
    app.register_blueprint(license_stats_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(audit_log_bp)
    app.register_blueprint(user_settings_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(fleet_bp)
    app.register_blueprint(license_check_bp)


# ==================== 请求耗时中间件 ====================

def _setup_request_logging(app):
    """配置请求耗时记录"""
    @app.before_request
    def _start_timer():
        request._start_time = time.time()

    @app.after_request
    def _log_request_time(response):
        if hasattr(request, '_start_time'):
            elapsed = time.time() - request._start_time
            if elapsed > 1.0:
                logger.warning(
                    f"慢请求 [{elapsed:.2f}s] {request.method} {request.path}"
                )
            elif elapsed > 0.5:
                logger.info(
                    f"请求耗时 [{elapsed:.2f}s] {request.method} {request.path}"
                )
        return response


# ==================== 应用工厂 ====================

def create_app():
    """创建Flask应用 - 按需加载蓝图"""
    from flask import send_from_directory
    from utils.rate_limiter import rate_limit_middleware

    app = Flask(__name__, static_folder='frontend', static_url_path='/frontend')

    # 密钥配置
    app.config['SECRET_KEY'] = settings.SECRET_KEY

    # 配置CORS
    CORS(app, origins=settings.CORS_ORIGINS)

    # 启用响应压缩
    Compress(app)
    app.config['COMPRESS_ALGORITHM'] = 'gzip'
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500

    # 请求频率限制中间件
    @app.before_request
    def before_req():
        result = rate_limit_middleware()
        if result:
            return result

    # 请求耗时记录
    _setup_request_logging(app)

    # 静态文件服务
    @app.route('/images/<path:filename>')
    def serve_images(filename):
        return send_from_directory('frontend/public/images', filename)

    @app.route('/favicon.ico')
    def serve_favicon():
        return send_from_directory('frontend/public', 'favicon.ico', mimetype='image/x-icon')

    # 获取运行模式
    app_mode = os.getenv('APP_MODE', 'all').lower()
    logger.info(f"应用模式: {app_mode}")

    # ==================== 注册蓝图 ====================
    if app_mode in ['all', 'desktop']:
        logger.info("正在注册桌面端业务 API...")
        _register_desktop_blueprints(app)
        logger.info("✓ 桌面端 API 注册完成")

    # license_v2 在所有模式下注册
    from api.license_v2 import license_bp as license_v2_bp
    if app_mode in ['all', 'desktop', 'web']:
        app.register_blueprint(license_v2_bp)

    if app_mode in ['all', 'web']:
        logger.info("正在注册网站端 API...")
        _register_web_blueprints(app)
        logger.info("✓ 网站端 API 注册完成")

    # ==================== 前端页面路由 ====================
    @app.route('/')
    def index():
        return send_from_directory('frontend', 'index.html')

    @app.route('/icons-local.js')
    def icons_local():
        return send_from_directory('frontend', 'icons-local.js', mimetype='application/javascript')

    @app.route('/setup.html')
    def setup():
        return send_from_directory('frontend', 'setup.html')

    @app.route('/settings.html')
    def settings():
        return send_from_directory('frontend', 'settings.html')

    @app.route('/test-icons')
    def test_icons():
        return send_from_directory('frontend', 'test-icons.html')

    # ==================== 健康检查 ====================
    @app.route('/health', methods=['GET'])
    def health():
        from utils.metrics import check_middleware_health

        ready = is_app_ready()
        middleware_health = check_middleware_health() if ready else {}
        all_healthy = ready and all(middleware_health.values())

        status = 'healthy' if all_healthy else ('starting' if not ready else 'degraded')
        status_code = 200 if all_healthy else (503 if not ready else 206)

        return jsonify({
            'status': status,
            'service': settings.APP_NAME,
            'version': settings.APP_VERSION,
            'ready': ready,
            'middleware': middleware_health,
        }), status_code

    # 启动就绪检测端点
    @app.route('/health/ready', methods=['GET'])
    def readiness():
        if is_app_ready():
            return jsonify({'ready': True}), 200
        return jsonify({'ready': False, 'error': str(_app_init_error)}), 503

    # Prometheus指标
    @app.route('/metrics', methods=['GET'])
    def metrics():
        from utils.metrics import generate_metrics_response
        return Response(
            generate_metrics_response()[0],
            mimetype='text/plain'
        )

    # ==================== 错误处理 ====================
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '接口不存在'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': '请求方法不允许'}), 405

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({'error': '请求过于频繁，请稍后重试'}), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"服务器内部错误: {error}", exc_info=True)
        if os.getenv('APP_ENV', 'development').lower() == 'production':
            return jsonify({'success': False, 'error': '操作失败，请联系管理员'}), 500
        return jsonify({'success': False, 'error': str(error)}), 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(error):
        """捕获未处理的全局异常"""
        logger.error(f"未捕获的异常: {error}", exc_info=True)
        if os.getenv('APP_ENV', 'development').lower() == 'production':
            return jsonify({'success': False, 'error': '服务器内部错误'}), 500
        return jsonify({'success': False, 'error': str(error)}), 500

    return app


# ==================== 后台初始化任务 ====================

def _init_database_background():
    """在后台线程中初始化数据库（不阻塞HTTP服务启动）"""
    global _app_init_error
    try:
        logger.info("[后台] 正在加载数据模型...")
        _import_all_models()
        _import_plugin_models()

        from database.db_config import init_db
        logger.info("[后台] 正在初始化数据库...")
        init_db()
        logger.info("[后台] 数据库初始化完成")

        # 初始化演示账号
        _init_demo_account()
    except Exception as e:
        _app_init_error = str(e)
        logger.error(f"[后台] 数据库初始化失败: {e}", exc_info=True)
        logger.warning("请确保MySQL服务已启动并正确配置数据库连接")
    finally:
        _app_ready.set()


def start_scheduler_in_background():
    """在后台启动定时任务调度器"""
    if settings.SKIP_SCHEDULER:
        logger.info("已跳过定时任务调度器（TONJCLAW_SKIP_SCHEDULER=1）")
        return
    try:
        from services.scheduler import init_scheduler
        logger.info("正在后台启动定时任务调度器...")
        init_scheduler()
    except Exception as e:
        logger.warning(f"定时任务调度器启动失败: {e}")


def _init_demo_account():
    """初始化演示账号（仅在无用户时创建）"""
    from models.user_models import User as UserModel
    from services.auth_service import AuthService
    from database.db_config import get_db_session

    db = get_db_session()
    try:
        user_count = db.query(UserModel).count()
        if user_count == 0:
            logger.info("检测到无用户账户，正在创建演示账号...")

            # 创建超级管理员 admin/12345678
            result = AuthService.register(
                db,
                email='admin@system.local',
                password='12345678',
                username='admin',
                company_name='系统管理员',
                phone='13800138000',
                subscription_type='yearly',
                max_groups=999
            )

            if result['success']:
                admin_user = db.query(UserModel).filter(UserModel.email == 'admin@system.local').first()
                if admin_user:
                    admin_user.is_active = True
                    admin_user.role = 'super_admin'
                    db.commit()
                    logger.info("✓ 超级管理员账号创建成功: admin / 12345678")
            else:
                logger.error(f"超级管理员账号创建失败: {result.get('error')}")

            # 创建普通用户 BOSS/888888
            result2 = AuthService.register(
                db,
                email='boss@demo.local',
                password='888888',
                username='BOSS',
                company_name='演示公司',
                phone='13900139000',
                subscription_type='monthly',
                max_groups=3
            )

            if result2['success']:
                logger.info("✓ 普通用户账号创建成功: BOSS / 888888")
                logger.info("⚠ 请立即修改默认密码以确保安全")
            else:
                logger.error(f"普通用户账号创建失败: {result2.get('error')}")
        else:
            logger.info(f"已存在 {user_count} 个用户账户，跳过演示账号创建")
    except Exception as e:
        logger.error(f"演示账号初始化失败: {e}", exc_info=True)
    finally:
        db.close()


# ==================== 主入口 ====================

def main():
    """主函数 - 快速启动流程"""
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    # 1. 创建应用（不阻塞）
    app = create_app()

    # 2. 在后台线程启动定时任务
    scheduler_thread = threading.Thread(target=start_scheduler_in_background, daemon=True)
    scheduler_thread.start()
    logger.info("定时任务调度器已在后台启动")

    # 3. 在后台初始化数据库（模型加载 + 建表 + 演示账号）
    db_thread = threading.Thread(target=_init_database_background, daemon=True)
    db_thread.start()
    logger.info("数据库初始化已在后台启动")

    # 4. 输出路由信息（如果开启）
    if settings.VERBOSE_ROUTE_LOG:
        logger.info("\n已注册的API路由:")
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            if rule.endpoint != 'static':
                methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                logger.info(f"  {methods:10s} {rule.rule}")

    # 5. 立即启动HTTP服务
    logger.info(f"\n服务启动: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"监控指标: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}/metrics")
    logger.info(f"健康检查: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}/health")
    logger.info(f"就绪检查: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}/health/ready")

    app.run(
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        debug=settings.DEBUG,
        threaded=True
    )


if __name__ == '__main__':
    main()