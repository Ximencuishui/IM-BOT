"""
机器人配置服务
管理微信Hook机器人的配置和运行状态
"""
import logging
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.user_models import User, RobotConfig, ReplyRule

logger = logging.getLogger(__name__)


class RobotService:
    """机器人配置服务类"""

    @staticmethod
    def create_config(db: Session, user_id: int, **kwargs) -> Dict:
        """
        创建机器人配置
        :param db: 数据库会话
        :param user_id: 用户ID
        :param kwargs: 配置信息(config_name, wechat_path, hook_dll_path等)
        :return: 创建结果
        """
        config_name = kwargs.get('config_name', '默认机器人')

        # 如果设为默认，先取消其他默认配置
        is_default = kwargs.get('is_default', False)
        if is_default:
            db.query(RobotConfig).filter(
                RobotConfig.user_id == user_id,
                RobotConfig.is_default == True
            ).update({'is_default': False})

        new_config = RobotConfig(
            user_id=user_id,
            config_name=config_name,
            wechat_path=kwargs.get('wechat_path'),
            wechat_version=kwargs.get('wechat_version'),
            hook_dll_path=kwargs.get('hook_dll_path'),
            tcp_server_host=kwargs.get('tcp_server_host', '127.0.0.1'),
            tcp_server_port=kwargs.get('tcp_server_port', 8888),
            auto_start=kwargs.get('auto_start', False),
            is_default=is_default,
            status='stopped'
        )

        db.add(new_config)
        db.commit()
        db.refresh(new_config)

        return {
            'success': True,
            'config': new_config.to_dict()
        }

    @staticmethod
    def update_config(db: Session, config_id: int, user_id: int, **kwargs) -> Dict:
        """
        更新机器人配置
        """
        config = db.query(RobotConfig).filter(
            RobotConfig.id == config_id,
            RobotConfig.user_id == user_id
        ).first()

        if not config:
            return {'success': False, 'error': '配置不存在或无权操作'}

        # 如果设为默认，先取消其他默认配置
        if kwargs.get('is_default'):
            db.query(RobotConfig).filter(
                RobotConfig.user_id == user_id,
                RobotConfig.id != config_id,
                RobotConfig.is_default == True
            ).update({'is_default': False})

        # 更新字段
        updatable_fields = [
            'config_name', 'wechat_path', 'wechat_version', 'hook_dll_path',
            'tcp_server_host', 'tcp_server_port', 'auto_start', 'is_default'
        ]
        for field in updatable_fields:
            if field in kwargs:
                setattr(config, field, kwargs[field])

        db.commit()
        db.refresh(config)

        return {
            'success': True,
            'config': config.to_dict()
        }

    @staticmethod
    def delete_config(db: Session, config_id: int, user_id: int) -> Dict:
        """
        删除机器人配置
        """
        config = db.query(RobotConfig).filter(
            RobotConfig.id == config_id,
            RobotConfig.user_id == user_id
        ).first()

        if not config:
            return {'success': False, 'error': '配置不存在或无权操作'}

        if config.status == 'running':
            return {'success': False, 'error': '请先停止运行中的机器人'}

        db.delete(config)
        db.commit()

        return {'success': True, 'message': '配置已删除'}

    @staticmethod
    def get_configs(db: Session, user_id: int) -> List[Dict]:
        """获取用户的机器人配置列表"""
        configs = db.query(RobotConfig).filter(
            RobotConfig.user_id == user_id
        ).order_by(RobotConfig.is_default.desc(), RobotConfig.created_at.desc()).all()

        return [c.to_dict() for c in configs]

    @staticmethod
    def get_config(db: Session, config_id: int, user_id: int) -> Dict:
        """获取单个机器人配置"""
        config = db.query(RobotConfig).filter(
            RobotConfig.id == config_id,
            RobotConfig.user_id == user_id
        ).first()

        if not config:
            return None

        return config.to_dict()

    @staticmethod
    def start_robot(db: Session, config_id: int, user_id: int) -> Dict:
        """
        启动机器人（模拟，实际需要调用Hook程序）
        """
        config = db.query(RobotConfig).filter(
            RobotConfig.id == config_id,
            RobotConfig.user_id == user_id
        ).first()

        if not config:
            return {'success': False, 'error': '配置不存在或无权操作'}

        if config.status == 'running':
            return {'success': False, 'error': '机器人已在运行中'}

        # 验证必要配置
        if not config.wechat_path or not config.hook_dll_path:
            return {'success': False, 'error': '请先配置微信路径和Hook DLL路径'}

        # 更新状态
        config.status = 'running'
        config.last_started_at = datetime.now()
        config.last_error = None
        db.commit()

        return {
            'success': True,
            'message': '机器人启动成功',
            'config': config.to_dict()
        }

    @staticmethod
    def stop_robot(db: Session, config_id: int, user_id: int) -> Dict:
        """
        停止机器人
        """
        config = db.query(RobotConfig).filter(
            RobotConfig.id == config_id,
            RobotConfig.user_id == user_id
        ).first()

        if not config:
            return {'success': False, 'error': '配置不存在或无权操作'}

        if config.status != 'running':
            return {'success': False, 'error': '机器人未在运行'}

        config.status = 'stopped'
        db.commit()

        return {
            'success': True,
            'message': '机器人已停止',
            'config': config.to_dict()
        }

    @staticmethod
    def get_default_config(db: Session, user_id: int) -> Dict:
        """获取默认机器人配置"""
        config = db.query(RobotConfig).filter(
            RobotConfig.user_id == user_id,
            RobotConfig.is_default == True
        ).first()

        if not config:
            # 如果没有默认配置，返回第一个
            config = db.query(RobotConfig).filter(
                RobotConfig.user_id == user_id
            ).order_by(RobotConfig.created_at.asc()).first()

        return config.to_dict() if config else None


