"""
指令配置管理服务
管理机器人固定指令集和自然语言语义扩展
"""
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from models.user_models import CommandConfig
from database.db_config import SessionLocal

logger = logging.getLogger(__name__)


class CommandConfigService:
    """指令配置服务"""

    # 默认指令集
    DEFAULT_COMMANDS = [
        {
            'command_name': 'sales_report',
            'keywords': json.dumps(['报表', '统计', '汇总', '今日报表', '销售统计']),
            'patterns': json.dumps([
                r'(?:报表|统计|汇总)',
                r'(?:今日|今天).*(?:报表|统计)',
                r'(?:配送|订单).*(?:多少|统计)'
            ]),
            'response_template': 'sales_report',
            'description': '销售员查询负责线路的订单汇总',
            'is_active': 1
        },
        {
            'command_name': 'customer_query',
            'keywords': json.dumps(['查订单', '查询', '多少钱', '我的订单', '查货']),
            'patterns': json.dumps([
                r'(?:查|查询).*(?:订单|货)',
                r'(?:多少|什么价格|多少钱)',
                r'(?:我的|本人).*(?:订单|货)'
            ]),
            'response_template': 'customer_query',
            'description': '客户查询当日订单详情',
            'is_active': 1
        },
        {
            'command_name': 'help',
            'keywords': json.dumps(['帮助', 'help', '指令', '怎么用']),
            'patterns': json.dumps([
                r'(?:帮助|help|指令|怎么用)'
            ]),
            'response_template': 'help_text',
            'description': '显示帮助信息',
            'is_active': 1
        }
    ]

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """获取数据库会话"""
        return SessionLocal()

    def init_default_commands(self) -> Dict:
        """
        初始化默认指令集

        返回:
        {'success': True, 'created_count': 3}
        """
        db = self._get_db()
        try:
            created_count = 0
            for cmd_data in self.DEFAULT_COMMANDS:
                # 检查是否已存在
                existing = db.query(CommandConfig).filter(
                    CommandConfig.command_name == cmd_data['command_name']
                ).first()

                if not existing:
                    cmd = CommandConfig(**cmd_data)
                    db.add(cmd)
                    created_count += 1

            db.commit()
            logger.info(f"初始化默认指令集成功: 创建{created_count}条")
            return {'success': True, 'created_count': created_count}

        except Exception as e:
            db.rollback()
            logger.error(f"初始化默认指令集失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_active_commands(self) -> List[Dict]:
        """获取所有激活的指令配置"""
        db = self._get_db()
        try:
            commands = db.query(CommandConfig).filter(
                CommandConfig.is_active == 1
            ).order_by(CommandConfig.usage_count.desc()).all()

            return [self._cmd_to_dict(cmd) for cmd in commands]

        except Exception as e:
            logger.error(f"获取指令配置失败: {e}", exc_info=True)
            return []

    def match_command(self, message: str) -> Optional[Dict]:
        """
        根据消息内容匹配指令

        匹配策略:
        1. 关键词匹配(任意一个关键词出现在消息中)
        2. 正则表达式匹配(按优先级)

        参数:
        - message: 用户消息内容

        返回:
        {
            "command_name": "sales_report",
            "confidence": 0.95,
            "matched_type": "keyword"  # keyword/pattern
        }
        """
        db = self._get_db()
        try:
            commands = db.query(CommandConfig).filter(
                CommandConfig.is_active == 1
            ).order_by(CommandConfig.usage_count.desc()).all()

            best_match = None
            best_confidence = 0.0

            for cmd in commands:
                confidence = self._calculate_match_confidence(message, cmd)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = cmd

            if best_match and best_confidence >= 0.6:  # 置信度阈值
                # 更新使用次数
                best_match.usage_count += 1
                db.commit()

                return {
                    'command_name': best_match.command_name,
                    'confidence': round(best_confidence, 2),
                    'matched_type': 'keyword' if best_confidence >= 0.8 else 'pattern',
                    'response_template': best_match.response_template
                }

            return None

        except Exception as e:
            logger.error(f"匹配指令失败: {e}", exc_info=True)
            return None

    def _calculate_match_confidence(self, message: str, cmd: CommandConfig) -> float:
        """
        计算消息与指令的匹配置信度

        评分规则:
        - 关键词匹配: 每个关键词0.2分,最高0.8分
        - 正则匹配: 0.9-1.0分
        """
        confidence = 0.0
        message_lower = message.lower()

        # 1. 关键词匹配
        try:
            keywords = json.loads(cmd.keywords) if cmd.keywords else []
            matched_keywords = [kw for kw in keywords if kw.lower() in message_lower]
            if matched_keywords:
                keyword_score = min(len(matched_keywords) * 0.2, 0.8)
                confidence = max(confidence, keyword_score)
        except Exception:
            pass

        # 2. 正则表达式匹配
        try:
            patterns = json.loads(cmd.patterns) if cmd.patterns else []
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    confidence = max(confidence, 0.95)
                    break
        except Exception:
            pass

        return confidence

    def create_command(self, **kwargs) -> Dict:
        """创建新指令配置"""
        db = self._get_db()
        try:
            # 验证必填字段
            if not kwargs.get('command_name'):
                return {'success': False, 'error': '指令名称不能为空'}

            # 检查是否已存在
            existing = db.query(CommandConfig).filter(
                CommandConfig.command_name == kwargs['command_name']
            ).first()
            if existing:
                return {'success': False, 'error': f"指令 '{kwargs['command_name']}' 已存在"}

            # 序列化列表字段
            if isinstance(kwargs.get('keywords'), list):
                kwargs['keywords'] = json.dumps(kwargs['keywords'])
            if isinstance(kwargs.get('patterns'), list):
                kwargs['patterns'] = json.dumps(kwargs['patterns'])

            cmd = CommandConfig(**kwargs)
            db.add(cmd)
            db.commit()

            logger.info(f"创建指令成功: {cmd.command_name}")
            return {'success': True, 'command_id': cmd.id}

        except Exception as e:
            db.rollback()
            logger.error(f"创建指令失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def update_command(self, command_id: int, **kwargs) -> Dict:
        """更新指令配置"""
        db = self._get_db()
        try:
            cmd = db.query(CommandConfig).filter(CommandConfig.id == command_id).first()
            if not cmd:
                return {'success': False, 'error': f'指令不存在: {command_id}'}

            # 更新字段
            for key, value in kwargs.items():
                if hasattr(cmd, key) and key != 'id':
                    # 序列化列表字段
                    if key in ['keywords', 'patterns'] and isinstance(value, list):
                        value = json.dumps(value)
                    setattr(cmd, key, value)

            db.commit()
            logger.info(f"更新指令成功: command_id={command_id}")
            return {'success': True}

        except Exception as e:
            db.rollback()
            logger.error(f"更新指令失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def delete_command(self, command_id: int) -> Dict:
        """删除指令配置(软删除)"""
        db = self._get_db()
        try:
            cmd = db.query(CommandConfig).filter(CommandConfig.id == command_id).first()
            if not cmd:
                return {'success': False, 'error': f'指令不存在: {command_id}'}

            cmd.is_active = 0
            db.commit()

            logger.info(f"删除指令成功: command_id={command_id}")
            return {'success': True}

        except Exception as e:
            db.rollback()
            logger.error(f"删除指令失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_usage_statistics(self) -> Dict:
        """获取指令使用统计"""
        db = self._get_db()
        try:
            commands = db.query(CommandConfig).filter(
                CommandConfig.is_active == 1
            ).order_by(CommandConfig.usage_count.desc()).all()

            total_usage = sum(cmd.usage_count for cmd in commands)

            return {
                'success': True,
                'total_commands': len(commands),
                'total_usage': total_usage,
                'commands': [
                    {
                        'command_name': cmd.command_name,
                        'description': cmd.description,
                        'usage_count': cmd.usage_count,
                        'usage_percentage': round(cmd.usage_count / total_usage * 100, 2) if total_usage > 0 else 0
                    }
                    for cmd in commands
                ]
            }

        except Exception as e:
            logger.error(f"获取使用统计失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def backup_commands(self) -> Dict:
        """备份所有指令配置到JSON"""
        db = self._get_db()
        try:
            commands = db.query(CommandConfig).all()

            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'commands': [self._cmd_to_dict(cmd) for cmd in commands]
            }

            return {'success': True, 'data': backup_data}

        except Exception as e:
            logger.error(f"备份指令配置失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def restore_commands(self, backup_data: Dict) -> Dict:
        """从JSON恢复指令配置"""
        db = self._get_db()
        try:
            if 'commands' not in backup_data:
                return {'success': False, 'error': '无效的备份数据'}

            restored_count = 0
            for cmd_data in backup_data['commands']:
                # 检查是否已存在
                existing = db.query(CommandConfig).filter(
                    CommandConfig.command_name == cmd_data['command_name']
                ).first()

                if existing:
                    # 更新现有指令
                    for key, value in cmd_data.items():
                        if key != 'id' and hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # 创建新指令
                    cmd = CommandConfig(**{k: v for k, v in cmd_data.items() if k != 'id'})
                    db.add(cmd)

                restored_count += 1

            db.commit()
            logger.info(f"恢复指令配置成功: {restored_count}条")
            return {'success': True, 'restored_count': restored_count}

        except Exception as e:
            db.rollback()
            logger.error(f"恢复指令配置失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _cmd_to_dict(self, cmd: CommandConfig) -> Dict:
        """将CommandConfig对象转换为字典"""
        try:
            keywords = json.loads(cmd.keywords) if cmd.keywords else []
        except Exception:
            keywords = []

        try:
            patterns = json.loads(cmd.patterns) if cmd.patterns else []
        except Exception:
            patterns = []

        return {
            'id': cmd.id,
            'command_name': cmd.command_name,
            'keywords': keywords,
            'patterns': patterns,
            'response_template': cmd.response_template,
            'description': cmd.description,
            'is_active': cmd.is_active,
            'usage_count': cmd.usage_count,
            'created_at': cmd.created_at.isoformat() if cmd.created_at else None
        }


# 全局单例
command_config_service = CommandConfigService()
