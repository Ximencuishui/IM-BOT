import crypto from 'crypto';

/** 32 位十六进制短码（16 字节：8 数据 + 8 HMAC） */
export const SHORT_CODE_RE = /^[a-fA-F0-9]{32}$/;

export function isShortActivationCode(code) {
  return SHORT_CODE_RE.test(String(code || '').trim());
}

export function wxidHash8(wxid) {
  return crypto.createHash('sha256').update(String(wxid || '').trim(), 'utf8').digest().subarray(0, 8);
}

/**
 * @param {Record<string, unknown>} payloadObj 签发 JSON（与旧版 RSA 载荷字段对齐）
 */
export function payloadObjToShortParams(payloadObj) {
  const p = payloadObj || {};
  const installation = p.installation === true;
  const sku =
    installation || String(p.license_sku || '').includes('ADMIN')
      ? 'ADMIN_YEAR'
      : 'GROUP_MONTH';
  const days = Math.min(
    65535,
    Math.max(
      1,
      Number(
        installation ? p.group_validity_days ?? p.days ?? 365 : p.days ?? 30
      ) || (installation ? 365 : 30)
    )
  );
  const iat = Math.floor(Number(p.iat) || Date.now() / 1000);
  const wxid = String(p.wxid || p.robot_wxid || '').trim();
  if (!wxid) throw new Error('签发短卡密须包含 wxid');
  return { sku, days, iat, wxid, installation };
}

function packDataBlock({ sku, days, iat, installation }) {
  const data = Buffer.alloc(8);
  data[0] = 1;
  data[1] = (sku === 'ADMIN_YEAR' ? 1 : 0) | (installation ? 0x04 : 0);
  data.writeUInt16BE(days, 2);
  data.writeUInt32BE(iat >>> 0, 4);
  return data;
}

function unpackDataBlock(data) {
  if (!data || data.length !== 8 || data[0] !== 1) return null;
  const skuFlag = data[1] & 0x01;
  const installation = (data[1] & 0x04) !== 0;
  const days = data.readUInt16BE(2);
  const iat = data.readUInt32BE(4);
  const sku = skuFlag === 1 ? 'ADMIN_YEAR' : 'GROUP_MONTH';
  return { sku, days, iat, installation, skuFlag };
}

/**
 * @returns {string} 32 位小写十六进制
 */
export function signShortActivationCode(cardSecret, params) {
  const secret = String(cardSecret || '').trim();
  if (!secret) throw new Error('未配置 ACTIVATION_CARD_SECRET');
  const { sku, days, iat, wxid, installation } = params;
  const data = packDataBlock({ sku, days, iat, installation });
  const wh = wxidHash8(wxid);
  const mac = crypto.createHmac('sha256', secret).update(data).update(wh).digest().subarray(0, 8);
  return Buffer.concat([data, mac]).toString('hex');
}

/**
 * 验签短码（须传入绑定 wxid，与签发时一致）
 */
export function verifyShortActivationCodeWithWxid(cardSecret, code, wxid) {
  const secret = String(cardSecret || '').trim();
  if (!secret) return { ok: false, reason: 'no_card_secret' };
  const raw = String(code || '').trim().toLowerCase();
  if (!SHORT_CODE_RE.test(raw)) return { ok: false, reason: 'bad_short_format' };
  const buf = Buffer.from(raw, 'hex');
  const data = buf.subarray(0, 8);
  const mac = buf.subarray(8, 16);
  const unpacked = unpackDataBlock(data);
  if (!unpacked) return { ok: false, reason: 'bad_short_payload' };
  const wh = wxidHash8(wxid);
  const macExpected = crypto.createHmac('sha256', secret).update(data).update(wh).digest().subarray(0, 8);
  if (!mac.equals(macExpected)) return { ok: false, reason: 'bad_short_signature' };
  const payload = expandShortPayload(unpacked, wh);
  return { ok: true, payload };
}

function expandShortPayload(unpacked, wxidHashBuf) {
  const { sku, days, iat, installation } = unpacked;
  const base = {
    _codec: 'v2',
    iat,
    days,
    wxid_hash: wxidHashBuf.toString('hex'),
    license_sku: sku === 'ADMIN_YEAR' ? 'ADMIN_YEAR_V1' : 'GROUP_MONTH_V1',
  };
  if (sku === 'ADMIN_YEAR' || installation) {
    return {
      ...base,
      installation: true,
      group_validity_days: days,
      admin_console_single: true,
      desktop_instances: 1,
    };
  }
  return base;
}

/** 门户展示：不验签，仅解析结构（需已知 wxid 才能还原 HMAC，此处只解析数据半段） */
export function decodeShortCodeDataHalf(code) {
  const raw = String(code || '').trim().toLowerCase();
  if (!SHORT_CODE_RE.test(raw)) return null;
  const data = Buffer.from(raw, 'hex').subarray(0, 8);
  const unpacked = unpackDataBlock(data);
  if (!unpacked) return null;
  return {
    ...unpacked,
    _codec: 'v2',
    license_sku: unpacked.sku === 'ADMIN_YEAR' ? 'ADMIN_YEAR_V1' : 'GROUP_MONTH_V1',
    group_validity_days: unpacked.installation ? unpacked.days : undefined,
  };
}

export function wxidMatchesPayload(payload, wxid) {
  if (!payload || typeof payload !== 'object') return true;
  if (payload._codec === 'v2') {
    const bot = String(wxid || '').trim();
    if (!bot) return false;
    const wh = wxidHash8(bot);
    const expect = String(payload.wxid_hash || '').trim().toLowerCase();
    return expect === wh.toString('hex');
  }
  const payloadWxid = String(payload.wxid || payload.robot_wxid || '').trim();
  const botWxid = String(wxid || '').trim();
  if (botWxid && payloadWxid && botWxid !== payloadWxid) return false;
  return true;
}
