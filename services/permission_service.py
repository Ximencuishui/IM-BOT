"""
插件权限控制服务
提供权限声明、权限检查、权限授权等功能
"""
import json
import logging
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from database.db_config import get_db_session

logger = logging.getLogger(__name__)

from models.plugin_models import PluginPackage, PluginVersion, PluginInstallation


class PermissionService:
    """权限控制服务"""

    ALL_PERMISSIONS = {
        'all': '全部权限',
        'order_manage': '订单管理',
        'customer_manage': '客户管理',
        'supplier_manage': '供应商管理',
        'product_manage': '商品管理',
        'report_view': '报表查看',
        'report_export': '报表导出',
        'email_send': '邮件发送',
        'message_read': '消息读取',
        'message_send': '消息发送',
        'promotion_manage': '促销管理',
        'course_manage': '课程管理',
        'student_manage': '学员管理',
        'teacher_manage': '教师管理',
        'property_manage': '房源管理',
        'matching': '智能匹配',
        'route_manage': '线路管理',
        'group_config': '群配置',
        'registration': '报名管理',
        'auto_reply': '自动回复',
        'worker_manage': '工人管理',
        'schedule_manage': '工期管理',
        'safety_check': '安全检查',
        'material_manage': '材料管理',
        'system_config': '系统配置',
        'plugin_manage': '插件管理',
        'audit_view': '审计查看'
    }

    @staticmethod
    def get_all_permissions() -> Dict[str, str]:
        """获取所有可用权限列表"""
        return PermissionService.ALL_PERMISSIONS

    @staticmethod
    def get_permission_groups() -> List[Dict]:
        """获取权限分组"""
        groups = [
            {
                'name': '订单相关',
                'permissions': ['order_manage', 'customer_manage', 'supplier_manage']
            },
            {
                'name': '商品相关',
                'permissions': ['product_manage', 'promotion_manage']
            },
            {
                'name': '报表相关',
                'permissions': ['report_view', 'report_export', 'email_send']
            },
            {
                'name': '消息相关',
                'permissions': ['message_read', 'message_send', 'auto_reply']
            },
            {
                'name': '教育相关',
                'permissions': ['course_manage', 'student_manage', 'teacher_manage']
            },
            {
                'name': '房产相关',
                'permissions': ['property_manage', 'matching']
            },
            {
                'name': '旅游相关',
                'permissions': ['route_manage', 'group_config', 'registration']
            },
            {
                'name': '工地相关',
                'permissions': ['worker_manage', 'schedule_manage', 'safety_check', 'material_manage']
            },
            {
                'name': '系统相关',
                'permissions': ['system_config', 'plugin_manage', 'audit_view']
            }
        ]
        return groups

    @staticmethod
    def parse_permissions(permission_str: str) -> Set[str]:
        """解析权限字符串为权限集合"""
        if not permission_str:
            return set()
        permissions = permission_str.split(',')
        return {p.strip() for p in permissions if p.strip()}

    @staticmethod
    def check_plugin_permissions(db: Session, user_id: int, plugin_id: int) -> Dict:
        """
        检查用户是否有安装插件所需的权限
        """
        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if not package:
            return {'success': False, 'error': '插件不存在'}

        latest_version = db.query(PluginVersion).filter(
            PluginVersion.package_id == plugin_id,
            PluginVersion.is_stable == True,
            PluginVersion.is_active == True
        ).order_by(PluginVersion.version.desc()).first()

        if not latest_version:
            return {'success': False, 'error': '没有可用版本'}

        required_permissions = PermissionService.parse_permissions(
            latest_version.required_permissions
        )

        if 'all' in required_permissions:
            return {'success': True, 'has_permission': True, 'missing_permissions': []}

        user_permissions = PermissionService.get_user_permissions(db, user_id)

        missing_permissions = required_permissions - user_permissions

        return {
            'success': True,
            'has_permission': len(missing_permissions) == 0,
            'required_permissions': list(required_permissions),
            'missing_permissions': list(missing_permissions),
            'plugin_name': package.plugin_name
        }

    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> Set[str]:
        """
        获取用户已拥有的所有权限
        通过已安装的插件权限聚合
        """
        permissions = set()

        installations = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id,
            PluginInstallation.status == 'installed'
        ).options(
            PluginInstallation.package
        ).all()

        for install in installations:
            if install.package:
                latest_version = db.query(PluginVersion).filter(
                    PluginVersion.package_id == install.package_id,
                    PluginVersion.is_stable == True,
                    PluginVersion.is_active == True
                ).order_by(PluginVersion.version.desc()).first()

                if latest_version and latest_version.required_permissions:
                    plugin_perms = PermissionService.parse_permissions(
                        latest_version.required_permissions
                    )
                    permissions.update(plugin_perms)

        return permissions

    @staticmethod
    def grant_permissions_to_user(db: Session, user_id: int, permissions: List[str]) -> Dict:
        """
        授予用户权限（通过安装虚拟插件实现）
        """
        from models.user_models import User

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'success': False, 'error': '用户不存在'}

        permission_str = ','.join(permissions)

        existing_virtual = db.query(PluginPackage).filter(
            PluginPackage.plugin_code == f'virtual_perms_{user_id}'
        ).first()

        if existing_virtual:
            existing_version = db.query(PluginVersion).filter(
                PluginVersion.package_id == existing_virtual.id
            ).first()
            if existing_version:
                existing_version.required_permissions = permission_str
                db.commit()
            return {'success': True, 'message': '权限已更新'}
        else:
            virtual_plugin = PluginPackage(
                plugin_code=f'virtual_perms_{user_id}',
                plugin_name=f'{user.username}权限扩展',
                description=f'{user.username}的额外权限',
                category='virtual',
                industry='',
                is_public=False,
                is_active=True,
                is_deprecated=False
            )
            db.add(virtual_plugin)
            db.commit()
            db.refresh(virtual_plugin)

            virtual_version = PluginVersion(
                package_id=virtual_plugin.id,
                version='1.0.0',
                required_permissions=permission_str,
                is_stable=True,
                is_active=True
            )
            db.add(virtual_version)
            db.commit()
            db.refresh(virtual_version)

            installation = PluginInstallation(
                user_id=user_id,
                package_id=virtual_plugin.id,
                version_id=virtual_version.id,
                installed_version='1.0.0',
                status='installed',
                installed_path=f'virtual/perms_{user_id}',
                config='{}'
            )
            db.add(installation)
            db.commit()

            return {'success': True, 'message': '权限已授予'}

    @staticmethod
    def get_plugin_required_permissions(db: Session, plugin_code: str) -> List[Dict]:
        """
        获取插件所需的权限列表（含描述）
        """
        package = db.query(PluginPackage).filter(
            PluginPackage.plugin_code == plugin_code
        ).first()

        if not package:
            return []

        latest_version = db.query(PluginVersion).filter(
            PluginVersion.package_id == package.id,
            PluginVersion.is_stable == True,
            PluginVersion.is_active == True
        ).order_by(PluginVersion.version.desc()).first()

        if not latest_version:
            return []

        perms = PermissionService.parse_permissions(latest_version.required_permissions)

        result = []
        for perm in perms:
            result.append({
                'code': perm,
                'name': PermissionService.ALL_PERMISSIONS.get(perm, perm)
            })

        return result

    @staticmethod
    def can_access_feature(db: Session, user_id: int, feature_code: str) -> bool:
        """
        检查用户是否有权限访问特定功能
        """
        user_permissions = PermissionService.get_user_permissions(db, user_id)
        return feature_code in user_permissions or 'all' in user_permissions


permission_service = PermissionService()