"""
水电五金行业插件
提供五金商品管理、订单处理、库存管理、安装服务预约等功能
"""
from .models import *
from .service import HardwareService
from .api import hardware_bp


def register_plugin(app):
    app.register_blueprint(hardware_bp)