"""
续费提醒通知服务
支持邮件和短信通知
"""
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from models.user_models import License, User
import logging

logger = logging.getLogger(__name__)


class RenewalNotificationService:
    """续费提醒通知服务类"""
    
    @staticmethod
    def get_expiring_licenses(db: Session, days_before: int = 7) -> List[Dict]:
        """
        获取即将过期的授权码列表
        :param db: 数据库会话
        :param days_before: 提前多少天提醒
        :return: 即将过期的授权码列表
        """
        now = datetime.now()
        expiry_date = now + timedelta(days=days_before)
        
        # 查询即将过期且未启用自动续费的授权码
        expiring_licenses = db.query(License).join(User).filter(
            License.is_active == True,
            License.is_revoked == False,
            License.auto_renew == False,
            License.expires_at <= expiry_date,
            License.expires_at > now,
            User.is_active == True
        ).all()
        
        result = []
        for lic in expiring_licenses:
            days_remaining = (lic.expires_at - now).days
            result.append({
                'license': lic,
                'user': lic.user,
                'days_remaining': days_remaining
            })
        
        return result
    
    @staticmethod
    def send_email_notification(user: User, license: License, days_remaining: int) -> bool:
        """
        发送邮件提醒
        :param user: 用户对象
        :param license: 授权码对象
        :param days_remaining: 剩余天数
        :return: 是否发送成功
        """
        try:
            # TODO: 集成实际的邮件发送服务
            subject = f"【续费提醒】您的授权码将在{days_remaining}天后过期"
            
            body = f"""
尊敬的用户 {user.username or user.email}：

您的授权码 {license.license_code} 将在 {days_remaining} 天后过期（{license.expires_at.strftime('%Y-%m-%d')}）。

为避免服务中断，请及时续费。您可以：
1. 登录用户控制台进行手动续费
2. 启用自动续费功能，系统将自动为您续费

登录地址：https://your-domain.com/user-portal

如有问题，请联系客服。

此致
敬礼
            """
            
            logger.info(f"邮件提醒已准备: 用户={user.email}, 授权码={license.license_code}, 剩余{days_remaining}天")
            logger.debug(f"邮件主题: {subject}")
            logger.debug(f"邮件内容: {body}")
            
            # 实际实现时调用邮件发送API
            # from utils.email_utils import send_email
            # return send_email(user.email, subject, body)
            
            return True
            
        except Exception as e:
            logger.error(f"发送邮件提醒失败: {str(e)}")
            return False
    
    @staticmethod
    def send_sms_notification(user: User, license: License, days_remaining: int) -> bool:
        """
        发送短信提醒
        :param user: 用户对象
        :param license: 授权码对象
        :param days_remaining: 剩余天数
        :return: 是否发送成功
        """
        try:
            if not user.phone:
                logger.warning(f"用户 {user.id} 没有手机号码，无法发送短信")
                return False
            
            # TODO: 集成实际的短信发送服务
            message = f"【续费提醒】您的授权码{license.license_code[-8:]}将在{days_remaining}天后过期，请及时续费或启用自动续费。"
            
            logger.info(f"短信提醒已准备: 用户={user.phone}, 授权码={license.license_code}, 剩余{days_remaining}天")
            logger.debug(f"短信内容: {message}")
            
            # 实际实现时调用短信API
            # from utils.sms_utils import send_sms
            # return send_sms(user.phone, message)
            
            return True
            
        except Exception as e:
            logger.error(f"发送短信提醒失败: {str(e)}")
            return False
    
    @staticmethod
    def process_renewal_notifications(db: Session) -> Dict:
        """
        处理续费提醒通知
        这个方法应该被定时任务调用
        """
        try:
            # 检查不同时间点的提醒
            notification_schedule = [
                {'days': 30, 'type': 'early'},    # 提前30天
                {'days': 14, 'type': 'medium'},   # 提前14天
                {'days': 7, 'type': 'urgent'},    # 提前7天
                {'days': 3, 'type': 'critical'}   # 提前3天
            ]
            
            total_sent = 0
            email_sent = 0
            sms_sent = 0
            errors = []
            
            for schedule in notification_schedule:
                days_before = schedule['days']
                expiring = RenewalNotificationService.get_expiring_licenses(db, days_before)
                
                for item in expiring:
                    license_obj = item['license']
                    user = item['user']
                    days_remaining = item['days_remaining']
                    
                    # 发送邮件
                    if user.email:
                        email_success = RenewalNotificationService.send_email_notification(
                            user, license_obj, days_remaining
                        )
                        if email_success:
                            email_sent += 1
                        else:
                            errors.append(f"邮件发送失败: 用户={user.email}, 授权码={license_obj.license_code}")
                    
                    # 发送短信（如果有手机号）
                    if user.phone:
                        sms_success = RenewalNotificationService.send_sms_notification(
                            user, license_obj, days_remaining
                        )
                        if sms_success:
                            sms_sent += 1
                        else:
                            errors.append(f"短信发送失败: 用户={user.phone}, 授权码={license_obj.license_code}")
                    
                    total_sent += 1
                    
                    logger.info(f"续费提醒已发送: 授权码={license_obj.license_code}, "
                              f"用户={user.email}, 剩余{days_remaining}天")
            
            return {
                'success': True,
                'total_notifications': total_sent,
                'email_sent': email_sent,
                'sms_sent': sms_sent,
                'errors': errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"续费提醒处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def send_auto_renew_success_notification(user: User, license: License, 
                                            new_expiry: datetime, amount: float) -> bool:
        """
        发送自动续费成功通知
        :param user: 用户对象
        :param license: 授权码对象
        :param new_expiry: 新过期时间
        :param amount: 续费金额
        :return: 是否发送成功
        """
        try:
            subject = f"【续费成功】授权码 {license.license_code} 已自动续费"
            
            body = f"""
尊敬的用户 {user.username or user.email}：

您的授权码 {license.license_code} 已成功自动续费。

续费详情：
- 授权码：{license.license_code}
- 新过期时间：{new_expiry.strftime('%Y-%m-%d')}
- 续费金额：¥{amount:.2f}

如需取消自动续费，请登录用户控制台进行操作。

登录地址：https://your-domain.com/user-portal

此致
敬礼
            """
            
            logger.info(f"自动续费成功通知已发送: 用户={user.email}, 授权码={license.license_code}")
            
            # 实际实现时调用邮件发送API
            # from utils.email_utils import send_email
            # return send_email(user.email, subject, body)
            
            return True
            
        except Exception as e:
            logger.error(f"发送自动续费成功通知失败: {str(e)}")
            return False
