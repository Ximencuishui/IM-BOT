import logging
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from config.settings import settings

logger = logging.getLogger(__name__)


def _hook_port_open(base_url: str | None = None, timeout: float = 0.35) -> bool:
    try:
        host = '127.0.0.1'
        port = int(settings.HOOK_DLL_HTTP_PORT)
        if base_url:
            parsed = urlparse(base_url)
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port:
                port = parsed.port
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _hook_timeout(default: float = 6.0) -> float:
    return float(getattr(settings, 'HOOK_PROBE_TIMEOUT', default) or default)


def _hook_success(data: Any) -> bool:
    if not isinstance(data, dict):
        return True
    if data.get('errCode') is not None:
        return int(data['errCode']) == 0
    if data.get('code') is not None:
        return int(data['code']) == 0
    return True


def _parse_profile_cache(data: dict) -> dict:
    wxid = ''
    nickname = ''
    avatar_url = ''
    if not isinstance(data, dict):
        return {'ok': False, 'wxid': '', 'nickname': '', 'avatar_url': '', 'raw': data}

    inner = data.get('data')
    if isinstance(inner, dict):
        wxid = str(inner.get('wxid') or inner.get('userName') or '').strip()
        nickname = str(inner.get('nickName') or inner.get('nickname') or '').strip()
        avatar_url = str(inner.get('avatar') or inner.get('avatar_url') or '').strip()
    elif isinstance(inner, str):
        pass
    else:
        wxid = _pick_wxid_from_response(data)

    return {
        'ok': bool(wxid),
        'wxid': wxid,
        'nickname': nickname,
        'avatar_url': avatar_url,
        'raw': data,
    }


def _pick_wxid_from_response(data: dict) -> str:
    nested = data.get('data') if isinstance(data.get('data'), dict) else {}
    for source in (data, nested):
        for key in (
            'account_wxid', 'wxid', 'userName', 'username',
            'account', 'self_wxid', 'login_wxid',
        ):
            val = source.get(key)
            if val:
                s = str(val).strip()
                if s and not s.endswith('@chatroom'):
                    return s
    return ''


