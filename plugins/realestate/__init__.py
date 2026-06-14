"""
房产中介行业插件
提供房源管理、客户管理、交易流程、智能匹配等功能
"""
from .models import *
from .service import RealEstateService
from .api import realestate_bp


def register_plugin(app):
    """注册插件"""
    app.register_blueprint(realestate_bp)