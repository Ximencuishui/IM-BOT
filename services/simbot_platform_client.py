"""SimBot 管理平台 HTTP 客户端（桌面端授权可选走平台核销）"""
from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import settings

logger = logging.getLogger(__name__)


def _headers(bearer_token: str | None = None) -> dict:
    h = {'Content-Type': 'application/json'}
    token = bearer_token or settings.SIMBOT_PLATFORM_TOKEN
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def platform_available() -> bool:
    return bool(settings.SIMBOT_PLATFORM_URL.strip())


def redeem_robot_on_platform(
    wxid: str,
    code: str,
    bearer_token: str | None = None,
) -> dict | None:
    base = settings.SIMBOT_PLATFORM_URL.rstrip('/')
    if not base:
        return None
    paths = (
        '/api/admin/prd/robot-redeem',
        '/api/prd/robot-redeem',
    )
    body = {'wxid': wxid, 'code': code, 'last_card_cipher': code}
    last_err = None
    for path in paths:
        try:
            resp = requests.post(
                f'{base}{path}',
                json=body,
                headers=_headers(bearer_token),
                timeout=30,
            )
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                last_err = data.get('error') or resp.text
                continue
            return data
        except Exception as exc:
            last_err = str(exc)
            logger.warning('platform redeem %s failed: %s', path, exc)
    if last_err:
        return {'error': last_err}
    return None


def fetch_license_status_from_platform(bearer_token: str | None = None) -> dict | None:
    base = settings.SIMBOT_PLATFORM_URL.rstrip('/')
    if not base:
        return None
    for path in ('/api/admin/prd/license-status', '/api/prd/license-status'):
        try:
            resp = requests.get(
                f'{base}{path}',
                headers=_headers(bearer_token),
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.debug('platform license-status %s: %s', path, exc)
    return None


def fetch_groups_from_platform(
    *,
    sync: bool = True,
    desk: bool = True,
    bearer_token: str | None = None,
) -> dict | None:
    base = settings.SIMBOT_PLATFORM_URL.rstrip('/')
    if not base:
        return None
    params = {'sync': '1' if sync else '0', 'desk': '1' if desk else '0'}
    for path in ('/api/admin/prd/groups', '/api/prd/groups'):
        try:
            resp = requests.get(
                f'{base}{path}',
                params=params,
                headers=_headers(bearer_token),
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.debug('platform groups %s: %s', path, exc)
    return None


def fetch_hook_chatrooms_from_platform(bearer_token: str | None = None) -> dict | None:
    base = settings.SIMBOT_PLATFORM_URL.rstrip('/')
    if not base:
        return None
    for path in ('/api/admin/hook/chatrooms', '/api/hook/chatrooms'):
        try:
            resp = requests.get(
                f'{base}{path}',
                headers=_headers(bearer_token),
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.debug('platform hook chatrooms %s: %s', path, exc)
    return None
