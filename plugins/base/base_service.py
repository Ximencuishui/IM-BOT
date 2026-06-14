"""
服务基类 - 所有行业插件服务必须继承此类
"""


class BaseService:
    """服务基类"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def parse_message(self, message_text):
        return {}
    
    def process_message(self, message_data):
        return {}
    
    def generate_report(self, report_type, date_range):
        return {}
    
    def get_stats(self, period):
        return {}