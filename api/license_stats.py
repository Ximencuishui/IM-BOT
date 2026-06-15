"""
授权码统计分析API
提供授权码使用情况的统计分析功能
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from models.user_models import License, RenewalHistory, TeamMember
from datetime import datetime, timedelta

license_stats_bp = Blueprint('license_stats', __name__, url_prefix='/api/license-stats')


@license_stats_bp.route('/overview', methods=['GET'])
@login_required
def get_license_overview():
    """获取授权码概览统计"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        now = datetime.now()
        
        # 总授权码数
        total_licenses = db.query(License).filter(
            License.user_id == user.id
        ).count()
        
        # 活跃授权码数
        active_licenses = db.query(License).filter(
            License.user_id == user.id,
            License.is_active == True,
            License.is_revoked == False
        ).count()
        
        # 已撤销授权码数
        revoked_licenses = db.query(License).filter(
            License.user_id == user.id,
            License.is_revoked == True
        ).count()
        
        # 即将过期（7天内）
        seven_days_later = now + timedelta(days=7)
        expiring_soon = db.query(License).filter(
            License.user_id == user.id,
            License.is_active == True,
            License.is_revoked == False,
            License.expires_at <= seven_days_later,
            License.expires_at > now
        ).count()
        
        # 已过期
        expired_licenses = db.query(License).filter(
            License.user_id == user.id,
            License.is_active == True,
            License.is_revoked == False,
            License.expires_at <= now
        ).count()
        
        # 启用自动续费的数量
        auto_renew_count = db.query(License).filter(
            License.user_id == user.id,
            License.auto_renew == True,
            License.is_active == True,
            License.is_revoked == False
        ).count()
        
        # 按类型统计
        type_stats = db.query(
            License.license_type,
            func.count(License.id)
        ).filter(
            License.user_id == user.id
        ).group_by(License.license_type).all()
        
        type_breakdown = {}
        for lic_type, count in type_stats:
            type_breakdown[lic_type] = count
        
        return jsonify({
            'success': True,
            'overview': {
                'total_licenses': total_licenses,
                'active_licenses': active_licenses,
                'revoked_licenses': revoked_licenses,
                'expiring_soon': expiring_soon,
                'expired_licenses': expired_licenses,
                'auto_renew_count': auto_renew_count,
                'type_breakdown': type_breakdown
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_stats_bp.route('/salesperson', methods=['GET'])
@login_required
def get_salesperson_stats():
    """获取销售员维度的统计"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 查询所有销售员及其授权的授权码数量
        salesperson_stats = db.query(
            TeamMember.id,
            TeamMember.name,
            TeamMember.phone,
            TeamMember.wx_id,
            func.count(License.id).label('license_count'),
            func.sum(func.case(
                (License.is_active == True, 1),
                else_=0
            )).label('active_count')
        ).outerjoin(
            License, 
            and_(
                License.assigned_to == TeamMember.id,
                License.user_id == user.id
            )
        ).filter(
            TeamMember.user_id == user.id
        ).group_by(
            TeamMember.id,
            TeamMember.name,
            TeamMember.phone,
            TeamMember.wx_id
        ).all()
        
        result = []
        for stat in salesperson_stats:
            result.append({
                'id': stat.id,
                'name': stat.name,
                'phone': stat.phone,
                'wx_id': stat.wx_id,
                'license_count': stat.license_count or 0,
                'active_count': stat.active_count or 0
            })
        
        return jsonify({
            'success': True,
            'salespersons': result,
            'total_salespersons': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_stats_bp.route('/trend', methods=['GET'])
@login_required
def get_license_trend():
    """
    获取授权码趋势统计
    Query params:
        - period: day/week/month（默认month）
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        period = request.args.get('period', 'month')
        
        now = datetime.now()
        if period == 'day':
            start_date = now - timedelta(days=30)
            group_by = [extract('year', License.created_at), extract('month', License.created_at), extract('day', License.created_at)]
        elif period == 'week':
            start_date = now - timedelta(weeks=12)
            group_by = [extract('year', License.created_at), extract('week', License.created_at)]
        else:  # month
            start_date = now - timedelta(days=365)
            group_by = [extract('year', License.created_at), extract('month', License.created_at)]
        
        # 按月统计新增授权码
        trend_data = db.query(
            *group_by,
            func.count(License.id)
        ).filter(
            License.user_id == user.id,
            License.created_at >= start_date
        ).group_by(*group_by).order_by(*group_by).all()
        
        result = []
        for row in trend_data:
            if period == 'day':
                date_str = f"{int(row[0])}-{int(row[1]):02d}-{int(row[2]):02d}"
            elif period == 'week':
                date_str = f"{int(row[0])}-W{int(row[1]):02d}"
            else:
                date_str = f"{int(row[0])}-{int(row[1]):02d}"
            
            result.append({
                'date': date_str,
                'count': row[-1]
            })
        
        return jsonify({
            'success': True,
            'period': period,
            'trend': result
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@license_stats_bp.route('/renewal-analysis', methods=['GET'])
@login_required
def get_renewal_analysis():
    """获取续费分析统计"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        now = datetime.now()
        last_year = now - timedelta(days=365)
        
        # 总续费次数和金额
        renewal_stats = db.query(
            func.count(RenewalHistory.id),
            func.sum(RenewalHistory.amount),
            func.avg(RenewalHistory.amount)
        ).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= last_year,
            RenewalHistory.status == 'success'
        ).first()
        
        total_renewals = renewal_stats[0] or 0
        total_amount = float(renewal_stats[1]) if renewal_stats[1] else 0.0
        avg_amount = float(renewal_stats[2]) if renewal_stats[2] else 0.0
        
        # 按续费类型统计
        type_stats = db.query(
            RenewalHistory.renew_type,
            func.count(RenewalHistory.id),
            func.sum(RenewalHistory.amount)
        ).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= last_year,
            RenewalHistory.status == 'success'
        ).group_by(RenewalHistory.renew_type).all()
        
        renew_type_breakdown = {}
        for renew_type, count, amount in type_stats:
            renew_type_breakdown[renew_type] = {
                'count': count,
                'amount': float(amount) if amount else 0.0
            }
        
        # 自动续费率
        total_licenses = db.query(License).filter(
            License.user_id == user.id,
            License.is_active == True,
            License.is_revoked == False
        ).count()
        
        auto_renew_licenses = db.query(License).filter(
            License.user_id == user.id,
            License.auto_renew == True,
            License.is_active == True,
            License.is_revoked == False
        ).count()
        
        auto_renew_rate = round((auto_renew_licenses / total_licenses * 100) if total_licenses > 0 else 0, 2)
        
        return jsonify({
            'success': True,
            'analysis': {
                'period': 'last_year',
                'total_renewals': total_renewals,
                'total_amount': round(total_amount, 2),
                'avg_renewal_amount': round(avg_amount, 2),
                'auto_renew_rate': auto_renew_rate,
                'renew_type_breakdown': renew_type_breakdown
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
