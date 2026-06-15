"""
自动续费服务
处理授权码的自动续费逻辑
"""
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from models.user_models import License, PricingConfig, RenewalHistory
import logging

logger = logging.getLogger(__name__)


class AutoRenewService:
    """自动续费服务类"""
    
    @staticmethod
    def get_renew_period_days(period: str) -> int:
        """根据续费周期获取天数"""
        period_map = {
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365
        }
        return period_map.get(period, 30)
    
    @staticmethod
    def calculate_renew_price(db: Session, license_count: int, period: str) -> Dict:
        """计算续费价格"""
        # 获取基础价格
        base_price_config = db.query(PricingConfig).filter(
            PricingConfig.config_key == 'license_monthly_price'
        ).first()
        base_price = float(base_price_config.config_value) if base_price_config else 100.0
        
        # 折扣映射
        discount_map = {
            '1m': {'months': 1, 'discount': 1.0},
            '3m': {'months': 3, 'discount': 0.95},
            '6m': {'months': 6, 'discount': 0.90},
            '1y': {'months': 12, 'discount': 0.80}
        }
        
        if period not in discount_map:
            return {'success': False, 'error': '无效的续费周期'}
        
        info = discount_map[period]
        months = info['months']
        discount = info['discount']
        
        # 计算总价
        total_price = license_count * base_price * months * discount
        
        return {
            'success': True,
            'base_price': base_price,
            'months': months,
            'discount': discount,
            'total_price': round(total_price, 2)
        }
    
    @staticmethod
    def process_auto_renewals(db: Session) -> Dict:
        """
        处理所有需要自动续费的授权码
        这个方法应该被定时任务调用
        """
        try:
            # 查找所有启用自动续费且即将过期的授权码
            now = datetime.now()
            seven_days_later = now + timedelta(days=7)
            
            licenses_to_renew = db.query(License).filter(
                License.auto_renew == True,
                License.is_active == True,
                License.is_revoked == False,
                License.expires_at <= seven_days_later,
                License.expires_at > now
            ).all()
            
            renewed_count = 0
            failed_count = 0
            errors = []
            
            for license_obj in licenses_to_renew:
                try:
                    if not license_obj.renew_period:
                        errors.append(f"授权码 {license_obj.license_code} 未设置续费周期")
                        failed_count += 1
                        continue
                    
                    # 计算新的过期时间
                    days_to_add = AutoRenewService.get_renew_period_days(license_obj.renew_period)
                    old_expiry = license_obj.expires_at
                    new_expiry = old_expiry + timedelta(days=days_to_add)
                    
                    # 计算续费金额
                    price_result = AutoRenewService.calculate_renew_price(db, 1, license_obj.renew_period)
                    amount = price_result['total_price'] if price_result['success'] else 0.0
                    discount = price_result['discount'] if price_result['success'] else 1.0
                    months = price_result['months'] if price_result['success'] else 1
                    
                    # 更新授权码
                    license_obj.expires_at = new_expiry
                    license_obj.last_renewed_at = now
                    
                    # 记录续费历史
                    renewal_record = RenewalHistory(
                        user_id=license_obj.user_id,
                        license_id=license_obj.id,
                        renew_type='auto',
                        period=license_obj.renew_period,
                        months=months,
                        amount=amount,
                        discount=discount,
                        old_expiry=old_expiry,
                        new_expiry=new_expiry,
                        payment_method='auto_renew',
                        status='success',
                        paid_at=now
                    )
                    db.add(renewal_record)
                    
                    renewed_count += 1
                    logger.info(f"授权码 {license_obj.license_code} 自动续费成功，新过期时间: {new_expiry}")
                    
                    # 发送续费成功通知
                    try:
                        from services.renewal_notification_service import RenewalNotificationService
                        RenewalNotificationService.send_auto_renew_success_notification(
                            license_obj.user, license_obj, new_expiry, amount
                        )
                    except Exception as notify_err:
                        logger.warning(f"发送续费通知失败: {str(notify_err)}")
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"授权码 {license_obj.license_code} 续费失败: {str(e)}")
                    logger.error(f"授权码 {license_obj.license_code} 续费失败: {str(e)}")
            
            db.commit()
            
            return {
                'success': True,
                'renewed_count': renewed_count,
                'failed_count': failed_count,
                'errors': errors if errors else None
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"自动续费处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def enable_auto_renew(db: Session, license_id: int, user_id: int, 
                         renew_period: str = '1m') -> Dict:
        """启用自动续费"""
        try:
            license_obj = db.query(License).filter(
                License.id == license_id,
                License.user_id == user_id
            ).first()
            
            if not license_obj:
                return {'success': False, 'error': '授权码不存在或无权操作'}
            
            if license_obj.is_revoked:
                return {'success': False, 'error': '授权码已被撤销'}
            
            license_obj.auto_renew = True
            license_obj.renew_period = renew_period
            
            db.commit()
            
            return {
                'success': True,
                'message': f'已启用自动续费，周期: {renew_period}'
            }
            
        except Exception as e:
            db.rollback()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def disable_auto_renew(db: Session, license_id: int, user_id: int) -> Dict:
        """禁用自动续费"""
        try:
            license_obj = db.query(License).filter(
                License.id == license_id,
                License.user_id == user_id
            ).first()
            
            if not license_obj:
                return {'success': False, 'error': '授权码不存在或无权操作'}
            
            license_obj.auto_renew = False
            license_obj.renew_period = None
            
            db.commit()
            
            return {
                'success': True,
                'message': '已禁用自动续费'
            }
            
        except Exception as e:
            db.rollback()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_auto_renew_status(db: Session, user_id: int) -> Dict:
        """获取用户的自动续费状态统计"""
        try:
            # 统计启用自动续费的授权码
            auto_renew_licenses = db.query(License).filter(
                License.user_id == user_id,
                License.auto_renew == True,
                License.is_active == True,
                License.is_revoked == False
            ).all()
            
            # 按周期分组统计
            period_stats = {}
            for lic in auto_renew_licenses:
                period = lic.renew_period or 'unknown'
                if period not in period_stats:
                    period_stats[period] = 0
                period_stats[period] += 1
            
            return {
                'success': True,
                'total_auto_renew': len(auto_renew_licenses),
                'period_breakdown': period_stats,
                'licenses': [lic.to_dict() for lic in auto_renew_licenses]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
