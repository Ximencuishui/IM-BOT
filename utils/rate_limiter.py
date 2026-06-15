"""
API请求频率限制器
使用内存字典实现简单的请求频率限制，防止暴力攻击
"""
from collections import defaultdict
from datetime import datetime
from flask import request, jsonify, g
import time

rate_limit_storage = defaultdict(list)

RATE_LIMIT_CONFIG = {
    'default': {'requests': 100, 'seconds': 60},
    'login': {'requests': 5, 'seconds': 60},
    'admin': {'requests': 50, 'seconds': 60},
    'sensitive': {'requests': 10, 'seconds': 60}
}


def get_client_ip():
    """获取客户端IP地址"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr


def cleanup_old_requests(ip, config_key='default'):
    """清理过期的请求记录"""
    config = RATE_LIMIT_CONFIG.get(config_key, RATE_LIMIT_CONFIG['default'])
    now = time.time()
    rate_limit_storage[ip] = [
        timestamp for timestamp in rate_limit_storage[ip]
        if now - timestamp < config['seconds']
    ]


def check_rate_limit(config_key='default'):
    """检查请求频率是否超限"""
    ip = get_client_ip()
    config = RATE_LIMIT_CONFIG.get(config_key, RATE_LIMIT_CONFIG['default'])
    
    cleanup_old_requests(ip, config_key)
    
    if len(rate_limit_storage[ip]) >= config['requests']:
        return False, {
            'error': '请求过于频繁，请稍后再试',
            'retry_after': config['seconds']
        }
    
    rate_limit_storage[ip].append(time.time())
    return True, None


def rate_limit_decorator(config_key='default'):
    """请求频率限制装饰器"""
    def decorator(f):
        def wrapped_function(*args, **kwargs):
            allowed, error_info = check_rate_limit(config_key)
            if not allowed:
                return jsonify({'success': False, **error_info}), 429
            return f(*args, **kwargs)
        return wrapped_function
    return decorator


def rate_limit_middleware():
    """请求频率限制中间件"""
    ip = get_client_ip()
    path = request.path
    method = request.method
    
    # 对登录接口进行严格限制
    if '/api/auth/login' in path and method == 'POST':
        allowed, error_info = check_rate_limit('login')
        if not allowed:
            return jsonify({'success': False, **error_info}), 429
    
    # 对管理员接口进行限制
    if '/api/admin/' in path:
        allowed, error_info = check_rate_limit('admin')
        if not allowed:
            return jsonify({'success': False, **error_info}), 429
    
    # 对敏感操作进行严格限制
    sensitive_paths = [
        '/api/admin/users',
        '/api/admin/permissions',
        '/api/admin/audit-logs/cleanup'
    ]
    if any(sensitive_path in path for sensitive_path in sensitive_paths) and method in ['POST', 'PUT', 'DELETE']:
        allowed, error_info = check_rate_limit('sensitive')
        if not allowed:
            return jsonify({'success': False, **error_info}), 429
    
    return None