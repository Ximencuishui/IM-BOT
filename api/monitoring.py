"""
系统监控API
提供系统健康状态、性能指标等信息
"""
from flask import Blueprint, jsonify
from datetime import datetime
import psutil
import os
import sys

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/admin/monitoring')


@monitoring_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        
        # 网络信息
        net_io = psutil.net_io_counters()
        
        return jsonify({
            'success': True,
            'system': {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_bp.route('/app-status', methods=['GET'])
def get_app_status():
    """获取应用状态"""
    try:
        from config.settings import settings
        from utils.metrics import check_middleware_health
        
        # 检查中间件健康状态
        middleware_health = check_middleware_health()
        
        # 获取进程信息
        process = psutil.Process(os.getpid())
        
        return jsonify({
            'success': True,
            'app': {
                'name': settings.APP_NAME,
                'version': settings.APP_VERSION,
                'uptime': datetime.now().timestamp() - process.create_time(),
                'pid': os.getpid(),
                'status': 'running',
                'middleware': middleware_health
            },
            'process': {
                'cpu_percent': process.cpu_percent(),
                'memory_info': {
                    'rss': process.memory_info().rss,
                    'vms': process.memory_info().vms
                },
                'threads': process.num_threads(),
                'connections': len(process.connections())
            },
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_bp.route('/database-status', methods=['GET'])
def get_database_status():
    """获取数据库状态"""
    try:
        from database.db_config import engine, get_db_session
        from sqlalchemy import text
        
        db = get_db_session()
        
        # 测试数据库连接
        db.execute(text("SELECT 1"))
        
        # 获取表数量
        table_count = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"
        )).scalar()
        
        # 获取数据库大小（MySQL）
        db_size = db.execute(text(
            "SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb "
            "FROM information_schema.tables WHERE table_schema = DATABASE()"
        )).scalar() or 0
        
        db.close()
        
        return jsonify({
            'success': True,
            'database': {
                'status': 'connected',
                'type': 'mysql',
                'table_count': table_count,
                'size_mb': float(db_size)
            },
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'database': {
                'status': 'disconnected'
            }
        }), 500


@monitoring_bp.route('/recent-activities', methods=['GET'])
def get_recent_activities():
    """获取最近活动"""
    try:
        from models.user_models import AuditLog
        from database.db_config import get_db_session
        from sqlalchemy.orm import Session
        
        db: Session = get_db_session()
        
        # 获取最近20条活动记录
        activities = db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(20).all()
        
        db.close()
        
        return jsonify({
            'success': True,
            'activities': [
                {
                    'id': act.id,
                    'username': act.username,
                    'action': act.action,
                    'description': act.description,
                    'created_at': act.created_at.isoformat(),
                    'status': act.status
                }
                for act in activities
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_bp.route('/health-summary', methods=['GET'])
def get_health_summary():
    """获取健康摘要"""
    try:
        from utils.metrics import check_middleware_health
        
        # 检查所有组件
        middleware_health = check_middleware_health()
        
        # 计算总体健康状态
        all_healthy = all(middleware_health.values())
        
        # 获取系统资源使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            'success': True,
            'overall_status': 'healthy' if all_healthy else 'degraded',
            'components': middleware_health,
            'resources': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            },
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
