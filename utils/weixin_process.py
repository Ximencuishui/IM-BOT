"""Windows 微信进程探测"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

_WEIXIN_IMAGE_NAMES = ('Weixin.exe', 'WeChat.exe')


def _tasklist_pids(image_name: str) -> list[int]:
    if os.name != 'nt':
        return []
    try:
        out = subprocess.check_output(
            ['tasklist', '/FI', f'IMAGENAME eq {image_name}', '/FO', 'CSV', '/NH'],
            encoding='utf-8',
            errors='ignore',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except Exception:
        return []
    pids = []
    for line in out.splitlines():
        line = line.strip()
        if not line or image_name.lower() not in line.lower():
            continue
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image_name.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                continue
    return pids


def get_running_weixin_pid() -> int | None:
    for name in _WEIXIN_IMAGE_NAMES:
        pids = _tasklist_pids(name)
        if pids:
            return pids[0]
    return None


def get_running_weixin_executable() -> str | None:
    """从正在运行的微信进程读取 exe 路径（冷注入关进程前应先调用）。"""
    pid = get_running_weixin_pid()
    if not pid:
        return None
    try:
        out = subprocess.check_output(
            [
                'powershell',
                '-NoProfile',
                '-Command',
                f'(Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue).Path',
            ],
            encoding='utf-8',
            errors='ignore',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            timeout=8,
        ).strip()
        if out and Path(out).is_file():
            return str(Path(out).resolve())
    except Exception:
        pass
    return None


def stop_running_weixin(wait_ms: int = 3000) -> bool:
    if os.name != 'nt':
        return False
    try:
        for name in _WEIXIN_IMAGE_NAMES:
            subprocess.run(
                ['taskkill', '/IM', name, '/F', '/T'],
                check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        time.sleep(wait_ms / 1000.0)
        return get_running_weixin_pid() is None
    except Exception:
        return False


def should_quit_weixin_before_inject() -> bool:
    return os.getenv('WECHAT_QUIT_BEFORE_INJECT', '0') == '1'
