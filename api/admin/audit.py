"""
管理员审计日志API
包含日志查询、统计、导出、清理功能
"""
from flask import request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.db_config import get_db_session
from services.auth_service import admin_required
from datetime import datetime, timedelta


def log_admin_action(db: Session, user_id: int, username: str, action_type: str, description: str):
    """记录管理员操作日志"""
    try:
        from models.audit_log import AuditLog
        
        log = AuditLog(
            user_id=user_id,
            username=username,
            action_type=action_type,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:255]
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Failed to log audit action: {e}")


def init_audit_routes(admin_bp):
    """初始化审计日志路由"""
    
    @admin_bp.route('/audit-logs', methods=['GET'])
    @admin_required
    def get_audit_logs():
        """获取审计日志列表（仅管理员）"""
        from models.audit_log import AuditLog
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        action_type = request.args.get('action_type')
        user_id = request.args.get('user_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        db: Session = get_db_session()
        try:
            query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
            
            if action_type:
                query = query.filter(AuditLog.action_type == action_type)
            if user_id:
                query = query.filter(AuditLog.user_id == int(user_id))
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)
            
            total = query.count()
            logs = query.offset((page - 1) * per_page).limit(per_page).all()
            
            return jsonify({
                'success': True,
                'logs': [log.to_dict() for log in logs],
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


    @admin_bp.route('/audit-logs/stats', methods=['GET'])
    @admin_required
    def get_audit_stats():
        """获取审计统计信息（仅管理员）"""
        from models.audit_log import AuditLog
        
        db: Session = get_db_session()
        try:
            total_logs = db.query(AuditLog).count()
            today_logs = db.query(AuditLog).filter(
                AuditLog.created_at >= datetime.now().strftime('%Y-%m-%d')
            ).count()
            
            action_stats = db.query(
                AuditLog.action_type,
                func.count(AuditLog.id)
            ).group_by(AuditLog.action_type).all()
            
            action_stats_dict = {row[0]: row[1] for row in action_stats}
            
            return jsonify({
                'success': True,
                'total_logs': total_logs,
                'today_logs': today_logs,
                'action_stats': action_stats_dict
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/audit-logs/export', methods=['POST'])
    @admin_required
    def export_audit_logs():
        """导出审计日志（仅管理员）"""
        from models.audit_log import AuditLog
        
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        db: Session = get_db_session()
        try:
            query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
            
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)
            
            logs = query.all()
            
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', '用户ID', '用户名', '操作类型', '操作描述', 'IP地址', '用户代理', '创建时间'])
            
            for log in logs:
                writer.writerow([
                    log.id,
                    log.user_id,
                    log.username or '',
                    log.action_type,
                    log.description or '',
                    log.ip_address or '',
                    log.user_agent or '',
                    log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else ''
                ])
            
            output.seek(0)
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename=audit_logs.csv'
            }
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/audit-logs/cleanup', methods=['POST'])
    @admin_required
    def cleanup_old_logs():
        """清理旧日志（仅管理员）"""
        from models.audit_log import AuditLog
        
        data = request.get_json()
        days = data.get('days', 90)
        
        db: Session = get_db_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.commit()
            
            current_user = get_current_user_from_request(db)
            if current_user:
                log_admin_action(db, current_user.id, current_user.username,
                               'log_cleanup', f'清理日志: 删除{deleted_count}条{days}天前的日志')
            
            return jsonify({
                'success': True,
                'message': f'已清理 {deleted_count} 条日志',
                'deleted_count': deleted_count
            }), 200
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


def get_current_user_from_request(db):
    """从请求中获取当前用户"""
    from services.auth_service import get_current_user_from_request as _get_user
    return _get_user(db)