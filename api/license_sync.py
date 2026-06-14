"""
授权码同步API
支持从桌面端同步授权码和销售员绑定关系
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from models.user_models import License, TeamMember
from datetime import datetime

sync_bp = Blueprint('license_sync', __name__, url_prefix='/api/license/sync')


@sync_bp.route('/from-desktop', methods=['POST'])
@login_required
def sync_licenses_from_desktop():
    """
    从桌面端同步授权码信息
    Body: {
        "licenses": [
            {
                "license_code": "ABC123...",
                "bound_to": "group_xxx",
                "assigned_salesperson": {
                    "name": "张三",
                    "phone": "13800138000",
                    "wx_id": "zhangsan_wx"
                },
                "expires_at": "2026-12-31T23:59:59",
                "is_active": true
            }
        ]
    }
    """
    data = request.get_json()
    if not data or 'licenses' not in data:
        return jsonify({'success': False, 'error': '请提供授权码列表'}), 400
    
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        synced_count = 0
        errors = []
        
        for lic_data in data['licenses']:
            try:
                license_code = lic_data.get('license_code')
                if not license_code:
                    errors.append(f"缺少授权码")
                    continue
                
                # 查找或创建授权码
                license_obj = db.query(License).filter(
                    License.license_code == license_code
                ).first()
                
                if not license_obj:
                    # 创建新的授权码记录
                    license_obj = License(
                        user_id=user.id,
                        license_code=license_code,
                        license_type='monthly',  # 默认月付
                        is_active=lic_data.get('is_active', False),
                        expires_at=datetime.fromisoformat(lic_data['expires_at']) if lic_data.get('expires_at') else None
                    )
                    db.add(license_obj)
                else:
                    # 更新现有授权码
                    license_obj.is_active = lic_data.get('is_active', license_obj.is_active)
                    if lic_data.get('expires_at'):
                        license_obj.expires_at = datetime.fromisoformat(lic_data['expires_at'])
                    if lic_data.get('bound_to'):
                        license_obj.bound_to = lic_data['bound_to']
                
                # 处理销售员信息
                salesperson_data = lic_data.get('assigned_salesperson')
                if salesperson_data:
                    # 查找或创建销售员
                    team_member = db.query(TeamMember).filter(
                        TeamMember.user_id == user.id,
                        TeamMember.name == salesperson_data['name']
                    ).first()
                    
                    if not team_member:
                        team_member = TeamMember(
                            user_id=user.id,
                            name=salesperson_data['name'],
                            phone=salesperson_data.get('phone'),
                            wx_id=salesperson_data.get('wx_id'),
                            is_active=True
                        )
                        db.add(team_member)
                        db.flush()  # 获取ID
                    
                    # 关联授权码和销售员
                    license_obj.assigned_to = team_member.id
                
                synced_count += 1
                
            except Exception as e:
                errors.append(f"处理授权码 {lic_data.get('license_code', 'unknown')} 时出错: {str(e)}")
                continue
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功同步 {synced_count} 个授权码',
            'synced_count': synced_count,
            'errors': errors if errors else None
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@sync_bp.route('/status', methods=['GET'])
@login_required
def get_sync_status():
    """获取同步状态统计"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        
        # 统计有销售员绑定的授权码数量
        licenses_with_salesperson = db.query(License).filter(
            License.user_id == user.id,
            License.assigned_to != None
        ).count()
        
        # 统计总授权码数量
        total_licenses = db.query(License).filter(
            License.user_id == user.id
        ).count()
        
        return jsonify({
            'success': True,
            'sync_status': {
                'total_licenses': total_licenses,
                'licenses_with_salesperson': licenses_with_salesperson,
                'sync_percentage': round((licenses_with_salesperson / total_licenses * 100) if total_licenses > 0 else 0, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
