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
            # 1. 匹配指令并提取参数
            user_id = sender_info.get('customer_id', sender_info.get('wxid', 'unknown'))
            context = command_config_service.get_conversation_context(str(user_id))
            command_match = command_config_service.match_command_with_params(message, context)

            if not command_match:
                return {'success': False, 'message': '❓ 未识别的指令，发送"帮助"查看可用指令'}

            command_name = command_match['command_name']
            params = command_match.get('params', {})

            # 2. 根据指令类型执行相应操作
            if command_name == 'sales_report':
                sales_person = sender_info.get('sales_person')
                if not sales_person:
                    return {'success': False, 'message': '❌ 您不是销售员,无法查询线路报表'}
                summary = robot_report_service.get_sales_route_summary(sales_person)
                reply_text = robot_report_service.generate_text_report(summary, 'sales')
                command_config_service.clear_conversation_context(str(user_id))
                return {'success': True, 'reply_content': reply_text, 'command_name': command_name}

            elif command_name == 'customer_query':
                customer_id = sender_info.get('customer_id')
                if not customer_id:
                    return {'success': False, 'message': '❌ 无法识别您的客户身份'}
                detail = robot_report_service.get_customer_order_detail(customer_id)
                reply_text = robot_report_service.generate_text_report(detail, 'customer')
                command_config_service.clear_conversation_context(str(user_id))
                return {'success': True, 'reply_content': reply_text, 'command_name': command_name}

            elif command_name == 'help':
                help_text = RobotService._generate_help_text()
                command_config_service.clear_conversation_context(str(user_id))
                return {'success': True, 'reply_content': help_text, 'command_name': command_name}

            else:
                if ':' in command_name:
                    return RobotService._handle_plugin_command(db, message, sender_info, command_name, params)

                return {'success': False, 'message': '❓ 未知指令类型'}

        except Exception as e:
            logger.error(f"智能指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_plugin_command(db: Session, message: str, sender_info: Dict, command_name: str, params: Dict = None) -> Dict:
        """
        处理插件指令（升级版：支持参数提取和多轮对话）

        参数:
        - db: 数据库会话
        - message: 用户消息
        - sender_info: 发送者信息
        - command_name: 指令名称 (格式: plugin_name:command_name)
        - params: 从消息中提取的参数字典
        """
        if params is None:
            params = {}

        try:
            plugin_name, action = command_name.split(':', 1)

            handlers = {
                'construction': RobotService._handle_construction_command,
                'fooddelivery': RobotService._handle_fooddelivery_command,
                'bakery': RobotService._handle_bakery_command,
                'realestate': RobotService._handle_realestate_command,
                'hotpot': RobotService._handle_hotpot_command,
                'education': RobotService._handle_education_command,
                'evparts': RobotService._handle_evparts_command,
                'fleet': RobotService._handle_fleet_command,
                'hardware': RobotService._handle_hardware_command,
                'japanesefood': RobotService._handle_japanesefood_command,
                'partswholesale': RobotService._handle_partswholesale_command,
                'phoneparts': RobotService._handle_phoneparts_command,
                'seafood': RobotService._handle_seafood_command,
                'teacoffee': RobotService._handle_teacoffee_command,
                'travel': RobotService._handle_travel_command,
            }

            if plugin_name in handlers:
                return handlers[plugin_name](db, message, sender_info, action, params)
            else:
                return {'success': False, 'message': f'未知插件: {plugin_name}'}

        except Exception as e:
            logger.error(f"插件指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'插件指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_construction_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            from plugins.construction.service import ConstructionService
            from datetime import date, timedelta
            service = ConstructionService(db)

            if action == 'report_volume':
                if params.get('quantity') and params.get('site_name'):
                    # 查找工地ID
                    sites = service.list_sites()
                    site_id = None
                    for s in sites:
                        if params['site_name'] in s.get('site_name', '') or s.get('site_name', '') in params['site_name']:
                            site_id = s['id']
                            break
                    volume_data = {
                        'site_id': site_id or 0,
                        'work_type': params.get('text', '土方开挖'),
                        'work_type_name': params.get('text', '土方开挖'),
                        'actual_volume': float(params['quantity']),
                        'unit': params.get('unit', '方'),
                        'remark': params.get('text', ''),
                    }
                    if site_id:
                        service.report_daily_volume(volume_data)
                    return {'success': True, 'reply_content': f'✅ 已记录工程量：{params["site_name"]} {params["quantity"]}{params.get("unit", "方")}', 'command_name': 'construction:report_volume'}
                return {'success': True, 'reply_content': '📝 请回复工程量信息，格式：\n工地名称 施工类型 数量 单位\n例如：城东工地 土方开挖 500 方', 'command_name': 'construction:report_volume', 'action_required': True, 'action_params': {'type': 'volume_report'}}
            elif action == 'report_expense':
                if params.get('amount') and params.get('category'):
                    sites = service.list_sites()
                    site_id = None
                    site_name = params.get('site_name', '')
                    for s in sites:
                        if site_name in s.get('site_name', '') or s.get('site_name', '') in site_name:
                            site_id = s['id']
                            break
                    expense_data = {
                        'site_id': site_id or 0,
                        'category_id': 0,
                        'amount': float(params['amount']),
                        'remark': f"{params.get('category', '')} {params.get('text', '')}",
                    }
                    service.report_expense(expense_data)
                    return {'success': True, 'reply_content': f'✅ 已记录费用：{params["category"]} {params["amount"]}元', 'command_name': 'construction:report_expense'}
                return {'success': True, 'reply_content': '💰 请回复费用信息，格式：\n费用类型 金额 备注\n例如：燃油费 300 城东工地', 'command_name': 'construction:report_expense', 'action_required': True, 'action_params': {'type': 'expense_report'}}
            elif action == 'consumable_in':
                if params.get('quantity') and params.get('unit'):
                    return {'success': True, 'reply_content': f'✅ 已记录耗材入库：{params.get("text", "")} {params["quantity"]}{params.get("unit", "")}', 'command_name': 'construction:consumable_in'}
                return {'success': True, 'reply_content': '📦 请回复耗材入库信息，格式：\n耗材名称 数量 单位 工地\n例如：柴油 500 升 城东工地', 'command_name': 'construction:consumable_in', 'action_required': True, 'action_params': {'type': 'consumable_in'}}
            elif action == 'consumable_out':
                if params.get('quantity') and params.get('unit'):
                    return {'success': True, 'reply_content': f'✅ 已记录耗材出库：{params.get("text", "")} {params["quantity"]}{params.get("unit", "")}', 'command_name': 'construction:consumable_out'}
                return {'success': True, 'reply_content': '📤 请回复耗材出库信息，格式：\n耗材名称 数量 单位 工地\n例如：水泥 10 袋 城东工地', 'command_name': 'construction:consumable_out', 'action_required': True, 'action_params': {'type': 'consumable_out'}}
            elif action == 'equipment_lease':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'✅ 已记录设备租赁申请：{params["text"]}', 'command_name': 'construction:equipment_lease'}
                return {'success': True, 'reply_content': '🤖 请回复设备租赁信息，格式：\n设备名称 工地 租期(天)\n例如：挖掘机 城东工地 30', 'command_name': 'construction:equipment_lease', 'action_required': True, 'action_params': {'type': 'equipment_lease'}}
            elif action == 'financial_record':
                if params.get('amount'):
                    return {'success': True, 'reply_content': f'✅ 已记录财务：{params.get("category", "其他")} {params["amount"]}元', 'command_name': 'construction:financial_record'}
                return {'success': True, 'reply_content': '💰 请回复财务记账信息，格式：\n收支类型 金额 对方单位 备注\n例如：收入 50000 城东地产 工程款', 'command_name': 'construction:financial_record', 'action_required': True, 'action_params': {'type': 'financial_record'}}
            elif action == 'salary_report':
                today = date.today()
                start = today - timedelta(days=30)
                result = service.get_salary_report(start, today)
                if result.get('success') and result.get('data'):
                    data = result['data']
                    reply = f'💼 【薪资查询结果（{start}~{today}）】\n'
                    reply += f'  👥 员工总数：{data.get("total_workers", 0)}人\n'
                    reply += f'  💰 总薪资：{data.get("total_salary", 0)}元\n'
                    details = data.get('details', [])
                    for r in details[:5]:
                        reply += f'  • {r.get("worker_name", "未知")}: {r.get("total_salary", 0)}元\n'
                    return {'success': True, 'reply_content': reply, 'command_name': 'construction:salary_report'}
                return {'success': True, 'reply_content': '💼 近30天无薪资记录', 'command_name': 'construction:salary_report'}
            elif action == 'site_stats':
                stats = service.get_stats()
                if stats:
                    reply = '📊 【工地统计报表】\n'
                    reply += f'  👷 当前工人数：{stats.get("total_workers", 0)}人\n'
                    reply += f'  📋 今日考勤：{stats.get("attendance_count", 0)}人\n'
                    reply += f'  ⚠️ 待处理安全问题：{stats.get("pending_safety_issues", 0)}项\n'
                    reply += f'  📦 工程量记录：{stats.get("work_volume_count", 0)}条\n'
                    return {'success': True, 'reply_content': reply, 'command_name': 'construction:site_stats'}
                return {'success': True, 'reply_content': '📊 暂无工地统计数据', 'command_name': 'construction:site_stats'}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}

        except ImportError:
            return {'success': False, 'message': '建筑工程插件未安装'}
        except Exception as e:
            logger.error(f"建筑工程指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_fooddelivery_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 订单 {params["order_no"]} 查询中...', 'command_name': 'fooddelivery:order_query'}
                if params.get('phone'):
                    return {'success': True, 'reply_content': f'📋 手机号 {params["phone"]} 关联订单查询中...', 'command_name': 'fooddelivery:order_query'}
                return {'success': True, 'reply_content': '📋 请回复订单号或手机号查询订单状态', 'command_name': 'fooddelivery:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'delivery_status':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'🚗 订单 {params["order_no"]} 配送状态查询中...', 'command_name': 'fooddelivery:delivery_status'}
                return {'success': True, 'reply_content': '🚗 请回复订单号查询配送进度', 'command_name': 'fooddelivery:delivery_status', 'action_required': True, 'action_params': {'type': 'delivery_status'}}
            elif action == 'menu_query':
                return {'success': True, 'reply_content': '📖 【今日菜单】\n🍚 主食：米饭、炒面\n🥩 主菜：红烧肉、宫保鸡丁\n🥬 素菜：清炒时蔬\n🍲 汤品：紫菜蛋花汤', 'command_name': 'fooddelivery:menu_query'}
            elif action == 'inventory_warning':
                return {'success': True, 'reply_content': '📦 【库存预警】\n⚠️ 大米：剩余5袋，低于安全库存\n⚠️ 食用油：剩余3桶，建议补货\n✅ 其他食材库存充足', 'command_name': 'fooddelivery:inventory_warning'}
            elif action == 'rush_order':
                return {'success': True, 'reply_content': '⏰ 已收到催单请求，正在加急处理中\n预计15分钟内送达，请耐心等待', 'command_name': 'fooddelivery:rush_order'}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"餐饮配送指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_bakery_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'🍰 订单 {params["order_no"]} 查询中...', 'command_name': 'bakery:order_query'}
                return {'success': True, 'reply_content': '🍰 请回复订单号查询蛋糕订单状态', 'command_name': 'bakery:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '🥚 【原料库存】\n🍞 高筋面粉：50kg ✅\n🍰 低筋面粉：30kg ✅\n🧈 黄油：15kg ✅\n🥛 淡奶油：10L ⚠️ 建议补货\n🥚 鸡蛋：200个 ✅', 'command_name': 'bakery:inventory_query'}
            elif action == 'member_query':
                if params.get('phone'):
                    return {'success': True, 'reply_content': f'👤 会员 {params["phone"]} 查询中...', 'command_name': 'bakery:member_query'}
                return {'success': True, 'reply_content': '👤 请回复手机号查询会员信息', 'command_name': 'bakery:member_query', 'action_required': True, 'action_params': {'type': 'member_query'}}
            elif action == 'product_query':
                return {'success': True, 'reply_content': '🍞 【今日产品】\n🍓 草莓蛋糕 ￥128\n🍫 巧克力慕斯 ￥98\n🥐 可颂 ￥18\n🍪 曲奇饼干 ￥38/盒\n🎂 生日蛋糕 ￥198起', 'command_name': 'bakery:product_query'}
            elif action == 'custom_cake':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🎂 已收到定制需求：{params["text"]}\n客服将尽快与您联系确认', 'command_name': 'bakery:custom_cake'}
                return {'success': True, 'reply_content': '🎂 请回复定制需求：\n蛋糕类型 尺寸 祝福语\n例如：水果蛋糕 8寸 生日快乐', 'command_name': 'bakery:custom_cake', 'action_required': True, 'action_params': {'type': 'custom_cake'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"烘焙甜品指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_realestate_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'house_query':
                if params.get('amount') and params.get('text'):
                    return {'success': True, 'reply_content': f'🏠 正在为您搜索：{params.get("text", "")} 预算{params["amount"]}万...', 'command_name': 'realestate:house_query'}
                return {'success': True, 'reply_content': '🏠 请回复需求：\n买房/租房 区域 预算\n例如：买房 城东 100万', 'command_name': 'realestate:house_query', 'action_required': True, 'action_params': {'type': 'house_query'}}
            elif action == 'customer_follow':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'👤 客户 {params["name"]} 的跟进记录查询中...', 'command_name': 'realestate:customer_follow'}
                return {'success': True, 'reply_content': '👤 请回复客户姓名查询跟进记录', 'command_name': 'realestate:customer_follow', 'action_required': True, 'action_params': {'type': 'customer_follow'}}
            elif action == 'transaction_progress':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 交易 {params["order_no"]} 进度查询中...', 'command_name': 'realestate:transaction_progress'}
                return {'success': True, 'reply_content': '📋 请回复交易编号查询进度', 'command_name': 'realestate:transaction_progress', 'action_required': True, 'action_params': {'type': 'transaction_progress'}}
            elif action == 'viewing_record':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'🔑 客户 {params["name"]} 的带看记录查询中...', 'command_name': 'realestate:viewing_record'}
                return {'success': True, 'reply_content': '🔑 请回复客户姓名查询带看记录', 'command_name': 'realestate:viewing_record', 'action_required': True, 'action_params': {'type': 'viewing_record'}}
            elif action == 'price_estimate':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'💰 正在评估 {params["text"]} 的房产价值...', 'command_name': 'realestate:price_estimate'}
                return {'success': True, 'reply_content': '💰 请回复小区名称和面积查询估价', 'command_name': 'realestate:price_estimate', 'action_required': True, 'action_params': {'type': 'price_estimate'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"房产中介指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_hotpot_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'food_query':
                return {'success': True, 'reply_content': '🥘 【今日食材】\n🥩 肥牛卷 ￥38/份\n🐑 羊肉卷 ￥42/份\n🦐 虾滑 ￥28/份\n🥬 蔬菜拼盘 ￥18/份\n🍄 菌菇拼盘 ￥22/份', 'command_name': 'hotpot:food_query'}
            elif action == 'soup_base':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🍲 已选择锅底：{params["text"]}', 'command_name': 'hotpot:soup_base'}
                return {'success': True, 'reply_content': '🍲 请选择锅底：麻辣/番茄/菌汤/清汤', 'command_name': 'hotpot:soup_base', 'action_required': True, 'action_params': {'type': 'soup_base'}}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 订单 {params["order_no"]} 查询中...', 'command_name': 'hotpot:order_query'}
                return {'success': True, 'reply_content': '📋 请回复订单号查询订单状态', 'command_name': 'hotpot:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'delivery_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'🚗 订单 {params["order_no"]} 配送中...', 'command_name': 'hotpot:delivery_query'}
                return {'success': True, 'reply_content': '🚗 请回复订单号查询配送进度', 'command_name': 'hotpot:delivery_query', 'action_required': True, 'action_params': {'type': 'delivery_query'}}
            elif action == 'inventory_warning':
                return {'success': True, 'reply_content': '❄️ 【冻品库存】\n✅ 肥牛卷：充足\n✅ 羊肉卷：充足\n⚠️ 虾滑：库存偏低\n✅ 冻豆腐：充足', 'command_name': 'hotpot:inventory_warning'}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"火锅食材指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_education_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'course_query':
                if params.get('date'):
                    return {'success': True, 'reply_content': f'📚 {params["date"]} 课程：\n09:00 Python基础\n14:00 Web开发\n16:00 项目实战', 'command_name': 'education:course_query'}
                return {'success': True, 'reply_content': '📚 请回复日期查询课程安排', 'command_name': 'education:course_query', 'action_required': True, 'action_params': {'type': 'course_query'}}
            elif action == 'student_query':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'👨‍🎓 学员 {params["name"]} 信息查询中...', 'command_name': 'education:student_query'}
                return {'success': True, 'reply_content': '👨‍🎓 请回复学员姓名查询信息', 'command_name': 'education:student_query', 'action_required': True, 'action_params': {'type': 'student_query'}}
            elif action == 'attendance_check':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'✅ 考勤已记录：{params["text"]}', 'command_name': 'education:attendance_check'}
                return {'success': True, 'reply_content': '✅ 请回复"打卡"或"请假"', 'command_name': 'education:attendance_check', 'action_required': True, 'action_params': {'type': 'attendance_check'}}
            elif action == 'schedule_query':
                return {'success': True, 'reply_content': '📅 【老师排班】\n周一 张老师 09:00-17:00\n周二 李老师 09:00-17:00\n周三 张老师 13:00-21:00\n周四 王老师 09:00-17:00', 'command_name': 'education:schedule_query'}
            elif action == 'enrollment_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🎓 课程"{params["text"]}"学费查询中...', 'command_name': 'education:enrollment_query'}
                return {'success': True, 'reply_content': '🎓 请回复课程名称咨询学费', 'command_name': 'education:enrollment_query', 'action_required': True, 'action_params': {'type': 'enrollment_query'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"教育培训指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_evparts_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'parts_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🔧 正在查询配件：{params["text"]}', 'command_name': 'evparts:parts_query'}
                return {'success': True, 'reply_content': '🔧 请回复配件名称或型号查询', 'command_name': 'evparts:parts_query', 'action_required': True, 'action_params': {'type': 'parts_query'}}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📦 订单 {params["order_no"]} 发货状态查询中...', 'command_name': 'evparts:order_query'}
                return {'success': True, 'reply_content': '📦 请回复订单号查询发货状态', 'command_name': 'evparts:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '📊 【配件库存】\n🔋 电池组：50组 ✅\n⚡ 电机：30台 ✅\n🛞 轮胎：200条 ✅\n🚗 控制器：15台 ⚠️', 'command_name': 'evparts:inventory_query'}
            elif action == 'repair_record':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🛠️ 已登记维修：{params["text"]}', 'command_name': 'evparts:repair_record'}
                return {'success': True, 'reply_content': '🛠️ 请回复故障描述登记维修', 'command_name': 'evparts:repair_record', 'action_required': True, 'action_params': {'type': 'repair_record'}}
            elif action == 'price_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'💰 配件"{params["text"]}"价格查询中...', 'command_name': 'evparts:price_query'}
                return {'success': True, 'reply_content': '💰 请回复配件名称查询价格', 'command_name': 'evparts:price_query', 'action_required': True, 'action_params': {'type': 'price_query'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"电动车配件指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_fleet_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'vehicle_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🚛 车辆 {params["text"]} 状态查询中...', 'command_name': 'fleet:vehicle_query'}
                return {'success': True, 'reply_content': '🚛 请回复车牌号查询车辆状态', 'command_name': 'fleet:vehicle_query', 'action_required': True, 'action_params': {'type': 'vehicle_query'}}
            elif action == 'driver_query':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'👨‍✈️ 司机 {params["name"]} 排班查询中...', 'command_name': 'fleet:driver_query'}
                return {'success': True, 'reply_content': '👨‍✈️ 请回复司机姓名查询排班', 'command_name': 'fleet:driver_query', 'action_required': True, 'action_params': {'type': 'driver_query'}}
            elif action == 'dispatch':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'📋 已创建调度任务：{params["text"]}', 'command_name': 'fleet:dispatch'}
                return {'success': True, 'reply_content': '📋 请回复任务信息：\n目的地 货物 时间\n例如：城东仓库 钢材 明天9点', 'command_name': 'fleet:dispatch', 'action_required': True, 'action_params': {'type': 'dispatch'}}
            elif action == 'fuel_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'⛽ 车辆 {params["text"]} 油耗查询中...', 'command_name': 'fleet:fuel_query'}
                return {'success': True, 'reply_content': '⛽ 请回复车牌号查询油耗', 'command_name': 'fleet:fuel_query', 'action_required': True, 'action_params': {'type': 'fuel_query'}}
            elif action == 'maintenance':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🔧 车辆 {params["text"]} 保养记录查询中...', 'command_name': 'fleet:maintenance'}
                return {'success': True, 'reply_content': '🔧 请回复车牌号查询保养记录', 'command_name': 'fleet:maintenance', 'action_required': True, 'action_params': {'type': 'maintenance'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"车队管理指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_hardware_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'product_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🔩 正在查询产品：{params["text"]}', 'command_name': 'hardware:product_query'}
                return {'success': True, 'reply_content': '🔩 请回复产品名称查询规格', 'command_name': 'hardware:product_query', 'action_required': True, 'action_params': {'type': 'product_query'}}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📦 订单 {params["order_no"]} 发货状态查询中...', 'command_name': 'hardware:order_query'}
                return {'success': True, 'reply_content': '📦 请回复订单号查询发货状态', 'command_name': 'hardware:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '📊 【五金库存】\n🔩 螺丝M6：5000个 ✅\n🔧 扳手：200把 ✅\n📏 卷尺：150个 ✅\n⚡ 电线：30卷 ⚠️', 'command_name': 'hardware:inventory_query'}
            elif action == 'supplier_query':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'🤝 供应商 {params["name"]} 信息查询中...', 'command_name': 'hardware:supplier_query'}
                return {'success': True, 'reply_content': '🤝 请回复供应商名称查询信息', 'command_name': 'hardware:supplier_query', 'action_required': True, 'action_params': {'type': 'supplier_query'}}
            elif action == 'quote_request':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'💰 已收到询价：{params["text"]}\n正在为您生成报价...', 'command_name': 'hardware:quote_request'}
                return {'success': True, 'reply_content': '💰 请回复产品名称和数量询价', 'command_name': 'hardware:quote_request', 'action_required': True, 'action_params': {'type': 'quote_request'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"五金建材指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_japanesefood_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'menu_query':
                return {'success': True, 'reply_content': '🍣 【今日菜单】\n🐟 三文鱼刺身 ￥68\n🍤 天妇罗拼盘 ￥48\n🍜 豚骨拉面 ￥38\n🍱 鳗鱼饭 ￥58\n🥗 和风沙拉 ￥28', 'command_name': 'japanesefood:menu_query'}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 订单 {params["order_no"]} 查询中...', 'command_name': 'japanesefood:order_query'}
                return {'success': True, 'reply_content': '📋 请回复订单号查询状态', 'command_name': 'japanesefood:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '🐟 【生鲜库存】\n🍣 三文鱼：15kg ✅\n🦐 甜虾：8kg ✅\n🐙 八爪鱼：5kg ⚠️\n🍚 寿司米：50kg ✅', 'command_name': 'japanesefood:inventory_query'}
            elif action == 'member_query':
                if params.get('phone'):
                    return {'success': True, 'reply_content': f'👤 会员 {params["phone"]} 查询中...', 'command_name': 'japanesefood:member_query'}
                return {'success': True, 'reply_content': '👤 请回复手机号查询会员信息', 'command_name': 'japanesefood:member_query', 'action_required': True, 'action_params': {'type': 'member_query'}}
            elif action == 'booking':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🍱 已收到预约：{params["text"]}\n我们将尽快确认', 'command_name': 'japanesefood:booking'}
                return {'success': True, 'reply_content': '🍱 请回复预约信息：\n日期 人数 包间/大厅\n例如：明天 6人 包间', 'command_name': 'japanesefood:booking', 'action_required': True, 'action_params': {'type': 'booking'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"日式料理指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_partswholesale_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'product_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'📦 正在查询产品：{params["text"]}', 'command_name': 'partswholesale:product_query'}
                return {'success': True, 'reply_content': '📦 请回复产品名称查询批发价', 'command_name': 'partswholesale:product_query', 'action_required': True, 'action_params': {'type': 'product_query'}}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 订单 {params["order_no"]} 发货状态查询中...', 'command_name': 'partswholesale:order_query'}
                return {'success': True, 'reply_content': '📋 请回复订单号查询发货状态', 'command_name': 'partswholesale:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '📊 【配件批发库存】\n🔧 轴承：500套 ✅\n⚙️ 齿轮：300个 ✅\n🔩 螺栓：2000个 ✅\n📐 密封圈：100个 ⚠️', 'command_name': 'partswholesale:inventory_query'}
            elif action == 'customer_query':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'👤 客户 {params["name"]} 对账查询中...', 'command_name': 'partswholesale:customer_query'}
                return {'success': True, 'reply_content': '👤 请回复客户名称查询对账', 'command_name': 'partswholesale:customer_query', 'action_required': True, 'action_params': {'type': 'customer_query'}}
            elif action == 'price_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'💰 产品"{params["text"]}"批发价查询中...', 'command_name': 'partswholesale:price_query'}
                return {'success': True, 'reply_content': '💰 请回复产品名称查询批发价', 'command_name': 'partswholesale:price_query', 'action_required': True, 'action_params': {'type': 'price_query'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"配件批发指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_phoneparts_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'parts_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'📱 正在查询配件：{params["text"]}', 'command_name': 'phoneparts:parts_query'}
                return {'success': True, 'reply_content': '📱 请回复手机型号和配件类型', 'command_name': 'phoneparts:parts_query', 'action_required': True, 'action_params': {'type': 'parts_query'}}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📦 订单 {params["order_no"]} 发货状态查询中...', 'command_name': 'phoneparts:order_query'}
                return {'success': True, 'reply_content': '📦 请回复订单号查询发货状态', 'command_name': 'phoneparts:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '📊 【手机配件库存】\n📱 屏幕总成：80套 ✅\n🔋 电池：150块 ✅\n📷 摄像头：60个 ✅\n🔌 充电口：40个 ⚠️', 'command_name': 'phoneparts:inventory_query'}
            elif action == 'repair_service':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🔧 已登记维修：{params["text"]}\n预计24小时内完成', 'command_name': 'phoneparts:repair_service'}
                return {'success': True, 'reply_content': '🔧 请回复故障描述：\n手机型号 故障类型\n例如：iPhone15 换屏', 'command_name': 'phoneparts:repair_service', 'action_required': True, 'action_params': {'type': 'repair_service'}}
            elif action == 'price_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'💰 配件"{params["text"]}"价格查询中...', 'command_name': 'phoneparts:price_query'}
                return {'success': True, 'reply_content': '💰 请回复配件名称查询价格', 'command_name': 'phoneparts:price_query', 'action_required': True, 'action_params': {'type': 'price_query'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"手机配件指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_seafood_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'product_query':
                return {'success': True, 'reply_content': '🦐 【今日海鲜】\n🐟 鲈鱼 ￥28/斤\n🦐 基围虾 ￥45/斤\n🦀 大闸蟹 ￥68/只\n🐚 花蛤 ￥15/斤\n🐠 多宝鱼 ￥38/斤', 'command_name': 'seafood:product_query'}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📦 订单 {params["order_no"]} 发货状态查询中...', 'command_name': 'seafood:order_query'}
                return {'success': True, 'reply_content': '📦 请回复订单号查询发货状态', 'command_name': 'seafood:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '🐟 【鲜货库存】\n🦐 基围虾：30斤 ✅\n🐟 鲈鱼：20斤 ✅\n🦀 大闸蟹：50只 ✅\n🐚 花蛤：15斤 ⚠️', 'command_name': 'seafood:inventory_query'}
            elif action == 'supplier_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🤝 产地 {params["text"]} 供应商查询中...', 'command_name': 'seafood:supplier_query'}
                return {'success': True, 'reply_content': '🤝 请回复产地查询供应商', 'command_name': 'seafood:supplier_query', 'action_required': True, 'action_params': {'type': 'supplier_query'}}
            elif action == 'fresh_check':
                return {'success': True, 'reply_content': '✅ 【新鲜度检查】\n🐟 鲈鱼：新鲜度95% ✅\n🦐 基围虾：新鲜度90% ✅\n🦀 大闸蟹：新鲜度92% ✅\n🐚 花蛤：新鲜度78% ⚠️ 建议尽快处理', 'command_name': 'seafood:fresh_check'}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"海鲜水产指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_teacoffee_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'menu_query':
                return {'success': True, 'reply_content': '☕ 【今日菜单】\n🥤 珍珠奶茶 ￥15\n🍵 抹茶拿铁 ￥22\n☕ 美式咖啡 ￥18\n🍑 蜜桃乌龙 ￥16\n🧋 黑糖波波 ￥20', 'command_name': 'teacoffee:menu_query'}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 取餐码 {params["order_no"]} 查询中...', 'command_name': 'teacoffee:order_query'}
                return {'success': True, 'reply_content': '📋 请回复取餐码查询订单', 'command_name': 'teacoffee:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'inventory_query':
                return {'success': True, 'reply_content': '🍵 【原料库存】\n🍃 茶叶：20kg ✅\n☕ 咖啡豆：15kg ✅\n🥛 奶精：30kg ✅\n🍯 糖浆：10L ⚠️', 'command_name': 'teacoffee:inventory_query'}
            elif action == 'member_query':
                if params.get('phone'):
                    return {'success': True, 'reply_content': f'👤 会员 {params["phone"]} 积分查询中...', 'command_name': 'teacoffee:member_query'}
                return {'success': True, 'reply_content': '👤 请回复手机号查询会员积分', 'command_name': 'teacoffee:member_query', 'action_required': True, 'action_params': {'type': 'member_query'}}
            elif action == 'custom_order':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'🥤 已收到定制订单：{params["text"]}\n预计5分钟内完成', 'command_name': 'teacoffee:custom_order'}
                return {'success': True, 'reply_content': '🥤 请回复定制需求：\n饮品名称 甜度 冰量\n例如：珍珠奶茶 少糖 去冰', 'command_name': 'teacoffee:custom_order', 'action_required': True, 'action_params': {'type': 'custom_order'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"茶饮咖啡指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _handle_travel_command(db: Session, message: str, sender_info: Dict, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        try:
            if action == 'route_query':
                return {'success': True, 'reply_content': '🗺️ 【热门线路】\n🏖️ 三亚5日游 ￥3980\n🏔️ 云南6日游 ￥2980\n🏯 西安4日游 ￥1980\n🌊 厦门3日游 ￥1580\n🏞️ 张家界4日游 ￥2280', 'command_name': 'travel:route_query'}
            elif action == 'order_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'📋 订单 {params["order_no"]} 行程查询中...', 'command_name': 'travel:order_query'}
                return {'success': True, 'reply_content': '📋 请回复订单号查询行程', 'command_name': 'travel:order_query', 'action_required': True, 'action_params': {'type': 'order_query'}}
            elif action == 'customer_query':
                if params.get('name'):
                    return {'success': True, 'reply_content': f'👤 游客 {params["name"]} 信息查询中...', 'command_name': 'travel:customer_query'}
                return {'success': True, 'reply_content': '👤 请回复游客姓名查询信息', 'command_name': 'travel:customer_query', 'action_required': True, 'action_params': {'type': 'customer_query'}}
            elif action == 'schedule_query':
                if params.get('order_no'):
                    return {'success': True, 'reply_content': f'🏨 行程 {params["order_no"]} 安排查询中...', 'command_name': 'travel:schedule_query'}
                return {'success': True, 'reply_content': '🏨 请回复行程编号查询安排', 'command_name': 'travel:schedule_query', 'action_required': True, 'action_params': {'type': 'schedule_query'}}
            elif action == 'price_query':
                if params.get('text'):
                    return {'success': True, 'reply_content': f'💰 线路"{params["text"]}"报价查询中...', 'command_name': 'travel:price_query'}
                return {'success': True, 'reply_content': '💰 请回复线路名称查询报价', 'command_name': 'travel:price_query', 'action_required': True, 'action_params': {'type': 'price_query'}}
            else:
                return {'success': False, 'message': f'未知操作: {action}'}
        except Exception as e:
            logger.error(f"旅游服务指令处理失败: {e}", exc_info=True)
            return {'success': False, 'message': f'指令处理失败: {str(e)}'}

    @staticmethod
    def _generate_help_text() -> str:
        """
        生成帮助信息，覆盖全部15个行业插件，分组展示
        """
        from services.command_config_service import command_config_service

        # 行业名称与图标映射
        INDUSTRY_MAP = {
            'construction':   ('🏗️', '建筑工程'),
            'fooddelivery':   ('🛵', '餐饮配送'),
            'bakery':         ('🍰', '烘焙甜品'),
            'realestate':     ('🏠', '房产中介'),
            'hotpot':         ('🥘', '火锅食材'),
            'education':      ('📚', '教育培训'),
            'evparts':        ('🔋', '电动车配件'),
            'fleet':          ('🚛', '车队管理'),
            'hardware':       ('🔩', '五金建材'),
            'japanesefood':   ('🍣', '日式料理'),
            'partswholesale': ('📦', '配件批发'),
            'phoneparts':     ('📱', '手机配件'),
            'seafood':        ('🦐', '海鲜水产'),
            'teacoffee':      ('🍵', '茶饮咖啡'),
            'travel':         ('✈️', '旅游服务'),
        }

        try:
            commands = command_config_service.get_active_commands()

            help_text = "📖 【机器人指令帮助】\n"
            help_text += "━━━━━━━━━━━━━━━━━━━━\n\n"

            plugin_commands = {}
            base_commands = []

            for cmd in commands:
                if ':' in cmd['command_name']:
                    plugin_name = cmd['command_name'].split(':', 1)[0]
                    if plugin_name not in plugin_commands:
                        plugin_commands[plugin_name] = []
                    plugin_commands[plugin_name].append(cmd)
                else:
                    base_commands.append(cmd)

            # 基础指令
            if base_commands:
                help_text += "📌 【基础指令】\n"
                for cmd in base_commands:
                    examples = cmd.get('examples', [])
                    example_str = f" 示例: {examples[0]}" if examples else ""
                    help_text += f"  • {cmd['description']}{example_str}\n"
                help_text += "\n"

            # 行业插件指令 - 分组展示
            help_text += "📦 【行业插件指令】\n\n"

            for plugin_name in sorted(plugin_commands.keys()):
                cmds = plugin_commands[plugin_name]
                emoji, label = INDUSTRY_MAP.get(plugin_name, ('📋', plugin_name))
                help_text += f"{emoji} {label} ({len(cmds)}项指令):\n"

                for cmd in cmds:
                    short_name = cmd['command_name'].split(':', 1)[-1]
                    desc = cmd['description']
                    examples = cmd.get('examples', [])
                    example_str = f" | 示例: {examples[0]}" if examples else ""
                    help_text += f"  ▸ {desc}{example_str}\n"
                help_text += "\n"

            help_text += "━━━━━━━━━━━━━━━━━━━━\n"
            help_text += "💡 【使用提示】\n"
            help_text += "  • 直接发送关键词即可触发指令\n"
            help_text += "  • 支持自然语言,如\"今天挖了多少\"、\"查一下订单\"\n"
            help_text += "  • 支持参数提取,如\"工程量 城东工地 500方\"\n"
            help_text += "  • 发送\"帮助\"随时查看此列表\n"
            help_text += f"  • 共支持 {len(plugin_commands)} 个行业、{sum(len(c) for c in plugin_commands.values()) + len(base_commands)} 条指令\n"
            help_text += "━━━━━━━━━━━━━━━━━━━━\n"

            return help_text

        except Exception as e:
            logger.error(f"生成帮助信息失败: {e}", exc_info=True)
            return (
                "📖 【机器人指令帮助】\n\n"
                "� 基础指令:\n"
                "  • 发送\"报表\"查询销售汇总\n"
                "  • 发送\"查订单\"查询订单详情\n\n"
                "💡 提示: 直接@机器人发送指令即可"
            )


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
