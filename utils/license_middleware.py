"""
授权检查中间件
在关键API调用前验证授权状态
"""
import logging
from functools import wraps
from flask import request, jsonify
from services.license_service import license_service

logger = logging.getLogger(__name__)


# 不需要授权检查的路由白名单
WHITELIST_ROUTES = [
    '/health',
    '/metrics',
    '/api/license/activate',
    '/api/license/status',
    '/api/license/machine-id',
]


def require_license(f):
    """
    授权检查装饰器
    用于需要有效授权的API端点
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查是否在白名单中
        if request.path in WHITELIST_ROUTES:
            return f(*args, **kwargs)

        # 检查授权状态
        license_check = license_service.check_license()

        if not license_check.get('has_valid_license'):
            logger.warning(f"未授权访问: {request.path} from {request.remote_addr}")
            return jsonify({
                'error': '未找到有效授权',
                'code': 'LICENSE_REQUIRED',
                'hint': '请访问 /api/license/activate 激活授权码'
            }), 403

        # 检查是否有即将过期的授权
        expiring = license_check.get('expiring_soon', [])
        if expiring:
            # 在响应头中添加警告
            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                resp_obj = response[0]
            else:
                resp_obj = response

            # 添加警告信息
            if hasattr(resp_obj, 'headers'):
                warning_msg = '; '.join(
                    f"授权{lic['license_code']}剩余{lic['days_remaining']}天"
                    for lic in expiring
                )
                resp_obj.headers['X-License-Warning'] = warning_msg

            return response

        return f(*args, **kwargs)

    return decorated_function


def check_group_license(group_id: str) -> bool:
    """
    检查特定群是否有授权

    Args:
        group_id: 微信群ID

    Returns:
        是否有有效授权
    """
    result = license_service.check_license(bound_to=group_id)
    return result.get('has_valid_license', False)


def get_license_info():
    """
    获取当前授权信息(用于添加到响应中)
    """
    result = license_service.check_license()
    return {
        'has_valid_license': result.get('has_valid_license', False),
        'active_count': result.get('active_count', 0),
        'expiring_soon': result.get('expiring_soon', []),
    }
