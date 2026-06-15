"""
管理员用户管理API
包含用户的CRUD操作、密码重置、详细信息获取
"""
from flask import request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import admin_required, get_current_user_from_request
from models.user_models import User
from datetime import datetime


def init_users_routes(admin_bp):
    """初始化用户管理路由"""
    
    @admin_bp.route('/users', methods=['GET'])
    @admin_required
    def get_all_users():
        """获取所有用户列表（仅管理员）- 支持分页和筛选"""
        db: Session = get_db_session()
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('page_size', 20))
            
            username = request.args.get('username')
            email = request.args.get('email')
            role = request.args.get('role')
            is_active = request.args.get('is_active')
            
            query = db.query(User)
            
            if username:
                query = query.filter(User.username.like(f'%{username}%'))
            if email:
                query = query.filter(User.email.like(f'%{email}%'))
            if role:
                query = query.filter(User.role == role)
            if is_active is not None:
                query = query.filter(User.is_active == (is_active == '1'))
            
            total = query.count()
            users = query.offset((page - 1) * per_page).limit(per_page).all()
            
            return jsonify({
                'success': True,
                'users': [user.to_dict() for user in users],
                'pagination': {
                    'page': page,
                    'page_size': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/users/<int:user_id>', methods=['GET'])
    @admin_required
    def get_user(user_id):
        """获取单个用户详情（仅管理员）"""
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/users', methods=['POST'])
    @admin_required
    def create_user():
        """创建新用户（仅管理员）"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
        
        db: Session = get_db_session()
        try:
            existing_user = db.query(User).filter(User.email == data['email']).first()
            if existing_user:
                return jsonify({'success': False, 'error': '该邮箱已被注册'}), 400
            
            from services.auth_service import AuthService
            new_user = User(
                email=data['email'],
                password_hash=AuthService.hash_password(data['password']),
                username=data.get('username', ''),
                phone=data.get('phone', ''),
                company_name=data.get('company_name', ''),
                role=data.get('role', 'user'),
                subscription_type=data.get('subscription_type', 'monthly'),
                max_groups=data.get('max_groups', 3),
                is_active=data.get('is_active', True)
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            current_user = get_current_user_from_request(db)
            if current_user:
                from api.admin.audit import log_admin_action
                log_admin_action(db, current_user.id, current_user.username,
                               'user_create', f'创建用户: {new_user.email}')
            
            return jsonify({
                'success': True,
                'user': new_user.to_dict()
            }), 201
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/users/<int:user_id>', methods=['PUT'])
    @admin_required
    def update_user(user_id):
        """更新用户信息（仅管理员）"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            if 'username' in data:
                user.username = data['username']
            if 'phone' in data:
                user.phone = data['phone']
            if 'company_name' in data:
                user.company_name = data['company_name']
            if 'role' in data:
                user.role = data['role']
            if 'subscription_type' in data:
                user.subscription_type = data['subscription_type']
            if 'max_groups' in data:
                user.max_groups = data['max_groups']
            if 'is_active' in data:
                user.is_active = data['is_active']
            
            db.commit()
            db.refresh(user)
            
            current_user_info = get_current_user_from_request(db)
            if current_user_info:
                from api.admin.audit import log_admin_action
                log_admin_action(db, current_user_info.id, current_user_info.username,
                               'user_update', f'更新用户: {user.email}')
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
            }), 200
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
    @admin_required
    def delete_user(user_id):
        """删除用户（仅管理员）"""
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            current_user = get_current_user_from_request(db)
            if current_user and current_user.id == user_id:
                return jsonify({'success': False, 'error': '不能删除自己的账户'}), 400
            
            deleted_email = user.email
            db.delete(user)
            db.commit()
            
            if current_user:
                from api.admin.audit import log_admin_action
                log_admin_action(db, current_user.id, current_user.username,
                               'user_delete', f'删除用户: {deleted_email}')
            
            return jsonify({
                'success': True,
                'message': '用户删除成功'
            }), 200
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
    @admin_required
    def reset_user_password(user_id):
        """重置用户密码（仅管理员）"""
        from services.auth_service import AuthService
        
        data = request.get_json()
        if not data or 'new_password' not in data:
            return jsonify({'success': False, 'error': '缺少新密码'}), 400
        
        new_password = data['new_password']
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': '密码长度至少6位'}), 400
        
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            user.password_hash = AuthService.hash_password(new_password)
            db.commit()
            
            current_user = get_current_user_from_request(db)
            if current_user:
                from api.admin.audit import log_admin_action
                log_admin_action(db, current_user.id, current_user.username,
                               'password_reset', f'重置用户密码: {user.email}')
            
            return jsonify({
                'success': True,
                'message': '密码重置成功'
            }), 200
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/users/<int:user_id>/detail', methods=['GET'])
    @admin_required
    def get_user_detail(user_id):
        """获取用户详细信息（仅管理员）"""
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            license_count = len(user.licenses)
            active_license_count = len([lic for lic in user.licenses if lic.is_active and not lic.is_revoked])
            team_member_count = len(user.team_members)
            
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'license_count': license_count,
                'active_license_count': active_license_count,
                'team_member_count': team_member_count,
                'available_groups': user.available_groups,
                'is_subscription_valid': user.is_subscription_valid
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()