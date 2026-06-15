"""
管理员权限管理API
包含权限列表、用户权限配置、角色管理
"""
from flask import request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import admin_required, get_current_user_from_request


def init_permissions_routes(admin_bp):
    """初始化权限管理路由"""
    
    @admin_bp.route('/permissions', methods=['GET'])
    @admin_required
    def get_all_permissions():
        """获取所有可用权限列表（仅管理员）"""
        from services.permission_service import PermissionService
        
        return jsonify({
            'success': True,
            'permissions': PermissionService.get_all_permissions(),
            'groups': PermissionService.get_permission_groups()
        }), 200


    @admin_bp.route('/permissions/user/<int:user_id>', methods=['GET'])
    @admin_required
    def get_user_permissions(user_id):
        """获取用户权限列表（仅管理员）"""
        from services.permission_service import PermissionService
        
        db: Session = get_db_session()
        try:
            permissions = PermissionService.get_user_permissions(db, user_id)
            
            from models.user_models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'permissions': list(permissions)
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/permissions/user/<int:user_id>', methods=['PUT'])
    @admin_required
    def update_user_permissions(user_id):
        """更新用户权限（仅管理员）"""
        from services.permission_service import PermissionService
        
        data = request.get_json()
        if not data or 'permissions' not in data:
            return jsonify({'success': False, 'error': '缺少权限列表'}), 400
        
        db: Session = get_db_session()
        try:
            result = PermissionService.grant_permissions_to_user(db, user_id, data['permissions'])
            
            if result['success']:
                current_user = get_current_user_from_request(db)
                if current_user:
                    from api.admin.audit import log_admin_action
                    log_admin_action(db, current_user.id, current_user.username,
                                   'permission_update', f'更新用户权限: 用户ID {user_id}, 权限: {", ".join(data["permissions"])}')
                
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'user_id': user_id,
                    'permissions': data['permissions']
                }), 200
            else:
                return jsonify(result), 400
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/permissions/check', methods=['POST'])
    @admin_required
    def check_permission():
        """检查用户是否拥有指定权限（仅管理员）"""
        from services.permission_service import PermissionService
        
        data = request.get_json()
        if not data or 'user_id' not in data or 'feature_code' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        db: Session = get_db_session()
        try:
            has_permission = PermissionService.can_access_feature(db, data['user_id'], data['feature_code'])
            
            return jsonify({
                'success': True,
                'user_id': data['user_id'],
                'feature_code': data['feature_code'],
                'has_permission': has_permission
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()


    @admin_bp.route('/roles', methods=['GET'])
    @admin_required
    def get_all_roles():
        """获取所有角色定义（仅管理员）"""
        roles = {
            'super_admin': {
                'name': '超级管理员',
                'description': '拥有系统全部权限',
                'permissions': ['all']
            },
            'admin': {
                'name': '管理员',
                'description': '拥有管理权限，可管理用户、授权码等',
                'permissions': ['order_manage', 'customer_manage', 'product_manage', 'report_view', 'report_export']
            },
            'user': {
                'name': '普通用户',
                'description': '只能访问自己的数据',
                'permissions': []
            }
        }
        
        return jsonify({
            'success': True,
            'roles': roles
        }), 200


    @admin_bp.route('/roles/<string:role_name>/permissions', methods=['GET'])
    @admin_required
    def get_role_permissions(role_name):
        """获取指定角色的权限列表（仅管理员）"""
        role_permissions = {
            'super_admin': ['all'],
            'admin': ['order_manage', 'customer_manage', 'product_manage', 'report_view', 'report_export', 'system_config', 'audit_view'],
            'user': []
        }
        
        from services.permission_service import PermissionService
        
        if role_name not in role_permissions:
            return jsonify({'success': False, 'error': '角色不存在'}), 404
        
        permissions_with_names = []
        all_permissions = PermissionService.get_all_permissions()
        
        for perm_code in role_permissions[role_name]:
            permissions_with_names.append({
                'code': perm_code,
                'name': all_permissions.get(perm_code, perm_code)
            })
        
        return jsonify({
            'success': True,
            'role': role_name,
            'permissions': permissions_with_names
        }), 200