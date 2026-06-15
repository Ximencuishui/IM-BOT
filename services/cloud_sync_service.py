"""
云端规则同步服务
实现桌面端与云端规则库的下载/上传同步功能
"""
import json
import requests
from typing import Dict, List, Optional
from config.settings import settings


class CloudSyncService:
    """云端规则同步服务"""

    def __init__(self, cloud_url: str = None, token: str = None):
        self.cloud_url = cloud_url or settings.CLOUD_API_URL or "http://localhost:5000"
        self.token = token
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def set_token(self, token: str):
        """设置认证令牌"""
        self.token = token
        self.session.headers.update({'Authorization': f'Bearer {token}'})

    # ==================== 规则模板浏览 ====================

    def get_industries(self) -> List[str]:
        """获取所有行业分类"""
        try:
            resp = self.session.get(f"{self.cloud_url}/api/rule-templates/industries", timeout=10)
            if resp.status_code == 200:
                return resp.json().get('industries', [])
        except Exception as e:
            print(f"获取行业分类失败: {e}")
        return []

    def list_templates(self, industry: str = None, featured_only: bool = False) -> List[Dict]:
        """
        获取规则模板列表
        :param industry: 行业筛选
        :param featured_only: 仅精选
        :return: 模板列表
        """
        try:
            params = {}
            if industry:
                params['industry'] = industry
            if featured_only:
                params['featured_only'] = 'true'

            resp = self.session.get(f"{self.cloud_url}/api/rule-templates/", params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json().get('templates', [])
        except Exception as e:
            print(f"获取模板列表失败: {e}")
        return []

    def get_template_detail(self, template_id: int) -> Optional[Dict]:
        """获取模板详情"""
        try:
            resp = self.session.get(f"{self.cloud_url}/api/rule-templates/{template_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json().get('template')
        except Exception as e:
            print(f"获取模板详情失败: {e}")
        return None

    def download_template(self, template_id: int) -> Optional[Dict]:
        """
        下载模板规则（包含完整规则内容）
        :return: 完整的规则数据
        """
        try:
            resp = self.session.post(
                f"{self.cloud_url}/api/rule-templates/{template_id}/download",
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get('template')
        except Exception as e:
            print(f"下载模板失败: {e}")
        return None

    # ==================== 用户规则备份 ====================

    def upload_backup(self, backup_data: Dict) -> bool:
        """
        上传规则备份到云端
        :param backup_data: {
            "backup_name": "备份名称",
            "parse_rules": [...],
            "stat_rules": [...],
            "reply_rules": [...],
            "template_id": 1,  # 可选
            "version": "1.0"
        }
        :return: 是否成功
        """
        if not self.token:
            print("未登录，请先设置认证令牌")
            return False

        try:
            resp = self.session.post(
                f"{self.cloud_url}/api/rule-templates/backups",
                json=backup_data,
                timeout=10
            )
            if resp.status_code in [200, 201]:
                return True
            else:
                print(f"上传失败: {resp.json().get('error', '未知错误')}")
        except Exception as e:
            print(f"上传备份失败: {e}")
        return False

    def get_backups(self) -> List[Dict]:
        """获取用户的云端备份列表"""
        if not self.token:
            return []

        try:
            resp = self.session.get(f"{self.cloud_url}/api/rule-templates/backups", timeout=10)
            if resp.status_code == 200:
                return resp.json().get('backups', [])
        except Exception as e:
            print(f"获取备份列表失败: {e}")
        return []

    def restore_backup(self, backup_id: int) -> Optional[Dict]:
        """
        从云端恢复指定备份
        :return: 备份的规则数据
        """
        backups = self.get_backups()
        for backup in backups:
            if backup['id'] == backup_id:
                return {
                    'parse_rules': backup.get('parse_rules', []),
                    'stat_rules': backup.get('stat_rules', []),
                    'reply_rules': backup.get('reply_rules', [])
                }
        return None

    # ==================== 规则应用 ====================

    @staticmethod
    def apply_parse_rules(parse_rules: List[Dict], local_service) -> Dict:
        """
        应用解析规则到本地服务
        :param parse_rules: 云端下载的解析规则列表
        :param local_service: 本地解析服务对象
        :return: 应用结果
        """
        success_count = 0
        for rule_data in parse_rules:
            try:
                # 这里需要根据实际本地解析服务的API来适配
                # 示例：假设本地服务有add_rule方法
                if hasattr(local_service, 'add_rule'):
                    local_service.add_rule(rule_data)
                    success_count += 1
            except Exception as e:
                print(f"应用解析规则失败 [{rule_data.get('rule_name')}]: {e}")

        return {'success': success_count, 'total': len(parse_rules)}

    @staticmethod
    def collect_local_rules(local_services: Dict) -> Dict:
        """
        收集本地规则用于上传备份
        :param local_services: {
            "parse_rules": [...],
            "stat_rules": [...],
            "reply_rules": [...]
        }
        :return: 规则数据字典
        """
        return {
            'parse_rules': local_services.get('parse_rules', []),
            'stat_rules': local_services.get('stat_rules', []),
            'reply_rules': local_services.get('reply_rules', [])
        }
