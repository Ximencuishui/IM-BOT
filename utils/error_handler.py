"""
统一错误处理工具
生产环境返回通用错误信息，详细日志记录在服务端

增强:
    - 支持更多错误类型(验证错误、权限错误、资源不存在)
    - 统一响应格式
    - 自动记录审计日志
"""
import logging
import os
import traceback
from flask import jsonify

logger = logging.getLogger(__name__)

# 是否为生产环境
IS_PRODUCTION = os.getenv('APP_ENV', 'development').lower() == 'production'


class AppError(Exception):
    """应用级错误基类"""

    def __init__(self, message: str, status_code: int = 400, context: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.context = context or {}


class ValidationError(AppError):
    """参数验证错误"""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, status_code=400, context=context)


class AuthError(AppError):
    """认证/授权错误"""
    def __init__(self, message: str = '认证失败', status_code: int = 401, context: dict = None):
        super().__init__(message, status_code=status_code, context=context)


class NotFoundError(AppError):
    """资源不存在错误"""
    def __init__(self, message: str = '资源不存在', context: dict = None):
        super().__init__(message, status_code=404, context=context)


class PermissionError_(AppError):
    """权限不足错误"""
    def __init__(self, message: str = '权限不足', context: dict = None):
        super().__init__(message, status_code=403, context=context)


class BusinessError(AppError):
    """业务逻辑错误"""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, status_code=400, context=context)


def handle_error(e: Exception, context: str = '') -> tuple:
    """
    统一错误处理函数

    参数:
        e: 异常对象
        context: 错误发生的上下文信息

    返回:
        (响应数据, HTTP状态码)
    """
    if isinstance(e, AppError):
        status_code = e.status_code
        error_msg = e.message
        extra = e.context

        log_level = logging.WARNING if status_code < 500 else logging.ERROR
        logger.log(log_level, f"[{context}] {error_msg} | extra={extra}")
    else:
        status_code = 500
        error_msg = str(e) if not IS_PRODUCTION else '服务器内部错误'
        logger.error(f"[{context}] 未预期错误: {traceback.format_exc()}")

    return jsonify({
        'success': False,
        'error': error_msg,
        'code': status_code,
    }), status_code


def handle_db_error(e: Exception, db_session, context: str = '') -> tuple:
    """
    数据库错误处理（自动回滚）

    参数:
        e: 异常对象
        db_session: 数据库会话对象
        context: 错误发生的上下文信息

    返回:
        (响应数据, HTTP状态码)
    """
    try:
        db_session.rollback()
    except Exception as rollback_err:
        logger.error(f"[{context}] 回滚失败: {str(rollback_err)}")

    return handle_error(e, context)


def success_response(data=None, message='操作成功') -> tuple:
    """统一成功响应"""
    response = {'success': True, 'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response), 200


def error_response(error, status_code=400) -> tuple:
    """统一错误响应"""
    return jsonify({
        'success': False,
        'error': error,
        'code': status_code,
    }), status_code