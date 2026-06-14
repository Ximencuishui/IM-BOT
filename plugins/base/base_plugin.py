"""
插件基类 - 所有行业插件必须继承此类
"""
from flask import Blueprint


class BasePlugin:
    """插件基类"""
    
    PLUGIN_CODE = ""
    PLUGIN_NAME = ""
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = ""
    PLUGIN_CATEGORY = "industry"
    PLUGIN_INDUSTRY = ""
    PLUGIN_AUTHOR = "TonjClaw"
    PLUGIN_DEPENDENCIES = []
    
    def __init__(self, app=None):
        self.app = app
        self._api_bp = None
    
    def install(self):
        pass
    
    def uninstall(self):
        pass
    
    def enable(self):
        pass
    
    def disable(self):
        pass
    
    def register_routes(self, app):
        if self._api_bp:
            app.register_blueprint(self._api_bp)
    
    def register_rules(self):
        pass
    
    def register_events(self):
        pass
    
    def get_api_bp(self):
        return self._api_bp
    
    def get_dashboard_widgets(self):
        return []
    
    def get_report_templates(self):
        return []
    
    def create_api_bp(self, name=None):
        bp_name = name or self.PLUGIN_CODE
        self._api_bp = Blueprint(bp_name, __name__, url_prefix=f'/api/{bp_name}')
        return self._api_bp