class HookClient:
    """VXHook / PC 微信 Hook 控制面 HTTP 客户端（参考 sim-bot-node hook/client.js）"""

    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or settings.HOOK_BASE_URL).rstrip('/')
        self.token = token if token is not None else settings.HOOK_API_TOKEN
        self.session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            headers['X-Api-Key'] = self.token
        self.session.headers.update(headers)

    def probe_control_plane(self) -> dict:
        if not _hook_port_open(self.base_url):
            return {'ok': False, 'error': 'control_plane_unreachable'}
        t = _hook_timeout(1.5)
        try:
            self.session.get(f'{self.base_url}/', timeout=t)
            return {'ok': True, 'via': 'get_root'}
        except Exception:
            pass
        for path in ('/api/get_profile_cache', '/api/check_login'):
            try:
                self.session.post(f'{self.base_url}{path}', json={}, timeout=t)
                return {'ok': True, 'via': path}
            except Exception:
                continue
        return {'ok': False, 'error': 'control_plane_unreachable'}

    def health_probe(self) -> dict:
        r = self.probe_control_plane()
        return {'ok': r.get('ok', False), 'error': r.get('error')}

    def get_profile_cache(self) -> dict:
        try:
            resp = self.session.post(
                f'{self.base_url}/api/get_profile_cache',
                json={},
                timeout=10,
            )
            if resp.status_code == 200:
                return _parse_profile_cache(resp.json())
        except Exception as exc:
            logger.debug('get_profile_cache failed: %s', exc)
        return {'ok': False, 'wxid': '', 'nickname': '', 'avatar_url': '', 'raw': None}

    def probe_login_wxid(self) -> dict:
        prof = self.get_profile_cache()
        if prof.get('wxid'):
            return {
                'ok': True,
                'wxid': prof['wxid'],
                'apiPath': '/api/get_profile_cache',
                'nickname': prof.get('nickname', ''),
                'avatar_url': prof.get('avatar_url', ''),
            }
        for path in (
            '/api/check_login',
            '/api/get_login_info',
            '/api/get_user_info',
            '/api/GetUserInfo',
            '/api/get_account_info',
        ):
            try:
                resp = self.session.post(f'{self.base_url}{path}', json={}, timeout=8)
                if resp.status_code != 200:
                    continue
                wxid = _pick_wxid_from_response(resp.json())
                if wxid:
                    return {'ok': True, 'wxid': wxid, 'apiPath': path}
            except Exception:
                continue
        return {'ok': False, 'wxid': '', 'message': 'hook login wxid not available'}

    def get_chatroom_list(self) -> dict:
        try:
            resp = self.session.post(
                f'{self.base_url}/api/get_chatroom_list',
                json={},
                timeout=15,
            )
            if resp.status_code != 200:
                return {'ok': False, 'items': [], 'total': 0}
            data = resp.json()
            items = []
            if isinstance(data, dict):
                raw = data.get('data') or data.get('list') or data.get('chatrooms')
                if isinstance(raw, list):
                    items = raw
                elif isinstance(raw, dict):
                    items = list(raw.values()) if raw else []
            from utils.hook_chatroom import normalize_hook_chatroom_item

            norm = [normalize_hook_chatroom_item(it) for it in items if isinstance(it, dict)]
            return {'ok': _hook_success(data), 'items': norm, 'total': len(norm), 'raw': data}
        except Exception as exc:
            logger.error('get_chatroom_list failed: %s', exc)
            return {'ok': False, 'items': [], 'total': 0, 'error': str(exc)}

    def send_text(self, wxid: str, msg: str) -> bool:
        try:
            response = self.session.post(
                f'{self.base_url}/api/send_text_msg',
                json={'wxid': wxid, 'msg': msg},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f'发送文本消息失败: {e}')
            return False

    def send_at_text(self, room_id: str, msg: str, wxids: List[str]) -> bool:
        try:
            response = self.session.post(
                f'{self.base_url}/api/send_at_text',
                json={
                    'roomId': room_id,
                    'msg': msg,
                    'wxids': ','.join(wxids),
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f'发送@消息失败: {e}')
            return False

    def send_pat(self, room_id: str, wxid: str) -> bool:
        try:
            response = self.session.post(
                f'{self.base_url}/api/send_pat',
                json={'roomId': room_id, 'wxid': wxid},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f'发送拍一拍失败: {e}')
            return False

    def send_quote(
        self,
        reply: str,
        refer_content: str,
        from_usr: str,
        new_msg_id: str,
        send_to: str,
        create_time: int = 0,
    ) -> bool:
        try:
            response = self.session.post(
                f'{self.base_url}/api/send_quote',
                json={
                    'reply': reply,
                    'referContent': refer_content,
                    'fromUsr': from_usr,
                    'newmsgid': new_msg_id,
                    'msgSource': '',
                    'createTime': create_time,
                    'sendto': send_to,
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f'发送引用消息失败: {e}')
            return False

    def batch_send_text(self, messages: List[Dict[str, str]]) -> bool:
        try:
            response = self.session.post(
                f'{self.base_url}/api/batch_send_text_msg',
                json={'messages': messages},
                timeout=15,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f'批量发送消息失败: {e}')
            return False

    def get_group_members(self, wxid: str, room_id: str) -> Dict:
        try:
            response = self.session.post(
                f'{self.base_url}/api/get_group_member_contact',
                json={'wxid': wxid, 'roomId': room_id},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f'查询群成员失败: {e}')
            return {}

    def voice_to_text(self, client_msg_id: str, new_msg_id: str, length: str) -> str:
        try:
            response = self.session.post(
                f'{self.base_url}/api/get_voice_trans',
                json={
                    'clientMsgId': client_msg_id,
                    'newMsgId': new_msg_id,
                    'length': length,
                },
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('text', '')
            return ''
        except Exception as e:
            logger.error(f'语音转文本失败: {e}')
            return ''


hook_client = HookClient()
