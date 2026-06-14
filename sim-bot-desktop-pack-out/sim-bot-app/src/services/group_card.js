/**
 * 群内卡密：加入白名单 / 续费 / 续期 —— RSA 验签（与 /admin/activate 同源），核销防重放。
 * 「解密」在实现上为验签后解码 payload（本服务仅持公钥；签发方持私钥）。
 */
import {
  verifyActivationCode,
  activationFingerprint,
  assertPayloadRedeemDeadline,
  getActivationCardSecret,
} from '../auth/activation.js';
import { getWechatLoginWxid } from '../db/wechat_login_store.js';
import { extendWxGroupExpiresAt, isActiveWhitelistedGroup, upsertWxGroupBound } from '../db/wx_groups_store.js';
import { recordCardHistory, extendGroupWhitelist, isCardUsed } from '../db/prd_store.js';
import {
  applyGroupOwnerOnWhitelistJoin,
  getChatroomDisplayMeta,
  syncChatroomNickFromHookList,
  syncGroupDisplayMetaFromCache,
} from '../db/chatroom_cache_store.js';

const CARD_KW_RE = /(?:加入白名单|续费|续期)/;
const WHITELIST_JOIN_RE = /加入白名单/;
const HEX32_RE = /[a-fA-F0-9]{32}/;

export function isWhitelistJoinMessage(content) {
  return WHITELIST_JOIN_RE.test(String(content || '').replace(/\s+/g, ''));
}

export function hasGroupCardKeyword(content) {
  return CARD_KW_RE.test(String(content || '').replace(/\s+/g, ''));
}

/** 仅 32 位卡密、无「加入白名单/续费/续期」关键词（常见于分两条发送） */
export function isStandaloneGroupCardHex(content) {
  const compact = String(content || '').replace(/\s+/g, '');
  if (!compact || hasGroupCardKeyword(compact)) return '';
  const m = compact.match(new RegExp(`^${HEX32_RE.source}$`));
  return m ? m[0] : '';
}

/** 合并 Hook 多字段正文，避免 real_content / content 不一致导致识别失败 */
export function getGroupCardInboundText(obj, ex) {
  const str = (v) => {
    if (typeof v === 'string') return v.trim();
    if (v && typeof v === 'object' && typeof v.String === 'string') return v.String.trim();
    return '';
  };
  const parts = [
    str(ex?.content),
    str(ex?.originalContent),
    str(obj?.real_content),
    str(obj?.content),
    obj?.msg != null ? String(obj.msg).trim() : '',
  ];
  const seen = new Set();
  const out = [];
  for (const p of parts) {
    if (!p || seen.has(p)) continue;
    seen.add(p);
    out.push(p);
  }
  return out.join('\n').trim();
}

function globalRouteExists(db, guideWord, categoryWord) {
  const g = String(guideWord || '').trim();
  const c = String(categoryWord || '').trim();
  if (!g || !c) return false;
  const ok = db
    .prepare(
      `SELECT 1 FROM cmd_routes
       WHERE is_active = 1 AND guide_word = ? AND category_word = ?
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
       LIMIT 1`
    )
    .get(g, c);
  return Boolean(ok);
}

function seedDefaultMacauTe(db, wxGroupId) {
  if (!globalRouteExists(db, '新澳门', '特')) return;
  db.prepare(
    `INSERT OR IGNORE INTO wx_group_route_enables (wx_group_id, guide_word, category_word, is_enabled, updated_at)
     VALUES (?, '新澳门', '特', 1, datetime('now'))`
  ).run(wxGroupId);
}

/**
 * @returns {{ code: string } | { error: string } | null}
 */
