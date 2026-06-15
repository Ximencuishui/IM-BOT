"""
电动车配件行业插件
提供电动车配件商品管理、订单处理、电池管理、维修服务等功能
"""
from .models import *
from .service import EVPartsService
from .api import evparts_bp


def register_plugin(app):
    app.register_blueprint(evparts_bp)