"""
火锅食材行业插件
提供食材分类管理、锅底识别、订单处理、配送管理等功能
"""
from .models import *
from .service import HotpotService
from .api import hotpot_bp


def register_plugin(app):
    app.register_blueprint(hotpot_bp)