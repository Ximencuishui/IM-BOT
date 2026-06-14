"""
Hook 消息回调与控制 API（参考 sim-bot-node：POST /api/recvMsg、GET /api/health/tray）
"""
from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request

from config.settings import settings
from services.hook_runtime_service import (
    collect_tray_heartbeat,
    collect_tray_heartbeat_light,
    record_inbound_recv,
)
from services.wechat_inject_service import run_wechat_hook_inject
from utils.hook_inject_config import build_hook_inject_config
from utils.hook_recv_normalize import normalize_hook_inbound_payload

logger = logging.getLogger(__name__)

hook_callback_bp = Blueprint('hook_callback', __name__)

_HOOK_OK_BODY = {'errCode': 0, 'code': 0, 'msg': 'ok'}


def _is_loopback() -> bool:
    addr = (request.remote_addr or '').strip()
    if addr in ('127.0.0.1', '::1', 'localhost'):
        return True
    if request.access_route:
        return request.access_route[-1] in ('127.0.0.1', '::1')
    return False


def _parse_recv_body():
    if request.is_json:
        return request.get_json(silent=True)
    raw = request.get_data(as_text=True)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _dispatch_hook_message(payload: dict) -> dict:
    from services.message_service import process_incoming_message

    record_inbound_recv()
    return process_incoming_message(payload)


@hook_callback_bp.route('/recvMsg', methods=['POST'])
@hook_callback_bp.route('/api/recvMsg', methods=['POST'])
def recv_msg_callback():
    """Hook DLL HTTP 回调（与注入配置 http_callback_url 一致）"""
    try:
        body = _parse_recv_body()
        payload = normalize_hook_inbound_payload(body)
        if not payload:
            return jsonify(_HOOK_OK_BODY), 200
        result = _dispatch_hook_message(payload)
        if result.get('status') == 'error':
            logger.warning('[recvMsg] process error: %s', result.get('error'))
        return jsonify(_HOOK_OK_BODY), 200
    except Exception as exc:
        logger.warning('[recvMsg] error: %s', exc, exc_info=True)
        return jsonify(_HOOK_OK_BODY), 200


@hook_callback_bp.route('/api/health/tray', methods=['GET'])
def tray_health():
    """桌面端顶栏 Hook 状态（本机 loopback）"""
    if not _is_loopback():
        return jsonify({'error': 'forbidden'}), 403
    quick = str(request.args.get('quick', '1')).strip() not in ('0', 'false', 'no')
    payload = collect_tray_heartbeat_light() if quick else collect_tray_heartbeat()
    return jsonify(payload), 200


@hook_callback_bp.route('/api/bot/wechat-inject', methods=['POST'])
def bot_wechat_inject():
    """手动/自动热注入（本机 loopback，不关微信）"""
    if not _is_loopback():
        return jsonify({'error': 'forbidden'}), 403
    try:
        hot = str(request.args.get('hot', '0')).strip() in ('1', 'true', 'yes')
        data = request.get_json(silent=True) or {}
        exe_override = (
            data.get('wechat_exe_path')
            or data.get('wechatExePath')
            or ''
        ).strip()
        if not exe_override:
            from database.db_config import get_db_session
            from services.wechat_exe_store import get_saved_wechat_exe_path
            db = get_db_session()
            try:
                exe_override = get_saved_wechat_exe_path(db)
            finally:
                db.close()
        result = run_wechat_hook_inject(
            bootstrap_inject=True,
            quit_before_inject=not hot,
            wechat_exe_path=exe_override or None,
        )
        if not result.get('ok'):
            return jsonify(result), 200
        return jsonify(result), 200
    except Exception as exc:
        logger.error('[api/bot/wechat-inject] %s', exc, exc_info=True)
        return jsonify({'ok': False, 'error': str(exc)}), 500


@hook_callback_bp.route('/api/hook/inject-config', methods=['GET'])
def hook_inject_config_view():
    """查看当前注入配置（供桌面端展示）"""
    inj = build_hook_inject_config()
    return jsonify({
        'success': True,
        'config': inj,
        'hook_api_base': settings.HOOK_BASE_URL,
        'hook_receive_mode': settings.HOOK_RECEIVE_MODE,
        'bot_inbound_enabled': settings.BOT_INBOUND_ENABLED,
    }), 200


@hook_callback_bp.route('/push/group-message', methods=['PUT'])
def group_message_callback():
    """旧版 vxhook 群聊推送（保留兼容）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        payload = normalize_hook_inbound_payload(data) or data
        from_username = payload.get('fromUserName')
        real_content = payload.get('real_content')
        content = payload.get('content', {})
        if isinstance(content, dict):
            content = content.get('String', '')
        message_content = real_content if real_content else content
        sender_nick = payload.get('sender_nick', '')

        logger.info(
            '收到群聊消息(legacy) - 群ID: %s, 发送者: %s',
            from_username,
            sender_nick,
        )

        result = _dispatch_hook_message({
            'group_id': from_username,
            'sender': sender_nick,
            'content': message_content,
            'timestamp': payload.get('createTime'),
            'msg_type': payload.get('msgType'),
            'msg_id': payload.get('msgId'),
            'new_msg_id': payload.get('newMsgId'),
            'raw_data': payload,
        })
        return jsonify({'success': True, 'result': result}), 200
    except Exception as exc:
        logger.error('处理群聊消息回调失败: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500


@hook_callback_bp.route('/push/private-message', methods=['PUT'])
def private_message_callback():
    """旧版 vxhook 私聊推送（保留兼容）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        payload = normalize_hook_inbound_payload(data) or data
        from_username = payload.get('fromUserName')
        content = payload.get('content', '')
        if isinstance(content, dict):
            content = content.get('String', '')
        sender_nick = payload.get('sender_nick', '')

        result = _dispatch_hook_message({
            'group_id': None,
            'sender': from_username,
            'sender_nick': sender_nick,
            'content': content,
            'timestamp': payload.get('createTime'),
            'msg_type': payload.get('msgType'),
            'msg_id': payload.get('msgId'),
            'new_msg_id': payload.get('newMsgId'),
            'is_private': True,
            'raw_data': payload,
        })
        return jsonify({'success': True, 'result': result}), 200
    except Exception as exc:
        logger.error('处理私聊消息回调失败: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
