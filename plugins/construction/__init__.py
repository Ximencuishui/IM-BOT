"""
工地管理行业插件
提供工人打卡、天气工期管理、工作面记录、工程量记录等功能
"""
from .models import *
from .service import ConstructionService
from .api import construction_bp


def register_plugin(app):
    app.register_blueprint(construction_bp)