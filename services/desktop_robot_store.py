"""桌面端机器人主程序授权（对齐 sim-bot-node prd_store）"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from config.settings import settings
from models.desktop_bot_models import CardHistory, DesktopRobotConfig
from services.simbot_activation_service import (
    activation_fingerprint,
    assert_payload_redeem_deadline,
    payload_days,
    verify_activation_code,
    wxid_matches_payload,
)
from services import simbot_platform_client


def _machine_secret() -> bytes:
    seed = '|'.join([
        os.environ.get('COMPUTERNAME', ''),
        os.environ.get('USERNAME', os.environ.get('USER', '')),
        settings.SECRET_KEY,
        settings.SIMBOT_MACHINE_KEY,
    ])
    return hashlib.sha256(seed.encode('utf-8')).digest()


def compute_integrity_hash(expire_date: str, cipher: str) -> str:
    payload = f'{expire_date or ""}{cipher or ""}'
    return hmac.new(_machine_secret(), payload.encode('utf-8'), hashlib.sha256).hexdigest()


def verify_integrity(expire_date: str, cipher: str, saved_hash: str) -> bool:
    if not saved_hash:
        return False
    return compute_integrity_hash(expire_date, cipher) == str(saved_hash)


def today_ymd() -> str:
    d = datetime.now()
    return f'{d.year}{d.month:02d}{d.day:02d}'


def format_expire_display(exp: str) -> str:
    s = str(exp or '').strip()
    if len(s) != 8 or not s.isdigit():
        return '—'
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}'


def add_days_to_ymd(ymd: str, days: int) -> str:
    y, m, d = int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8])
    from datetime import timedelta
    t = datetime(y, m, d) + timedelta(days=days)
    return f'{t.year}{t.month:02d}{t.day:02d}'


def get_robot_config(db: Session) -> Optional[DesktopRobotConfig]:
    return db.query(DesktopRobotConfig).first()


def upsert_robot_config(
    db: Session,
    *,
    wxid: str,
    expire_date: str,
    last_card_cipher: str = '',
) -> DesktopRobotConfig:
    wx = str(wxid or '').strip()
    exp = str(expire_date or '').strip()
    cipher = str(last_card_cipher or '')
    if not wx or not exp:
        raise ValueError('wxid / expire_date 必填')
    integrity = compute_integrity_hash(exp, cipher)
    row = db.query(DesktopRobotConfig).filter(DesktopRobotConfig.wxid == wx).first()
    if row:
        row.expire_date = exp
        row.last_card_cipher = cipher
        row.integrity_hash = integrity
    else:
        row = DesktopRobotConfig(
            wxid=wx,
            expire_date=exp,
            last_card_cipher=cipher,
            integrity_hash=integrity,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def verify_robot_config_row(row: DesktopRobotConfig | None) -> bool:
    if not row:
        return False
    return verify_integrity(row.expire_date, row.last_card_cipher or '', row.integrity_hash)


def is_card_used(db: Session, card_no: str) -> bool:
    return (
        db.query(CardHistory)
        .filter(CardHistory.card_no == str(card_no or '').strip())
        .first()
        is not None
    )


def record_card_history(db: Session, card_no: str, target_id: str) -> None:
    fp = str(card_no or '').strip()
    tid = str(target_id or '').strip()
    if not fp or not tid:
        return
    if is_card_used(db, fp):
        return
    db.add(CardHistory(card_no=fp, target_id=tid))
    db.commit()


def is_robot_license_valid(db: Session) -> bool:
    if settings.SKIP_ROBOT_LICENSE_CHECK:
        return True
    row = get_robot_config(db)
    if not row:
        return False
    if not verify_robot_config_row(row):
        return False
    exp = str(row.expire_date or '').strip()
    if len(exp) != 8:
        return False
    return exp >= today_ymd()


def seed_robot_license_days(
    db: Session,
    *,
    wxid: str,
    days: int,
    last_card_cipher: str = '',
) -> dict:
    wx = str(wxid or '').strip()
    n_days = max(1, min(3660, int(days or 365)))
    cur = get_robot_config(db)
    base = today_ymd()
    if cur and cur.expire_date and len(cur.expire_date) == 8 and cur.expire_date >= base:
        base = cur.expire_date
    expire_date = add_days_to_ymd(base, n_days)
    upsert_robot_config(db, wxid=wx, expire_date=expire_date, last_card_cipher=last_card_cipher)
    return {
        'wxid': wx,
        'expire_date': expire_date,
        'expire_display': format_expire_display(expire_date),
    }


def _load_public_key_pem() -> str:
    path = settings.ACTIVATION_PUBLIC_KEY_PATH
    if not path or not os.path.isfile(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def redeem_robot_card_cipher(
    db: Session,
    *,
    wxid: str,
    code: str,
    bearer_token: str | None = None,
) -> dict:
    target_wxid = str(wxid or '').strip()
    cipher = str(code or '').strip()
    if not target_wxid:
        return {'error': '缺少机器 wxid，请先完成微信登录'}
    if not cipher:
        return {'error': '请粘贴卡密密文'}

    if simbot_platform_client.platform_available():
        plat = simbot_platform_client.redeem_robot_on_platform(
            target_wxid, cipher, bearer_token
        )
        if plat and not plat.get('error'):
            exp = str(plat.get('expire_date') or '').strip()
            if exp:
                upsert_robot_config(
                    db,
                    wxid=target_wxid,
                    expire_date=exp,
                    last_card_cipher=cipher,
                )
                record_card_history(db, activation_fingerprint(cipher), target_wxid)
                return {
                    'ok': True,
                    'wxid': target_wxid,
                    'expire_date': exp,
                    'expire_display': plat.get('expire_display') or format_expire_display(exp),
                    'via': 'simbot_platform',
                }
            days = int(plat.get('days') or 365)
            seeded = seed_robot_license_days(
                db, wxid=target_wxid, days=days, last_card_cipher=cipher
            )
            record_card_history(db, activation_fingerprint(cipher), target_wxid)
            return {'ok': True, **seeded, 'days': days, 'via': 'simbot_platform'}
        if plat and plat.get('error'):
            return {'error': plat['error']}

    pem = _load_public_key_pem()
    secret = settings.ACTIVATION_CARD_SECRET
    if not pem and not secret:
        return {
            'error': '未配置 SimBot 管理平台地址或本地验签公钥/卡密密钥（SIMBOT_PLATFORM_URL / ACTIVATION_PUBLIC_KEY）',
        }

    verified = verify_activation_code(
        public_key_pem=pem,
        card_secret=secret,
        wxid=target_wxid,
        code=cipher,
    )
    if not verified.get('ok'):
        return {'error': f"卡密无效（{verified.get('reason', 'verify_failed')}）"}

    payload = verified.get('payload') or {}
    deadline = assert_payload_redeem_deadline(payload)
    if not deadline.get('ok'):
        return {'error': '该卡密已超过兑换截止时间'}

    fp = activation_fingerprint(cipher)
    if is_card_used(db, fp):
        return {'error': '该卡密已使用，不能重复核销'}

    if not wxid_matches_payload(payload, target_wxid):
        return {'error': '卡密绑定的 wxid 与当前机器不一致'}

    days = payload_days(payload)
    record_card_history(db, fp, target_wxid)
    seeded = seed_robot_license_days(
        db, wxid=target_wxid, days=days, last_card_cipher=cipher
    )
    return {'ok': True, **seeded, 'days': days, 'via': 'local_verify'}


def get_license_status(db: Session, hook_wxid: str = '') -> dict:
    row = get_robot_config(db)
    wxid = str(hook_wxid or '').strip() or (row.wxid if row else '')
    try:
        from services.demo_boss_license import DEMO_LICENSE_MARKER
        demo_marker = DEMO_LICENSE_MARKER
    except ImportError:
        demo_marker = '__demo_boss_auto__'
    demo_auto = bool(row and row.last_card_cipher == demo_marker)
    status = {
        'robot_configured': bool(row),
        'robot_valid': is_robot_license_valid(db),
        'integrity_ok': verify_robot_config_row(row) or demo_auto,
        'expire_date': row.expire_date if row else None,
        'expire_display': format_expire_display(row.expire_date) if row else '—',
        'wxid': wxid,
        'robot_wxid': row.wxid if row else '',
        'platform_configured': simbot_platform_client.platform_available(),
        'demo_auto_license': demo_auto,
    }
    if demo_auto:
        from services.demo_boss_license import demo_trial_status
        status.update(demo_trial_status(db))
    return status
