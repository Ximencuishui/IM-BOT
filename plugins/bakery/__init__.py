"""
烘焙甜品行业插件
提供烘焙产品管理、订单处理、原料库存、会员管理、蛋糕定制等功能
"""
from .models import *
from .service import BakeryService
from .api import bakery_bp


def register_plugin(app):
    app.register_blueprint(bakery_bp)