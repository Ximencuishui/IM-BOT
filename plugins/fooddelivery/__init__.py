"""
餐饮配送行业插件
提供商品管理、订单处理、桌台管理、员工管理、促销活动、销售报表等功能
"""
from .models import *
from .service import FoodDeliveryService
from .api import fooddelivery_bp


def register_plugin(app):
    app.register_blueprint(fooddelivery_bp)