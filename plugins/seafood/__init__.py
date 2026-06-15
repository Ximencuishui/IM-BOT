"""
海鲜批发行业插件
提供客户管理、供应商管理、订单处理、急单处理、截单提醒、报表统计等功能
"""
from .models import *
from .service import SeafoodService
from .api import seafood_bp


def register_plugin(app):
    app.register_blueprint(seafood_bp)