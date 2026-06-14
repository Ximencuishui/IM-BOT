"""桌面端：用户配置的微信安装路径（持久化到 t_app_settings）"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from services.bot_runtime_store import _get_setting, _set_setting

WECHAT_EXE_PATH_KEY = 'wechat_exe_path'


def get_saved_wechat_exe_path(db: Session) -> str:
    return str(_get_setting(db, WECHAT_EXE_PATH_KEY) or '').strip()


def set_saved_wechat_exe_path(db: Session, path: str) -> None:
    p = str(path or '').strip()
    if not p:
        raise ValueError('路径不能为空')
    if not Path(p).is_file():
        raise ValueError('文件不存在，请选择 Weixin.exe 或 WeChat.exe')
    name = Path(p).name.lower()
    if name not in ('weixin.exe', 'wechat.exe'):
        raise ValueError('请选择微信主程序 Weixin.exe 或 WeChat.exe')
    _set_setting(db, WECHAT_EXE_PATH_KEY, str(Path(p).resolve()))


def validate_wechat_exe_path(path: str) -> dict:
    p = str(path or '').strip().strip('"')
    if not p:
        return {'valid': False, 'error': '请输入微信安装路径'}
    file = Path(p)
    if not file.is_file():
        return {'valid': False, 'error': '文件不存在，请检查路径是否正确'}
    if file.name.lower() not in ('weixin.exe', 'wechat.exe'):
        return {'valid': False, 'error': '请选择 Weixin.exe 或 WeChat.exe'}
    return {'valid': True, 'path': str(file.resolve())}
