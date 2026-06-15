"""
授权码管理服务 v2
提供授权码生成、分配、查询、续期等功能
"""
import secrets
import string
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models.user_models import User, License, TeamMember

# 授权码字符集配置（排除易混淆字符）
_LICENSE_CODE_EXCLUDE = {'0', 'O', '1', 'I', 'L'}
_LICENSE_CODE_CHARS = string.ascii_uppercase + string.digits
LICENSE_CODE_CHARS = ''.join(c for c in _LICENSE_CODE_CHARS if c not in _LICENSE_CODE_EXCLUDE)
LICENSE_CODE_LENGTH = 16


class LicenseServiceV2:
    """授权码服务类"""

    @staticmethod
    def generate_license_code() -> str:
        """生成随机授权码"""
        return ''.join(secrets.choice(LICENSE_CODE_CHARS)
                       for _ in range(LICENSE_CODE_LENGTH))

    @staticmethod
    def create_license(db: Session, user_id: int, license_type: str = 'monthly',
                       bound_to: str = None) -> Dict:
        """
        创建新的授权码
        :param db: 数据库会话
        :param user_id: 用户ID
        :param license_type: 授权类型 monthly/yearly
        :param bound_to: 绑定的群ID（可选）
        :return: 创建结果
        """
        # 检查用户是否存在
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'success': False, 'error': '用户不存在'}

        # 检查用户是否有可用名额
        if user.available_groups <= 0:
            return {'success': False, 'error': f'已达到最大群数量限制({user.max_groups}个)'}

        # 生成唯一授权码
        while True:
            code = LicenseServiceV2.generate_license_code()
            existing = db.query(License).filter(License.license_code == code).first()
            if not existing:
                break

        # 计算有效期
        now = datetime.now()
        if license_type == 'yearly':
            expires_at = now + timedelta(days=365)
        else:  # monthly
            expires_at = now + timedelta(days=30)

        # 创建授权记录
        new_license = License(
            user_id=user_id,
            license_code=code,
            license_type=license_type,
            bound_to=bound_to,
            is_active=False,  # 需要激活后才生效
            expires_at=expires_at
        )

        db.add(new_license)
        db.commit()
        db.refresh(new_license)

        return {
            'success': True,
            'license': new_license.to_dict()
        }

    @staticmethod
    def activate_license(db: Session, license_code: str, machine_id: str = None,
                         bound_to: str = None) -> Dict:
        """
        激活授权码
        :param db: 数据库会话
        :param license_code: 授权码
        :param machine_id: 机器指纹
        :param bound_to: 绑定的群ID
        :return: 激活结果
        """
        # 查找授权码
        license_obj = db.query(License).filter(License.license_code == license_code).first()
        if not license_obj:
            return {'success': False, 'error': '授权码不存在'}

        # 检查是否已撤销
        if license_obj.is_revoked:
            return {'success': False, 'error': '授权码已被撤销'}

        # 检查是否已激活
        if license_obj.is_active:
            return {'success': False, 'error': '授权码已激活'}

        # 检查是否过期
        if license_obj.expires_at and datetime.now() > license_obj.expires_at:
            return {'success': False, 'error': '授权码已过期'}

        # 激活授权
        license_obj.is_active = True
        license_obj.activated_at = datetime.now()
        if machine_id:
            license_obj.machine_id = machine_id
        if bound_to:
            license_obj.bound_to = bound_to

        db.commit()
        db.refresh(license_obj)

        return {
            'success': True,
            'license': license_obj.to_dict()
        }

    @staticmethod
    def revoke_license(db: Session, license_id: int, user_id: int) -> Dict:
        """
        撤销授权码
        :param db: 数据库会话
        :param license_id: 授权ID
        :param user_id: 用户ID（用于权限验证）
        :return: 撤销结果
        """
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == user_id
        ).first()

        if not license_obj:
            return {'success': False, 'error': '授权不存在或无权操作'}

        if license_obj.is_revoked:
            return {'success': False, 'error': '授权已被撤销'}

        license_obj.is_active = False
        license_obj.is_revoked = True
        db.commit()

        return {'success': True, 'message': '授权已撤销'}

    @staticmethod
    def renew_license(db: Session, license_id: int, user_id: int,
                      extend_days: int = None) -> Dict:
        """
        续期授权
        :param db: 数据库会话
        :param license_id: 授权ID
        :param user_id: 用户ID
        :param extend_days: 延长天数（默认根据授权类型）
        :return: 续期结果
        """
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == user_id
        ).first()

        if not license_obj:
            return {'success': False, 'error': '授权不存在或无权操作'}

        if license_obj.is_revoked:
            return {'success': False, 'error': '授权已被撤销，无法续期'}

        # 计算延长时间
        if extend_days is None:
            extend_days = 30 if license_obj.license_type == 'monthly' else 365

        # 如果已过期，从当前时间开始计算；否则从过期时间延长
        base_time = datetime.now() if not license_obj.expires_at or \
                                    datetime.now() > license_obj.expires_at \
                    else license_obj.expires_at

        license_obj.expires_at = base_time + timedelta(days=extend_days)
        license_obj.is_active = True
        license_obj.is_revoked = False

        db.commit()
        db.refresh(license_obj)

        return {
            'success': True,
            'license': license_obj.to_dict()
        }

    @staticmethod
    def extend_license_by_months(db: Session, license_id: int, user_id: int,
                                  months: int) -> Dict:
        """
        按月展期授权
        :param db: 数据库会话
        :param license_id: 授权ID
        :param user_id: 用户ID
        :param months: 展期月数 (1, 3, 6, 12)
        :return: 展期结果
        """
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == user_id
        ).first()

        if not license_obj:
            return {'success': False, 'error': '授权不存在或无权操作'}

        if license_obj.is_revoked:
            return {'success': False, 'error': '授权已被撤销，无法展期'}

        # 计算延长时间（按月）
        base_time = datetime.now() if not license_obj.expires_at or \
                                    datetime.now() > license_obj.expires_at \
                    else license_obj.expires_at

        license_obj.expires_at = base_time + relativedelta(months=months)
        license_obj.is_active = True
        license_obj.is_revoked = False

        db.commit()
        db.refresh(license_obj)

        # 计算折扣
        discounts = {1: 1.0, 3: 0.95, 6: 0.9, 12: 0.8}
        discount = discounts.get(months, 1.0)
        base_price = 100  # 基础价格：100元/月
        total_price = base_price * months * discount

        return {
            'success': True,
            'message': f'展期{months}个月成功',
            'license': license_obj.to_dict(),
            'price': total_price,
            'discount': discount
        }

    @staticmethod
    def toggle_auto_renew(db: Session, license_id: int, user_id: int,
                          auto_renew: bool) -> Dict:
        """
        切换自动续费
        :param db: 数据库会话
        :param license_id: 授权ID
        :param user_id: 用户ID
        :param auto_renew: 是否启用自动续费
        :return: 操作结果
        """
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == user_id
        ).first()

        if not license_obj:
            return {'success': False, 'error': '授权不存在或无权操作'}

        license_obj.auto_renew = auto_renew
        db.commit()

        return {
            'success': True,
            'message': f'已{"启用" if auto_renew else "禁用"}自动续费'
        }

    @staticmethod
    def assign_to_team_member(db: Session, license_id: int, user_id: int,
                               member_id: int) -> Dict:
        """
        将授权分配给团队成员
        :param db: 数据库会话
        :param license_id: 授权ID
        :param user_id: 用户ID
        :param member_id: 团队成员ID
        :return: 分配结果
        """
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == user_id
        ).first()

        if not license_obj:
            return {'success': False, 'error': '授权不存在或无权操作'}

        # 验证团队成员归属
        member = db.query(TeamMember).filter(
            TeamMember.id == member_id,
            TeamMember.user_id == user_id
        ).first()

        if not member:
            return {'success': False, 'error': '团队成员不存在'}

        license_obj.assigned_to = member_id
        db.commit()

        return {'success': True, 'message': '分配成功'}

    @staticmethod
    def get_user_licenses(db: Session, user_id: int,
                          active_only: bool = False) -> List[Dict]:
        """
        获取用户的授权列表
        :param db: 数据库会话
        :param user_id: 用户ID
        :param active_only: 是否只返回活跃的
        :return: 授权列表
        """
        query = db.query(License).filter(License.user_id == user_id)

        if active_only:
            query = query.filter(
                License.is_active == True,
                License.is_revoked == False
            )

        licenses = query.order_by(License.created_at.desc()).all()
        return [lic.to_dict() for lic in licenses]

    @staticmethod
    def get_license_stats(db: Session, user_id: int) -> Dict:
        """
        获取用户授权统计
        :param db: 数据库会话
        :param user_id: 用户ID
        :return: 统计数据
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'error': '用户不存在'}

        all_licenses = db.query(License).filter(License.user_id == user_id).all()

        active_count = len([lic for lic in all_licenses
                           if lic.is_active and not lic.is_revoked])
        revoked_count = len([lic for lic in all_licenses if lic.is_revoked])
        expired_count = len([lic for lic in all_licenses
                            if not lic.is_revoked and lic.expires_at and
                            datetime.now() > lic.expires_at])

        return {
            'max_groups': user.max_groups,
            'used_groups': active_count,
            'available_groups': user.available_groups,
            'active_count': active_count,
            'revoked_count': revoked_count,
            'expired_count': expired_count,
            'total_count': len(all_licenses),
            'subscription_valid': user.is_subscription_valid,
            'subscription_expires_at': user.subscription_expires_at.isoformat() \
                if user.subscription_expires_at else None
        }
