"""
微信 Hook 注入 JSON 配置（与 sim-bot-node inject_config 对齐）
"""
from __future__ import annotations

import json
import os

from config.settings import settings


def build_hook_inject_config() -> dict:
    tcp_host = settings.TCP_HOST if settings.TCP_HOST != '0.0.0.0' else '127.0.0.1'
    tcp_port = settings.TCP_PORT
    http_port = settings.FLASK_PORT
    hook_dll_http_port = settings.HOOK_DLL_HTTP_PORT

    callback_port = settings.HOOK_CALLBACK_PORT
    callback_http_port = callback_port if callback_port > 0 and callback_port != http_port else http_port

    callback_url = settings.HOOK_CALLBACK_URL or (
        f'http://127.0.0.1:{callback_http_port}/api/recvMsg'
    )

    mode_raw = (settings.HOOK_RECEIVE_MODE or 'http').strip().lower()
    if mode_raw == 'tcp':
        recivemode = 'tcp'
    elif mode_raw in ('all', 'both'):
        recivemode = 'all'
    else:
        recivemode = 'http'

    return {
        'recivemode': recivemode,
        'tcp_ip': tcp_host,
        'tcp_port': tcp_port,
        'http_server_port': hook_dll_http_port,
        'http_callback_url': callback_url,
        'usedefault': False,
        'start_server_while_login': True,
    }


def hook_inject_config_json() -> str:
    return json.dumps(build_hook_inject_config(), ensure_ascii=False)
