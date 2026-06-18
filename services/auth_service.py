"""
用户认证服务
提供邮箱注册、登录、JWT令牌生成与验证功能
"""
import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from sqlalchemy.orm import Session
from models.user_models import User
from config.settings import settings


class AuthService:
    """认证服务类"""

    # JWT配置
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise EnvironmentError("生产环境必须设置 JWT_SECRET_KEY 环境变量")
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24  # Token有效期24小时

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False

    @staticmethod
    def generate_token(user_id: int, email: str) -> str:
        """生成JWT令牌"""
        from datetime import timezone
        now = datetime.now(timezone.utc)  # 使用UTC时间避免时区问题
        payload = {
            'user_id': user_id,
            'email': email,
            'exp': now + timedelta(hours=AuthService.JWT_EXPIRATION_HOURS),
            'iat': now,
            'nbf': now
        }
        token = jwt.encode(payload, AuthService.JWT_SECRET_KEY, algorithm=AuthService.JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_token(token: str) -> dict:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token,
                AuthService.JWT_SECRET_KEY,
                algorithms=[AuthService.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def register(db: Session, email: str, password: str, **kwargs) -> dict:
        """用户注册"""
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return {'success': False, 'error': '该邮箱已被注册'}

        # 密码强度检查
        if len(password) < 6:
            return {'success': False, 'error': '密码长度至少6位'}

        # 计算默认订阅过期时间（30天）
        from datetime import timedelta
        default_subscription_days = kwargs.get('subscription_days', 30)
        subscription_expires_at = datetime.now() + timedelta(days=default_subscription_days)

        # 创建新用户
        new_user = User(
            email=email,
            password_hash=AuthService.hash_password(password),
            username=kwargs.get('username', ''),
            phone=kwargs.get('phone', ''),
            company_name=kwargs.get('company_name', ''),
            subscription_type=kwargs.get('subscription_type', 'monthly'),
            subscription_expires_at=subscription_expires_at,
            max_groups=kwargs.get('max_groups', 3),
            is_active=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 生成token
        token = AuthService.generate_token(new_user.id, new_user.email)

        return {
            'success': True,
            'user': new_user.to_dict(),
            'token': token
        }

    @staticmethod
    def login(db: Session, email_or_username: str, password: str) -> dict:
        """用户登录 - 支持邮箱或用户名登录"""
        # 查找用户（支持邮箱或用户名）
        user = db.query(User).filter(
            (User.email == email_or_username) | (User.username == email_or_username)
        ).first()
        
        if not user:
            return {'success': False, 'error': '用户名/邮箱或密码错误'}

        # 检查账户状态
        if not user.is_active:
            return {'success': False, 'error': '账户已被禁用，请联系管理员'}

        # 验证密码
        if not AuthService.verify_password(password, user.password_hash):
            return {'success': False, 'error': '用户名/邮箱或密码错误'}

        # 更新最后登录时间
        user.last_login_at = datetime.now()
        db.commit()

        demo_license = None
        try:
            from services.demo_boss_license import (
                ensure_demo_boss_robot_license,
                is_demo_boss_user,
            )
            if is_demo_boss_user(user):
                demo_license = ensure_demo_boss_robot_license(db)
        except Exception:
            pass

        # 生成token
        token = AuthService.generate_token(user.id, user.email)

        # 构建授权信息
        license_info = {
            'expires_at': user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            'subscription_type': user.subscription_type,
            'max_groups': user.max_groups,
            'is_valid': user.is_subscription_valid
        }

        result = {
            'success': True,
            'user': user.to_dict(),
            'token': token,
            'license': license_info,
        }
        if demo_license:
            result['demo_license'] = demo_license
        return result

    @staticmethod
    def get_current_user(db: Session, user_id: int) -> User:
        """根据用户ID获取用户信息"""
        return db.query(User).filter(User.id == user_id).first()


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求头获取token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'success': False, 'error': '未提供认证令牌'}), 401

        # 提取token (Bearer <token>)
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'success': False, 'error': '无效的认证格式'}), 401

        token = parts[1]

        # 验证token
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': '令牌无效或已过期'}), 401

        # 将用户信息存入g对象
        g.current_user_id = payload['user_id']
        g.current_user_email = payload['email']

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    @login_required  # 首先确保用户已登录
    def decorated_function(*args, **kwargs):
        # 从数据库获取用户详细信息以检查角色
        from database.db_config import get_db_session
        db = get_db_session()
        try:
            user_id = getattr(g, 'current_user_id', None)
            if not user_id:
                return jsonify({'success': False, 'error': '未提供认证令牌'}), 401
            
            user = AuthService.get_current_user(db, user_id)
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            # 检查是否为管理员或超级管理员
            if user.role not in ['admin', 'super_admin']:
                return jsonify({'success': False, 'error': '需要管理员权限'}), 403
            
            # 将用户角色信息存入g对象
            g.current_user_role = user.role
            
            return f(*args, **kwargs)
        finally:
            db.close()

    return decorated_function


def role_required(required_roles):
    """角色权限验证装饰器工厂函数
    
    Args:
        required_roles: 允许的角色列表，如 ['admin', 'super_admin']
    """
    def decorator(f):
        @wraps(f)
        @login_required  # 首先确保用户已登录
        def decorated_function(*args, **kwargs):
            # 获取当前用户信息
            user_id = getattr(g, 'current_user_id', None)
            if not user_id:
                return jsonify({'success': False, 'error': '未提供认证令牌'}), 401

            # 从数据库获取用户详细信息以检查角色
            from database.db_config import get_db_session
            db = get_db_session()
            try:
                user = AuthService.get_current_user(db, user_id)
                if not user:
                    return jsonify({'success': False, 'error': '用户不存在'}), 404
                
                # 检查用户角色是否在允许的角色列表中
                if user.role not in required_roles:
                    return jsonify({
                        'success': False, 
                        'error': f'需要以下权限之一: {", ".join(required_roles)}'
                    }), 403
                
                # 将用户角色信息存入g对象
                g.current_user_role = user.role
                
                return f(*args, **kwargs)
            finally:
                db.close()

        return decorated_function
    return decorator


def get_current_user_from_request(db: Session) -> User:
    """从请求中获取当前用户"""
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
        return None
    return AuthService.get_current_user(db, user_id)
