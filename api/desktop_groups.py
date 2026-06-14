"""
桌面端多群配置 API（对齐 sim-bot-node 群管理 + SimBot 平台群级授权）
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.desktop_group_store import (
    compute_groups_desk_revision,
    get_bot_wxid,
    link_customer_to_group,
    list_bound_groups,
    list_group_desk_rows,
    redeem_group_card_cipher,
    set_wechat_login_wxid,
    sync_chatrooms_from_hook,
    unbind_group,
    upsert_wx_group_bound,
)
from services.desktop_robot_store import is_robot_license_valid
from services.hook_client import hook_client

desktop_groups_bp = Blueprint('desktop_groups', __name__, url_prefix='/api/desktop/groups')


def _token():
    auth = request.headers.get('Authorization', '')
    return auth[7:].strip() if auth.startswith('Bearer ') else None


@desktop_groups_bp.route('', methods=['GET'])
@login_required
def list_groups():
    db = get_db_session()
    try:
        sync = str(request.args.get('sync', '0')) == '1'
        rows = list_group_desk_rows(db, sync_hook=sync)
        wxid = get_bot_wxid(db)
        if wxid:
            set_wechat_login_wxid(db, wxid)
        return jsonify({
            'groups': rows,
            'groups_desk_revision': compute_groups_desk_revision(db),
        }), 200
    finally:
        db.close()


@desktop_groups_bp.route('/bound', methods=['GET'])
@login_required
def list_bound():
    db = get_db_session()
    try:
        return jsonify({'groups': list_bound_groups(db)}), 200
    finally:
        db.close()


@desktop_groups_bp.route('/hook/chatrooms', methods=['GET'])
@login_required
def hook_chatrooms():
    db = get_db_session()
    try:
        sync_result = sync_chatrooms_from_hook(db)
        rooms = hook_client.get_chatroom_list()
        return jsonify({
            **rooms,
            'cached': sync_result.get('total', 0),
            'synced': sync_result.get('total', 0),
        }), 200
    finally:
        db.close()


@desktop_groups_bp.route('/bind', methods=['POST'])
@login_required
def bind_group():
    db = get_db_session()
    try:
        data = request.get_json() or {}
        gid = data.get('wx_group_id') or data.get('room_id')
        if not gid:
            return jsonify({'error': '缺少 wx_group_id'}), 400
        if not is_robot_license_valid(db):
            return jsonify({'error': '机器人主授权无效'}), 403
        from services.demo_boss_license import (
            assert_demo_can_bind_group,
            ensure_demo_boss_group_license,
            is_demo_boss_user,
        )

        user = get_current_user_from_request(db)
        if is_demo_boss_user(user):
            blocked = assert_demo_can_bind_group(db, gid)
            if blocked:
                return jsonify(blocked), 403
        result = upsert_wx_group_bound(
            db,
            wx_group_id=gid,
            name=data.get('name'),
            manual_owner=data.get('manual_owner'),
        )
        if is_demo_boss_user(user):
            ensure_demo_boss_group_license(db, gid)
        return jsonify({'ok': True, **result}), 200
    finally:
        db.close()


@desktop_groups_bp.route('/redeem', methods=['POST'])
@login_required
def redeem_group():
    """群级卡密核销（SimBot 管理平台 / 本地验签，替代原 license_v2 桌面激活）"""
    db = get_db_session()
    try:
        user = get_current_user_from_request(db)
        data = request.get_json() or {}
        wx_group_id = data.get('wx_group_id') or data.get('room_id')
        code = data.get('code') or data.get('last_card_cipher') or data.get('license_code') or ''
        if not wx_group_id:
            return jsonify({'success': False, 'error': '缺少 wx_group_id'}), 400
        result = redeem_group_card_cipher(
            db,
            wx_group_id=wx_group_id,
            code=code,
            user_id=user.id,
            bearer_token=_token(),
        )
        if result.get('error'):
            return jsonify({'success': False, 'error': result['error']}), 400

        from services.bot_runtime_store import append_bot_work_log

        append_bot_work_log(
            db,
            'info',
            f"群 {wx_group_id} 卡密续期至 {result.get('expire_display', '')}",
            None,
        )
        notify = result.get('notify_text')
        hook_sent = False
        if notify:
            hook_sent = hook_client.send_text(wx_group_id, notify)

        return jsonify({
            'success': True,
            'ok': True,
            'hook_notify_sent': hook_sent,
            **result,
        }), 200
    finally:
        db.close()


@desktop_groups_bp.route('/unbind', methods=['POST'])
@login_required
def unbind():
    db = get_db_session()
    try:
        data = request.get_json() or {}
        gid = data.get('wx_group_id')
        if not gid:
            return jsonify({'error': '缺少 wx_group_id'}), 400
        result = unbind_group(db, gid)
        if result.get('error'):
            return jsonify(result), 404
        return jsonify(result), 200
    finally:
        db.close()


@desktop_groups_bp.route('/link-customer', methods=['POST'])
@login_required
def group_link_customer():
    db = get_db_session()
    try:
        data = request.get_json() or {}
        gid = data.get('wx_group_id')
        cid = data.get('customer_id')
        if not gid or not cid:
            return jsonify({'error': '缺少 wx_group_id 或 customer_id'}), 400
        result = link_customer_to_group(db, gid, int(cid))
        if result.get('error'):
            return jsonify(result), 400
        return jsonify(result), 200
    finally:
        db.close()


@desktop_groups_bp.route('/batch-redeem', methods=['POST'])
@login_required
def batch_redeem():
    db = get_db_session()
    try:
        user = get_current_user_from_request(db)
        data = request.get_json() or {}
        ids = data.get('wx_group_ids') or []
        codes = data.get('codes') or []
        if len(ids) != len(codes):
            return jsonify({'error': '群数量与激活码行数须一致'}), 400
        results = []
        for gid, code in zip(ids, codes):
            r = redeem_group_card_cipher(
                db,
                wx_group_id=gid,
                code=str(code).strip(),
                user_id=user.id,
                bearer_token=_token(),
            )
            results.append({'wx_group_id': gid, **r})
        failed = [x for x in results if x.get('error')]
        if failed and len(failed) == len(results):
            return jsonify({'success': False, 'results': results}), 400
        return jsonify({'success': True, 'results': results}), 200
    finally:
        db.close()
