"""
统一错误处理工具
生产环境返回通用错误信息，详细日志记录在服务端
"""
import logging
import os

logger = logging.getLogger(__name__)

# 是否为生产环境
IS_PRODUCTION = os.getenv('APP_ENV', 'development').lower() == 'production'


def handle_error(e: Exception, context: str = '') -> tuple:
    """
    统一错误处理函数
    
    参数:
        e: 异常对象
        context: 错误发生的上下文信息
        
    返回:
        (响应数据, HTTP状态码)
    """
    # 记录详细日志到服务端
    logger.error(f"[{context}] 错误: {str(e)}", exc_info=True)
    
    # 生产环境返回通用错误信息
    if IS_PRODUCTION:
        return jsonify({
            'success': False,
            'error': '操作失败，请联系管理员'
        }), 500
    
    # 开发环境返回详细错误信息
    return jsonify({
        'success': False,
        'error': str(e),
        'context': context
    }), 500


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
    # 回滚事务
    try:
        db_session.rollback()
    except Exception as rollback_err:
        logger.error(f"[{context}] 回滚失败: {str(rollback_err)}")
    
    return handle_error(e, context)


def success_response(data=None, message='操作成功') -> tuple:
    """
    统一成功响应
    
    参数:
        data: 响应数据
        message: 成功消息
        
    返回:
        (响应数据, HTTP状态码)
    """
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        response['data'] = data
    
    return jsonify(response), 200


def error_response(error, status_code=400, success=False) -> tuple:
    """
    统一错误响应
    
    参数:
        error: 错误信息
        status_code: HTTP状态码
        success: 是否成功（默认为False）
        
    返回:
        (响应数据, HTTP状态码)
    """
    return jsonify({
        'success': success,
        'error': error
    }), status_code


# 需要导入jsonify
from flask import jsonify