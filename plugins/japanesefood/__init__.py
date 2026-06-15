"""
日料寿司行业插件
提供寿司菜单管理、订单处理、食材管理、套餐组合、外卖配送等功能
"""
from .models import *
from .service import JapaneseFoodService
from .api import japanesefood_bp


def register_plugin(app):
    app.register_blueprint(japanesefood_bp)