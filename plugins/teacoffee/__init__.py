"""
茶饮咖啡行业插件
提供饮品菜单管理、订单处理、会员管理、原料库存、饮品推荐等功能
"""
from .models import *
from .service import TeaCoffeeService
from .api import teacoffee_bp


def register_plugin(app):
    app.register_blueprint(teacoffee_bp)