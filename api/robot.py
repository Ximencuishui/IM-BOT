"""
机器人配置API
提供机器人配置的增删改查、启动/停止、自动回复规则管理
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.robot_service import RobotService, ReplyRuleService

robot_bp = Blueprint('robot', __name__, url_prefix='/api/robot')


# ==================== 机器人配置管理 ====================

@robot_bp.route('/configs', methods=['GET'])
@login_required
def list_configs():
    """获取机器人配置列表"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        configs = RobotService.get_configs(db, user.id)

        return jsonify({
            'success': True,
            'configs': configs,
            'count': len(configs)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs/<int:config_id>', methods=['GET'])
@login_required
def get_config(config_id):
    """获取单个机器人配置"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        config = RobotService.get_config(db, config_id, user.id)

        if not config:
            return jsonify({'success': False, 'error': '配置不存在'}), 404

        return jsonify({'success': True, 'config': config}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs/default', methods=['GET'])
@login_required
def get_default_config():
    """获取默认机器人配置"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        config = RobotService.get_default_config(db, user.id)

        if not config:
            return jsonify({'success': False, 'error': '未找到配置'}), 404

        return jsonify({'success': True, 'config': config}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs', methods=['POST'])
@login_required
def create_config():
    """
    创建机器人配置
    Body: {
        "config_name": "主机器人",
        "wechat_path": "C:\\Program Files\\Tencent\\WeChat\\WeChat.exe",
        "hook_dll_path": "D:\\tools\\wechat-hook\\hook.dll",
        "tcp_server_host": "127.0.0.1",
        "tcp_server_port": 8888,
        "auto_start": true,
        "is_default": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RobotService.create_config(db, user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs/<int:config_id>', methods=['PUT'])
@login_required
def update_config(config_id):
    """
    更新机器人配置
    Body: {字段同创建}
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RobotService.update_config(db, config_id, user.id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs/<int:config_id>', methods=['DELETE'])
@login_required
def delete_config(config_id):
    """删除机器人配置"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RobotService.delete_config(db, config_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs/<int:config_id>/start', methods=['POST'])
@login_required
def start_robot(config_id):
    """启动机器人"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RobotService.start_robot(db, config_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/configs/<int:config_id>/stop', methods=['POST'])
@login_required
def stop_robot(config_id):
    """停止机器人"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = RobotService.stop_robot(db, config_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 自动回复规则管理 ====================

@robot_bp.route('/configs/<int:config_id>/reply-rules', methods=['GET'])
@login_required
def list_reply_rules(config_id):
    """获取机器人的自动回复规则列表"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        rules = ReplyRuleService.get_rules(db, config_id, user.id)

        return jsonify({
            'success': True,
            'rules': rules,
            'count': len(rules)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/reply-rules', methods=['POST'])
@login_required
def create_reply_rule():
    """
    创建自动回复规则
    Body: {
        "robot_config_id": 1,
        "rule_name": "欢迎语",
        "trigger_type": "keyword",  // keyword/pattern/all
        "trigger_content": "你好",
        "reply_type": "text",
        "reply_content": "您好！我是自动助手，请问有什么可以帮您？",
        "priority": 10,
        "is_active": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    if not data.get('robot_config_id'):
        return jsonify({'success': False, 'error': '请指定机器人配置ID'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ReplyRuleService.create_rule(db, data['robot_config_id'], user.id, **data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/reply-rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_reply_rule(rule_id):
    """
    更新自动回复规则
    Body: {字段同创建}
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ReplyRuleService.update_rule(db, rule_id, user.id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/reply-rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_reply_rule(rule_id):
    """删除自动回复规则"""
    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ReplyRuleService.delete_rule(db, rule_id, user.id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/reply-match', methods=['POST'])
@login_required
def test_reply_match():
    """
    测试回复匹配
    Body: {
        "robot_config_id": 1,
        "message": "你好"
    }
    """
    data = request.get_json()
    if not data or not data.get('robot_config_id') or not data.get('message'):
        return jsonify({'success': False, 'error': '请提供机器人配置ID和消息内容'}), 400

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        result = ReplyRuleService.match_reply(db, data['robot_config_id'], data['message'])

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== 指令管理API ====================

@robot_bp.route('/commands', methods=['GET'])
def get_commands():
    """获取所有激活的指令配置"""
    from services.command_config_service import command_config_service

    try:
        commands = command_config_service.get_active_commands()
        return jsonify({
            'success': True,
            'count': len(commands),
            'commands': commands
        }), 200
    except Exception as e:
        logger.error(f"获取指令配置失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/commands', methods=['POST'])
def create_command():
    """创建新指令配置"""
    from services.command_config_service import command_config_service

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        result = command_config_service.create_command(**data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建指令失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/commands/<int:command_id>', methods=['PUT'])
def update_command(command_id):
    """更新指令配置"""
    from services.command_config_service import command_config_service

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        result = command_config_service.update_command(command_id, **data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"更新指令失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/commands/<int:command_id>', methods=['DELETE'])
def delete_command(command_id):
    """删除指令配置"""
    from services.command_config_service import command_config_service

    try:
        result = command_config_service.delete_command(command_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"删除指令失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/commands/statistics', methods=['GET'])
def get_command_statistics():
    """获取指令使用统计"""
    from services.command_config_service import command_config_service

    try:
        stats = command_config_service.get_usage_statistics()

        if stats['success']:
            return jsonify(stats), 200
        else:
            return jsonify(stats), 400
    except Exception as e:
        logger.error(f"获取指令统计失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/commands/backup', methods=['GET'])
def backup_commands():
    """备份指令配置"""
    from services.command_config_service import command_config_service

    try:
        result = command_config_service.backup_commands()

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"备份指令配置失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/commands/restore', methods=['POST'])
def restore_commands():
    """恢复指令配置"""
    from services.command_config_service import command_config_service

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供备份数据'}), 400

        result = command_config_service.restore_commands(data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"恢复指令配置失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@robot_bp.route('/hook-health', methods=['GET'])
@login_required
def robot_hook_health():
    """Hook 托盘状态（已登录，供非 loopback 前端轮询）"""
    from services.hook_runtime_service import collect_tray_heartbeat

    return jsonify(collect_tray_heartbeat()), 200


@robot_bp.route('/wechat-inject', methods=['POST'])
@login_required
def robot_wechat_inject():
    """已登录用户触发微信 Hook 注入（等同 loopback 注入接口）"""
    from services.wechat_inject_service import run_wechat_hook_inject

    try:
        result = run_wechat_hook_inject(bootstrap_inject=True, quit_before_inject=False)
        if not result.get('ok'):
            return jsonify(result), 500
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@robot_bp.route('/status', methods=['GET'])
@login_required
def robot_status():
    """机器人与 Hook 运行状态（桌面端监控）"""
    from services.hook_runtime_service import collect_tray_heartbeat, get_inbound_recv_stats

    db: Session = get_db_session()
    try:
        user = get_current_user_from_request(db)
        config = RobotService.get_default_config(db, user.id)
        tray = collect_tray_heartbeat()
        stats = get_inbound_recv_stats()

        is_running = bool(config and config.get('status') == 'running')
        return jsonify({
            'success': True,
            'is_running': is_running,
            'tcp_connected': tray.get('hook_tcp_listening', False),
            'hook_enabled': tray.get('hook_ready', False),
            'hook_control_ok': tray.get('hook_control_ok', False),
            'wechat_process_running': tray.get('wechat_process_running', False),
            'hook_profile': tray.get('hook_profile', {}),
            'inbound_enabled': tray.get('inbound_enabled', True),
            'today_messages': stats.get('inbound_recv_count', 0),
            'today_orders': 0,
            'error_count': 0,
            'hook_callback_url': tray.get('hook_callback_url'),
            'hook_receive_mode': tray.get('hook_receive_mode'),
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@robot_bp.route('/process-command', methods=['POST'])
def process_smart_command():
    """
    智能指令处理接口(供微信Hook调用)

    Request Body:
    {
        "message": "报表",
        "sender": {
            "customer_id": 1,
            "customer_name": "张三餐馆",
            "sales_person": "李四",
            "route_id": 2
        }
    }
    """
    from services.robot_service import RobotService

    try:
        data = request.get_json()
        if not data or not data.get('message'):
            return jsonify({'success': False, 'error': '消息内容不能为空'}), 400

        message = data['message']
        sender_info = data.get('sender', {})

        db: Session = get_db_session()
        try:
            result = RobotService.process_smart_command(db, message, sender_info)

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400
        finally:
            db.close()

    except Exception as e:
        logger.error(f"智能指令处理失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
