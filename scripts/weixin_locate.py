"""定位 PC 微信 Weixin.exe（常见路径）"""
from __future__ import annotations

import os
from pathlib import Path


def locate_weixin_exe() -> str | None:
    if os.name != 'nt':
        return None

    candidates: list[Path] = []
    pf = os.environ.get('ProgramFiles', r'C:\Program Files')
    pfx86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    local = os.environ.get('LOCALAPPDATA', '')

    for base in (
        Path(pf) / 'Tencent' / 'Weixin',
        Path(pf) / 'Tencent' / 'WeChat',
        Path(pfx86) / 'Tencent' / 'Weixin',
        Path(pfx86) / 'Tencent' / 'WeChat',
        Path(local) / 'Programs' / 'Tencent' / 'Weixin',
        Path(local) / 'Programs' / 'Tencent' / 'WeChat',
    ):
        candidates.append(base / 'Weixin.exe')
        candidates.append(base / 'WeChat.exe')

    for path in candidates:
        if path.is_file():
            return str(path.resolve())
    return None
