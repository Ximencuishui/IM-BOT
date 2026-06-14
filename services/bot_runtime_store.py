"""机器人入站开关与工作日志（对齐 sim-bot-node runtime_store）"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.desktop_bot_models import AppSetting, BotWorkLog

BOT_INBOUND_KEY = 'bot_inbound_enabled'
BOT_RUNTIME_STARTED_KEY = 'bot_runtime_started_at'
BOT_INBOUND_USER_PAUSED_KEY = 'bot_inbound_user_paused'
MAX_WORK_LOGS = 800


def _get_setting(db: Session, key: str) -> Optional[str]:
    row = db.query(AppSetting).filter(AppSetting.setting_key == key).first()
    return row.setting_value if row else None


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.setting_key == key).first()
    if row:
        row.setting_value = value
        row.updated_at = datetime.now()
    else:
        db.add(AppSetting(setting_key=key, setting_value=value))
    db.commit()


def get_bot_inbound_enabled(db: Session) -> bool:
    val = _get_setting(db, BOT_INBOUND_KEY)
    if val is None:
        return True
    v = str(val).lower()
    return v not in ('0', 'false', 'off')


def set_bot_inbound_enabled(db: Session, enabled: bool) -> None:
    _set_setting(db, BOT_INBOUND_KEY, '1' if enabled else '0')


def is_bot_inbound_user_paused(db: Session) -> bool:
    return _get_setting(db, BOT_INBOUND_USER_PAUSED_KEY) == '1'


def set_bot_inbound_user_paused(db: Session, paused: bool) -> None:
    _set_setting(db, BOT_INBOUND_USER_PAUSED_KEY, '1' if paused else '0')


def sync_bot_runtime_started_at(db: Session, enabled: bool) -> None:
    if enabled:
        _set_setting(db, BOT_RUNTIME_STARTED_KEY, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    else:
        row = db.query(AppSetting).filter(AppSetting.setting_key == BOT_RUNTIME_STARTED_KEY).first()
        if row:
            db.delete(row)
            db.commit()


def get_bot_runtime_started_at(db: Session) -> Optional[str]:
    val = _get_setting(db, BOT_RUNTIME_STARTED_KEY)
    return str(val).strip() if val else None


def append_bot_work_log(
    db: Session,
    level: str,
    message: str,
    detail_json: str | None = None,
) -> None:
    db.add(
        BotWorkLog(
            level=str(level or 'info'),
            message=str(message or '')[:2000],
            detail_json=detail_json,
        )
    )
    db.commit()
    _prune_work_logs(db)


def _prune_work_logs(db: Session) -> None:
    count = db.query(BotWorkLog).count()
    if count <= MAX_WORK_LOGS:
        return
    excess = count - MAX_WORK_LOGS
    ids = (
        db.query(BotWorkLog.id)
        .order_by(BotWorkLog.id.asc())
        .limit(excess)
        .all()
    )
    for (log_id,) in ids:
        db.query(BotWorkLog).filter(BotWorkLog.id == log_id).delete()
    db.commit()


def list_bot_work_logs(db: Session, limit: int = 80) -> list[dict]:
    limit = max(1, min(200, int(limit)))
    rows = (
        db.query(BotWorkLog)
        .order_by(BotWorkLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            'id': r.id,
            'level': r.level,
            'message': r.message,
            'detail_json': r.detail_json,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
