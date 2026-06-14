"""
启动微信 Hook 注入（参考 sim-bot-node launch-wechat-hook.mjs，不修改子项目代码）

用法: python scripts/launch_wechat_hook.py
依赖: WECHAT_HK_DIR 或项目根/hk 或 sim-bot-node/hk 下的 x64 inject.exe
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.weixin_locate import locate_weixin_exe
from utils.weixin_process import (
    get_running_weixin_executable,
    get_running_weixin_pid,
    should_quit_weixin_before_inject,
    stop_running_weixin,
)
from utils.hook_inject_config import hook_inject_config_json


def resolve_hk_root() -> Path:
    if os.getenv('WECHAT_HK_DIR'):
        return Path(os.getenv('WECHAT_HK_DIR')).resolve()
    for candidate in (
        ROOT / 'hk',
        ROOT / 'sim-bot-node' / 'hk',
    ):
        if (candidate / 'x64 inject.exe').is_file():
            return candidate.resolve()
    return (ROOT / 'hk').resolve()


def main() -> int:
    if os.name != 'nt':
        print('本脚本仅支持 Windows。', file=sys.stderr)
        return 1

    hk_root = resolve_hk_root()
    inject_exe = hk_root / 'x64 inject.exe'
    dll_path = hk_root / 'libGLESv1.dll'

    if not inject_exe.is_file():
        print(f'未找到注入程序: {inject_exe}', file=sys.stderr)
        print('请设置 WECHAT_HK_DIR 或将 hk 套件放到项目 hk/ 目录', file=sys.stderr)
        return 1
    if not dll_path.is_file():
        print(f'未找到 DLL: {dll_path}', file=sys.stderr)
        return 1

    always_launch = os.getenv('WECHAT_INJECT_ALWAYS_LAUNCH') == '1'
    cached_exe: str | None = os.getenv('WECHAT_EXE_PATH', '').strip() or None
    if cached_exe and not Path(cached_exe).is_file():
        cached_exe = None

    if not always_launch and should_quit_weixin_before_inject() and get_running_weixin_pid():
        if not cached_exe:
            cached_exe = get_running_weixin_executable()
        print('[bootstrap] 关闭已运行的微信以便重新注入…')
        stop_running_weixin(wait_ms=3000)

    running_pid = None if always_launch else get_running_weixin_pid()
    target_arg: str

    if running_pid is None:
        print('查找微信…')
        weixin = cached_exe or locate_weixin_exe()
        if not weixin:
            print(
                '未找到 Weixin.exe / WeChat.exe。请确认已安装 PC 版微信；'
                '或在 .env 中设置 WECHAT_EXE_PATH=你的微信安装路径',
                file=sys.stderr,
            )
            return 1
        print(f'找到 — {weixin}')
        target_arg = str(Path(weixin).resolve())
    else:
        print(f'检测到微信已在运行（PID {running_pid}），直接注入…')
        target_arg = str(running_pid)

    json_arg = hook_inject_config_json()
    print('注入配置:', json_arg)

    cmd = [str(inject_exe), target_arg, str(dll_path), json_arg]
    print('执行:', ' '.join(cmd[:3]), '<config-json>')

    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        print(f'注入失败，退出码 {proc.returncode}', file=sys.stderr)
        return proc.returncode

    print('微信 Hook 注入完成。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
