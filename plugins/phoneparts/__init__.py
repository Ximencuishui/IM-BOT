"""
手机零配件行业插件
提供手机配件商品管理、订单处理、维修服务、手机型号适配等功能
"""
from .models import *
from .service import PhonePartsService
from .api import phoneparts_bp


def register_plugin(app):
    app.register_blueprint(phoneparts_bp)