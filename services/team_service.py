"""
团队管理服务
提供销售人员的CRUD操作
"""
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.user_models import User, TeamMember


class TeamService:
    """团队管理服务类"""

    @staticmethod
    def create_member(db: Session, user_id: int, **kwargs) -> Dict:
        """
        创建团队成员
        :param db: 数据库会话
        :param user_id: 用户ID
        :param kwargs: 成员信息(name必填, phone, wx_id, managed_group_id, position)
        :return: 创建结果
        """
        name = kwargs.get('name', '').strip()
        if not name:
            return {'success': False, 'error': '姓名不能为空'}

        # 检查是否已存在相同微信号的成员
        wx_id = kwargs.get('wx_id')
        if wx_id:
            existing = db.query(TeamMember).filter(
                TeamMember.user_id == user_id,
                TeamMember.wx_id == wx_id
            ).first()
            if existing:
                return {'success': False, 'error': '该微信号已存在'}

        new_member = TeamMember(
            user_id=user_id,
            name=name,
            phone=kwargs.get('phone'),
            wx_id=wx_id,
            managed_group_id=kwargs.get('managed_group_id'),
            position=kwargs.get('position'),
            is_active=True
        )

        db.add(new_member)
        db.commit()
        db.refresh(new_member)

        return {
            'success': True,
            'member': new_member.to_dict()
        }

    @staticmethod
    def update_member(db: Session, member_id: int, user_id: int, **kwargs) -> Dict:
        """
        更新团队成员信息
        """
        member = db.query(TeamMember).filter(
            TeamMember.id == member_id,
            TeamMember.user_id == user_id
        ).first()

        if not member:
            return {'success': False, 'error': '成员不存在或无权操作'}

        # 更新字段
        if 'name' in kwargs:
            member.name = kwargs['name']
        if 'phone' in kwargs:
            member.phone = kwargs['phone']
        if 'wx_id' in kwargs:
            member.wx_id = kwargs['wx_id']
        if 'managed_group_id' in kwargs:
            member.managed_group_id = kwargs['managed_group_id']
        if 'position' in kwargs:
            member.position = kwargs['position']
        if 'is_active' in kwargs:
            member.is_active = kwargs['is_active']

        db.commit()
        db.refresh(member)

        return {
            'success': True,
            'member': member.to_dict()
        }

    @staticmethod
    def delete_member(db: Session, member_id: int, user_id: int) -> Dict:
        """
        删除团队成员（软删除，设置为非活跃）
        """
        member = db.query(TeamMember).filter(
            TeamMember.id == member_id,
            TeamMember.user_id == user_id
        ).first()

        if not member:
            return {'success': False, 'error': '成员不存在或无权操作'}

        # 检查是否有分配的授权
        active_licenses = [lic for lic in member.assigned_licenses if lic.is_active]
        if active_licenses:
            return {
                'success': False,
                'error': f'该成员还有{len(active_licenses)}个活跃授权，请先重新分配'
            }

        member.is_active = False
        db.commit()

        return {'success': True, 'message': '成员已删除'}

    @staticmethod
    def get_members(db: Session, user_id: int, active_only: bool = True) -> List[Dict]:
        """
        获取团队成员列表
        """
        query = db.query(TeamMember).filter(TeamMember.user_id == user_id)

        if active_only:
            query = query.filter(TeamMember.is_active == True)

        members = query.order_by(TeamMember.created_at.desc()).all()
        return [m.to_dict() for m in members]

    @staticmethod
    def get_member(db: Session, member_id: int, user_id: int) -> Dict:
        """
        获取单个成员详情
        """
        member = db.query(TeamMember).filter(
            TeamMember.id == member_id,
            TeamMember.user_id == user_id
        ).first()

        if not member:
            return None

        return member.to_dict()

    @staticmethod
    def get_team_stats(db: Session, user_id: int) -> Dict:
        """
        获取团队统计信息
        """
        members = db.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.is_active == True
        ).all()

        total_members = len(members)
        total_assigned_licenses = sum(len([lic for lic in m.assigned_licenses if lic.is_active])
                                       for m in members)

        return {
            'total_members': total_members,
            'total_assigned_licenses': total_assigned_licenses,
            'members': [m.to_dict() for m in members]
        }
