"""
旅行社行业插件
提供旅游线路管理、群配置、报名处理、自动回复等功能
"""
from .models import *
from .service import TravelService
from .api import travel_bp


def register_plugin(app):
    app.register_blueprint(travel_bp)