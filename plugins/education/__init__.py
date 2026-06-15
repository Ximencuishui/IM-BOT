"""
教育培训行业插件
提供课程管理、学员跟踪、教师管理、学习进度等功能
"""
from .models import *
from .service import EducationService
from .api import education_bp


def register_plugin(app):
    """注册插件"""
    app.register_blueprint(education_bp)