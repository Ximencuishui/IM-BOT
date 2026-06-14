"""BOSS 演示账号：免卡密自动开通短期授权（桌面端本地试用）"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.user_models import User
from services.desktop_robot_store import (
    add_days_to_ymd,
    format_expire_display,
    get_robot_config,
    today_ymd,
    upsert_robot_config,
)

DEMO_BOSS_EMAIL = 'boss@demo.local'
DEMO_BOSS_USERNAME = 'BOSS'
DEMO_LICENSE_MARKER = '__demo_boss_auto__'
DEMO_GROUP_MARKER = '__demo_boss_group__'
DEMO_LICENSE_DAYS = 1
DEMO_MAX_GROUPS = 3
DEMO_WXID_FALLBACK = '__tonjclaw_demo_boss__'


def is_demo_boss_user(user: User | None) -> bool:
    if not user:
        return False
    email = str(user.email or '').strip().lower()
    username = str(user.username or '').strip().upper()
    return email == DEMO_BOSS_EMAIL or username == DEMO_BOSS_USERNAME


def _resolve_robot_wxid(db: Session, hook_wxid: str = '') -> str:
    hook = str(hook_wxid or '').strip()
    if hook:
        return hook
    row = get_robot_config(db)
    if row and row.last_card_cipher == DEMO_LICENSE_MARKER and row.wxid:
        return str(row.wxid).strip()
    return DEMO_WXID_FALLBACK


def count_active_bound_groups(db: Session) -> int:
    from models.desktop_group_models import WxGroup

    return (
        db.query(WxGroup)
        .filter(WxGroup.is_active == 1)
        .count()
    )


def demo_trial_status(db: Session) -> dict:
    bound = count_active_bound_groups(db)
    row = get_robot_config(db)
    expire_display = format_expire_display(row.expire_date) if row else '—'
    return {
        'days': DEMO_LICENSE_DAYS,
        'max_groups': DEMO_MAX_GROUPS,
        'bound_groups': bound,
        'remaining_groups': max(0, DEMO_MAX_GROUPS - bound),
        'expire_display': expire_display,
        'demo_auto_license': bool(row and row.last_card_cipher == DEMO_LICENSE_MARKER),
    }


def assert_demo_can_bind_group(db: Session, wx_group_id: str) -> dict | None:
    """演示账号最多绑定 DEMO_MAX_GROUPS 个群；已绑定的群允许重复操作。"""
    gid = str(wx_group_id or '').strip()
    if not gid:
        return {'error': '缺少 wx_group_id'}
    from models.desktop_group_models import WxGroup

    row = db.query(WxGroup).filter(
        WxGroup.wx_group_id == gid,
        WxGroup.is_active == 1,
    ).first()
    if row:
        return None
    if count_active_bound_groups(db) >= DEMO_MAX_GROUPS:
        return {
            'error': (
                f'免费测试期最多绑定 {DEMO_MAX_GROUPS} 个群，'
                f'请先解绑其他群或联系开通正式授权'
            ),
        }
    return None


def ensure_demo_boss_robot_license(db: Session, *, hook_wxid: str = '') -> dict:
    """
    从今天起可用 DEMO_LICENSE_DAYS 天（含当日），无需卡密。
    若 Hook 已返回 wxid，则绑定到真实 wxid。
    """
    wxid = _resolve_robot_wxid(db, hook_wxid)
    expire_date = add_days_to_ymd(today_ymd(), DEMO_LICENSE_DAYS)
    upsert_robot_config(
        db,
        wxid=wxid,
        expire_date=expire_date,
        last_card_cipher=DEMO_LICENSE_MARKER,
    )
    trial = demo_trial_status(db)
    return {
        'wxid': wxid,
        'expire_date': expire_date,
        'expire_display': format_expire_display(expire_date),
        'days': DEMO_LICENSE_DAYS,
        'max_groups': DEMO_MAX_GROUPS,
        'bound_groups': trial['bound_groups'],
        'remaining_groups': trial['remaining_groups'],
        'demo_auto_license': True,
    }


def is_demo_robot_license_row(db: Session) -> bool:
    row = get_robot_config(db)
    return bool(row and row.last_card_cipher == DEMO_LICENSE_MARKER)


def ensure_demo_boss_group_license(db: Session, wx_group_id: str) -> None:
    """演示账号绑定群后自动获得 1 天群服务期，无需群卡密。"""
    from models.desktop_group_models import WxGroup
    from services.desktop_group_store import compute_integrity_hash, upsert_wx_group_bound

    gid = str(wx_group_id or '').strip()
    if not gid:
        return
    exp_dt = datetime.now() + timedelta(days=DEMO_LICENSE_DAYS)
    upsert_wx_group_bound(db, wx_group_id=gid, expires_at=exp_dt)
    row = db.query(WxGroup).filter(WxGroup.wx_group_id == gid).first()
    if row:
        row.last_card_cipher = DEMO_GROUP_MARKER
        row.integrity_hash = compute_integrity_hash(
            exp_dt.strftime('%Y-%m-%d %H:%M:%S'),
            DEMO_GROUP_MARKER,
        )
        db.commit()
