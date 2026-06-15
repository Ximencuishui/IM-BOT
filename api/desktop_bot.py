"""
桌面端机器人与系统运维 API（对齐 sim-bot-node，仅 APP_MODE desktop/all）
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from flask import Blueprint, jsonify, request

from config.settings import settings
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from services.bot_runtime_store import (
    append_bot_work_log,
    get_bot_inbound_enabled,
    get_bot_runtime_started_at,
    list_bot_work_logs,
    set_bot_inbound_enabled,
    set_bot_inbound_user_paused,
    sync_bot_runtime_started_at,
)
from services.desktop_robot_store import (
    get_license_status,
    get_robot_config,
    is_robot_license_valid,
    redeem_robot_card_cipher,
    verify_robot_config_row,
)
from services.hook_runtime_service import collect_tray_heartbeat, probe_hook_readiness
from services.wechat_inject_service import run_wechat_hook_inject

desktop_bot_bp = Blueprint('desktop_bot', __name__, url_prefix='/api/desktop')


def _auth_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return None


def _ensure_demo_boss_license_for_user(db, user) -> str:
    """演示账号自动续 1 天主程序授权；返回用于授权的 wxid。"""
    from services.desktop_group_store import get_bot_wxid
    from services.demo_boss_license import (
        ensure_demo_boss_robot_license,
        is_demo_boss_user,
    )

    wxid = get_bot_wxid(db)
    if is_demo_boss_user(user):
        ensure_demo_boss_robot_license(db, hook_wxid=wxid)
        wxid = get_bot_wxid(db) or wxid
    return wxid


@desktop_bot_bp.route('/bot/status', methods=['GET'])
@login_required
def bot_status():
    db = get_db_session()
    try:
        user = get_current_user_from_request(db)
        wxid = _ensure_demo_boss_license_for_user(db, user)
        inbound = get_bot_inbound_enabled(db)
        started = get_bot_runtime_started_at(db) if inbound else None
        lic = get_license_status(db, wxid)
        from services.hook_runtime_service import evaluate_hook_runtime, get_inbound_recv_stats

        tray = {**evaluate_hook_runtime(), **get_inbound_recv_stats()}
        return jsonify({
            'inbound_enabled': inbound,
            'started_at': started,
            **lic,
            **tray,
        }), 200
    finally:
        db.close()


@desktop_bot_bp.route('/bot/inbound', methods=['POST'])
@login_required
def bot_inbound():
    db = get_db_session()
    try:
        user = get_current_user_from_request(db)
        _ensure_demo_boss_license_for_user(db, user)
        data = request.get_json() or {}
        enabled = bool(data.get('enabled'))
        if enabled and not is_robot_license_valid(db):
            return jsonify({
                'error': '机器人主授权已过期，请先在「主程序续费」完成 SimBot 管理平台卡密激活',
            }), 403

        was = get_bot_inbound_enabled(db)
        set_bot_inbound_enabled(db, enabled)
        set_bot_inbound_user_paused(db, not enabled)
        if enabled and not was:
            sync_bot_runtime_started_at(db, True)
            append_bot_work_log(db, 'info', '机器人入站处理已启动', None)
        elif not enabled and was:
            sync_bot_runtime_started_at(db, False)
            append_bot_work_log(db, 'info', '机器人入站处理已暂停', None)

        on = get_bot_inbound_enabled(db)
        return jsonify({
            'ok': True,
            'inbound_enabled': on,
            'started_at': get_bot_runtime_started_at(db) if on else None,
        }), 200
    finally:
        db.close()


@desktop_bot_bp.route('/bot/work-logs', methods=['GET'])
@login_required
def bot_work_logs():
    db = get_db_session()
    try:
        limit = request.args.get('limit', 80)
        return jsonify({'logs': list_bot_work_logs(db, limit)}), 200
    finally:
        db.close()


@desktop_bot_bp.route('/bot/wechat-inject', methods=['POST'])
@login_required
def bot_wechat_inject():
    db = get_db_session()
    try:
        user = get_current_user_from_request(db)
        _ensure_demo_boss_license_for_user(db, user)
        if not is_robot_license_valid(db):
            return jsonify({'error': '主授权无效或已过期，请先完成续费'}), 403
        # 默认冷注入；传 hot=1 时为热注入（不关微信，仅高级排障用）
        hot = str(request.args.get('hot', '0')).strip() in ('1', 'true', 'yes')
        data = request.get_json(silent=True) or {}
        exe_override = (
            data.get('wechat_exe_path')
            or data.get('wechatExePath')
            or ''
        ).strip()
        if not exe_override:
            from services.wechat_exe_store import get_saved_wechat_exe_path
            exe_override = get_saved_wechat_exe_path(db)
        result = run_wechat_hook_inject(
            bootstrap_inject=True,
            quit_before_inject=not hot,
            wechat_exe_path=exe_override or None,
        )
        if not result.get('ok'):
            return jsonify(result), 200
        if result.get('ok'):
            set_bot_inbound_enabled(db, True)
            sync_bot_runtime_started_at(db, True)
            append_bot_work_log(db, 'info', '微信 Hook 注入完成', None)
        return jsonify(result), 200
    finally:
        db.close()


@desktop_bot_bp.route('/bot/wechat-exe-path', methods=['GET'])
@login_required
def get_wechat_exe_path():
    db = get_db_session()
    try:
        from services.wechat_exe_store import get_saved_wechat_exe_path
        from utils.weixin_locate import locate_weixin_exe

        saved = get_saved_wechat_exe_path(db)
        detected = locate_weixin_exe()
        return jsonify({
            'saved_path': saved,
            'detected_path': detected,
            'path': saved or detected or '',
        }), 200
    finally:
        db.close()


@desktop_bot_bp.route('/bot/wechat-exe-path', methods=['POST'])
@login_required
def save_wechat_exe_path():
    db = get_db_session()
    try:
        from services.wechat_exe_store import set_saved_wechat_exe_path, validate_wechat_exe_path

        data = request.get_json() or {}
        path = data.get('path') or data.get('wechat_exe_path') or ''
        check = validate_wechat_exe_path(path)
        if not check.get('valid'):
            return jsonify({'success': False, 'error': check.get('error')}), 400
        set_saved_wechat_exe_path(db, check['path'])
        return jsonify({'success': True, 'path': check['path']}), 200
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        db.close()


@desktop_bot_bp.route('/license-status', methods=['GET'])
@login_required
def license_status():
    """快速返回授权状态（不阻塞在 Hook 探测上）。"""
    db = get_db_session()
    try:
        user = get_current_user_from_request(db)
        wxid = _ensure_demo_boss_license_for_user(db, user)
        return jsonify(get_license_status(db, wxid)), 200
    finally:
        db.close()


@desktop_bot_bp.route('/robot-redeem', methods=['POST'])
@login_required
def robot_redeem():
    db = get_db_session()
    try:
        data = request.get_json() or {}
        code = data.get('code') or data.get('last_card_cipher') or ''
        wxid = data.get('wxid') or ''
        if not wxid:
            readiness = probe_hook_readiness()
            wxid = readiness.get('wxid', '')
        result = redeem_robot_card_cipher(
            db,
            wxid=wxid,
            code=code,
            bearer_token=_auth_token_from_request(),
        )
        if result.get('error'):
            return jsonify({'success': False, 'error': result['error']}), 400
        append_bot_work_log(
            db,
            'info',
            f"主程序卡密激活成功，到期 {result.get('expire_display', '')}",
            None,
        )
        return jsonify({'success': True, **result}), 200
    finally:
        db.close()


@desktop_bot_bp.route('/robot-config', methods=['GET'])
@login_required
def robot_config_view():
    db = get_db_session()
    try:
        row = get_robot_config(db)
        cfg = None
        if row:
            cfg = {
                'wxid': row.wxid,
                'expire_date': row.expire_date,
                'last_card_cipher': (row.last_card_cipher or '')[:80] + '...'
                if row.last_card_cipher and len(row.last_card_cipher) > 80
                else row.last_card_cipher,
            }
        return jsonify({
            'config': cfg,
            'integrity_ok': verify_robot_config_row(row),
        }), 200
    finally:
        db.close()


@desktop_bot_bp.route('/debug/parse-test', methods=['POST'])
@login_required
def parse_test():
    """订单解析试算（调试工具）"""
    from services.order_parser import OrderParser

    data = request.get_json() or {}
    text = str(data.get('content') or data.get('message') or '').strip()
    if not text:
        return jsonify({'success': False, 'error': '请输入试算文本'}), 400
    parser = OrderParser()
    try:
        result = parser.parse_message(text)
        return jsonify({'success': True, 'result': result}), 200
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@desktop_bot_bp.route('/ops/backup', methods=['GET'])
@login_required
def ops_backup_status():
    backup_dir = os.path.join('data', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    files = []
    if os.path.isdir(backup_dir):
        for name in sorted(os.listdir(backup_dir), reverse=True)[:20]:
            path = os.path.join(backup_dir, name)
            if os.path.isfile(path):
                files.append({
                    'name': name,
                    'size': os.path.getsize(path),
                    'mtime': datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                })
    return jsonify({
        'backup_dir': os.path.abspath(backup_dir),
        'sqlite_path': os.path.abspath(settings.SQLITE_DB_PATH),
        'files': files,
        'platform_url': settings.SIMBOT_PLATFORM_URL or None,
    }), 200


@desktop_bot_bp.route('/ops/backup', methods=['POST'])
@login_required
def ops_backup_run():
    src = settings.SQLITE_DB_PATH
    if not os.path.isfile(src):
        return jsonify({'ok': False, 'error': '数据库文件不存在'}), 400
    backup_dir = os.path.join('data', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(backup_dir, f'tonjclaw_{stamp}.db')
    shutil.copy2(src, dest)
    db = get_db_session()
    try:
        append_bot_work_log(db, 'info', f'手动备份数据库：{dest}', None)
    finally:
        db.close()
    return jsonify({'ok': True, 'path': os.path.abspath(dest)}), 200