export function parseGroupCardMessage(content) {
  const raw = String(content || '').trim();
  const compact = raw.replace(/\s+/g, '');
  if (!compact || !CARD_KW_RE.test(compact)) return null;
  const m32 = compact.match(HEX32_RE);
  if (m32) return { code: m32[0] };
  const mLegacy = compact.match(/([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)/);
  if (!mLegacy) return { error: '请在同一消息内附上卡密（32 位激活码或一行签名激活串）。' };
  return { code: mLegacy[1] };
}

/**
 * @returns {{ replyText: string } | null}
 */
export async function tryRedeemGroupCardMessage({
  db,
  wxGroupId,
  senderWxid,
  content,
  publicKeyPem,
  hookClient = null,
  mutate = true,
  logger = null,
}) {
  const parsed = parseGroupCardMessage(content);
  if (!parsed) return null;
  if (!isActiveWhitelistedGroup(db, wxGroupId) && !isWhitelistJoinMessage(content)) {
    return null;
  }
  if (parsed.error) return { replyText: parsed.error };
  const cardSecret = getActivationCardSecret();
  if (!publicKeyPem?.trim() && !cardSecret) {
    return {
      replyText:
        '服务端未配置 ACTIVATION_CARD_SECRET 或激活公钥，无法核销卡密。',
    };
  }
  const botWxid = String(getWechatLoginWxid(db) || '').trim();
  const robotRow = db.prepare('SELECT wxid FROM robot_config LIMIT 1').get();
  const bindWxid = botWxid || String(robotRow?.wxid || '').trim();
  if (!bindWxid) {
    return { replyText: '请先在桌面端登录微信后再核销群卡。' };
  }

  const v = verifyActivationCode(
    { publicKeyPem: publicKeyPem || null, cardSecret, wxid: bindWxid },
    parsed.code
  );
  if (!v.ok) {
    const wxHint =
      v.reason === 'bad_short_signature' || v.reason === 'short_code_needs_wxid'
        ? '请确认本机微信已登录，且卡密由销售端按当前机器人 wxid 签发。'
        : '';
    return {
      replyText: `卡密无效或已损坏（${v.reason || 'verify_failed'}）。${wxHint}`,
    };
  }
  if (v.payload?.installation === true) {
    return { replyText: '此为产品安装类授权码，请使用微信群续期卡密。' };
  }
  const dl = assertPayloadRedeemDeadline(v.payload);
  if (!dl.ok) {
    return { replyText: '该卡密已超过兑换截止时间。' };
  }

  const days = Math.min(3660, Math.max(1, Number(v.payload?.days ?? 30) || 30));
  const fp = activationFingerprint(parsed.code);
  if (isCardUsed(db, fp)) {
    return { replyText: '该卡密已使用，不能重复核销。' };
  }

  if (mutate) {
    try {
      db.prepare(
        `INSERT INTO activation_redemptions (code_fingerprint, raw_payload, wx_group_id, redeemed_by_user_id)
         VALUES (?,?,?,NULL)`
      ).run(fp, JSON.stringify(v.payload), wxGroupId);
    } catch {
      return { replyText: '该卡密已使用，不能重复核销。' };
    }
    recordCardHistory(db, fp, wxGroupId);
  } else {
    const used = db.prepare(`SELECT 1 FROM activation_redemptions WHERE code_fingerprint = ?`).get(fp);
    if (used) return { replyText: '[试算] 该卡密已核销过。' };
  }

  const existing = db.prepare(`SELECT * FROM wx_groups WHERE wx_group_id = ?`).get(wxGroupId);
  const whitelistJoin = isWhitelistJoinMessage(content);

  if (!existing) {
    if (!mutate) {
      return { replyText: `[试算] 将新绑本群并开通约 ${days} 天；默认仅开启玩法「新澳门·特」（其余请用开启指令）。` };
    }
    const t = new Date();
    t.setDate(t.getDate() + days);
    const expiresIso = t.toISOString();
    const sender = String(senderWxid || '').trim();
    upsertWxGroupBound(db, {
      wx_group_id: wxGroupId,
      expires_at: expiresIso,
      strict_play_routes: 1,
      manual_owner: whitelistJoin && sender ? sender : undefined,
    });
    seedDefaultMacauTe(db, wxGroupId);
    const meta0 = getChatroomDisplayMeta(db, wxGroupId);
    extendGroupWhitelist(db, wxGroupId, expiresIso.replace('T', ' ').slice(0, 19), parsed.code, meta0);
    let ownerNote = '';
    if (whitelistJoin) {
      if (hookClient) await syncChatroomNickFromHookList(db, hookClient, wxGroupId);
      const o = await applyGroupOwnerOnWhitelistJoin(db, hookClient, wxGroupId, senderWxid);
      syncGroupDisplayMetaFromCache(db, wxGroupId);
      if (o.manual_owner) ownerNote = ` 已登记群主：${o.manual_owner}。`;
    }
    if (typeof logger?.info === 'function') {
      logger.info(`[group-card] 新绑群 ${wxGroupId} 续期+${days}d strict=1 owner=${ownerNote || '-'}`);
    }
    if (typeof db.persist === 'function') db.persist();
    return {
      replyText: `群已绑定并开通约 ${days} 天（至 ${expiresIso.slice(0, 10)}）。已默认开启「新澳门·特」，请用「开启+渠道/玩法」逐步打开其它玩法；发「查玩法」查看。${ownerNote}`,
    };
  }

  if (!mutate) {
    const base = existing.expires_at ? new Date(existing.expires_at) : new Date();
    const t = base.getTime() < Date.now() ? new Date() : base;
    const t2 = new Date(t);
    t2.setDate(t2.getDate() + days);
    return { replyText: `[试算] 将在现有到期基础上续 ${days} 天，新到期约为 ${t2.toISOString().slice(0, 10)}。` };
  }

  const expiresIso = extendWxGroupExpiresAt(db, wxGroupId, days);
  const meta1 = getChatroomDisplayMeta(db, wxGroupId);
  extendGroupWhitelist(db, wxGroupId, expiresIso.replace('T', ' ').slice(0, 19), parsed.code, meta1);
  let ownerNote = '';
  if (whitelistJoin) {
    if (hookClient) await syncChatroomNickFromHookList(db, hookClient, wxGroupId);
    const o = await applyGroupOwnerOnWhitelistJoin(db, hookClient, wxGroupId, senderWxid);
    syncGroupDisplayMetaFromCache(db, wxGroupId);
    if (o.manual_owner) ownerNote = ` 已更新群主：${o.manual_owner}。`;
  }
  if (typeof logger?.info === 'function') {
    logger.info(`[group-card] 续期群 ${wxGroupId} +${days}d → ${expiresIso}${ownerNote}`);
  }
  if (typeof db.persist === 'function') db.persist();
  return {
    replyText: `续期成功：已延长约 ${days} 天，当前到期 ${expiresIso.slice(0, 10)}。${ownerNote}`,
  };
}
