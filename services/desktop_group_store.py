"""
桌面端多群配置与群级授权（对齐 sim-bot-node wx_groups + redeemGroupCardCipher）
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from config.settings import settings
from models.desktop_bot_models import AppSetting, CardHistory
from models.desktop_group_models import WxChatroomCache, WxGroup
from models.models import Customer
from models.user_models import License, User
from services.desktop_robot_store import (
    compute_integrity_hash,
    get_robot_config,
    is_card_used,
    is_robot_license_valid,
    record_card_history,
    verify_integrity,
)
from services.simbot_activation_service import (
    activation_fingerprint,
    assert_payload_redeem_deadline,
    payload_days,
    verify_activation_code,
    wxid_matches_payload,
)
from services import simbot_platform_client
from utils.hook_chatroom import extract_chatroom_id, extract_chatroom_nick

logger = logging.getLogger(__name__)

WECHAT_LOGIN_WXID_KEY = 'wechat_login_wxid'


def _format_expire_display(dt: datetime | None) -> str:
    if not dt:
        return '—'
    return dt.strftime('%Y-%m-%d %H:%M')


def _days_left(expires_at: datetime | None) -> int | None:
    if not expires_at:
        return None
    delta = expires_at - datetime.now()
    return max(0, delta.days)


def set_wechat_login_wxid(db: Session, wxid: str) -> None:
    wx = str(wxid or '').strip()
    if not wx:
        return
    row = db.query(AppSetting).filter(AppSetting.setting_key == WECHAT_LOGIN_WXID_KEY).first()
    if row:
        row.setting_value = wx
    else:
        db.add(AppSetting(setting_key=WECHAT_LOGIN_WXID_KEY, setting_value=wx))
    db.commit()


def get_bot_wxid(db: Session) -> str:
    row = db.query(AppSetting).filter(AppSetting.setting_key == WECHAT_LOGIN_WXID_KEY).first()
    if row and row.setting_value:
        return str(row.setting_value).strip()
    robot = get_robot_config(db)
    return robot.wxid if robot else ''


def upsert_wx_group_bound(
    db: Session,
    *,
    wx_group_id: str,
    name: str | None = None,
    manual_owner: str | None = None,
    expires_at: datetime | None = None,
    customer_id: int | None = None,
) -> dict:
    gid = str(wx_group_id or '').strip()
    if not gid:
        raise ValueError('缺少 wx_group_id')

    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
    if not row:
        row = WxGroup(
            wx_group_id=gid,
            name=name,
            manual_owner=manual_owner,
            expires_at=expires_at,
            customer_id=customer_id,
            is_active=1,
            integrity_hash=compute_integrity_hash(
                expires_at.isoformat() if expires_at else '',
                '',
            ),
        )
        db.add(row)
        created = True
    else:
        if name is not None:
            row.name = name
        if manual_owner is not None:
            row.manual_owner = manual_owner
        if expires_at is not None:
            row.expires_at = expires_at
        if customer_id is not None:
            row.customer_id = customer_id
        row.is_active = 1
        created = False
    db.commit()
    return {'created': created, 'wx_group_id': gid}


def extend_wx_group_expires(db: Session, wx_group_id: str, add_days: int) -> datetime:
    gid = str(wx_group_id or '').strip()
    days = max(1, min(3660, int(add_days or 30)))
    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
    base = datetime.now()
    if row and row.expires_at and row.expires_at > base:
        base = row.expires_at
    new_exp = base + timedelta(days=days)
    if not row:
        upsert_wx_group_bound(db, wx_group_id=gid, expires_at=new_exp)
    else:
        row.expires_at = new_exp
        row.is_active = 1
        row.integrity_hash = compute_integrity_hash(
            new_exp.strftime('%Y-%m-%d %H:%M:%S'),
            row.last_card_cipher or '',
        )
        db.commit()
    return new_exp


def is_group_service_valid(db: Session, wx_group_id: str) -> bool:
    if settings.SKIP_ROBOT_LICENSE_CHECK:
        return True
    gid = str(wx_group_id or '').strip()
    if not gid or not gid.endswith('@chatroom'):
        return True
    if not is_robot_license_valid(db):
        return False
    row = db.query(WxGroup).filter(
        WxGroup.wx_group_id == gid,
        WxGroup.is_active == 1,
    ).first()
    if not row:
        return False
    if row.integrity_hash and not verify_integrity(
        row.expires_at.strftime('%Y-%m-%d %H:%M:%S') if row.expires_at else '',
        row.last_card_cipher or '',
        row.integrity_hash,
    ):
        return False
    if not row.expires_at:
        return True
    return row.expires_at >= datetime.now()


def list_bound_groups(db: Session) -> list[dict]:
    rows = db.query(WxGroup).filter(WxGroup.is_active == 1).order_by(WxGroup.updated_at.desc()).all()
    out = []
    for g in rows:
        out.append({
            'wx_group_id': g.wx_group_id,
            'name': g.name or g.wx_group_id,
            'manual_owner': g.manual_owner or '',
            'expires_at': g.expires_at.isoformat() if g.expires_at else None,
            'expire_display': _format_expire_display(g.expires_at),
            'days_left': _days_left(g.expires_at),
            'is_bound': True,
            'customer_id': g.customer_id,
        })
    return out


def list_group_desk_rows(db: Session, *, sync_hook: bool = False) -> list[dict]:
    if sync_hook:
        try:
            sync_chatrooms_from_hook(db)
        except Exception as exc:
            logger.warning('sync hook chatrooms failed: %s', exc)

    bound = {g['wx_group_id']: g for g in list_bound_groups(db)}
    caches = db.query(WxChatroomCache).order_by(WxChatroomCache.updated_at.desc()).all()
    seen = set()
    out = []

    for c in caches:
        gid = str(c.room_id or '').strip()
        if not gid or '@chatroom' not in gid or gid in seen:
            continue
        seen.add(gid)
        b = bound.get(gid)
        name = (b and b.get('name')) or c.nick_name or c.remark or gid
        out.append({
            'wx_group_id': gid,
            'name': name,
            'is_bound': gid in bound,
            'owner_wxid': (b or {}).get('manual_owner') or c.owner_wxid or '',
            'member_count': c.member_count or 0,
            'expire_display': (b or {}).get('expire_display', '—'),
            'days_left': (b or {}).get('days_left'),
            'expires_at': (b or {}).get('expires_at'),
        })

    for gid, b in bound.items():
        if gid in seen:
            continue
        seen.add(gid)
        out.append({
            'wx_group_id': gid,
            'name': b.get('name') or gid,
            'is_bound': True,
            'owner_wxid': b.get('manual_owner', ''),
            'member_count': 0,
            'expire_display': b.get('expire_display', '—'),
            'days_left': b.get('days_left'),
            'expires_at': b.get('expires_at'),
        })

    out.sort(key=lambda x: (not x['is_bound'], x.get('name') or ''))
    return out


def compute_groups_desk_revision(db: Session) -> str:
    rows = list_group_desk_rows(db, sync_hook=False)
    parts = [
        f"{r['wx_group_id']}|{1 if r['is_bound'] else 0}|{r.get('expire_display','')}|{r.get('days_left','')}"
        for r in rows
    ]
    h = 0
    s = '\n'.join(parts)
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return f'{len(rows)}:{h:x}'


def sync_chatrooms_from_hook(db: Session) -> dict:
    from services.hook_client import hook_client

    rooms = hook_client.get_chatroom_list()
    items = rooms.get('items') or []
    count = 0
    now = datetime.now()
    for item in items:
        if not isinstance(item, dict):
            continue
        gid = extract_chatroom_id(item)
        if not gid:
            continue
        nick = extract_chatroom_nick(item)
        row = db.query(WxChatroomCache).filter(WxChatroomCache.room_id == gid).first()
        if row:
            row.nick_name = nick or row.nick_name
            row.member_count = int(item.get('member_count') or item.get('memberCount') or row.member_count or 0)
            row.updated_at = now
        else:
            db.add(
                WxChatroomCache(
                    room_id=gid,
                    nick_name=nick,
                    member_count=int(item.get('member_count') or item.get('memberCount') or 0),
                    owner_wxid=str(item.get('owner') or item.get('owner_wxid') or ''),
                    updated_at=now,
                )
            )
        count += 1
    db.commit()
    return {'ok': True, 'total': count}


def unbind_group(db: Session, wx_group_id: str) -> dict:
    gid = str(wx_group_id or '').strip()
    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
    if not row:
        return {'error': '群未绑定'}
    row.is_active = 0
    db.commit()
    return {'ok': True}


def _load_public_key_pem() -> str:
    path = settings.ACTIVATION_PUBLIC_KEY_PATH
    if not path or not __import__('os').path.isfile(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _sync_license_v2_for_group(
    db: Session,
    user_id: int,
    wx_group_id: str,
    expires_at: datetime,
    license_code_hint: str = '',
) -> None:
    """群核销成功后同步写入 license_v2（bound_to=群ID）"""
    lic = (
        db.query(License)
        .filter(License.bound_to == wx_group_id, License.user_id == user_id)
        .order_by(License.id.desc())
        .first()
    )
    if lic:
        lic.is_active = True
        lic.is_revoked = False
        lic.expires_at = expires_at
        lic.activated_at = lic.activated_at or datetime.now()
        if license_code_hint:
            lic.license_code = license_code_hint[:64]
    else:
        from services.license_service_v2 import LicenseServiceV2

        code = LicenseServiceV2.generate_license_code()
        lic = License(
            user_id=user_id,
            license_code=code,
            license_type='yearly' if (expires_at - datetime.now()).days > 180 else 'monthly',
            bound_to=wx_group_id,
            is_active=True,
            activated_at=datetime.now(),
            expires_at=expires_at,
        )
        db.add(lic)
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.available_groups > 0:
            user.available_groups -= 1
    db.commit()


def redeem_group_card_cipher(
    db: Session,
    *,
    wx_group_id: str,
    code: str,
    user_id: int | None = None,
    bearer_token: str | None = None,
) -> dict:
    gid = str(wx_group_id or '').strip()
    cipher = str(code or '').strip()
    if not gid or not cipher:
        return {'error': '缺少群 ID 或卡密'}
    if not is_robot_license_valid(db):
        return {'error': '机器人主授权已过期，请先完成主程序续费'}

    if simbot_platform_client.platform_available():
        base = settings.SIMBOT_PLATFORM_URL.rstrip('/')
        for path in (
            f'/api/admin/prd/groups/{gid}/bind',
            f'/api/admin/prd/groups/{gid}/redeem',
        ):
            try:
                import requests

                resp = requests.post(
                    f'{base}{path}',
                    json={'code': cipher, 'last_card_cipher': cipher},
                    headers=simbot_platform_client._headers(bearer_token),
                    timeout=30,
                )
                data = resp.json() if resp.content else {}
                if resp.status_code < 400 and not data.get('error'):
                    exp_raw = data.get('expires_at') or data.get('expire_at')
                    days = int(data.get('days') or 30)
                    if exp_raw:
                        try:
                            exp_dt = datetime.fromisoformat(str(exp_raw).replace('Z', '+00:00')[:19])
                        except ValueError:
                            exp_dt = extend_wx_group_expires(db, gid, days)
                    else:
                        exp_dt = extend_wx_group_expires(db, gid, days)
                    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
                    cipher_store = cipher
                    if row:
                        row.expires_at = exp_dt
                        row.last_card_cipher = cipher_store
                        row.integrity_hash = compute_integrity_hash(
                            exp_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            cipher_store,
                        )
                        row.is_active = 1
                    else:
                        upsert_wx_group_bound(db, wx_group_id=gid, expires_at=exp_dt)
                        row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
                        if row:
                            row.last_card_cipher = cipher_store
                            row.integrity_hash = compute_integrity_hash(
                                exp_dt.strftime('%Y-%m-%d %H:%M:%S'),
                                cipher_store,
                            )
                            db.commit()
                    record_card_history(db, activation_fingerprint(cipher), gid)
                    if user_id:
                        _sync_license_v2_for_group(db, user_id, gid, exp_dt)
                    return {
                        'ok': True,
                        'wx_group_id': gid,
                        'expires_at': exp_dt.isoformat(),
                        'expire_display': _format_expire_display(exp_dt),
                        'days': days,
                        'via': 'simbot_platform',
                        'notify_text': data.get('notify_text'),
                    }
                if data.get('error'):
                    return {'error': data['error']}
            except Exception as exc:
                logger.warning('platform group redeem %s: %s', path, exc)

    bot_wxid = get_bot_wxid(db)
    if not bot_wxid:
        return {'error': '请先登录微信后再核销群卡'}

    verified = verify_activation_code(
        public_key_pem=_load_public_key_pem(),
        card_secret=settings.ACTIVATION_CARD_SECRET,
        wxid=bot_wxid,
        code=cipher,
    )
    if not verified.get('ok'):
        return {'error': f"卡密无效（{verified.get('reason', 'verify_failed')}）"}
    payload = verified.get('payload') or {}
    if payload.get('installation') is True:
        return {'error': '此为产品安装类授权码，请使用群续期卡密'}
    deadline = assert_payload_redeem_deadline(payload)
    if not deadline.get('ok'):
        return {'error': '该卡密已超过兑换截止时间'}
    fp = activation_fingerprint(cipher)
    if is_card_used(db, fp):
        return {'error': '该卡密已使用，不能重复核销'}
    if not wxid_matches_payload(payload, bot_wxid):
        return {'error': '卡密绑定的机器人 wxid 与当前主授权不一致'}

    days = payload_days(payload)
    if payload.get('installation'):
        days = int(payload.get('group_validity_days') or payload.get('days') or 365)

    record_card_history(db, fp, gid)
    cache = db.query(WxChatroomCache).filter(WxChatroomCache.room_id == gid).first()
    name = cache.nick_name if cache else None
    upsert_wx_group_bound(db, wx_group_id=gid, name=name)
    exp_dt = extend_wx_group_expires(db, gid, days)
    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
    if row:
        row.last_card_cipher = cipher
        row.integrity_hash = compute_integrity_hash(
            exp_dt.strftime('%Y-%m-%d %H:%M:%S'),
            cipher,
        )
        db.commit()

    cust = db.query(Customer).filter(Customer.wx_group_id == gid).first()
    if cust and row and not row.customer_id:
        row.customer_id = cust.id
        db.commit()

    if user_id:
        _sync_license_v2_for_group(db, user_id, gid, exp_dt)

    notify = (
        f'[系统通知] 本群已成功使用卡密续费，有效期延长 {days} 天，'
        f'新截止日期为：{_format_expire_display(exp_dt)}。'
    )
    return {
        'ok': True,
        'wx_group_id': gid,
        'days': days,
        'expires_at': exp_dt.isoformat(),
        'expire_display': _format_expire_display(exp_dt),
        'notify_text': notify,
        'via': 'local_verify',
    }


def link_customer_to_group(db: Session, wx_group_id: str, customer_id: int) -> dict:
    gid = str(wx_group_id or '').strip()
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        return {'error': '客户不存在'}
    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
    if row:
        row.customer_id = customer_id
    else:
        upsert_wx_group_bound(
            db,
            wx_group_id=gid,
            name=cust.customer_name,
            customer_id=customer_id,
        )
    if not cust.wx_group_id:
        cust.wx_group_id = gid
    db.commit()
    return {'ok': True}
