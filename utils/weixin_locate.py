"""定位 PC 微信 Weixin.exe / WeChat.exe（对齐 sim-bot-node weixin-locate.mjs）"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

TARGET_NAMES = ('weixin.exe', 'wechat.exe')


def _expand_env_path(s: str) -> str:
    if not s:
        return s

    def repl(m: re.Match) -> str:
        return os.environ.get(m.group(1), m.group(0))

    return re.sub(r'%([^%]+)%', repl, s)


def _normalize_install_to_exe(p: str | None) -> str | None:
    if not p:
        return None
    s = _expand_env_path(str(p).strip().strip('"\''))
    if not s:
        return None
    path = Path(s)
    if path.is_file() and path.name.lower() in TARGET_NAMES:
        return str(path.resolve())
    if path.is_dir():
        for rel in ('Weixin.exe', 'Weixin/Weixin.exe', 'WeChat.exe', 'WeChat/WeChat.exe'):
            c = path / rel.replace('/', os.sep)
            if c.is_file():
                return str(c.resolve())
    return None


def _parse_reg_value(output: str) -> str | None:
    for line in (output or '').splitlines():
        m = re.search(r'\bREG_(?:EXPAND_)?SZ\s+(.+)$', line, re.I)
        if m:
            return m.group(1).strip()
    return None


def _try_registry() -> str | None:
    if os.name != 'nt':
        return None
    queries = [
        (r'HKCU\Software\Tencent\Weixin', 'InstallPath'),
        (r'HKCU\Software\Tencent\Weixin', 'InstallLocation'),
        (r'HKCU\Software\Tencent\WeChat', 'InstallPath'),
        (r'HKLM\SOFTWARE\WOW6432Node\Tencent\Weixin', 'InstallPath'),
        (r'HKLM\SOFTWARE\Tencent\Weixin', 'InstallPath'),
        (r'HKLM\SOFTWARE\WOW6432Node\Tencent\WeChat', 'InstallPath'),
        (r'HKLM\SOFTWARE\Tencent\WeChat', 'InstallPath'),
    ]
    for key_path, value_name in queries:
        try:
            out = subprocess.check_output(
                ['reg', 'query', key_path, '/v', value_name],
                encoding='utf-8',
                errors='ignore',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            hit = _normalize_install_to_exe(_parse_reg_value(out))
            if hit:
                return hit
        except Exception:
            continue
    return None


def _try_common_paths() -> str | None:
    roots = [
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
    ]
    for root in roots:
        tencent = Path(root) / 'Tencent'
        if not tencent.is_dir():
            continue
        try:
            for ent in tencent.iterdir():
                if not ent.is_dir():
                    continue
                for rel in (
                    'Weixin/Weixin.exe',
                    'Weixin.exe',
                    'WeChat/WeChat.exe',
                    'WeChat.exe',
                ):
                    c = ent / rel.replace('/', os.sep)
                    if c.is_file():
                        return str(c.resolve())
        except OSError:
            continue

    local = os.environ.get('LOCALAPPDATA', '')
    if local:
        wx_root = Path(local) / 'Tencent' / 'Weixin'
        if wx_root.is_dir():
            try:
                for d in wx_root.iterdir():
                    if d.is_dir():
                        c = d / 'Weixin.exe'
                        if c.is_file():
                            return str(c.resolve())
            except OSError:
                pass
    return None


def locate_weixin_exe(*, allow_env: bool = True) -> str | None:
    """返回微信主程序绝对路径。"""
    if os.name != 'nt':
        return None

    if allow_env:
        override = os.environ.get('WECHAT_EXE_PATH', '').strip()
        if override:
            p = Path(override)
            if p.is_file():
                return str(p.resolve())

    hit = _try_registry()
    if hit:
        return hit
    return _try_common_paths()
