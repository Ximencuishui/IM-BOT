"""
车队调度行业插件
提供泥土车管理、物流车管理、任务调度、路线规划、维护保养等功能
"""
from .models import *
from .service import FleetService
from .api import fleet_bp


def register_plugin(app):
    app.register_blueprint(fleet_bp)