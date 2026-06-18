"""
指令配置管理服务
管理机器人固定指令集、自然语言语义扩展、参数提取和多轮对话
"""
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from models.user_models import CommandConfig
from database.db_config import SessionLocal

logger = logging.getLogger(__name__)

# 通用参数提取正则
_PARAM_PATTERNS = {
    'amount': r'(?:￥|¥)?\s*(\d+(?:\.\d{1,2})?)\s*(?:元|块|万元|万)',
    'quantity': r'(\d+(?:\.\d+)?)\s*(?:方|吨|升|袋|箱|个|件|套|台|辆|斤|公斤|kg|KG)',
    'phone': r'(1[3-9]\d{9})',
    'date': r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:今天|明天|后天|昨天|大后天)',
    'person_name': r'(?:工人|司机|师傅|客户|会员)?\s*([\u4e00-\u9fa5]{2,4})\s*(?:在|的|是)',
    'site_name': r'(城[东西南北]|[\u4e00-\u9fa5]{2,6})(?:工地|项目|仓库|门店)',
    'order_no': r'(?:订单号|单号|编号)[：:]?\s*([A-Za-z0-9]+)',
}

# 多轮对话状态缓存（按用户ID存储）
_conversation_context: Dict[str, Dict] = {}


class CommandConfigService:
    """指令配置服务"""

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
            'examples': json.dumps(['报表', '今日统计', '今天订单多少']),
            'param_schema': json.dumps({'date': '可选，日期筛选'}),
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
            'description': '客户查询当日订单详情和金额',
            'examples': json.dumps(['查订单', '我的订单', '多少钱']),
            'param_schema': json.dumps({}),
            'is_active': 1
        },
        {
            'command_name': 'help',
            'keywords': json.dumps(['帮助', 'help', '指令', '怎么用', '功能']),
            'patterns': json.dumps([
                r'(?:帮助|help|指令|怎么用|功能)'
            ]),
            'response_template': 'help_text',
            'description': '显示帮助信息与指令列表',
            'examples': json.dumps(['帮助', '怎么用', 'help']),
            'param_schema': json.dumps({}),
            'is_active': 1
        }
    ]

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        return SessionLocal()

    def init_default_commands(self) -> Dict:
        db = self._get_db()
        try:
            created_count = 0
            for cmd_data in self.DEFAULT_COMMANDS:
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
        """匹配指令（保持向后兼容）"""
        result = self.match_command_with_params(message)
        if result:
            return {
                'command_name': result['command_name'],
                'confidence': result['confidence'],
                'matched_type': result['matched_type'],
                'response_template': result['response_template']
            }
        return None

    def match_command_with_params(self, message: str, context: Dict = None) -> Optional[Dict]:
        """
        根据消息内容匹配指令并提取参数

        参数:
        - message: 用户消息内容
        - context: 多轮对话上下文(可选)

        返回:
        {
            "command_name": "sales_report",
            "confidence": 0.95,
            "matched_type": "keyword",
            "response_template": "sales_report",
            "params": {"amount": 500, "site": "城东工地", ...},
            "examples": ["使用示例1", "使用示例2"],
            "param_schema": {"amount": "金额"}
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

            if best_match and best_confidence >= 0.6:
                best_match.usage_count += 1
                db.commit()

                params = self._extract_command_params(message, best_match)

                examples = []
                try:
                    examples = json.loads(best_match.examples) if best_match.examples else []
                except Exception:
                    pass

                schema = {}
                try:
                    schema = json.loads(best_match.param_schema) if best_match.param_schema else {}
                except Exception:
                    pass

                return {
                    'command_name': best_match.command_name,
                    'confidence': round(best_confidence, 2),
                    'matched_type': 'keyword' if best_confidence >= 0.8 else 'pattern',
                    'response_template': best_match.response_template,
                    'params': params,
                    'examples': examples,
                    'param_schema': schema
                }

            return None
        except Exception as e:
            logger.error(f"匹配指令失败: {e}", exc_info=True)
            return None

    def _extract_command_params(self, message: str, cmd: CommandConfig) -> Dict:
        """从消息中提取结构化参数"""
        params = {}

        # 从param_schema中获取要提取的字段
        try:
            schema = json.loads(cmd.param_schema) if cmd.param_schema else {}
        except Exception:
            schema = {}

        # 按schema定义逐个提取
        for field_name, field_desc in schema.items():
            if field_name in ['amount', 'money']:
                m = re.search(r'(?:￥|¥)?\s*(\d+(?:\.\d{1,2})?)\s*(?:元|块|万元|万)?', message)
                if m:
                    val = float(m.group(1))
                    if '万' in message[m.end():m.end()+1]:
                        val *= 10000
                    params[field_name] = val

            elif field_name in ['quantity', 'count', 'volume']:
                m = re.search(r'(\d+(?:\.\d+)?)\s*(?:方|吨|升|袋|箱|个|件|套|台|辆|斤|公斤|kg|KG)', message)
                if m:
                    params[field_name] = float(m.group(1))
                else:
                    m = re.search(r'(\d+)\s*', message)
                    if m:
                        params[field_name] = float(m.group(1))

            elif field_name in ['phone', 'mobile']:
                m = re.search(r'1[3-9]\d{9}', message)
                if m:
                    params[field_name] = m.group(0)

            elif field_name in ['date', 'date_str']:
                date_map = {'今天': 'today', '明天': 'tomorrow', '后天': 'day_after_tomorrow', '昨天': 'yesterday'}
                for word, eng in date_map.items():
                    if word in message:
                        if eng == 'today':
                            params[field_name] = datetime.now().strftime('%Y-%m-%d')
                        elif eng == 'tomorrow':
                            params[field_name] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                        elif eng == 'day_after_tomorrow':
                            params[field_name] = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
                        elif eng == 'yesterday':
                            params[field_name] = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                        break
                if field_name not in params:
                    m = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', message)
                    if m:
                        params[field_name] = m.group(1).replace('/', '-')

            elif field_name in ['site_name', 'location']:
                m = re.search(r'(城[东西南北]|[\u4e00-\u9fa5]{2,6})(?:工地|项目|仓库|门店|厂区)', message)
                if m:
                    params[field_name] = m.group(0)
                else:
                    m = re.search(r'([\u4e00-\u9fa5]{2,6})(?:工地|项目|仓库)', message)
                    if m:
                        params[field_name] = m.group(0)

            elif field_name in ['name', 'person', 'worker_name', 'customer_name']:
                m = re.search(r'(?:给|帮|替)\s*([\u4e00-\u9fa5]{2,4})', message)
                if m:
                    params[field_name] = m.group(1)
                else:
                    m = re.search(r'([\u4e00-\u9fa5]{2,4})\s*(?:的|是|在)', message)
                    if m:
                        params[field_name] = m.group(1)

            elif field_name in ['order_no', 'order_id']:
                m = re.search(r'(?:订单号|单号|编号)[：:]?\s*([A-Za-z0-9\-]+)', message)
                if m:
                    params[field_name] = m.group(1)
                else:
                    m = re.search(r'([A-Z0-9]{8,})', message)
                    if m:
                        params[field_name] = m.group(1)

            elif field_name == 'text':
                params[field_name] = message.strip()

            elif field_name in ['unit']:
                m = re.search(r'(\d+(?:\.\d+)?)\s*(方|吨|升|袋|箱|个|件|套|台|辆|斤|公斤)', message)
                if m:
                    params['quantity'] = float(m.group(1))
                    params[field_name] = m.group(2)

            elif field_name == 'category':
                cats = ['燃油费', '过路费', '维修费', '生活补贴', '易耗品', '材料费', '运输费']
                for cat in cats:
                    if cat in message:
                        params[field_name] = cat
                        break
                if field_name not in params:
                    params[field_name] = '其他'

        return params

    def _calculate_match_confidence(self, message: str, cmd: CommandConfig) -> float:
        """
        计算消息与指令的匹配置信度

        评分规则:
        - 关键词匹配: 匹配1个关键词得0.7分,每多匹配1个加0.1分,最高0.9分
        - 正则匹配: 0.95分
        """
        confidence = 0.0
        message_lower = message.lower()

        try:
            keywords = json.loads(cmd.keywords) if cmd.keywords else []
            matched_keywords = [kw for kw in keywords if kw.lower() in message_lower]
            if matched_keywords:
                keyword_score = min(0.7 + len(matched_keywords) * 0.1, 0.9)
                confidence = max(confidence, keyword_score)
        except Exception:
            pass

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
        db = self._get_db()
        try:
            if not kwargs.get('command_name'):
                return {'success': False, 'error': '指令名称不能为空'}
            existing = db.query(CommandConfig).filter(
                CommandConfig.command_name == kwargs['command_name']
            ).first()
            if existing:
                return {'success': False, 'error': f"指令 '{kwargs['command_name']}' 已存在"}
            for key in ['keywords', 'patterns', 'examples', 'param_schema']:
                if isinstance(kwargs.get(key), list):
                    kwargs[key] = json.dumps(kwargs[key])
                elif isinstance(kwargs.get(key), dict):
                    kwargs[key] = json.dumps(kwargs[key])
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
        db = self._get_db()
        try:
            cmd = db.query(CommandConfig).filter(CommandConfig.id == command_id).first()
            if not cmd:
                return {'success': False, 'error': f'指令不存在: {command_id}'}
            for key, value in kwargs.items():
                if hasattr(cmd, key) and key != 'id':
                    if key in ['keywords', 'patterns', 'examples', 'param_schema']:
                        if isinstance(value, list):
                            value = json.dumps(value)
                        elif isinstance(value, dict):
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
        db = self._get_db()
        try:
            if 'commands' not in backup_data:
                return {'success': False, 'error': '无效的备份数据'}
            restored_count = 0
            for cmd_data in backup_data['commands']:
                existing = db.query(CommandConfig).filter(
                    CommandConfig.command_name == cmd_data['command_name']
                ).first()
                if existing:
                    for key, value in cmd_data.items():
                        if key != 'id' and hasattr(existing, key):
                            setattr(existing, key, value)
                else:
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

    def register_plugin_commands(self, plugin_name: str, commands: List[Dict]) -> Dict:
        """注册插件指令"""
        db = self._get_db()
        try:
            created_count = 0
            updated_count = 0
            for cmd_data in commands:
                cmd_name = f"{plugin_name}:{cmd_data['command_name']}"
                existing = db.query(CommandConfig).filter(
                    CommandConfig.command_name == cmd_name
                ).first()
                if existing:
                    for key, value in cmd_data.items():
                        if key in ['keywords', 'patterns', 'examples', 'param_schema']:
                            if isinstance(value, list):
                                value = json.dumps(value)
                            elif isinstance(value, dict):
                                value = json.dumps(value)
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    updated_count += 1
                else:
                    data = cmd_data.copy()
                    data['command_name'] = cmd_name
                    for key in ['keywords', 'patterns', 'examples', 'param_schema']:
                        if key in data:
                            if isinstance(data[key], list):
                                data[key] = json.dumps(data[key])
                            elif isinstance(data[key], dict):
                                data[key] = json.dumps(data[key])
                    cmd = CommandConfig(**data)
                    db.add(cmd)
                    created_count += 1
            db.commit()
            logger.info(f"插件指令注册成功: {plugin_name} - 创建{created_count}条, 更新{updated_count}条")
            return {'success': True, 'created_count': created_count, 'updated_count': updated_count}
        except Exception as e:
            db.rollback()
            logger.error(f"插件指令注册失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_plugin_commands(self, plugin_name: str) -> List[Dict]:
        db = self._get_db()
        try:
            prefix = f"{plugin_name}:"
            commands = db.query(CommandConfig).filter(
                CommandConfig.command_name.like(f"{prefix}%"),
                CommandConfig.is_active == 1
            ).all()
            return [self._cmd_to_dict(cmd) for cmd in commands]
        except Exception as e:
            logger.error(f"获取插件指令失败: {e}", exc_info=True)
            return []

    def unregister_plugin_commands(self, plugin_name: str) -> Dict:
        db = self._get_db()
        try:
            prefix = f"{plugin_name}:"
            deleted_count = db.query(CommandConfig).filter(
                CommandConfig.command_name.like(f"{prefix}%")
            ).update({'is_active': 0})
            db.commit()
            logger.info(f"插件指令卸载成功: {plugin_name} - 禁用{deleted_count}条")
            return {'success': True, 'deleted_count': deleted_count}
        except Exception as e:
            db.rollback()
            logger.error(f"插件指令卸载失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_conversation_context(self, user_id: str) -> Dict:
        """获取用户的多轮对话上下文"""
        if user_id not in _conversation_context:
            _conversation_context[user_id] = {}
        return _conversation_context[user_id]

    def set_conversation_context(self, user_id: str, key: str, value: any):
        """设置多轮对话上下文"""
        if user_id not in _conversation_context:
            _conversation_context[user_id] = {}
        _conversation_context[user_id][key] = value

    def clear_conversation_context(self, user_id: str):
        """清除用户的多轮对话上下文"""
        if user_id in _conversation_context:
            del _conversation_context[user_id]

    def _cmd_to_dict(self, cmd: CommandConfig) -> Dict:
        try:
            keywords = json.loads(cmd.keywords) if cmd.keywords else []
        except Exception:
            keywords = []
        try:
            patterns = json.loads(cmd.patterns) if cmd.patterns else []
        except Exception:
            patterns = []
        try:
            examples = json.loads(cmd.examples) if cmd.examples else []
        except Exception:
            examples = []
        try:
            param_schema = json.loads(cmd.param_schema) if cmd.param_schema else {}
        except Exception:
            param_schema = {}

        return {
            'id': cmd.id,
            'command_name': cmd.command_name,
            'keywords': keywords,
            'patterns': patterns,
            'response_template': cmd.response_template,
            'description': cmd.description,
            'examples': examples,
            'param_schema': param_schema,
            'is_active': cmd.is_active,
            'usage_count': cmd.usage_count,
            'created_at': cmd.created_at.isoformat() if cmd.created_at else None
        }


# 全局单例
command_config_service = CommandConfigService()