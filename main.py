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
"""
from flask import Flask, jsonify, Response
from flask_cors import CORS
import logging
import os
import sys
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from database.db_config import init_db, get_db_session
# 导入模型以确保表被创建
from models.models import *
from models.license_model import LegacyLicense  # 旧版授权模型
from models.user_models import *  # 导入用户端模型
from models.desktop_bot_models import *  # 桌面端机器人/授权表
from models.desktop_group_models import *  # 桌面端多群配置表
from models.plugin_models import *  # 插件市场模型

# 行业插件模型导入（使用插件版本）
from plugins.education.models import *  # 教育培训模型
from plugins.realestate.models import *  # 房产中介模型
from plugins.travel.models import *  # 旅行社插件模型
from plugins.construction.models import *  # 工地管理插件模型
from plugins.fooddelivery.models import *  # 餐饮配送插件模型
from plugins.seafood.models import *  # 海鲜批发插件模型
from plugins.fleet.models import *  # 车队调度插件模型

# ============================================================
# API 蓝图导入 - 按功能模块分组
# ============================================================

# --- 桌面端业务 API（本地部署 - 第3部分）---
from api.orders import orders_bp                # 订单管理
from api.products import products_bp            # 商品管理
from api.customers import customers_bp          # 客户管理
from api.reports import reports_bp              # 报表导出
from api.salespersons import salespersons_bp    # 销售人员管理
from api.dashboard import dashboard_bp          # 数据看板
from api.robot import robot_bp                  # 机器人配置
from api.rules import rule_bp                   # 规则配置
from api.rule_templates import rule_template_bp # 规则模板库
from api.rule_import import rule_import_bp      # 规则导入
from api.routes import routes_bp                # 线路产品管理
# from api.travel import travel_bp                # 旅行社服务API - 使用插件版本
# from api.construction import construction_bp     # 工地管理API - 使用插件版本
from api.plugin import plugin_bp                # 插件市场API

# --- 行业插件API ---
from plugins.education.api import education_bp   # 教育培训API
from plugins.realestate.api import realestate_bp # 房产中介API
from plugins.travel.api import travel_bp         # 旅行社API
from plugins.construction.api import construction_bp # 工地管理API
from plugins.fooddelivery.api import fooddelivery_bp # 餐饮配送API
from plugins.seafood.api import seafood_bp       # 海鲜批发API
from api.license import license_bp              # 旧版授权激活（桌面端）
from api.hook_callback import hook_callback_bp  # Hook 回调接口
from api.desktop_bot import desktop_bot_bp      # 桌面端机器人/运维（SimBot 对齐）
from api.desktop_groups import desktop_groups_bp  # 桌面端多群配置

# --- 网站端 API（云端服务 - 第1、2部分）---
from api.auth import auth_bp                    # 用户认证（注册、登录）
from api.admin import admin_bp                  # 管理员功能（用户管理、系统设置）
from api.system_settings import system_settings_bp  # 系统设置（邮件、支付、参数、通知模板）
from api.affiliate import affiliate_bp          # 推广管理
from api.pricing import pricing_bp              # 定价配置、授权展期
from api.license_v2 import license_bp as license_v2_bp      # 授权码管理V2
from api.license_sync import sync_bp            # 授权码同步
from api.auto_renew import auto_renew_bp        # 自动续费
from api.renewal_history import renewal_history_bp  # 续费历史
from api.license_stats import license_stats_bp  # 授权统计
from api.team import team_bp                    # 团队管理（混合）
from api.monitoring import monitoring_bp        # 系统监控
from api.audit_log import audit_log_bp          # 审计日志
from api.user_settings import user_settings_bp    # 用户设置API
from api.setup import setup_bp                    # 安装引导API
from plugins.fleet.api import fleet_bp            # 车队调度插件API
from utils.logger import setup_logger
from utils.metrics import generate_metrics_response, check_middleware_health
from utils.rate_limiter import rate_limit_middleware

# 配置日志
os.makedirs(settings.LOG_DIR, exist_ok=True)
logger = setup_logger('main')


def create_app():
    """
    创建Flask应用
    
    根据 APP_MODE 环境变量决定加载哪些模块:
        - all: 加载所有模块（默认）
        - web: 仅加载网站端模块
        - desktop: 仅加载桌面端模块
    """
    from flask import send_from_directory
    
    app = Flask(__name__, static_folder='frontend', static_url_path='/frontend')
    
    from config.settings import settings
    
    # 配置静态文件服务，支持 public 目录（用于 favicon 和 logo）
    from flask import send_from_directory
    @app.route('/images/<path:filename>')
    def serve_images(filename):
        return send_from_directory('frontend/public/images', filename)
        
    @app.route('/favicon.ico')
    def serve_favicon():
        return send_from_directory('frontend/public', 'favicon.ico', mimetype='image/x-icon')
    app.config['SECRET_KEY'] = settings.SECRET_KEY

    # 配置CORS
    CORS(app, origins=settings.CORS_ORIGINS)
    
    # 请求频率限制中间件
    @app.before_request
    def before_req():
        result = rate_limit_middleware()
        if result:
            return result

    # 获取运行模式
    app_mode = os.getenv('APP_MODE', 'all').lower()
    
    logger.info(f"应用模式: {app_mode}")

    # ============================================================
    # 注册蓝图 - 按模块分组
    # ============================================================
    
    if app_mode in ['all', 'desktop']:
        logger.info("正在注册桌面端业务 API...")
        
        # --- 桌面端核心业务 API（第3部分）---
        app.register_blueprint(orders_bp)           # 订单管理
        app.register_blueprint(products_bp)         # 商品管理
        app.register_blueprint(customers_bp)        # 客户管理
        app.register_blueprint(reports_bp)          # 报表导出
        app.register_blueprint(salespersons_bp)     # 销售人员管理
        app.register_blueprint(dashboard_bp)        # 数据看板
        app.register_blueprint(robot_bp)            # 机器人配置
        app.register_blueprint(rule_bp)             # 规则配置
        app.register_blueprint(rule_template_bp)    # 规则模板库
        app.register_blueprint(rule_import_bp)      # 规则导入
        app.register_blueprint(routes_bp)           # 线路产品管理
        # app.register_blueprint(license_bp)          # 旧版授权激活（已废弃，使用V2）
        app.register_blueprint(hook_callback_bp)    # Hook 回调接口
        app.register_blueprint(desktop_bot_bp)    # 桌面端机器人/运维
        app.register_blueprint(desktop_groups_bp)  # 桌面端多群配置
        # app.register_blueprint(travel_bp)          # 旅行社服务API - 使用插件版本
        # app.register_blueprint(construction_bp)    # 工地管理API - 使用插件版本
        app.register_blueprint(plugin_bp)          # 插件市场API
        
        # --- 行业插件API注册 ---
        app.register_blueprint(education_bp)       # 教育培训API
        app.register_blueprint(realestate_bp)     # 房产中介API
        app.register_blueprint(travel_bp)         # 旅行社API
        app.register_blueprint(construction_bp)   # 工地管理API
        app.register_blueprint(fooddelivery_bp)   # 餐饮配送API
        app.register_blueprint(seafood_bp)       # 海鲜批发API
        
        logger.info("✓ 桌面端 API 注册完成")
    
    # license_v2_bp 需要在所有模式下注册（桌面端和网站端都需要）
    if app_mode in ['all', 'desktop', 'web']:
        app.register_blueprint(license_v2_bp)       # 授权码管理V2
    
    if app_mode in ['all', 'web']:
        logger.info("正在注册网站端 API...")
        
        # --- 网站端 API（第1、2部分）---
        app.register_blueprint(auth_bp)             # 用户认证
        app.register_blueprint(admin_bp)            # 管理员功能
        app.register_blueprint(system_settings_bp)  # 系统设置
        app.register_blueprint(affiliate_bp)        # 推广管理
        app.register_blueprint(pricing_bp)          # 定价配置
        # license_v2_bp 已在桌面端注册，这里跳过
        # app.register_blueprint(license_v2_bp)       # 授权码管理V2
        app.register_blueprint(sync_bp)             # 授权码同步
        app.register_blueprint(auto_renew_bp)       # 自动续费
        app.register_blueprint(renewal_history_bp)  # 续费历史
        app.register_blueprint(license_stats_bp)    # 授权统计
        app.register_blueprint(team_bp)             # 团队管理
        app.register_blueprint(monitoring_bp)       # 系统监控
        app.register_blueprint(audit_log_bp)        # 审计日志
        app.register_blueprint(user_settings_bp)    # 用户设置API
        app.register_blueprint(setup_bp)            # 安装引导API
        app.register_blueprint(fleet_bp)            # 车队调度插件API
        
        logger.info("✓ 网站端 API 注册完成")

    # ============================================================
    # 前端页面路由
    # ============================================================
    @app.route('/')
    def index():
        """官网首页"""
        return send_from_directory('frontend', 'index.html')

    # 注意：以下旧架构路由已废弃，请使用 tonjclaw-web Vue 项目
    # @app.route('/user-portal')
    # def user_portal():
    #     """用户中心（网站端）- 已废弃"""
    #     return send_from_directory('frontend', 'user-portal.html')
    
    # @app.route('/admin-portal')
    # def admin_portal():
    #     """管理员控制台（网站端）- 已废弃"""
    #     return send_from_directory('frontend', 'admin-portal.html')
    
    @app.route('/icons-local.js')
    def icons_local():
        """提供本地图标库文件"""
        return send_from_directory('frontend', 'icons-local.js', mimetype='application/javascript')
    
    @app.route('/setup.html')
    def setup():
        """安装引导页面"""
        return send_from_directory('frontend', 'setup.html')
    
    @app.route('/settings.html')
    def settings():
        """用户设置页面"""
        return send_from_directory('frontend', 'settings.html')
    
    @app.route('/test-icons')
    def test_icons():
        """图标测试页面"""
        return send_from_directory('frontend', 'test-icons.html')
    
    # @app.route('/test-admin-portal')
    # def test_admin_portal():
    #     """Admin Portal 测试页面 - 已废弃"""
    #     return send_from_directory('frontend', 'test-admin-portal.html')

    # 健康检查
    @app.route('/health', methods=['GET'])
    def health():
        middleware_health = check_middleware_health()
        all_healthy = all(middleware_health.values())

        status = 'healthy' if all_healthy else 'degraded'
        status_code = 200 if all_healthy else 206

        return jsonify({
            'status': status,
            'service': settings.APP_NAME,
            'version': settings.APP_VERSION,
            'middleware': middleware_health
        }), status_code

    # Prometheus指标
    @app.route('/metrics', methods=['GET'])
    def metrics():
        return Response(
            generate_metrics_response()[0],
            mimetype='text/plain'
        )

    # 404处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '接口不存在'}), 404

    # 500处理 - 生产环境返回通用错误信息
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"服务器内部错误: {error}", exc_info=True)
        
        import os
        if os.getenv('APP_ENV', 'development').lower() == 'production':
            return jsonify({'success': False, 'error': '操作失败，请联系管理员'}), 500
        else:
            return jsonify({'success': False, 'error': str(error)}), 500

    return app


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


def init_demo_account():
    """初始化演示账号（仅在无用户时创建）"""
    from models.user_models import User as UserModel
    from services.auth_service import AuthService
    
    db = get_db_session()
    try:
        # 检查是否已有用户
        user_count = db.query(UserModel).count()
        if user_count == 0:
            logger.info("检测到无用户账户，正在创建演示账号...")
            
            # 1. 创建超级管理员 admin/12345678
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
                # 标记为超级管理员
                admin_user = db.query(UserModel).filter(UserModel.email == 'admin@system.local').first()
                if admin_user:
                    admin_user.is_active = True
                    admin_user.role = 'super_admin'  # 设置超级管理员角色
                    db.commit()
                    logger.info("✓ 超级管理员账号创建成功: admin / 12345678")
            else:
                logger.error(f"超级管理员账号创建失败: {result.get('error')}")
            
            # 2. 创建普通用户 BOSS/888888
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


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    # 初始化数据库
    try:
        logger.info("正在初始化数据库...")
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        logger.warning("请确保MySQL服务已启动并正确配置数据库连接")
        sys.exit(1)

    # 初始化演示账号
    init_demo_account()

    # 创建应用
    app = create_app()

    if settings.VERBOSE_ROUTE_LOG:
        logger.info("\n已注册的API路由:")
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            if rule.endpoint != 'static':
                methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                logger.info(f"  {methods:10s} {rule.rule}")

    # 在后台线程启动定时任务
    scheduler_thread = threading.Thread(target=start_scheduler_in_background, daemon=True)
    scheduler_thread.start()
    logger.info("定时任务调度器已在后台启动")

    # 启动服务
    logger.info(f"\n服务启动: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"监控指标: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}/metrics")
    logger.info(f"健康检查: http://{settings.FLASK_HOST}:{settings.FLASK_PORT}/health")
    logger.info(f"Hook 回调: {settings.HOOK_CALLBACK_URL}")
    logger.info(f"Hook 控制面: {settings.HOOK_BASE_URL}")

    app.run(
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        debug=settings.DEBUG,
        threaded=True
    )


if __name__ == '__main__':
    main()
