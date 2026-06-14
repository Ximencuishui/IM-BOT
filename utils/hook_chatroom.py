"""从 Hook get_chatroom_list 条目中解析群 ID 与昵称（对齐 sim-bot-node username 字段）"""
from __future__ import annotations


def extract_chatroom_id(item: dict) -> str:
    if not isinstance(item, dict):
        return ''
    ordered_keys = (
        'username',
        'room_id',
        'userName',
        'chatroom',
        'chatroomUserName',
        'wxid',
    )
    plain = ''
    for key in ordered_keys:
        val = str(item.get(key) or '').strip()
        if not val:
            continue
        if '@chatroom' in val:
            return val
        if not plain and '@' not in val:
            plain = val
    if plain:
        return f'{plain}@chatroom'
    return ''


def extract_chatroom_nick(item: dict) -> str:
    if not isinstance(item, dict):
        return ''
    return str(
        item.get('nick_name')
        or item.get('nickName')
        or item.get('nickname')
        or item.get('name')
        or item.get('remark')
        or ''
    ).strip()


def normalize_hook_chatroom_item(item: dict) -> dict:
    """统一字段，供 API / 前端使用。"""
    if not isinstance(item, dict):
        return {}
    rid = extract_chatroom_id(item)
    nick = extract_chatroom_nick(item)
    return {
        **item,
        'username': rid or str(item.get('username') or '').strip(),
        'wxid': rid or str(item.get('wxid') or '').strip(),
        'room_id': rid or str(item.get('room_id') or '').strip(),
        'nick_name': nick,
        'nickName': nick or str(item.get('nickName') or '').strip(),
    }
