"""
审计日志API
记录系统操作日志，追踪敏感操作
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import admin_required
from datetime import datetime, timedelta
import json

audit_log_bp = Blueprint('audit_log', __name__, url_prefix='/api/admin/audit-logs')


@audit_log_bp.route('', methods=['GET'])
@admin_required
def list_audit_logs():
    """获取审计日志列表"""
    db: Session = get_db_session()
    try:
        from models.user_models import AuditLog
        
        # 查询参数
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        resource = request.args.get('resource')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        keyword = request.args.get('keyword')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = db.query(AuditLog)
        
        # 过滤条件
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource == resource)
        if status:
            query = query.filter(AuditLog.status == status)
        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(AuditLog.created_at <= datetime.fromisoformat(end_date))
        if keyword:
            query = query.filter(
                (AuditLog.username.like(f'%{keyword}%')) |
                (AuditLog.description.like(f'%{keyword}%')) |
                (AuditLog.ip_address.like(f'%{keyword}%'))
            )
        
        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'total': total,
            'page': page,
            'per_page': per_page
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@audit_log_bp.route('/stats', methods=['GET'])
@admin_required
def audit_stats():
    """获取审计统计信息"""
    db: Session = get_db_session()
    try:
        from models.user_models import AuditLog
        from sqlalchemy import func
        
        # 总日志数
        total_logs = db.query(func.count(AuditLog.id)).scalar() or 0
        
        # 今日日志数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_logs = db.query(func.count(AuditLog.id)).filter(
            AuditLog.created_at >= today_start
        ).scalar() or 0
        
        # 按操作类型统计
        action_stats = db.query(
            AuditLog.action,
            func.count(AuditLog.id)
        ).group_by(AuditLog.action).all()
        
        # 按资源类型统计
        resource_stats = db.query(
            AuditLog.resource,
            func.count(AuditLog.id)
        ).group_by(AuditLog.resource).all()
        
        # 成功/失败统计
        status_stats = db.query(
            AuditLog.status,
            func.count(AuditLog.id)
        ).group_by(AuditLog.status).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_logs': total_logs,
                'today_logs': today_logs,
                'action_stats': [{'action': a, 'count': c} for a, c in action_stats],
                'resource_stats': [{'resource': r, 'count': c} for r, c in resource_stats],
                'status_stats': [{'status': s, 'count': c} for s, c in status_stats]
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@audit_log_bp.route('/export', methods=['POST'])
@admin_required
def export_audit_logs():
    """导出审计日志"""
    data = request.get_json() or {}
    
    db: Session = get_db_session()
    try:
        from models.user_models import AuditLog
        
        # 查询条件
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        action = data.get('action')
        resource = data.get('resource')
        
        query = db.query(AuditLog)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(AuditLog.created_at <= datetime.fromisoformat(end_date))
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource == resource)
        
        logs = query.order_by(AuditLog.created_at.desc()).all()
        
        # 转换为CSV格式
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '用户名', '操作类型', '资源', '描述', 'IP地址', '状态', '时间'])
        
        for log in logs:
            writer.writerow([
                log.id,
                log.username or '-',
                log.action,
                log.resource or '-',
                log.description,
                log.ip_address or '-',
                log.status,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        csv_data = output.getvalue()
        output.close()
        
        return jsonify({
            'success': True,
            'csv_data': csv_data,
            'count': len(logs)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@audit_log_bp.route('/cleanup', methods=['POST'])
@admin_required
def cleanup_old_logs():
    """清理旧日志"""
    data = request.get_json()
    if not data or 'days' not in data:
        return jsonify({'success': False, 'error': '请指定保留天数'}), 400
    
    days = int(data['days'])
    
    db: Session = get_db_session()
    try:
        from models.user_models import AuditLog
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 删除旧日志
        deleted_count = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).delete()
        
        db.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'已清理 {deleted_count} 条{days}天前的日志'
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


def create_audit_log(user_id, username, action, resource=None, resource_id=None, 
                    description=None, old_value=None, new_value=None, 
                    ip_address=None, user_agent=None, status='success', error_message=None):
    """
    创建审计日志（内部函数）
    
    Args:
        user_id: 用户ID
        username: 用户名
        action: 操作类型
        resource: 资源类型
        resource_id: 资源ID
        description: 操作描述
        old_value: 旧值
        new_value: 新值
        ip_address: IP地址
        user_agent: 用户代理
        status: 状态
        error_message: 错误信息
    """
    db: Session = get_db_session()
    try:
        from models.user_models import AuditLog
        
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            resource_id=resource_id,
            description=description,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        
        db.add(log)
        db.commit()
        return log
    except Exception as e:
        db.rollback()
        print(f"创建审计日志失败: {e}")
        return None
    finally:
        db.close()
