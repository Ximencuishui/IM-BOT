"""
规范化 Hook HTTP 回调 / TCP JSON 载荷（参考 sim-bot-node recv_normalize）
"""
from __future__ import annotations

import json
from typing import Any, Optional

_WRAP_KEYS = ('data', 'Data', 'msg', 'message', 'body', 'Body', 'payload', 'Payload')


def normalize_hook_inbound_payload(raw: Any) -> Optional[dict]:
    if raw is None:
        return None

    obj = raw
    if isinstance(obj, str):
        text = obj.strip()
        if not text:
            return None
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return None

    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                return item
        return None

    if not isinstance(obj, dict):
        return None

    for key in _WRAP_KEYS:
        inner = obj.get(key)
        if isinstance(inner, dict):
            rest = {k: v for k, v in obj.items() if k != key}
            return {**rest, **inner}

    return obj
