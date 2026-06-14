"""
解析规则和统计规则服务
"""
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.user_models import User, ParseRule, StatRule


class ParseRuleService:
    """消息解析规则服务"""

    @staticmethod
    def create_rule(db: Session, user_id: int, **kwargs) -> Dict:
        """创建解析规则"""
        rule_name = kwargs.get('rule_name', '').strip()
        if not rule_name:
            return {'success': False, 'error': '规则名称不能为空'}

        rule_type = kwargs.get('rule_type', 'regex')
        if rule_type not in ['regex', 'keyword', 'custom']:
            return {'success': False, 'error': '规则类型必须为regex、keyword或custom'}

        new_rule = ParseRule(
            user_id=user_id,
            rule_name=rule_name,
            rule_type=rule_type,
            pattern=kwargs.get('pattern'),
            extract_fields=kwargs.get('extract_fields'),
            priority=kwargs.get('priority', 0),
            is_active=kwargs.get('is_active', True),
            description=kwargs.get('description')
        )

        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)

        return {
            'success': True,
            'rule': new_rule.to_dict()
        }

    @staticmethod
    def update_rule(db: Session, rule_id: int, user_id: int, **kwargs) -> Dict:
        """更新解析规则"""
        rule = db.query(ParseRule).filter(
            ParseRule.id == rule_id,
            ParseRule.user_id == user_id
        ).first()

        if not rule:
            return {'success': False, 'error': '规则不存在或无权操作'}

        updatable_fields = [
            'rule_name', 'rule_type', 'pattern', 'extract_fields',
            'priority', 'is_active', 'description'
        ]
        for field in updatable_fields:
            if field in kwargs:
                setattr(rule, field, kwargs[field])

        db.commit()
        db.refresh(rule)

        return {
            'success': True,
            'rule': rule.to_dict()
        }

    @staticmethod
    def delete_rule(db: Session, rule_id: int, user_id: int) -> Dict:
        """删除解析规则"""
        rule = db.query(ParseRule).filter(
            ParseRule.id == rule_id,
            ParseRule.user_id == user_id
        ).first()

        if not rule:
            return {'success': False, 'error': '规则不存在或无权操作'}

        db.delete(rule)
        db.commit()

        return {'success': True, 'message': '规则已删除'}

    @staticmethod
    def get_rules(db: Session, user_id: int, active_only: bool = False) -> List[Dict]:
        """获取解析规则列表"""
        query = db.query(ParseRule).filter(ParseRule.user_id == user_id)

        if active_only:
            query = query.filter(ParseRule.is_active == True)

        rules = query.order_by(ParseRule.priority.desc(), ParseRule.created_at.desc()).all()
        return [r.to_dict() for r in rules]


class StatRuleService:
    """统计规则服务"""

    @staticmethod
    def create_rule(db: Session, user_id: int, **kwargs) -> Dict:
        """创建统计规则"""
        rule_name = kwargs.get('rule_name', '').strip()
        if not rule_name:
            return {'success': False, 'error': '规则名称不能为空'}

        stat_type = kwargs.get('stat_type', 'daily')
        if stat_type not in ['daily', 'weekly', 'monthly', 'custom']:
            return {'success': False, 'error': '统计类型必须为daily、weekly、monthly或custom'}

        new_rule = StatRule(
            user_id=user_id,
            rule_name=rule_name,
            stat_type=stat_type,
            dimensions=kwargs.get('dimensions'),
            filters=kwargs.get('filters'),
            chart_type=kwargs.get('chart_type', 'bar'),
            refresh_interval=kwargs.get('refresh_interval', 3600),
            is_active=kwargs.get('is_active', True)
        )

        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)

        return {
            'success': True,
            'rule': new_rule.to_dict()
        }

    @staticmethod
    def update_rule(db: Session, rule_id: int, user_id: int, **kwargs) -> Dict:
        """更新统计规则"""
        rule = db.query(StatRule).filter(
            StatRule.id == rule_id,
            StatRule.user_id == user_id
        ).first()

        if not rule:
            return {'success': False, 'error': '规则不存在或无权操作'}

        updatable_fields = [
            'rule_name', 'stat_type', 'dimensions', 'filters',
            'chart_type', 'refresh_interval', 'is_active'
        ]
        for field in updatable_fields:
            if field in kwargs:
                setattr(rule, field, kwargs[field])

        db.commit()
        db.refresh(rule)

        return {
            'success': True,
            'rule': rule.to_dict()
        }

    @staticmethod
    def delete_rule(db: Session, rule_id: int, user_id: int) -> Dict:
        """删除统计规则"""
        rule = db.query(StatRule).filter(
            StatRule.id == rule_id,
            StatRule.user_id == user_id
        ).first()

        if not rule:
            return {'success': False, 'error': '规则不存在或无权操作'}

        db.delete(rule)
        db.commit()

        return {'success': True, 'message': '规则已删除'}

    @staticmethod
    def get_rules(db: Session, user_id: int, active_only: bool = False) -> List[Dict]:
        """获取统计规则列表"""
        query = db.query(StatRule).filter(StatRule.user_id == user_id)

        if active_only:
            query = query.filter(StatRule.is_active == True)

        rules = query.order_by(StatRule.created_at.desc()).all()
        return [r.to_dict() for r in rules]
