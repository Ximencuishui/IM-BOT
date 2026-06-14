"""
微信 Hook 注入服务（参考 sim-bot-node wechat_inject.js）
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from config.settings import settings
from utils.hook_inject_config import build_hook_inject_config

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _humanize_inject_failure(stdout: str, stderr: str, returncode: int) -> str:
    blob = f'{stdout or ""}\n{stderr or ""}'
    if '未找到注入程序' in blob or 'inject.exe' in blob and '未找到' in blob:
        return (
            '未找到 hk 注入套件（x64 inject.exe）。'
            '请将 sim-bot-node/hk 复制到项目 hk/ 目录，或设置环境变量 WECHAT_HK_DIR。'
        )
    if '未找到 Weixin.exe' in blob or '未找到微信' in blob or 'WeChat.exe' in blob:
        return (
            '未找到 PC 版微信（Weixin.exe / WeChat.exe）。'
            '请在弹窗中填写微信主程序的完整路径后重试。'
        )
    if '错误代码: 2' in blob or '错误码: 2' in blob or 'error code: 2' in blob.lower():
        return (
            'Hook DLL 已加载，但内置 HTTP 服务（端口 19088）启动失败（错误码 2）。'
            '请依次尝试：① 以管理员身份运行后端；② 关闭占用 19088 端口的程序；'
            '③ 再次点击「查找微信并注入」重试（默认会先关闭微信再冷注入）。'
        )
    if 'Multi WeChat' in blob and returncode != 0:
        return (
            '注入进程异常退出（可能与多开/安全软件冲突）。'
            '请关闭其它微信多开工具后重试，或以管理员运行。'
            f' 详情：{stderr or stdout or returncode}'
        )
    if stderr:
        return stderr.strip()
    if stdout:
        lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
        return lines[-1] if lines else f'注入脚本退出码 {returncode}'
    return f'注入脚本退出码 {returncode}'


def _resolve_wechat_exe_for_inject(wechat_exe_path: str | None = None) -> str | None:
    from pathlib import Path

    from utils.weixin_locate import locate_weixin_exe
    from utils.weixin_process import get_running_weixin_executable

    for cand in (wechat_exe_path,):
        if cand and Path(cand).is_file():
            return str(Path(cand).resolve())
    exe = get_running_weixin_executable()
    if exe:
        return exe
    return locate_weixin_exe()


def is_wechat_not_found_result(result: dict) -> bool:
    if result.get('need_wechat_path'):
        return True
    err = str(result.get('error') or '')
    blob = f'{err}\n{result.get("stdout") or ""}\n{result.get("stderr") or ""}'
    markers = ('未找到 Weixin', '未找到 PC 版微信', 'WeChat.exe', 'WECHAT_EXE_PATH')
    return any(m in blob for m in markers)


def run_wechat_hook_inject(
    *,
    bootstrap_inject: bool | None = None,
    quit_before_inject: bool | None = None,
    wechat_exe_path: str | None = None,
) -> dict:
    if os.name != 'nt':
        return {'ok': False, 'error': '微信注入仅支持在 Windows 上执行'}

    script = PROJECT_ROOT / 'scripts' / 'launch_wechat_hook.py'
    if not script.is_file():
        return {'ok': False, 'error': '未找到 scripts/launch_wechat_hook.py'}

    from services.hook_runtime_service import evaluate_hook_runtime, invalidate_hook_cache, probe_hook_readiness

    existing = evaluate_hook_runtime()
    if existing.get('hook_ready') or (existing.get('hook_control_ok') and existing.get('hook_has_wxid')):
        return {
            'ok': True,
            'log': 'Hook 已就绪，无需重复注入',
            'skipped': True,
            'login_wxid': existing.get('hook_stored_wxid') or existing.get('hook_profile', {}).get('wxid', ''),
        }

    resolved_exe = _resolve_wechat_exe_for_inject(wechat_exe_path)
    if not resolved_exe:
        return {
            'ok': False,
            'need_wechat_path': True,
            'error': (
                '未找到 PC 版微信（Weixin.exe / WeChat.exe）。'
                '请在弹窗中填写微信主程序的完整路径后重试。'
            ),
        }

    inj = build_hook_inject_config()
    env = os.environ.copy()
    env['TONJCLAW_ROOT'] = str(PROJECT_ROOT)
    env['WECHAT_EXE_PATH'] = resolved_exe
    if settings.WECHAT_HK_DIR:
        env['WECHAT_HK_DIR'] = settings.WECHAT_HK_DIR

    if bootstrap_inject is not None:
        env['WECHAT_BOOTSTRAP_INJECT'] = '1' if bootstrap_inject else '0'
    if quit_before_inject is None:
        quit_before_inject = settings.WECHAT_QUIT_BEFORE_INJECT
    env['WECHAT_QUIT_BEFORE_INJECT'] = '1' if quit_before_inject else '0'

    env.setdefault('HOOK_RECEIVE_MODE', inj['recivemode'])
    env.setdefault('HOOK_CALLBACK_URL', inj['http_callback_url'])

    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0,
        )
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': '注入脚本超时'}
    except Exception as exc:
        logger.warning('[wechat-inject] spawn failed: %s', exc)
        return {'ok': False, 'error': str(exc)}

    stdout = (proc.stdout or '').strip()
    stderr = (proc.stderr or '').strip()

    if proc.returncode != 0:
        invalidate_hook_cache()
        readiness = probe_hook_readiness()
        if readiness.get('operational_ok'):
            return {
                'ok': True,
                'log': stdout or '注入过程有告警，但 Hook 已可用',
                'warn': _humanize_inject_failure(stdout, stderr, proc.returncode),
                'login_wxid': readiness.get('wxid', ''),
            }
        fail = {
            'ok': False,
            'error': _humanize_inject_failure(stdout, stderr, proc.returncode),
            'stdout': stdout,
            'stderr': stderr,
            'returncode': proc.returncode,
        }
        if is_wechat_not_found_result(fail):
            fail['need_wechat_path'] = True
        return fail

    invalidate_hook_cache()
    readiness = probe_hook_readiness()

    return {
        'ok': True,
        'log': stdout,
        'stderr': stderr or None,
        'inbound_enabled': settings.BOT_INBOUND_ENABLED,
        'login_wxid': readiness.get('wxid', ''),
    }
