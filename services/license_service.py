"""
授权验证服务
- 授权码激活
- 本地验证
- 云端同步
- 到期检查
"""
import hashlib
import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict

from sqlalchemy.orm import Session
from models.license_model import LegacyLicense as License
from database.db_config import SessionLocal
from config.settings import settings

logger = logging.getLogger(__name__)


class LicenseService:
    """授权服务"""

    # 云端授权API地址(可配置)
    LICENSE_API_BASE = getattr(settings, 'LICENSE_API_BASE', 'https://api.fooddelivery.com')

    def __init__(self):
        self.db_session = None
        self._machine_id = self._get_machine_id()

    def _get_db(self) -> Session:
        if self.db_session is None:
            self.db_session = SessionLocal()
        return self.db_session

    def close(self):
        if self.db_session:
            self.db_session.close()
            self.db_session = None

    def _get_machine_id(self) -> str:
        """获取机器指纹(用于绑定设备)"""
        try:
            import platform
            import hashlib
            
            # 收集机器信息生成唯一ID
            info = {
                'node': platform.node(),
                'platform': platform.platform(),
                'machine': platform.machine(),
                'processor': platform.processor(),
            }
            raw = json.dumps(info, sort_keys=True)
            return hashlib.sha256(raw.encode()).hexdigest()[:32]
        except Exception as e:
            logger.warning(f"获取机器指纹失败: {e}")
            return str(uuid.uuid4()).replace('-', '')[:32]

    @property
    def machine_id(self):
        return self._machine_id

    def activate_license(self, license_code: str, bound_to: str = None) -> Dict:
        """
        激活授权码

        Args:
            license_code: 授权码
            bound_to: 绑定对象(微信群ID或销售员ID)

        Returns:
            激活结果
        """
        db = self._get_db()

        try:
            # 检查授权码是否已存在
            existing = db.query(License).filter(License.license_code == license_code).first()
            if existing:
                if existing.is_revoked:
                    return {'success': False, 'error': '授权码已被撤销'}
                if existing.is_active:
                    return {'success': False, 'error': '授权码已激活', 'license': existing.to_dict()}

            # 从云端验证授权码
            cloud_result = self._verify_with_cloud(license_code)
            if not cloud_result.get('valid'):
                return {'success': False, 'error': cloud_result.get('error', '授权码无效')}

            # 计算有效期
            license_type = cloud_result.get('type', 'monthly')
            now = datetime.now()
            if license_type == 'yearly':
                expires_at = now + timedelta(days=365)
            else:
                expires_at = now + timedelta(days=30)

            # 创建或更新授权记录
            if existing:
                license_obj = existing
                license_obj.is_active = True
                license_obj.is_expired = False
                license_obj.activated_at = now
                license_obj.expires_at = expires_at
                license_obj.bound_to = bound_to or existing.bound_to
                license_obj.machine_id = self._machine_id
                license_obj.license_type = license_type
            else:
                license_obj = License(
                    license_code=license_code,
                    license_type=license_type,
                    bound_to=bound_to,
                    machine_id=self._machine_id,
                    activated_at=now,
                    expires_at=expires_at,
                    is_active=True,
                    is_expired=False,
                    sync_status='synced'
                )
                db.add(license_obj)

            db.commit()
            db.refresh(license_obj)

            logger.info(f"授权码激活成功: {license_code[:8]}...")

            return {
                'success': True,
                'license': license_obj.to_dict(),
                'message': f'授权激活成功,有效期至 {expires_at.strftime("%Y-%m-%d")}'
            }

        except Exception as e:
            db.rollback()
            logger.error(f"激活授权码失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def check_license(self, bound_to: str = None) -> Dict:
        """
        检查授权状态

        Args:
            bound_to: 检查特定绑定对象的授权

        Returns:
            授权状态
        """
        db = self._get_db()

        try:
            query = db.query(License).filter(
                License.is_active == True,
                License.is_revoked == False
            )

            if bound_to:
                query = query.filter(License.bound_to == bound_to)

            licenses = query.all()

            if not licenses:
                return {
                    'has_valid_license': False,
                    'message': '未找到有效授权',
                    'licenses': []
                }

            # 检查过期状态
            active_licenses = []
            expired_count = 0
            expiring_soon = []

            for lic in licenses:
                lic.check_expiry()
                if lic.is_expired:
                    expired_count += 1
                else:
                    active_licenses.append(lic.to_dict())
                    if lic.days_remaining <= 7:
                        expiring_soon.append({
                            'license_code': lic.license_code[:8] + '...',
                            'days_remaining': lic.days_remaining
                        })

            # 更新数据库
            db.commit()

            return {
                'has_valid_license': len(active_licenses) > 0,
                'active_count': len(active_licenses),
                'expired_count': expired_count,
                'expiring_soon': expiring_soon,
                'licenses': active_licenses,
                'machine_id': self._machine_id
            }

        except Exception as e:
            logger.error(f"检查授权状态失败: {e}", exc_info=True)
            return {
                'has_valid_license': False,
                'error': str(e)
            }

    def renew_license(self, license_code: str) -> Dict:
        """
        续期授权

        Args:
            license_code: 授权码

        Returns:
            续期结果
        """
        db = self._get_db()

        try:
            license_obj = db.query(License).filter(License.license_code == license_code).first()
            if not license_obj:
                return {'success': False, 'error': '授权码不存在'}

            if license_obj.is_revoked:
                return {'success': False, 'error': '授权码已被撤销'}

            # 从云端获取续期信息
            cloud_result = self._verify_with_cloud(license_code, renew=True)
            if not cloud_result.get('valid'):
                return {'success': False, 'error': cloud_result.get('error', '续期失败')}

            # 延长有效期
            license_type = license_obj.license_type
            if license_obj.expires_at and license_obj.expires_at > datetime.now():
                # 从当前过期时间延长
                base_date = license_obj.expires_at
            else:
                # 从当前时间开始
                base_date = datetime.now()

            if license_type == 'yearly':
                new_expires = base_date + timedelta(days=365)
            else:
                new_expires = base_date + timedelta(days=30)

            license_obj.expires_at = new_expires
            license_obj.is_expired = False
            license_obj.is_active = True
            license_obj.last_sync_at = datetime.now()
            license_obj.sync_status = 'synced'

            db.commit()

            logger.info(f"授权续期成功: {license_code[:8]}..., 新有效期: {new_expires}")

            return {
                'success': True,
                'new_expires_at': new_expires.isoformat(),
                'message': f'续期成功,有效期至 {new_expires.strftime("%Y-%m-%d")}'
            }

        except Exception as e:
            db.rollback()
            logger.error(f"授权续期失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def revoke_license(self, license_code: str) -> Dict:
        """撤销授权"""
        db = self._get_db()

        try:
            license_obj = db.query(License).filter(License.license_code == license_code).first()
            if not license_obj:
                return {'success': False, 'error': '授权码不存在'}

            license_obj.is_revoked = True
            license_obj.is_active = False
            db.commit()

            logger.info(f"授权已撤销: {license_code[:8]}...")
            return {'success': True, 'message': '授权已撤销'}

        except Exception as e:
            db.rollback()
            logger.error(f"撤销授权失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_active_groups_count(self) -> int:
        """获取当前授权的群数量"""
        db = self._get_db()
        count = db.query(License).filter(
            License.is_active == True,
            License.is_expired == False,
            License.is_revoked == False,
            License.bound_to.isnot(None)
        ).count()
        return count

    def can_add_group(self) -> bool:
        """检查是否可以添加新群(至少有一个有效授权)"""
        db = self._get_db()
        count = db.query(License).filter(
            License.is_active == True,
            License.is_expired == False,
            License.is_revoked == False
        ).count()
        return count > 0

    def _verify_with_cloud(self, license_code: str, renew: bool = False) -> Dict:
        """
        与云端API验证授权码

        注意: 实际部署时需要实现真实的HTTP请求
        这里提供模拟实现供测试
        """
        try:
            import urllib.request
            import urllib.error

            endpoint = '/api/license/verify' if not renew else '/api/license/renew'
            url = f"{self.LICENSE_API_BASE}{endpoint}"

            data = json.dumps({
                'license_code': license_code,
                'machine_id': self._machine_id
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result

        except Exception as e:
            logger.warning(f"云端验证失败: {e}")
            # 离线模式: 如果本地已有记录,允许使用
            return self._offline_verify(license_code)

    def _offline_verify(self, license_code: str) -> Dict:
        """离线验证(仅检查本地记录)"""
        db = self._get_db()
        license_obj = db.query(License).filter(License.license_code == license_code).first()

        if license_obj and license_obj.is_active and not license_obj.is_revoked:
            return {
                'valid': True,
                'type': license_obj.license_type
            }

        return {
            'valid': False,
            'error': '无法连接云端服务,且本地无有效授权记录'
        }


# 全局单例
license_service = LicenseService()
