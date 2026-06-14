"""SimBot 管理平台卡密验签（对齐 sim-bot-node activation / activation-codec）"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any

SHORT_CODE_RE = re.compile(r'^[a-fA-F0-9]{32}$', re.I)


def activation_fingerprint(code: str) -> str:
    return hashlib.sha256(str(code or '').strip().encode('utf-8')).hexdigest()


def is_short_activation_code(code: str) -> bool:
    return bool(SHORT_CODE_RE.match(str(code or '').strip()))


def _wxid_hash8(wxid: str) -> bytes:
    return hashlib.sha256(str(wxid or '').strip().encode('utf-8')).digest()[:8]


def _unpack_data_block(data: bytes) -> dict | None:
    if len(data) != 8 or data[0] != 1:
        return None
    sku_flag = data[1] & 0x01
    installation = (data[1] & 0x04) != 0
    days = int.from_bytes(data[2:4], 'big')
    iat = int.from_bytes(data[4:8], 'big')
    sku = 'ADMIN_YEAR' if sku_flag == 1 else 'GROUP_MONTH'
    return {'sku': sku, 'days': days, 'iat': iat, 'installation': installation}


def verify_short_activation_code(card_secret: str, code: str, wxid: str) -> dict:
    secret = str(card_secret or '').strip()
    if not secret:
        return {'ok': False, 'reason': 'no_card_secret'}
    raw = str(code or '').strip().lower()
    if not SHORT_CODE_RE.match(raw):
        return {'ok': False, 'reason': 'bad_short_format'}
    buf = bytes.fromhex(raw)
    data, mac = buf[:8], buf[8:16]
    unpacked = _unpack_data_block(data)
    if not unpacked:
        return {'ok': False, 'reason': 'bad_short_payload'}
    expect = hmac.new(secret.encode('utf-8'), data + _wxid_hash8(wxid), hashlib.sha256).digest()[:8]
    if mac != expect:
        return {'ok': False, 'reason': 'bad_short_mac'}
    payload = {
        'days': unpacked['days'],
        'iat': unpacked['iat'],
        'license_sku': unpacked['sku'],
        'installation': unpacked['installation'],
        'wxid': wxid,
    }
    if unpacked['installation']:
        payload['group_validity_days'] = unpacked['days']
    return {'ok': True, 'payload': payload}


def verify_rsa_activation_code(public_key_pem: str, code: str) -> dict:
    pem = str(public_key_pem or '').strip()
    if not pem:
        return {'ok': False, 'reason': 'no_public_key'}
    parts = str(code or '').strip().split('.')
    if len(parts) != 2:
        return {'ok': False, 'reason': 'bad_format'}
    payload_b64, sig_b64 = parts
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64 + '==').decode('utf-8')
        payload = json.loads(payload_json)
    except Exception:
        return {'ok': False, 'reason': 'bad_payload'}
    try:
        sig = base64.urlsafe_b64decode(sig_b64 + '==')
    except Exception:
        return {'ok': False, 'reason': 'bad_signature_encoding'}
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        key = load_pem_public_key(pem.encode('utf-8'))
        key.verify(sig, payload_b64.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
    except ImportError:
        return {'ok': False, 'reason': 'cryptography_not_installed'}
    except Exception:
        return {'ok': False, 'reason': 'bad_signature'}
    return {'ok': True, 'payload': payload}


def wxid_matches_payload(payload: dict, wxid: str) -> bool:
    if not payload:
        return False
    bind = str(
        payload.get('wxid')
        or payload.get('robot_wxid')
        or payload.get('account_wxid')
        or ''
    ).strip()
    if not bind:
        return True
    return bind == str(wxid or '').strip()


def assert_payload_redeem_deadline(payload: dict) -> dict:
    rb = payload.get('redeem_before') if payload else None
    if rb is None or rb == '':
        return {'ok': True}
    try:
        t = int(rb)
    except (TypeError, ValueError):
        return {'ok': True}
    if time.time() > t:
        return {'ok': False, 'reason': 'redeem_deadline_passed'}
    return {'ok': True}


def verify_activation_code(
    *,
    public_key_pem: str | None,
    card_secret: str | None,
    wxid: str,
    code: str,
) -> dict:
    trimmed = str(code or '').strip()
    if is_short_activation_code(trimmed):
        if not card_secret:
            return {'ok': False, 'reason': 'no_card_secret'}
        if not wxid:
            return {'ok': False, 'reason': 'short_code_needs_wxid'}
        return verify_short_activation_code(card_secret, trimmed, wxid)
    return verify_rsa_activation_code(public_key_pem or '', trimmed)


def payload_days(payload: dict) -> int:
    installation = payload.get('installation') is True
    raw = (
        payload.get('group_validity_days')
        if installation
        else payload.get('days')
    )
    days = int(raw or (365 if installation else 30))
    return max(1, min(3660, days))
