"""
规则模板库服务
提供云端规则模板的管理、下载、上传功能
"""
import json
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.user_models import User, RuleTemplate, UserRuleBackup


class RuleTemplateService:
    """规则模板服务类"""

    @staticmethod
    def get_templates(db: Session, industry: str = None, 
                      source_type: str = None, featured_only: bool = False) -> List[Dict]:
        """
        获取规则模板列表
        :param industry: 行业筛选
        :param source_type: 来源筛选
        :param featured_only: 仅精选
        :return: 模板列表
        """
        query = db.query(RuleTemplate).filter(
            RuleTemplate.is_public == True,
            RuleTemplate.is_active == True
        )

        if industry:
            query = query.filter(RuleTemplate.industry == industry)
        if source_type:
            query = query.filter(RuleTemplate.source_type == source_type)
        if featured_only:
            query = query.filter(RuleTemplate.is_featured == True)

        templates = query.order_by(
            RuleTemplate.is_featured.desc(),
            RuleTemplate.download_count.desc()
        ).all()

        return [t.to_dict() for t in templates]

    @staticmethod
    def get_template(db: Session, template_id: int) -> Optional[Dict]:
        """获取单个模板详情"""
        template = db.query(RuleTemplate).filter(
            RuleTemplate.id == template_id,
            RuleTemplate.is_active == True
        ).first()

        if not template:
            return None

        return template.to_dict()

    @staticmethod
    def download_template(db: Session, template_id: int) -> Optional[Dict]:
        """
        下载模板（增加下载次数）
        :return: 模板内容
        """
        template = db.query(RuleTemplate).filter(
            RuleTemplate.id == template_id,
            RuleTemplate.is_active == True
        ).first()

        if not template:
            return None

        # 增加下载次数
        template.download_count += 1
        db.commit()

        return template.to_dict()

    @staticmethod
    def upload_template(db: Session, user_id: int, **kwargs) -> Dict:
        """
        用户上传规则模板
        :param kwargs: template_name, industry, description, parse_rules, stat_rules, reply_rules
        """
        template_name = kwargs.get('template_name', '').strip()
        industry = kwargs.get('industry', '').strip()

        if not template_name or not industry:
            return {'success': False, 'error': '模板名称和行业不能为空'}

        new_template = RuleTemplate(
            template_name=template_name,
            industry=industry,
            description=kwargs.get('description'),
            parse_rules=json.dumps(kwargs.get('parse_rules', []), ensure_ascii=False),
            stat_rules=json.dumps(kwargs.get('stat_rules', []), ensure_ascii=False),
            reply_rules=json.dumps(kwargs.get('reply_rules', []), ensure_ascii=False),
            source_type='user',
            author_id=user_id,
            is_public=kwargs.get('is_public', True),
            is_active=True
        )

        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        return {
            'success': True,
            'template': new_template.to_dict()
        }

    @staticmethod
    def save_user_backup(db: Session, user_id: int, **kwargs) -> Dict:
        """
        保存用户规则备份到云端
        :param kwargs: backup_name, parse_rules, stat_rules, reply_rules, template_id
        """
        # 将之前的当前版本设为非当前
        db.query(UserRuleBackup).filter(
            UserRuleBackup.user_id == user_id,
            UserRuleBackup.is_current == True
        ).update({'is_current': False})

        backup = UserRuleBackup(
            user_id=user_id,
            backup_name=kwargs.get('backup_name', f'备份_{datetime.now().strftime("%Y%m%d_%H%M")}'),
            parse_rules=json.dumps(kwargs.get('parse_rules', []), ensure_ascii=False),
            stat_rules=json.dumps(kwargs.get('stat_rules', []), ensure_ascii=False),
            reply_rules=json.dumps(kwargs.get('reply_rules', []), ensure_ascii=False),
            template_id=kwargs.get('template_id'),
            version=kwargs.get('version', '1.0'),
            is_current=True
        )

        db.add(backup)
        db.commit()
        db.refresh(backup)

        return {
            'success': True,
            'backup': backup.to_dict()
        }

    @staticmethod
    def get_user_backups(db: Session, user_id: int) -> List[Dict]:
        """获取用户的规则备份列表"""
        backups = db.query(UserRuleBackup).filter(
            UserRuleBackup.user_id == user_id
        ).order_by(UserRuleBackup.created_at.desc()).all()

        return [b.to_dict() for b in backups]

    @staticmethod
    def get_industries(db: Session) -> List[str]:
        """获取所有行业分类"""
        industries = db.query(RuleTemplate.industry).filter(
            RuleTemplate.is_public == True,
            RuleTemplate.is_active == True
        ).distinct().all()

        return [i[0] for i in industries if i[0]]
