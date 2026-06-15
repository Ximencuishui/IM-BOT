"""
续费历史记录API
提供续费历史查询和统计功能
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from models.user_models import RenewalHistory, License
from datetime import datetime, timedelta

renewal_history_bp = Blueprint('renewal_history', __name__, url_prefix='/api/renewal-history')


@renewal_history_bp.route('/list', methods=['GET'])
@login_required
def get_renewal_history():
    """
    获取续费历史记录列表
    Query params:
        - page: 页码（默认1）
        - per_page: 每页数量（默认20）
        - license_id: 授权码ID（可选，筛选特定授权码）
        - start_date: 开始日期（可选）
        - end_date: 结束日期（可选）
        - renew_type: 续费类型（可选）
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 构建查询
        query = db.query(RenewalHistory).filter(
            RenewalHistory.user_id == user.id
        )
        
        # 筛选条件
        license_id = request.args.get('license_id')
        if license_id:
            query = query.filter(RenewalHistory.license_id == license_id)
        
        start_date = request.args.get('start_date')
        if start_date:
            query = query.filter(RenewalHistory.created_at >= datetime.fromisoformat(start_date))
        
        end_date = request.args.get('end_date')
        if end_date:
            query = query.filter(RenewalHistory.created_at <= datetime.fromisoformat(end_date))
        
        renew_type = request.args.get('renew_type')
        if renew_type:
            query = query.filter(RenewalHistory.renew_type == renew_type)
        
        # 总数
        total = query.count()
        
        # 分页查询，按时间倒序
        histories = query.order_by(RenewalHistory.created_at.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
        
        return jsonify({
            'success': True,
            'histories': [h.to_dict() for h in histories],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@renewal_history_bp.route('/stats', methods=['GET'])
@login_required
def get_renewal_stats():
    """
    获取续费统计数据
    Query params:
        - period: 统计周期 month/quarter/year（默认month）
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        period = request.args.get('period', 'month')
        
        # 计算时间范围
        now = datetime.now()
        if period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)
        
        # 基础查询
        base_query = db.query(RenewalHistory).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= start_date,
            RenewalHistory.status == 'success'
        )
        
        # 总续费次数
        total_count = base_query.count()
        
        # 总续费金额
        total_amount_result = db.query(func.sum(RenewalHistory.amount)).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= start_date,
            RenewalHistory.status == 'success'
        ).scalar()
        total_amount = float(total_amount_result) if total_amount_result else 0.0
        
        # 按续费类型统计
        type_stats = db.query(
            RenewalHistory.renew_type,
            func.count(RenewalHistory.id),
            func.sum(RenewalHistory.amount)
        ).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= start_date,
            RenewalHistory.status == 'success'
        ).group_by(RenewalHistory.renew_type).all()
        
        renew_type_breakdown = {}
        for renew_type, count, amount in type_stats:
            renew_type_breakdown[renew_type] = {
                'count': count,
                'amount': float(amount) if amount else 0.0
            }
        
        # 按周期统计
        period_stats = db.query(
            RenewalHistory.period,
            func.count(RenewalHistory.id),
            func.sum(RenewalHistory.amount)
        ).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= start_date,
            RenewalHistory.status == 'success'
        ).group_by(RenewalHistory.period).all()
        
        period_breakdown = {}
        for period_val, count, amount in period_stats:
            period_breakdown[period_val] = {
                'count': count,
                'amount': float(amount) if amount else 0.0
            }
        
        # 按月统计趋势
        monthly_trend = db.query(
            extract('year', RenewalHistory.created_at).label('year'),
            extract('month', RenewalHistory.created_at).label('month'),
            func.count(RenewalHistory.id),
            func.sum(RenewalHistory.amount)
        ).filter(
            RenewalHistory.user_id == user.id,
            RenewalHistory.created_at >= start_date,
            RenewalHistory.status == 'success'
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        trend_data = []
        for year, month, count, amount in monthly_trend:
            trend_data.append({
                'date': f"{int(year)}-{int(month):02d}",
                'count': count,
                'amount': float(amount) if amount else 0.0
            })
        
        return jsonify({
            'success': True,
            'stats': {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': now.isoformat(),
                'total_count': total_count,
                'total_amount': round(total_amount, 2),
                'renew_type_breakdown': renew_type_breakdown,
                'period_breakdown': period_breakdown,
                'monthly_trend': trend_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@renewal_history_bp.route('/license/<int:license_id>', methods=['GET'])
@login_required
def get_license_renewal_history(license_id):
    """
    获取特定授权码的续费历史
    """
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 验证授权码归属
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == user.id
        ).first()
        
        if not license_obj:
            return jsonify({'success': False, 'error': '授权码不存在或无权访问'}), 404
        
        # 查询该授权码的续费历史
        histories = db.query(RenewalHistory).filter(
            RenewalHistory.license_id == license_id,
            RenewalHistory.user_id == user.id
        ).order_by(RenewalHistory.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'license_code': license_obj.license_code,
            'histories': [h.to_dict() for h in histories],
            'count': len(histories)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
