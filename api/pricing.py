"""
授权码批量展期 API
支持用户端付费批量展期，含折扣逻辑
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from models.user_models import License, PricingConfig, RenewalHistory
from datetime import datetime, timedelta

pricing_bp = Blueprint('pricing', __name__, url_prefix='/api/pricing')


@pricing_bp.route('/config', methods=['GET'])
@login_required
def get_public_pricing():
    """获取公开定价配置（用户端可见）"""
    db: Session = get_db_session()
    try:
        configs = db.query(PricingConfig).all()
        pricing = {}
        for c in configs:
            pricing[c.config_key] = float(c.config_value)
        
        # 默认值
        if 'license_monthly_price' not in pricing:
            pricing['license_monthly_price'] = 100.0
        if 'app_yearly_fee' not in pricing:
            pricing['app_yearly_fee'] = 29999.0
            
        return jsonify({
            'success': True,
            'pricing': pricing
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@pricing_bp.route('/subscriptions', methods=['GET'])
@login_required
def get_user_subscriptions():
    """获取当前用户的订阅信息"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 从用户模型中获取订阅信息
        subscriptions = []
        
        # 无论是否有订阅过期时间，都返回订阅信息
        subscription_info = {
            'id': user.id,
            'plan_name': '年付套餐' if user.subscription_type == 'yearly' else '月付套餐',
            'plan_type': user.subscription_type or 'monthly',
            'price': 29999.0 if user.subscription_type == 'yearly' else 100.0,
            'start_date': user.created_at.isoformat() if user.created_at else None,
            'end_date': user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            'status': 'active' if user.is_subscription_valid else 'expired',
            'auto_renew': False,
            'max_groups': user.max_groups
        }
        subscriptions.append(subscription_info)
        
        return jsonify({
            'success': True,
            'subscriptions': subscriptions
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@pricing_bp.route('/licenses/extend', methods=['POST'])
@login_required
def batch_extend_licenses():
    """
    批量展期授权码
    Body: {
        "license_ids": [1, 2, 3],
        "period": "1m" | "3m" | "6m" | "1y",
        "enable_auto_renew": false,
        "auto_renew_period": "1m" | "3m" | "6m" | "1y"
    }
    折扣逻辑：
    - 1个月：原价
    - 3个月：95折
    - 6个月：9折
    - 1年：8折
    """
    data = request.get_json()
    if not data or not data.get('license_ids') or not data.get('period'):
        return jsonify({'success': False, 'error': '请提供授权码ID列表和展期周期'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        license_ids = data['license_ids']
        period = data['period']
        enable_auto_renew = data.get('enable_auto_renew', False)
        auto_renew_period = data.get('auto_renew_period', period)
        
        # 验证授权码是否属于当前用户
        licenses = db.query(License).filter(
            License.id.in_(license_ids),
            License.user_id == user.id
        ).all()
        
        if len(licenses) != len(license_ids):
            return jsonify({'success': False, 'error': '部分授权码不存在或无权操作'}), 400
        
        # 获取基础价格
        base_price_config = db.query(PricingConfig).filter(
            PricingConfig.config_key == 'license_monthly_price'
        ).first()
        base_price = float(base_price_config.config_value) if base_price_config else 100.0
        
        # 计算折扣和月数
        discount_map = {
            '1m': {'months': 1, 'discount': 1.0},
            '3m': {'months': 3, 'discount': 0.95},
            '6m': {'months': 6, 'discount': 0.90},
            '1y': {'months': 12, 'discount': 0.80}
        }
        
        if period not in discount_map:
            return jsonify({'success': False, 'error': '无效的展期周期'}), 400
        
        info = discount_map[period]
        months = info['months']
        discount = info['discount']
        
        # 计算总价
        total_price = len(licenses) * base_price * months * discount
        
        # 执行展期
        extended_count = 0
        for lic in licenses:
            current_expiry = lic.expires_at if lic.expires_at and lic.expires_at > datetime.now() else datetime.now()
            old_expiry = current_expiry
            new_expiry = current_expiry + timedelta(days=30 * months)
            
            lic.expires_at = new_expiry
            lic.is_active = True
            
            # 记录续费历史
            renewal_record = RenewalHistory(
                user_id=user.id,
                license_id=lic.id,
                renew_type='batch' if len(licenses) > 1 else 'manual',
                period=period,
                months=months,
                amount=round(base_price * months * discount, 2),
                discount=discount,
                old_expiry=old_expiry,
                new_expiry=new_expiry,
                payment_method='pending',  # 待支付
                status='pending'
            )
            db.add(renewal_record)
            
            # 如果启用自动续费，设置自动续费参数
            if enable_auto_renew:
                lic.auto_renew = True
                lic.renew_period = auto_renew_period
                lic.last_renewed_at = datetime.now()
            
            extended_count += 1
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功展期 {extended_count} 个授权码',
            'details': {
                'period': period,
                'months': months,
                'discount': discount,
                'base_price': base_price,
                'total_price': round(total_price, 2),
                'extended_count': extended_count,
                'auto_renew_enabled': enable_auto_renew,
                'auto_renew_period': auto_renew_period if enable_auto_renew else None
            }
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
