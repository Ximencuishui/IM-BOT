import crypto from 'crypto';
import fs from 'fs';
import {
  isShortActivationCode,
  verifyShortActivationCodeWithWxid,
} from './activation-codec.js';

/**
 * 离线激活：32 位短码（HMAC）或旧版 base64url.payload.sig（RSA-SHA256）
 */
export function loadPublicKey(pemPath) {
  if (!pemPath || !fs.existsSync(pemPath)) return null;
  return fs.readFileSync(pemPath, 'utf8');
}

export function getActivationCardSecret() {
  return String(
    process.env.ACTIVATION_CARD_SECRET || process.env.LICENSE_CARD_SECRET || ''
  ).trim();
}

/**
 * @param {string | { publicKeyPem?: string | null, cardSecret?: string | null, wxid?: string }} keysOrPem
 * @param {string} code
 */
export function verifyActivationCode(keysOrPem, code) {
  const opts =
    typeof keysOrPem === 'string' || keysOrPem == null
      ? { publicKeyPem: keysOrPem, cardSecret: getActivationCardSecret() }
      : keysOrPem;
  const publicKeyPem = opts.publicKeyPem;
  const cardSecret = opts.cardSecret ?? getActivationCardSecret();
  const wxid = opts.wxid;
  const trimmed = String(code || '').trim();

  if (isShortActivationCode(trimmed)) {
    if (!cardSecret) return { ok: false, reason: 'no_card_secret' };
    if (!wxid) return { ok: false, reason: 'short_code_needs_wxid' };
    return verifyShortActivationCodeWithWxid(cardSecret, trimmed, wxid);
  }

  if (!publicKeyPem) return { ok: false, reason: 'no_public_key' };
  const parts = trimmed.split('.');
  if (parts.length !== 2) return { ok: false, reason: 'bad_format' };
  const [payloadB64, sigB64] = parts;
  let payloadJson;
  try {
    payloadJson = Buffer.from(payloadB64, 'base64url').toString('utf8');
  } catch {
    return { ok: false, reason: 'bad_payload_encoding' };
  }
  let payload;
  try {
    payload = JSON.parse(payloadJson);
  } catch {
    return { ok: false, reason: 'bad_payload_json' };
  }
  const sig = Buffer.from(sigB64, 'base64url');
  const v = crypto.createVerify('RSA-SHA256');
  v.update(payloadB64);
  const ok = v.verify(publicKeyPem, sig);
  if (!ok) return { ok: false, reason: 'bad_signature' };
  return { ok: true, payload };
}

export function activationFingerprint(code) {
  return crypto.createHash('sha256').update(String(code).trim(), 'utf8').digest('hex');
}

/**
 * 码内可选字段 redeem_before（Unix 秒）：须在该时刻及之前完成桌面端核销，否则拒绝。
 */
export function assertPayloadRedeemDeadline(payload) {
  if (!payload || typeof payload !== 'object') return { ok: true };
  const rb = payload.redeem_before;
  if (rb === undefined || rb === null || rb === '') return { ok: true };
  const t = Number(rb);
  if (!Number.isFinite(t)) return { ok: true };
  const now = Math.floor(Date.now() / 1000);
  if (now > t) return { ok: false, reason: 'redeem_deadline_passed', redeem_before: t };
  return { ok: true };
}
