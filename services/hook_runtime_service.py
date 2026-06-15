"""
Hook 运行时状态探测（参考 sim-bot-node hook_readiness / tray_heartbeat）
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any

from config.settings import settings
from services.hook_client import hook_client
from utils.weixin_process import get_running_weixin_pid
from utils.hook_inject_config import build_hook_inject_config

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {'at': 0.0, 'data': None}
_probe_cache: dict[str, Any] = {'at': 0.0, 'data': None}


def _runtime_cache_ms() -> float:
    return float(getattr(settings, 'HOOK_RUNTIME_CACHE_MS', 5000) or 5000)


def _probe_cache_ms() -> float:
    return max(_runtime_cache_ms(), 5000.0)

_inbound_recv_count = 0


def _inbound_enabled_from_db() -> bool:
    try:
        from database.db_config import get_db_session
        from services.bot_runtime_store import get_bot_inbound_enabled

        db = get_db_session()
        try:
            return get_bot_inbound_enabled(db)
        finally:
            db.close()
    except Exception:
        return settings.BOT_INBOUND_ENABLED


def invalidate_hook_cache() -> None:
    _cache['at'] = 0.0
    _cache['data'] = None
    _probe_cache['at'] = 0.0
    _probe_cache['data'] = None


def record_inbound_recv() -> None:
    global _inbound_recv_count
    _inbound_recv_count += 1


def get_inbound_recv_stats() -> dict:
    return {'inbound_recv_count': _inbound_recv_count}


def _is_local_tcp_open(port: int, host: str = '127.0.0.1', timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pick_wxid(data: dict | None) -> str:
    if not data or not isinstance(data, dict):
        return ''
    candidates = []
    top = data
    nested = top.get('data') if isinstance(top.get('data'), dict) else {}
    for source in (top, nested):
        for key in (
            'account_wxid', 'wxid', 'userName', 'username',
            'account', 'self_wxid', 'login_wxid',
        ):
            val = source.get(key)
            if val:
                candidates.append(str(val).strip())
    for wxid in candidates:
        if wxid and not wxid.endswith('@chatroom'):
            return wxid
    return ''


def probe_hook_readiness() -> dict:
    now = time.time() * 1000
    if _probe_cache['data'] is not None and now - _probe_cache['at'] < _probe_cache_ms():
        return _probe_cache['data']

    empty = {
        'control_ok': False,
        'operational_ok': False,
        'has_wxid': False,
        'wxid': '',
        'nickname': '',
        'avatar_url': '',
        'wechat_login_required': False,
        'via': '',
        'error': '',
    }
    probe = hook_client.probe_control_plane()
    if not probe.get('ok'):
        result = {**empty, 'error': probe.get('error', 'control_plane_unreachable')}
        _probe_cache['at'] = now
        _probe_cache['data'] = result
        return result

    wxid = ''
    nickname = ''
    avatar_url = ''
    via = ''
    wechat_login_required = False

    profile = hook_client.get_profile_cache()
    raw_data = profile.get('raw', {}) if isinstance(profile.get('raw'), dict) else {}
    raw_inner = raw_data.get('data') if isinstance(raw_data.get('data'), str) else ''
    if isinstance(raw_inner, str) and 'no login' in raw_inner.lower():
        wechat_login_required = True

    if profile.get('wxid'):
        wxid = str(profile['wxid']).strip()
        nickname = profile.get('nickname', '')
        avatar_url = profile.get('avatar_url', '')
        via = 'get_profile_cache'

    if not wxid:
        login = hook_client.probe_login_wxid()
        if login.get('ok') and login.get('wxid'):
            wxid = str(login['wxid']).strip()
            nickname = login.get('nickname', '')
            avatar_url = login.get('avatar_url', '')
            via = login.get('apiPath', 'login_probe')

    api_ok = False
    if not wxid:
        rooms = hook_client.get_chatroom_list()
        items = rooms.get('items') or []
        total = int(rooms.get('total') or 0)
        api_ok = bool(rooms.get('ok') and (len(items) > 0 or total > 0))
        if api_ok:
            via = 'get_chatroom_list'

    operational_ok = bool(wxid) or api_ok
    result = {
        'control_ok': True,
        'operational_ok': operational_ok,
        'has_wxid': bool(wxid),
        'wxid': wxid,
        'nickname': nickname,
        'avatar_url': avatar_url,
        'wechat_login_required': wechat_login_required,
        'via': via,
        'error': '',
    }
    _probe_cache['at'] = now
    _probe_cache['data'] = result
    return result


def evaluate_hook_runtime() -> dict:
    now = time.time() * 1000
    if _cache['data'] is not None and now - _cache['at'] < _runtime_cache_ms():
        return _cache['data']

    readiness = probe_hook_readiness()
    wechat_running = get_running_weixin_pid() is not None if os.name == 'nt' else False
    hook_ready = readiness['operational_ok'] and readiness['control_ok']
    hook_partial = wechat_running and not hook_ready and readiness['control_ok'] is False

    data = {
        'wechat_process_running': wechat_running,
        'hook_control_ok': readiness['control_ok'],
        'hook_http_ok': readiness['control_ok'],
        'hook_ready': hook_ready,
        'hook_partial': hook_partial,
        'hook_has_wxid': readiness['has_wxid'],
        'hook_stored_wxid': readiness['wxid'],
        'hook_wechat_login_required': readiness['wechat_login_required'],
        'hook_profile': {
            'wxid': readiness['wxid'],
            'nickname': readiness['nickname'],
            'avatar_url': readiness['avatar_url'],
        },
        'needs_inject': wechat_running and not hook_ready,
        'inbound_enabled': _inbound_enabled_from_db(),
    }
    _cache['at'] = now
    _cache['data'] = data
    return data


def collect_tray_heartbeat_light() -> dict:
    """顶栏轮询用：不重复探测 Hook，不访问群表 revision（避免与群列表争抢 SQLite）。"""
    inj = build_hook_inject_config()
    callback_port = settings.HOOK_CALLBACK_PORT or settings.FLASK_PORT
    tcp_port = settings.TCP_PORT
    return {
        **evaluate_hook_runtime(),
        **get_inbound_recv_stats(),
        'hook_tcp_listening': _is_local_tcp_open(tcp_port) if os.name == 'nt' else False,
        'hook_callback_listening': _is_local_tcp_open(callback_port) if os.name == 'nt' else False,
        'hook_callback_port': callback_port,
        'hook_receive_mode': inj['recivemode'],
        'hook_callback_url': inj['http_callback_url'],
        'hook_dll_http_port': settings.HOOK_DLL_HTTP_PORT,
        'hook_api_base': settings.HOOK_BASE_URL,
        'groups_desk_revision': '',
    }


def collect_tray_heartbeat() -> dict:
    rt = evaluate_hook_runtime()
    groups_revision = ''
    try:
        from database.db_config import get_db_session
        from services.desktop_group_store import (
            compute_groups_desk_revision,
            set_wechat_login_wxid,
        )

        db = get_db_session()
        try:
            if rt.get('hook_profile', {}).get('wxid'):
                set_wechat_login_wxid(db, rt['hook_profile']['wxid'])
            groups_revision = compute_groups_desk_revision(db)
        finally:
            db.close()
    except Exception:
        groups_revision = ''

    inj = build_hook_inject_config()
    tcp_port = settings.TCP_PORT
    callback_port = settings.HOOK_CALLBACK_PORT or settings.FLASK_PORT

    hook_tcp_listening = _is_local_tcp_open(tcp_port) if os.name == 'nt' else False
    hook_callback_listening = _is_local_tcp_open(callback_port) if os.name == 'nt' else False

    return {
        **rt,
        **get_inbound_recv_stats(),
        'hook_tcp_listening': hook_tcp_listening,
        'hook_callback_listening': hook_callback_listening,
        'hook_callback_port': callback_port,
        'hook_receive_mode': inj['recivemode'],
        'hook_callback_url': inj['http_callback_url'],
        'hook_dll_http_port': settings.HOOK_DLL_HTTP_PORT,
        'hook_api_base': settings.HOOK_BASE_URL,
        'groups_desk_revision': groups_revision,
    }
