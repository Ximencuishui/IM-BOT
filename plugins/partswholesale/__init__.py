"""
配件批发行业插件
提供配件商品管理、订单处理、客户管理、库存管理、批发价格等功能
"""
from .models import *
from .service import PartsWholesaleService
from .api import partswholesale_bp


def register_plugin(app):
    app.register_blueprint(partswholesale_bp)