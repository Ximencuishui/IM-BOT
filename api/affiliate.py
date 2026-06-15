"""
推广管理API
管理平台推广员、佣金规则和推广链接
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import admin_required
from datetime import datetime
import uuid

affiliate_bp = Blueprint('affiliate', __name__, url_prefix='/api/admin/affiliates')


@affiliate_bp.route('/promoters', methods=['GET'])
@admin_required
def list_promoters():
    """获取推广员列表"""
    db: Session = get_db_session()
    try:
        from models.user_models import AffiliatePromoter
        
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = db.query(AffiliatePromoter)
        
        if keyword:
            query = query.filter(
                (AffiliatePromoter.promoter_name.like(f'%{keyword}%')) |
                (AffiliatePromoter.promoter_code.like(f'%{keyword}%'))
            )
        
        total = query.count()
        promoters = query.order_by(AffiliatePromoter.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        return jsonify({
            'success': True,
            'promoters': [p.to_dict() for p in promoters],
            'total': total,
            'page': page,
            'per_page': per_page
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@affiliate_bp.route('/promoters', methods=['POST'])
@admin_required
def create_promoter():
    """创建推广员"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    required_fields = ['promoter_name', 'commission_rate']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
    
    db: Session = get_db_session()
    try:
        from models.user_models import AffiliatePromoter
        
        # 生成推广员编号
        promoter_code = data.get('promoter_code') or f"PROM{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
        
        # 生成推广链接
        base_url = request.host_url.rstrip('/')
        promo_link = f"{base_url}/register?ref={promoter_code}"
        
        new_promoter = AffiliatePromoter(
            promoter_code=promoter_code,
            promoter_name=data['promoter_name'],
            contact_info=data.get('contact_info'),
            commission_rate=float(data['commission_rate']),
            promo_link=promo_link,
            remark=data.get('remark'),
            is_active=data.get('is_active', True)
        )
        
        db.add(new_promoter)
        db.commit()
        db.refresh(new_promoter)
        
        return jsonify({
            'success': True,
            'promoter': new_promoter.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@affiliate_bp.route('/promoters/<int:promoter_id>', methods=['PUT'])
@admin_required
def update_promoter(promoter_id):
    """更新推广员信息"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400
    
    db: Session = get_db_session()
    try:
        from models.user_models import AffiliatePromoter
        
        promoter = db.query(AffiliatePromoter).filter(AffiliatePromoter.id == promoter_id).first()
        if not promoter:
            return jsonify({'success': False, 'error': '推广员不存在'}), 404
        
        # 更新字段
        if 'promoter_name' in data:
            promoter.promoter_name = data['promoter_name']
        if 'contact_info' in data:
            promoter.contact_info = data['contact_info']
        if 'commission_rate' in data:
            promoter.commission_rate = float(data['commission_rate'])
        if 'remark' in data:
            promoter.remark = data['remark']
        if 'is_active' in data:
            promoter.is_active = data['is_active']
        
        db.commit()
        db.refresh(promoter)
        
        return jsonify({
            'success': True,
            'promoter': promoter.to_dict()
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@affiliate_bp.route('/promoters/<int:promoter_id>', methods=['DELETE'])
@admin_required
def delete_promoter(promoter_id):
    """删除推广员"""
    db: Session = get_db_session()
    try:
        from models.user_models import AffiliatePromoter
        
        promoter = db.query(AffiliatePromoter).filter(AffiliatePromoter.id == promoter_id).first()
        if not promoter:
            return jsonify({'success': False, 'error': '推广员不存在'}), 404
        
        db.delete(promoter)
        db.commit()
        
        return jsonify({'success': True, 'message': '删除成功'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@affiliate_bp.route('/promoters/<int:promoter_id>/regenerate-link', methods=['POST'])
@admin_required
def regenerate_promo_link(promoter_id):
    """重新生成推广链接"""
    db: Session = get_db_session()
    try:
        from models.user_models import AffiliatePromoter
        
        promoter = db.query(AffiliatePromoter).filter(AffiliatePromoter.id == promoter_id).first()
        if not promoter:
            return jsonify({'success': False, 'error': '推广员不存在'}), 404
        
        # 重新生成推广链接
        base_url = request.host_url.rstrip('/')
        promoter.promo_link = f"{base_url}/register?ref={promoter.promoter_code}"
        
        db.commit()
        db.refresh(promoter)
        
        return jsonify({
            'success': True,
            'promo_link': promoter.promo_link
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@affiliate_bp.route('/stats', methods=['GET'])
@admin_required
def affiliate_stats():
    """获取推广统计"""
    db: Session = get_db_session()
    try:
        from models.user_models import AffiliatePromoter
        from sqlalchemy import func
        
        # 总推广员数
        total_promoters = db.query(func.count(AffiliatePromoter.id)).scalar() or 0
        
        # 活跃推广员数
        active_promoters = db.query(func.count(AffiliatePromoter.id)).filter(
            AffiliatePromoter.is_active == True
        ).scalar() or 0
        
        # 平均佣金比例
        avg_commission = db.query(func.avg(AffiliatePromoter.commission_rate)).scalar() or 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_promoters': total_promoters,
                'active_promoters': active_promoters,
                'avg_commission_rate': round(float(avg_commission), 2)
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