class ReplyRuleService:
    """自动回复规则服务类"""

    @staticmethod
    def create_rule(db: Session, robot_config_id: int, user_id: int, **kwargs) -> Dict:
        """
        创建自动回复规则
        """
        # 验证机器人配置归属
        config = db.query(RobotConfig).filter(
            RobotConfig.id == robot_config_id,
            RobotConfig.user_id == user_id
        ).first()

        if not config:
            return {'success': False, 'error': '机器人配置不存在或无权操作'}

        rule_name = kwargs.get('rule_name', '').strip()
        if not rule_name:
            return {'success': False, 'error': '规则名称不能为空'}

        trigger_type = kwargs.get('trigger_type', 'keyword')
        if trigger_type not in ['keyword', 'pattern', 'all']:
            return {'success': False, 'error': '触发类型必须为keyword、pattern或all'}

        reply_content = kwargs.get('reply_content', '').strip()
        if not reply_content:
            return {'success': False, 'error': '回复内容不能为空'}

        new_rule = ReplyRule(
            robot_config_id=robot_config_id,
            rule_name=rule_name,
            trigger_type=trigger_type,
            trigger_content=kwargs.get('trigger_content'),
            reply_type=kwargs.get('reply_type', 'text'),
            reply_content=reply_content,
            priority=kwargs.get('priority', 0),
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
        """
        更新自动回复规则
        """
        rule = db.query(ReplyRule).join(RobotConfig).filter(
            ReplyRule.id == rule_id,
            RobotConfig.user_id == user_id
        ).first()

        if not rule:
            return {'success': False, 'error': '规则不存在或无权操作'}

        # 更新字段
        updatable_fields = [
            'rule_name', 'trigger_type', 'trigger_content', 'reply_type',
            'reply_content', 'priority', 'is_active'
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
        """
        删除自动回复规则
        """
        rule = db.query(ReplyRule).join(RobotConfig).filter(
            ReplyRule.id == rule_id,
            RobotConfig.user_id == user_id
        ).first()

        if not rule:
            return {'success': False, 'error': '规则不存在或无权操作'}

        db.delete(rule)
        db.commit()

        return {'success': True, 'message': '规则已删除'}

    @staticmethod
    def get_rules(db: Session, robot_config_id: int, user_id: int) -> List[Dict]:
        """
        获取机器人的自动回复规则列表
        """
        rules = db.query(ReplyRule).filter(
            ReplyRule.robot_config_id == robot_config_id
        ).order_by(ReplyRule.priority.desc(), ReplyRule.created_at.desc()).all()

        return [r.to_dict() for r in rules]

    @staticmethod
    def match_reply(db: Session, robot_config_id: int, message: str) -> Dict:
        """
        根据消息内容匹配回复规则
        :param db: 数据库会话
        :param robot_config_id: 机器人配置ID
        :param message: 收到的消息内容
        :return: 匹配的回复内容
        """
        import re

        # 获取所有活跃的规则，按优先级排序
        rules = db.query(ReplyRule).filter(
            ReplyRule.robot_config_id == robot_config_id,
            ReplyRule.is_active == True
        ).order_by(ReplyRule.priority.desc()).all()

        for rule in rules:
            matched = False

            if rule.trigger_type == 'all':
                matched = True
            elif rule.trigger_type == 'keyword':
                if rule.trigger_content and rule.trigger_content in message:
                    matched = True
            elif rule.trigger_type == 'pattern':
                if rule.trigger_content:
                    try:
                        if re.search(rule.trigger_content, message):
                            matched = True
                    except re.error:
                        continue

            if matched:
                # 更新匹配次数
                rule.match_count += 1
                db.commit()

                return {
                    'success': True,
                    'rule_id': rule.id,
                    'rule_name': rule.rule_name,
                    'reply_content': rule.reply_content
                }

        return {'success': False, 'message': '未找到匹配的回复规则'}

    @staticmethod
    def process_smart_command(db: Session, message: str, sender_info: Dict) -> Dict:
        """
        智能指令处理 - 集成指令配置服务

        参数:
        - db: 数据库会话
        - message: 用户消息
        - sender_info: 发送者信息 {customer_id, customer_name, sales_person, route_id}

        返回:
        {
            "success": True,
            "reply_content": "文本报表内容",
            "command_name": "sales_report"
        }
        """
        from services.command_config_service import command_config_service
        from services.robot_report_service import robot_report_service
        from datetime import date

        try:
            # 1. 匹配指令
            command_match = command_config_service.match_command(message)
            if not command_match:
                return {'success': False, 'message': '未识别的指令'}

            command_name = command_match['command_name']

            # 2. 根据指令类型执行相应操作
            if command_name == 'sales_report':
                # 销售员报表查询
                sales_person = sender_info.get('sales_person')
                if not sales_person:
                    return {
                        'success': False,
                        'message': '❌ 您不是销售员,无法查询线路报表'
                    }

                summary = robot_report_service.get_sales_route_summary(sales_person)
                reply_text = robot_report_service.generate_text_report(summary, 'sales')

                return {
                    'success': True,
                    'reply_content': reply_text,
                    'command_name': command_name
                }

            elif command_name == 'customer_query':
                # 客户订单查询
                customer_id = sender_info.get('customer_id')
                if not customer_id:
                    return {
                        'success': False,
                        'message': '❌ 无法识别您的客户身份'
                    }

                detail = robot_report_service.get_customer_order_detail(customer_id)
                reply_text = robot_report_service.generate_text_report(detail, 'customer')

                return {
                    'success': True,
                    'reply_content': reply_text,
                    'command_name': command_name
                }

            elif command_name == 'help':
                # 帮助信息
                help_text = (
                    "📖 【机器人指令帮助】\n\n"
                    "👔 销售员指令:\n"
                    "  • 发送 \"报表\" / \"统计\" / \"汇总\"\n"
                    "    查询您负责线路的今日订单汇总\n\n"
                    "👤 客户指令:\n"
                    "  • 发送 \"查订单\" / \"多少钱\" / \"我的订单\"\n"
                    "    查询您今日的订单详情和金额\n\n"
                    "💡 提示:\n"
                    "  • 可以直接@机器人发送指令\n"
                    "  • 支持自然语言,如 \"今天配送多少\"、\"我订了什么\""
                )

                return {
                    'success': True,
                    'reply_content': help_text,
                    'command_name': command_name
                }

            else:
                return {'success': False, 'message': '未知指令类型'}

        except Exception as e:
            logger.error(f"智能指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

