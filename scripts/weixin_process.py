"""Windows 微信进程探测（参考 sim-bot-node weixin-process.mjs）"""
from __future__ import annotations

import os
import subprocess
import time


def get_running_weixin_pid() -> int | None:
    if os.name != 'nt':
        return None
    try:
        out = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq Weixin.exe', '/FO', 'CSV', '/NH'],
            encoding='utf-8',
            errors='ignore',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except Exception:
        return None
    for line in out.splitlines():
        line = line.strip()
        if not line or 'Weixin.exe' not in line:
            continue
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == 'weixin.exe':
            try:
                return int(parts[1])
            except ValueError:
                continue
    return None


def stop_running_weixin(wait_ms: int = 3000) -> bool:
    if os.name != 'nt':
        return False
    pid = get_running_weixin_pid()
    if not pid:
        return True
    try:
        subprocess.run(
            ['taskkill', '/PID', str(pid), '/F'],
            check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        time.sleep(wait_ms / 1000.0)
        return get_running_weixin_pid() is None
    except Exception:
        return False


def should_quit_weixin_before_inject() -> bool:
    return os.getenv('WECHAT_QUIT_BEFORE_INJECT', '0') == '1'
