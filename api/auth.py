"""
用户认证API
提供注册、登录、获取当前用户信息等接口
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import AuthService, login_required, get_current_user_from_request
import time

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 简单的内存限流器 (IP -> {count, reset_time})
_login_attempts = {}

def check_rate_limit(ip, limit=5, window=60):
    now = time.time()
    if ip in _login_attempts:
        record = _login_attempts[ip]
        if now > record['reset_time']:
            _login_attempts[ip] = {'count': 1, 'reset_time': now + window}
            return True
        if record['count'] >= limit:
            return False
        record['count'] += 1
    else:
        _login_attempts[ip] = {'count': 1, 'reset_time': now + window}
    return True


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册
    Body: {
        "email": "user@example.com",
        "password": "123456",
        "username": "张三",
        "phone": "13800138000",
        "company_name": "XX食材配送"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'success': False, 'error': '邮箱和密码不能为空'}), 400

    db: Session = get_db_session()
    try:
        result = AuthService.register(
            db,
            email=email,
            password=password,
            username=data.get('username'),
            phone=data.get('phone'),
            company_name=data.get('company_name')
        )

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    Body: {
        "username": "admin 或 admin@example.com",
        "password": "123456"
    }
    """
    # 速率限制检查
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'success': False, 'error': '尝试次数过多，请稍后再试'}), 429

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    username_or_email = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username_or_email or not password:
        return jsonify({'success': False, 'error': '用户名/邮箱和密码不能为空'}), 400

    db: Session = get_db_session()
    try:
        result = AuthService.login(db, username_or_email, password)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'subscription_valid': user.is_subscription_valid,
            'available_groups': user.available_groups
        }), 200
    finally:
        db.close()


@auth_bp.route('/license', methods=['GET'])
@login_required
def get_license_info():
    """获取当前用户的授权信息"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        return jsonify({
            'success': True,
            'license': {
                'expires_at': user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                'subscription_type': user.subscription_type,
                'max_groups': user.max_groups,
                'is_valid': user.is_subscription_valid
            }
        }), 200
    finally:
        db.close()


@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    更新用户资料
    Body: {
        "username": "新用户名",
        "phone": "13800138000",
        "company_name": "新公司名"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        # 更新字段
        if 'username' in data:
            user.username = data['username']
        if 'phone' in data:
            user.phone = data['phone']
        if 'company_name' in data:
            user.company_name = data['company_name']

        db.commit()

        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    修改密码
    Body: {
        "old_password": "旧密码",
        "new_password": "新密码"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'success': False, 'error': '旧密码和新密码不能为空'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'error': '新密码长度至少6位'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        # 验证旧密码
        if not AuthService.verify_password(old_password, user.password_hash):
            return jsonify({'success': False, 'error': '旧密码错误'}), 400

        # 更新密码
        user.password_hash = AuthService.hash_password(new_password)
        db.commit()

        return jsonify({'success': True, 'message': '密码修改成功'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
