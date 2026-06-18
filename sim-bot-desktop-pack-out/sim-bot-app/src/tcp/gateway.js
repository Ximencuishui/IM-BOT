import net from 'net';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import XLSX from 'xlsx';
import {
  extractWechatFields,
  extractRevokedWxMessageIds,
  normalizeChatroomId,
} from './extract.js';
import { hookRawPayloadSummary } from '../util/logger.js';
import { syncWechatLoginFromHookPayload } from '../db/wechat_login_store.js';
import { resolveInboundOrderText, isWeChatNonTextInbound } from './inbound_attach.js';
import { evaluateRules, parseActionJson, buildRuleMissDebugReplyText } from '../rules/engine.js';
import {
  executeConfiguredCommand,
  maybeHandleDrawCommand,
  matchesDrawCommandLine,
  cmdRouteDisplayLabel,
  stripWeChatAtPrefix,
  matchesHelpInstruction,
  matchesInstructionOnlyLine,
  zodiacOfBallForSettlementYear,
  revokeOrdersForWxMessage,
  isGroupDebugRuleMissReplyEnabled,
  buildInboundOrderMissDebugText,
  buildUnrecognizedInboundMessageReply,
  buildInboundOrderParseFailureReply,
  inboundTextHasOrderDigits,
} from '../commands/engine.js';
import {
  getBotInboundEnabled,
  appendBotWorkLog,
  recordInboundWorkSummary,
} from '../bot/runtime_store.js';
import { resolveInboundSenderWxid } from '../bot/inbound_sender.js';
import {
  isPlaceholderGroupDisplayName,
  resolveChatroomDisplayName,
  syncChatroomMembersFromHook,
  syncChatroomNickFromHookList,
  syncGroupDisplayMetaFromCache,
} from '../db/chatroom_cache_store.js';
import {
  isShopRelatedMessage,
  buildShopHelpText,
} from '../services/shop_bot_handler.js';
import { pluginManager } from '../plugins/manager.js';
import {
  tryRedeemGroupCardMessage,
  isWhitelistJoinMessage,
  parseGroupCardMessage,
  getGroupCardInboundText,
  isStandaloneGroupCardHex,
} from '../services/group_card.js';
import { getActivationCardSecret } from '../auth/activation.js';
import { isActiveWhitelistedGroup } from '../db/wx_groups_store.js';
import { createInboundDedupe } from '../cache/inbound_dedupe.js';
import { createLocalOutboundQueue } from '../cache/local_outbound_queue.js';
import { isRobotLicenseValid, isGroupServiceValid } from '../db/prd_store.js';
import { hookReceiveUsesTcp } from '../hook/inject_config.js';
import { logInboundGroupMessage, shouldLogAllGroupInbound } from '../util/log_recv.js';

const GROUP_CARD_HEX32_RE = /[a-fA-F0-9]{32}/;
import { classifyInboundForPipeline, looksLikeInboundOrderAttempt } from '../commands/pipeline/index.js';

const HEADER = 4;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPORT_DIR = path.join(__dirname, '../../data/reports');
const MIN_REPLY_DELAY_MS = Math.max(0, Number(process.env.BOT_REPLY_DELAY_MIN_MS ?? 0));
const MAX_REPLY_DELAY_MS = Math.max(
  MIN_REPLY_DELAY_MS,
  Number(process.env.BOT_REPLY_DELAY_MAX_MS ?? process.env.BOT_REPLY_DELAY_MIN_MS ?? 0)
);
const ORDER_REPLY_MERGE_MS = Math.max(0, Number(process.env.ORDER_REPLY_MERGE_MS ?? 700));
/** 同一秒内 Hook 连发多帧（合并转发拆条）时，先拼成一段再下单；0 关闭。建议 80~120 */
const INBOUND_COALESCE_MS = Math.max(0, Number(process.env.INBOUND_COALESCE_MS ?? 0));

let activationPublicPemCache;
function loadActivationPublicPem() {
  if (activationPublicPemCache !== undefined) return activationPublicPemCache;
  const root = process.env.SIM_BOT_ROOT
    ? path.resolve(process.env.SIM_BOT_ROOT)
    : path.join(__dirname, '../..');
  let p =
    process.env.ACTIVATION_PUBLIC_KEY_PATH ||
    path.join(root, 'keys', 'activation_public.pem');
  if (p && !path.isAbsolute(p)) p = path.resolve(root, p);
  activationPublicPemCache = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
  return activationPublicPemCache;
}

/** 1 时入站 TCP 摘要用 info；默认走 debug（配合 DEBUG=1 才在终端看到） */
const INBOUND_LOG_VERBOSE = String(process.env.BOT_INBOUND_LOG_VERBOSE ?? process.env.INBOUND_LOG_VERBOSE ?? '') === '1';
let outboundContext = null;
let outboundQueue = null;
let inboundDedupe = null;

/** 与引擎回执「+12+34」同形时可合并（逐条转发多单时合成一条回复） */
function mergeableCmdReply(replyText) {
  return /^\+\d+(?:\+\d+)*$/.test(String(replyText || '').trim());
}

function mergePlusReplies(prev, next) {
  const p = String(prev || '').trim();
  const n = String(next || '').trim();
  if (!n) return p;
  if (!mergeableCmdReply(n)) return n;
  if (!p || !mergeableCmdReply(p)) return n;
  return p + n;
}

const orderMergeState = new Map();

/** 群 + 发送者 + createTime：连发帧先入桶，短窗内拼行再交给引擎（需 INBOUND_COALESCE_MS>0） */
const inboundCoalesceBuckets = new Map();

function mergeHookPayloadsForCoalesce(objs, contents, originals) {
  const last = objs[objs.length - 1];
  let merged;
  try {
    merged = structuredClone(last);
  } catch {
    merged = JSON.parse(JSON.stringify(last));
  }
  const mergedReal = contents.map((c) => String(c || '').trim()).filter(Boolean).join('\n');
  merged.real_content = mergedReal;
  const oJoined = originals.map((o) => String(o || '').trim()).filter(Boolean).join('\n');
  if (merged.content != null && typeof merged.content === 'object') {
    merged.content = { ...merged.content, String: oJoined };
  } else {
    merged.content = oJoined;
  }
  merged.__skipInboundCoalesce = true;
  return merged;
}

async function flushOrderMerge(mergeKey, logger) {
  const st = orderMergeState.get(mergeKey);
  if (!st || !st.mergedText) return;
  if (st.timeoutId) clearTimeout(st.timeoutId);
  orderMergeState.delete(mergeKey);
  const lj = st.lastJob;
  if (lj) {
    try {
      enqueueOutboundReply({ ...lj, replyText: st.mergedText }, logger);
    } catch (e) {
      logger.warn(`[order-merge] flush failed: ${e.message || 'unknown'}`);
    }
  }
}

function scheduleMergedCommandReply(job, logger) {
  const mergeKey = `${job.groupId || ''}::${job.senderWxid || ''}`;
  let st = orderMergeState.get(mergeKey);
  if (!st) st = { mergedText: '', lastJob: null, timeoutId: null };
  st.mergedText = mergePlusReplies(st.mergedText, job.replyText);
  st.lastJob = { ...job };
  if (st.timeoutId) clearTimeout(st.timeoutId);
  const tid = setTimeout(() => {
    const cur = orderMergeState.get(mergeKey);
    if (!cur || cur.timeoutId !== tid) return;
    orderMergeState.delete(mergeKey);
    const text = cur.mergedText;
    const flushJob = cur.lastJob;
    if (flushJob && text) {
      try {
        enqueueOutboundReply({ ...flushJob, replyText: text }, logger);
      } catch (e) {
        logger.warn(`[order-merge] send failed: ${e.message || 'unknown'}`);
      }
    }
  }, ORDER_REPLY_MERGE_MS);
  st.timeoutId = tid;
  orderMergeState.set(mergeKey, st);
}

function randomReplyDelayMs() {
  if (MAX_REPLY_DELAY_MS <= 0) return 0;
  return MIN_REPLY_DELAY_MS + Math.floor(Math.random() * (MAX_REPLY_DELAY_MS - MIN_REPLY_DELAY_MS + 1));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeCsvCell(v) {
  const s = String(v ?? '');
  return `"${s.replace(/"/g, '""')}"`;
}

function generateReportCsv(db) {
  fs.mkdirSync(REPORT_DIR, { recursive: true });
  const rows = db
    .prepare(
      `SELECT created_at, wx_group_id, sender_wxid, content_preview
       FROM message_audit
       ORDER BY id DESC
       LIMIT 50`
    )
    .all();
  const header = ['time', 'group_id', 'sender_wxid', 'content_preview'].join(',');
  const body = rows
    .map((r) =>
      [r.created_at, r.wx_group_id, r.sender_wxid, r.content_preview].map((x) => escapeCsvCell(x)).join(',')
    )
    .join('\n');
  const fileName = `report_${Date.now()}.csv`;
  const filePath = path.join(REPORT_DIR, fileName);
  fs.writeFileSync(filePath, `${header}\n${body}\n`, 'utf8');
  return filePath;
}

function parsePrivateReportCommand(content) {
  const raw = String(content || '').trim();
  if (!raw) return null;
  const compact = raw.replace(/\s+/g, '');
  if (!compact.startsWith('报表')) return null;
  let rest = compact.slice(2).replace(/^[:：+]/, '');
  if (!rest) return { error: '缺少渠道名，示例：报表+新澳门+按号' };
  let mode = '按号';
  const modeTail = rest.match(/(按号|按成员|成员)$/);
  if (modeTail) {
    mode = modeTail[1] === '成员' ? '按成员' : modeTail[1];
    rest = rest.slice(0, -modeTail[1].length);
  }
  const tokens = rest.split('+').map((x) => x.trim()).filter(Boolean);
  if (tokens.length === 0) return { error: '缺少渠道名，示例：报表+新澳门+按号' };
  let channelWord = '';
  let categoryWord = '';
  let date = '';
  for (const tk of tokens) {
    if (tk === '按号' || tk === '按成员') {
      mode = tk;
      continue;
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(tk)) {
      date = tk;
      continue;
    }
    if (!channelWord) channelWord = tk;
    else if (!categoryWord) categoryWord = tk;
  }
  if (!channelWord && tokens.length === 1) {
    channelWord = tokens[0];
  }
  if (!channelWord) return { error: '缺少渠道名，示例：报表+新澳门+按号' };
  return { channelWord, categoryWord, mode, date };
}

function normalizeChannelCategoryByRoutes(db, channelWord, categoryWord) {
  const ch = String(channelWord || '').trim();
  const cat = String(categoryWord || '').trim();
  if (!ch) return { channelWord: '', categoryWord: cat };
  if (cat) return { channelWord: ch, categoryWord: cat };
  const routes = db
    .prepare(
      `SELECT DISTINCT guide_word, category_word
       FROM cmd_routes
       WHERE is_active = 1
       ORDER BY LENGTH(guide_word) DESC, LENGTH(category_word) DESC`
    )
    .all();
  for (const r of routes) {
    const guide = String(r.guide_word || '').trim();
    const category = String(r.category_word || '').trim();
    if (!guide || !category) continue;
    if (!ch.startsWith(guide)) continue;
    const remain = ch.slice(guide.length).trim();
    if (remain && remain === category) {
      return { channelWord: guide, categoryWord: category };
    }
  }
  return { channelWord: ch, categoryWord: '' };
}

function parsePrivateHelpCommand(content, db) {
  const text = stripWeChatAtPrefix(String(content || ''), db).trim();
  if (!text) return false;
  return matchesHelpInstruction(text, db);
}

function buildPrivateHelpText() {
  return [
    '【私聊报表】',
    '报表+渠道 [+分类] [按号|按成员] [日期]',
    '例：报表新澳门特 / 报表新澳门按号 2026-04-26',
    '不传分类=该渠道全分类；默认当期',
  ].join('\n');
}

function getOwnedBoundGroups(db, ownerWxid) {
  void ownerWxid;
  const rows = db
    .prepare(`SELECT wx_group_id AS room_id FROM wx_groups WHERE is_active = 1`)
    .all();
  return rows.map((x) => String(x.room_id || '').trim()).filter(Boolean);
}

function resolveReportSettlementDate(db, groupIds, channelWord, categoryWord, date) {
  if (date) return date;
  if (!groupIds.length) return '';
  const placeholders = groupIds.map(() => '?').join(',');
  const cat = String(categoryWord || '').trim();
  const whereCat = cat ? ' AND category_word = ?' : '';
  const params = cat ? [channelWord, cat, ...groupIds] : [channelWord, ...groupIds];
  const row = db
    .prepare(
      `SELECT MAX(settlement_date) AS max_date
       FROM cmd_orders
       WHERE guide_word = ?
         ${whereCat}
         AND wx_group_id IN (${placeholders})`
    )
    .get(...params);
  return String(row?.max_date || '').trim();
}

function buildOrderReportWorkbook(db, { groupIds, channelWord, categoryWord, mode, settlementDate }) {
  const zodiacOfAgeBySettlementDate = (ballNo) => {
    const m = String(settlementDate || '').match(/^(\d{4})-\d{2}-\d{2}$/);
    const year = m ? Number(m[1]) : new Date().getFullYear();
    return zodiacOfBallForSettlementYear(ballNo, year);
  };

  const placeholders = groupIds.map(() => '?').join(',');
  const cat = String(categoryWord || '').trim();
  const whereCat = cat ? ' AND o.category_word = ?' : '';
  const paramsBase = cat ? [channelWord, settlementDate, cat, ...groupIds] : [channelWord, settlementDate, ...groupIds];
  let rows = [];
  if (mode === '按成员') {
    rows = db
      .prepare(
        `SELECT
           o.settlement_date,
           o.guide_word,
           o.category_word,
           o.sender_wxid,
           COALESCE(MAX(m.display_name), MAX(p.nick_name), MAX(m.nick_name), '') AS member_name,
           COUNT(*) AS detail_count,
           SUM(o.order_amount) AS total_amount
         FROM cmd_orders o
         LEFT JOIN wx_chatroom_members m
           ON m.wxid = o.sender_wxid AND m.room_id = o.wx_group_id
         LEFT JOIN wx_contact_profiles p
           ON p.wxid = o.sender_wxid
         WHERE o.guide_word = ?
           AND o.settlement_date = ?
           ${whereCat}
           AND o.wx_group_id IN (${placeholders})
         GROUP BY o.settlement_date, o.guide_word, o.category_word, o.sender_wxid
         ORDER BY o.category_word ASC, total_amount DESC, o.sender_wxid ASC`
      )
      .all(...paramsBase);
  } else {
    rows = db
      .prepare(
        `SELECT
           o.settlement_date,
           o.guide_word,
           o.category_word,
           o.item_value,
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.sender_wxid) AS member_count,
           SUM(o.order_amount) AS total_amount
         FROM cmd_orders o
         WHERE o.guide_word = ?
           AND o.settlement_date = ?
           ${whereCat}
           AND o.wx_group_id IN (${placeholders})
         GROUP BY o.settlement_date, o.guide_word, o.category_word, o.item_value
         ORDER BY o.category_word ASC, o.item_value ASC`
      )
      .all(...paramsBase);
  }

  const wb = XLSX.utils.book_new();
  const aoa = [];
  aoa.push(['报表类型', mode, '渠道', channelWord, '分类', cat || '全部', '结单日期', settlementDate]);
  aoa.push([]);
  if (mode === '按成员') {
    aoa.push(['分类', '成员wxid', '成员名称', '明细笔数', '总金额']);
    for (const r of rows) {
      aoa.push([
        String(r.category_word || ''),
        String(r.sender_wxid || ''),
        String(r.member_name || ''),
        Number(r.detail_count || 0),
        Number(r.total_amount || 0),
      ]);
    }
  } else {
    aoa.push(['分类', '号码', '明细笔数', '成员数', '总金额']);
    for (const r of rows) {
      aoa.push([
        String(r.category_word || ''),
        Number(r.item_value || 0),
        Number(r.detail_count || 0),
        Number(r.member_count || 0),
        Number(r.total_amount || 0),
      ]);
    }
  }
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  XLSX.utils.book_append_sheet(wb, ws, mode === '按成员' ? '按成员汇总' : '按号');

  if (mode === '按成员') {
    const detailRows = db
      .prepare(
        `SELECT
           o.settlement_date,
           o.guide_word,
           o.category_word,
           o.sender_wxid,
           COALESCE(m.display_name, p.nick_name, m.nick_name, '') AS member_name,
           o.item_value,
           o.order_amount,
           o.content_preview,
           o.created_at
         FROM cmd_orders o
         LEFT JOIN wx_chatroom_members m
           ON m.wxid = o.sender_wxid AND m.room_id = o.wx_group_id
         LEFT JOIN wx_contact_profiles p
           ON p.wxid = o.sender_wxid
         WHERE o.guide_word = ?
           AND o.settlement_date = ?
           ${whereCat}
           AND o.wx_group_id IN (${placeholders})
         ORDER BY o.category_word ASC, o.sender_wxid ASC, o.created_at ASC, o.item_value ASC`
      )
      .all(...paramsBase);
    const detailAoa = [];
    detailAoa.push([`期号：${settlementDate}`]);
    detailAoa.push([`渠道：${channelWord}`]);
    detailAoa.push([`分类：${cat || '全部'}`]);
    detailAoa.push([]);

    const grouped = new Map();
    for (const r of detailRows) {
      const wxid = String(r.sender_wxid || '').trim();
      const name = String(r.member_name || '').trim();
      const key = `${wxid}__${name}`;
      if (!grouped.has(key)) {
        grouped.set(key, {
          wxid,
          name,
          rows: [],
        });
      }
      grouped.get(key).rows.push(r);
    }

    let grandTotal = 0;
    let memberIdx = 1;
    for (const g of grouped.values()) {
      const memberTitle = String(g.name || '').trim() || String(g.wxid || '').trim() || `成员${memberIdx}`;
      detailAoa.push([`${memberTitle} 明细`, g.name || '-', g.wxid || '']);
      detailAoa.push(['序号', '号码(01-49)', '生肖', '金额', '下单时间', '下单指令']);
      let subTotal = 0;
      let seq = 1;
      for (const r of g.rows) {
        const n = Number(r.item_value || 0);
        const nLabel = Number.isFinite(n) ? String(Math.floor(n)).padStart(2, '0') : String(r.item_value || '');
        const zodiac = Number.isFinite(n) ? zodiacOfAgeBySettlementDate(n) : '';
        const amt = Number(r.order_amount || 0);
        detailAoa.push([
          seq,
          nLabel,
          zodiac,
          amt,
          String(r.created_at || ''),
          String(r.content_preview || ''),
        ]);
        subTotal += amt;
        seq += 1;
      }
      detailAoa.push(['', '小计', subTotal]);
      detailAoa.push([]);
      grandTotal += subTotal;
      memberIdx += 1;
    }
    detailAoa.push(['', '合计', grandTotal]);
    const detailWs = XLSX.utils.aoa_to_sheet(detailAoa);
    XLSX.utils.book_append_sheet(wb, detailWs, '按成员明细');
  }
  fs.mkdirSync(REPORT_DIR, { recursive: true });
  const fileName = `order_report_${channelWord}_${settlementDate}_${Date.now()}.xlsx`;
  const filePath = path.join(REPORT_DIR, fileName);
  XLSX.writeFile(wb, filePath);
  return { filePath, rowCount: rows.length };
}

function buildDedupeKey(obj, ex) {
  const parts = [
    obj?.newMsgId || '',
    obj?.msgId || '',
    obj?.msgSeq ?? '',
    ex?.groupId || '',
    ex?.senderWxid || '',
    ex?.content || '',
    obj?.event_type || '',
    obj?.msgType || '',
  ];
  return parts.join('|');
}

function normalizeNick(nick) {
  const n = String(nick || '').trim();
  if (!n || n.endsWith('@chatroom')) return '';
  return n;
}

function resolveSenderWxid(ex) {
  let wxid = ex.senderWxid || '';
  if (wxid && !String(wxid).endsWith('@chatroom')) return wxid;
  const m = String(ex.originalContent || '').match(/^([^:\n：]+)[:：]\s*\n/);
  const guessedWxid = m?.[1]?.trim();
  if (guessedWxid && !String(guessedWxid).endsWith('@chatroom')) return guessedWxid;
  return '';
}

async function executeOutboundJob(job) {
  const { logger, hookClient, db } = outboundContext || {};
  if (!logger || !hookClient) return;
  if (job.type === 'revoke_reply') {
    const atWxid = resolveSenderWxid(job);
    const atNick = normalizeNick(job.senderNick);
    let sendResult;
    if (job.groupId && atWxid && typeof hookClient.sendAtText === 'function') {
      const atPrefix = atNick ? `@${atNick} ` : '';
      sendResult = await hookClient.sendAtText(job.groupId, `${atPrefix}${job.message}`, atWxid);
    } else if (job.groupId && typeof hookClient.sendTextMsg === 'function') {
      sendResult = await hookClient.sendTextMsg(job.groupId, job.message);
    } else {
      sendResult = { ok: false, message: 'missing_send_api' };
    }
    if (sendResult.ok) {
      logger.info(
        `[revoke] auto replied room=${job.groupId} wxid=${atWxid || '-'} nick=${atNick || '-'}: ${replyLogPreview(job.message)}`
      );
    }
    else logger.warn(`[revoke] auto reply failed room=${job.groupId} error=${sendResult.message || 'unknown'}`);
    return;
  }

  if (job.type === 'text_reply') {
    if (job.groupId && typeof hookClient.sendTextMsg === 'function') {
      const sendResult = await hookClient.sendTextMsg(job.groupId, job.replyText);
      if (sendResult.ok) {
        logger.info(
          `[rule:${job.ruleName}] replied room=${job.groupId}: ${replyLogPreview(job.replyText)}`
        );
      } else {
        logger.warn(`[rule:${job.ruleName}] reply failed room=${job.groupId} error=${sendResult.message || 'unknown'}`);
        if (job.ruleName === 'group:whitelist_card' && db) {
          appendBotWorkLog(
            db,
            'warn',
            `群卡密回复发送失败：${sendResult.message || 'unknown'}`,
            JSON.stringify({ group_id: job.groupId, reply_preview: String(job.replyText || '').slice(0, 120) })
          );
        }
      }
      return;
    }
    if (job.targetWxid && typeof hookClient.sendTextMsg === 'function') {
      const sendResult = await hookClient.sendTextMsg(job.targetWxid, job.replyText);
      if (sendResult.ok) {
        logger.info(
          `[rule:${job.ruleName}] replied to ${job.targetWxid}: ${replyLogPreview(job.replyText)}`
        );
      }
      else logger.warn(`[rule:${job.ruleName}] reply failed target=${job.targetWxid} error=${sendResult.message || 'unknown'}`);
    }
    return;
  }

  if (job.type === 'file_reply') {
    const targetWxid = job.groupId || job.senderWxid;
    if (!targetWxid || typeof hookClient.sendFileMsg !== 'function') {
      logger.warn(`[rule:${job.ruleName}] send_file_msg unavailable, skip file sending`);
      return;
    }
    const atWxid = resolveSenderWxid(job);
    const atNick = normalizeNick(job.senderNick);
    if (job.groupId && atWxid && typeof hookClient.sendAtText === 'function') {
      const atPrefix = atNick ? `@${atNick} ` : '';
      const atTip = String(job.atTip || '请查收文件');
      const atResult = await hookClient.sendAtText(job.groupId, `${atPrefix}${atTip}`, atWxid);
      if (!atResult.ok) logger.warn(`[rule:${job.ruleName}] file-at tip failed room=${job.groupId} wxid=${atWxid} error=${atResult.message || 'unknown'}`);
    }
    let filePath = job.directFilePath || '';
    if (!filePath) filePath = generateReportCsv(db);
    const sendResult = await hookClient.sendFileMsg(targetWxid, filePath);
    if (sendResult.ok) logger.info(`[rule:${job.ruleName}] file sent target=${targetWxid} path=${filePath}`);
    else logger.warn(`[rule:${job.ruleName}] file send failed target=${targetWxid} path=${filePath} error=${sendResult.message || 'unknown'}`);
  }
}

function enqueueOutboundReply(job, logger) {
  if (!outboundQueue) {
    logger?.warn?.('[reply-queue] not initialized, drop outbound job');
    return;
  }
  const notBeforeMs = Date.now() + randomReplyDelayMs();
  outboundQueue.enqueue({ ...job, notBeforeMs });
}

function safeStringify(data) {
  try {
    return JSON.stringify(data);
  } catch {
    return '[unserializable_json]';
  }
}

function replyLogPreview(text, max = 160) {
  const s = String(text || '');
  if (s.length <= max) return s;
  return `${s.slice(0, max)}…[+${s.length - max}]`;
}

function buildAck(success, message = '') {
  const ackType = success ? 0x01 : 0x00;
  const ackBody = Buffer.from(
    JSON.stringify({
      type: 'ack',
      success,
      message,
      timestamp: Math.floor(Date.now() / 1000),
    }),
    'utf8'
  );
  const bodyLen = 1 + ackBody.length;
  const header = Buffer.alloc(4);
  header.writeUInt32BE(bodyLen, 0);
  return Buffer.concat([header, Buffer.from([ackType]), ackBody]);
}

function parseFrameBody(body) {
  const text = body.toString('utf8').trim();
  if (text.startsWith('{') || text.startsWith('[')) {
    return { msgType: 0x01, data: JSON.parse(text) };
  }
  const msgType = body[0];
  const jsonText = body.subarray(1).toString('utf8').trim();
  return { msgType, data: JSON.parse(jsonText) };
}

function logInboundResult(result, logger) {
  if (!result?.logLine) return;
  const level = result.logLevel || 'info';
  if (level === 'debug') {
    if (typeof logger.debug === 'function') logger.debug(result.logLine);
  } else {
    const logFn = typeof logger[level] === 'function' ? logger[level] : logger.info;
    logFn.call(logger, result.logLine);
  }
}

function wireTcpInboundSocket(socket, db, logger, hookClient, { sendAck = true, label = 'server' } = {}) {
  let buf = Buffer.alloc(0);
  let frameChain = Promise.resolve();

  const handleFrame = async (body) => {
    try {
      const parsed = parseFrameBody(body);
      if (parsed.data && typeof parsed.data === 'object') {
        parsed.data.__inboundChannel = 'tcp';
      }
      if (parsed.msgType === 0xff) {
        if (sendAck) socket.write(buildAck(true, 'pong'));
        return;
      }
      const result = await processMessage(parsed.data, db, logger, hookClient);
      if (sendAck) {
        try {
          socket.write(buildAck(true, 'Message processed'));
        } catch {
          /* socket closed */
        }
      }
      logInboundResult(result, logger);
    } catch (e) {
      logger.warn(`[TCP:${label}] frame error`, e.message);
      if (sendAck) {
        try {
          socket.write(buildAck(false, String(e.message)));
        } catch {
          /* ignore */
        }
      }
    }
  };

  socket.on('data', (chunk) => {
    buf = Buffer.concat([buf, chunk]);
    while (buf.length >= HEADER) {
      const len = buf.readUInt32BE(0);
      if (len > 10 * 1024 * 1024) {
        socket.destroy();
        return;
      }
      if (buf.length < HEADER + len) return;
      const body = buf.subarray(HEADER, HEADER + len);
      buf = buf.subarray(HEADER + len);
      frameChain = frameChain.then(() => handleFrame(body));
    }
  });

  socket.on('error', (e) => logger.warn(`[TCP:${label}] socket error`, e.message));
}

let tcpInboundClientStarted = false;

/** DLL 已占用 TCP 端口时：Node 作为客户端连上去收帧（仅 tcp/all 入站模式） */
function startTcpInboundClient({ host, port, db, logger, hookClient }) {
  if (tcpInboundClientStarted) return;
  tcpInboundClientStarted = true;

  const connectHost = host === '0.0.0.0' ? '127.0.0.1' : host;
  let retryMs = 2000;
  let reconnectTimer = null;
  let lastWarnAt = 0;

  const warnThrottled = (msg) => {
    const now = Date.now();
    if (now - lastWarnAt < 15_000) return;
    lastWarnAt = now;
    logger.warn(msg);
  };

  const scheduleReconnect = () => {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, retryMs);
    retryMs = Math.min(30_000, retryMs + 2000);
  };

  const connect = () => {
    const socket = net.connect({ host: connectHost, port }, () => {
      retryMs = 2000;
      logger.info(`[TCP] 客户端已连接 Hook ${connectHost}:${port}（DLL 监听模式）`);
      wireTcpInboundSocket(socket, db, logger, hookClient, { sendAck: true, label: 'client' });
    });
    socket.on('close', () => {
      warnThrottled(`[TCP] 与 Hook 的连接断开，${retryMs}ms 后重连…`);
      scheduleReconnect();
    });
    socket.on('error', (e) => {
      warnThrottled(`[TCP] 客户端连接 ${connectHost}:${port} 失败: ${e.message}`);
      scheduleReconnect();
    });
  };

  connect();
}

function initOutboundInboundContext(db, logger, hookClient) {
  outboundContext = { db, logger, hookClient };
  inboundDedupe = createInboundDedupe({
    ttlSec: Number(process.env.INBOUND_DEDUPE_TTL_SEC || 300),
  });
  outboundQueue = createLocalOutboundQueue({
    logger,
    randomGapMs: randomReplyDelayMs,
    executeJob: (task) => executeOutboundJob(task),
  });
  outboundQueue.startPoll();
}

export function startTcpGateway({ host, port, db, logger, hookClient }) {
  initOutboundInboundContext(db, logger, hookClient);

  const callbackUrl =
    process.env.HOOK_CALLBACK_URL ||
    `http://127.0.0.1:${Number(process.env.HTTP_PORT || 3000)}/api/recvMsg`;

  if (!hookReceiveUsesTcp()) {
    logger.info(
      `[入站] 模式=http，不连接 ${port}（群消息仅经 Hook HTTP 回调 ${callbackUrl}；61108 拒绝连接属正常）`
    );
    if (shouldLogAllGroupInbound()) {
      logger.info('[入站] 已开启群消息入站日志（info 级 [入站:群]；设 BOT_INBOUND_LOG_GROUP=0 可关闭）');
    }
    return null;
  }

  const server = net.createServer((socket) => {
    wireTcpInboundSocket(socket, db, logger, hookClient, { sendAck: true, label: 'server' });
  });

  server.on('error', (err) => {
    const code = err && err.code;
    if (code === 'EADDRINUSE') {
      logger.warn(`[TCP] 端口 ${port} 已被占用，改以 TCP 客户端连接 Hook 收消息`);
      startTcpInboundClient({ host, port, db, logger, hookClient });
      return;
    }
    logger.error('[TCP] listen error:', err?.message || err);
    process.exit(1);
  });

  server.listen(port, host, () => {
    logger.info(`TCP gateway listening ${host}:${port}`);
    if (INBOUND_COALESCE_MS > 0 && typeof logger.debug === 'function') {
      logger.debug(`TCP inbound coalesce ${INBOUND_COALESCE_MS}ms (group+sender+createTime)`);
    }
  });

  return server;
}

async function processMessage(obj, db, logger, hookClient) {
  syncWechatLoginFromHookPayload(db, obj);
  const ex = extractWechatFields(obj);
  bumpInboundRecvStats(db, ex);

  const inboundChannel = obj?.__inboundChannel === 'http' ? 'http' : 'tcp';
  const logGroupInbound = (skip) => {
    const noise = obj?.event_desc === 'tcpRespMessage' || Number(obj?.messageType) === 8;
    if (noise || skip === 'inbound_coalesce_buffer') return;
    logInboundGroupMessage({ ex, skipReason: skip, channel: inboundChannel }, logger);
  };

  const wxGidCard = ex.groupId || null;
  const senderCardRaw = resolveInboundSenderWxid(ex) || resolveSenderWxid(ex) || ex.senderWxid || '';
  const senderCard =
    senderCardRaw && !String(senderCardRaw).endsWith('@chatroom') ? senderCardRaw : '';
  const groupBound = wxGidCard ? isActiveWhitelistedGroup(db, wxGidCard) : false;
  const cardText = getGroupCardInboundText(obj, ex) || String(ex.content || '').trim();
  const whitelistJoinIntent = isWhitelistJoinMessage(cardText);
  const standaloneHex = isStandaloneGroupCardHex(cardText);
  const cardContentForRedeem =
    standaloneHex && !whitelistJoinIntent ? `加入白名单${standaloneHex}` : cardText;
  const allowCardOnGroup =
    wxGidCard &&
    (groupBound || whitelistJoinIntent || standaloneHex) &&
    (senderCard || whitelistJoinIntent || standaloneHex);
  if (
    !wxGidCard &&
    (whitelistJoinIntent || standaloneHex || parseGroupCardMessage(cardContentForRedeem))
  ) {
    logger?.warn?.(
      `[group-card] 已识别卡密文案但未解析到群 ID（请检查 Hook 报文 fromUserName/toUserName）：from=${String(obj?.fromUserName || '').slice(0, 40)} to=${String(obj?.toUserName || '').slice(0, 40)}`
    );
    appendBotWorkLog(
      db,
      'warn',
      '加入白名单/卡密消息未解析到群 chatroom_id，无法核销。请确认 Hook 回调正常。',
      JSON.stringify({
        fromUserName: obj?.fromUserName,
        toUserName: obj?.toUserName,
        recive_type: obj?.recive_type || obj?.receive_type,
      }).slice(0, 2000)
    );
  }
  if (allowCardOnGroup) {
    const pem = loadActivationPublicPem();
    const cardSecret = getActivationCardSecret();
    if (pem || cardSecret) {
      let cardHit = null;
      try {
        cardHit = await tryRedeemGroupCardMessage({
          db,
          wxGroupId: wxGidCard,
          senderWxid: senderCard,
          content: cardContentForRedeem,
          publicKeyPem: pem || null,
          hookClient,
          mutate: true,
          logger,
        });
      } catch (e) {
        logger?.warn?.(`[group-card] redeem failed group=${wxGidCard}: ${e?.message || e}`);
        cardHit = { replyText: `卡密核销失败：${e?.message || 'internal_error'}。请稍后重试或联系管理员。` };
      }
      if (!cardHit && (whitelistJoinIntent || standaloneHex) && groupBound) {
        cardHit = {
          replyText:
            '未能识别卡密内容。请在一行内发送：加入白名单+32位卡密（不要分两条消息）。',
        };
      }
      const cardReplyOk =
        cardHit &&
        (groupBound ||
          /群已绑定并开通|已续期|续期约|已开通约/u.test(String(cardHit.replyText || '')));
      if (cardReplyOk) {
        await enqueueOutboundReply(
          {
            type: 'text_reply',
            groupId: ex.groupId,
            senderWxid: ex.senderWxid,
            senderNick: ex.senderNick,
            originalContent: ex.originalContent,
            targetWxid: ex.groupId || ex.senderWxid,
            replyText: cardHit.replyText,
            ruleName: 'group:whitelist_card',
          },
          logger
        );
        const isHookRespNoiseEarly = obj?.event_desc === 'tcpRespMessage' || Number(obj?.messageType) === 8;
        const isEmptyAuditEarly = !ex.groupId && !ex.senderWxid && !(ex.content || '').slice(0, 40);
        if (!isHookRespNoiseEarly && !isEmptyAuditEarly) {
          recordInboundWorkSummary(db, ex, 'group_whitelist_card', []);
          db.prepare(
            `INSERT INTO message_audit (wx_group_id, sender_wxid, content_preview, raw_json, rule_hits)
             VALUES (?,?,?,?,?)`
          ).run(
            ex.groupId || null,
            ex.senderWxid || null,
            (ex.content || '').slice(0, 200),
            JSON.stringify(obj).slice(0, 8000),
            JSON.stringify({ hits: [], skip: 'group_whitelist_card' })
          );
        }
        const preview = (ex.content || '').slice(0, 40);
        logGroupInbound('group_whitelist_card');
        return {
          logLevel: 'info',
          logLine: `TCP msg sender_wxid=${ex.senderWxid || '-'} group=${ex.groupId || '-'} content='${preview}' group_whitelist_card`,
        };
      }
    } else if (parseGroupCardMessage(cardContentForRedeem)) {
      await enqueueOutboundReply(
        {
          type: 'text_reply',
          groupId: ex.groupId,
          senderWxid: ex.senderWxid,
          senderNick: ex.senderNick,
          originalContent: ex.originalContent,
          targetWxid: ex.groupId || ex.senderWxid,
          replyText:
            '服务端未配置 ACTIVATION_CARD_SECRET 或激活公钥（ACTIVATION_PUBLIC_KEY_PATH），无法核销卡密。',
          ruleName: 'group:whitelist_card_no_keys',
        },
        logger
      );
      logGroupInbound('group:whitelist_card_no_keys');
      return {
        logLevel: 'warn',
        logLine: `TCP msg group=${wxGidCard} whitelist_card_no_activation_keys`,
      };
    }
  }

  const wxGidDraw = ex.groupId || null;
  const senderDraw = resolveInboundSenderWxid(ex) || resolveSenderWxid(ex) || ex.senderWxid || '';
  const drawText = String(ex.content || '').trim();
  if (groupBound && wxGidDraw && senderDraw && drawText && matchesDrawCommandLine(drawText, db)) {
    const drawHit = maybeHandleDrawCommand(db, wxGidDraw, senderDraw, drawText, { mutate: true });
    if (drawHit?.replyText) {
      await enqueueOutboundReply(
        {
          type: 'text_reply',
          groupId: ex.groupId,
          senderWxid: ex.senderWxid,
          senderNick: ex.senderNick,
          originalContent: ex.originalContent,
          targetWxid: ex.groupId || ex.senderWxid,
          replyText: drawHit.replyText,
          ruleName: 'group:draw',
        },
        logger
      );
      const isHookRespNoiseDraw = obj?.event_desc === 'tcpRespMessage' || Number(obj?.messageType) === 8;
      const isEmptyAuditDraw = !ex.groupId && !ex.senderWxid && !(ex.content || '').slice(0, 40);
      if (!isHookRespNoiseDraw && !isEmptyAuditDraw) {
        recordInboundWorkSummary(db, ex, 'group_draw', []);
        db.prepare(
          `INSERT INTO message_audit (wx_group_id, sender_wxid, content_preview, raw_json, rule_hits)
           VALUES (?,?,?,?,?)`
        ).run(
          ex.groupId || null,
          ex.senderWxid || null,
          (ex.content || '').slice(0, 200),
          JSON.stringify(obj).slice(0, 8000),
          JSON.stringify({ hits: [], skip: 'group_draw' })
        );
      }
      const previewDraw = drawText.slice(0, 40);
      logGroupInbound('group_draw');
      return {
        logLevel: 'info',
        logLine: `TCP msg sender_wxid=${ex.senderWxid || '-'} group=${ex.groupId || '-'} content='${previewDraw}' group_draw`,
      };
    }
  }

  if (wxGidCard && !groupBound && !isWhitelistJoinMessage(cardText) && !standaloneHex) {
    logGroupInbound('unbound_whitelist_join_only');
    return {
      logLevel: 'debug',
      logLine: `TCP msg group=${wxGidCard} unbound_whitelist_join_only`,
    };
  }

  if (groupBound && wxGidCard && hookClient) {
    try {
      const cacheRow = db
        .prepare(`SELECT nick_name, member_count FROM wx_chatroom_cache WHERE room_id = ?`)
        .get(wxGidCard);
      const displayName = resolveChatroomDisplayName(db, wxGidCard);
      const needSync =
        !String(cacheRow?.nick_name || '').trim() ||
        Number(cacheRow?.member_count || 0) < 1 ||
        isPlaceholderGroupDisplayName(wxGidCard, displayName);
      if (needSync) {
        void (async () => {
          await syncChatroomNickFromHookList(db, hookClient, wxGidCard);
          await syncChatroomMembersFromHook(db, hookClient, wxGidCard);
          syncGroupDisplayMetaFromCache(db, wxGidCard);
          if (typeof db.persist === 'function') db.persist();
        })().catch(() => {});
      }
    } catch {
      /* cache 表可能未迁移 */
    }
  }

  if (!getBotInboundEnabled(db)) {
    const wxGidEarly = ex.groupId || null;
    const textEarly = String(ex.content || '').trim();
    if (wxGidEarly && textEarly && isActiveWhitelistedGroup(db, wxGidEarly)) {
      const g0 = db
        .prepare('SELECT id FROM wx_groups WHERE wx_group_id = ? AND is_active = 1')
        .get(wxGidEarly);
      if (g0) {
        appendBotWorkLog(
          db,
          'warn',
          `已停止，忽略群消息：${textEarly.slice(0, 120)}`,
          JSON.stringify({ wx_group_id: wxGidEarly })
        );
      }
    }
    logGroupInbound('bot_inbound_disabled');
    return { logLevel: 'debug', logLine: 'bot inbound disabled' };
  }

  if (!isRobotLicenseValid(db)) {
    const wxGidEarly = ex.groupId || null;
    const textEarly = String(ex.content || '').trim();
    if (wxGidEarly && textEarly) {
      appendBotWorkLog(
        db,
        'warn',
        `主授权已过期，忽略群消息：${textEarly.slice(0, 120)}`,
        JSON.stringify({ wx_group_id: wxGidEarly })
      );
    }
    return { logLevel: 'debug', logLine: 'robot license expired' };
  }

  const wxGid = ex.groupId || null;
  let ruleHits = [];
  let commandResult = null;
  let pipelineRoute = null;
  let skipReason = null;
  const isRevokeEvent =
    Number(ex.eventType) === 2001 ||
    Number(ex.msgType) === 10002 ||
    obj?.revoke_hit === true ||
    String(obj?.recive_type || '').includes('撤回');

  if (inboundDedupe) {
    const dedupeText = buildDedupeKey(obj, ex);
    if (dedupeText && !inboundDedupe.tryAcquire(dedupeText)) {
      skipReason = 'duplicate_message';
    }
  }

  if (!skipReason && wxGid && INBOUND_COALESCE_MS > 0 && !obj?.__skipInboundCoalesce && !isRevokeEvent) {
    const ct = Number(obj?.createTime);
    if (Number.isFinite(ct) && ct > 0) {
      const senderForCoalesce = resolveSenderWxid(ex) || ex.senderWxid || '';
      if (senderForCoalesce) {
        const gQuick = db
          .prepare('SELECT id FROM wx_groups WHERE wx_group_id = ? AND is_active = 1')
          .get(wxGid);
        if (gQuick) {
          const ckey = `${wxGid}::${senderForCoalesce}::${ct}`;
          let bucket = inboundCoalesceBuckets.get(ckey);
          if (!bucket) bucket = { objs: [], contents: [], originals: [], timerId: null };
          bucket.objs.push(obj);
          bucket.contents.push(String(ex.content || '').trim());
          bucket.originals.push(String(ex.originalContent || '').trim());
          if (bucket.timerId) clearTimeout(bucket.timerId);
          const tid = setTimeout(() => {
            const cur = inboundCoalesceBuckets.get(ckey);
            if (!cur || cur.timerId !== tid) return;
            inboundCoalesceBuckets.delete(ckey);
            const { objs: ob, contents: cb, originals: obo } = cur;
            if (!ob?.length) return;
            const mergedPayload = mergeHookPayloadsForCoalesce(ob, cb, obo);
            processMessage(mergedPayload, db, logger, hookClient).catch((e) =>
              logger.warn(`[inbound-coalesce] flush failed: ${e.message || 'unknown'}`)
            );
          }, INBOUND_COALESCE_MS);
          bucket.timerId = tid;
          inboundCoalesceBuckets.set(ckey, bucket);
          skipReason = 'inbound_coalesce_buffer';
        }
      }
    }
  }

  if (!skipReason && wxGid) {
    const gidNorm = normalizeChatroomId(wxGid) || wxGid;
    const group = db
      .prepare('SELECT * FROM wx_groups WHERE wx_group_id = ? AND is_active = 1')
      .get(gidNorm);
    if (!group) {
      skipReason = 'unknown_group';
    } else if (!isGroupServiceValid(db, wxGid)) {
      skipReason = 'expired_group';
      const hintText = String(ex.content || '').trim();
      if (hintText && !isWeChatNonTextInbound(obj, hintText)) {
        await enqueueOutboundReply(
          {
            type: 'text_reply',
            groupId: ex.groupId,
            senderWxid: ex.senderWxid,
            senderNick: ex.senderNick,
            originalContent: ex.originalContent,
            targetWxid: ex.groupId || ex.senderWxid,
            replyText: '本群服务已过期，请使用「续费+卡密」或联系管理员续期后再下单/使用功能指令。',
            ruleName: 'group:expired',
          },
          logger
        );
      }
    }

    // 完整 JSON 仅 debug，避免终端刷屏；需要时可 DEBUG=1 或 BOT_INBOUND_LOG_VERBOSE=1（摘要行）
    if (group && typeof logger.debug === 'function') {
      logger.debug?.(`[raw:bound_group] group=${wxGid}`, hookRawPayloadSummary(obj));
    }

    if (!skipReason && isRevokeEvent) {
      const senderWxid = resolveSenderWxid(ex) || ex.senderWxid || '';
      const mergeKey = `${wxGid}::${senderWxid}`;
      await flushOrderMerge(mergeKey, logger);
      const revokedIds = extractRevokedWxMessageIds(obj);
      const message = revokeOrdersForWxMessage(db, {
        wxGroupId: ex.groupId,
        senderWxid,
        wxMsgId: revokedIds.msgId,
        wxNewMsgId: revokedIds.newMsgId,
      });
      if (message) {
        await enqueueOutboundReply(
          {
            type: 'revoke_reply',
            groupId: ex.groupId,
            senderWxid: ex.senderWxid,
            senderNick: ex.senderNick,
            originalContent: ex.originalContent,
            message,
          },
          logger
        );
      }
      skipReason = 'revoke_event_handled';
    }

    if (!skipReason) {
      const senderWxid = resolveSenderWxid(ex) || ex.senderWxid || '';
      const mergeKey = `${wxGid}::${senderWxid}`;
      const inboundResolved = await resolveInboundOrderText(obj, ex, hookClient, logger);
      let orderText = ex.content;
      if (inboundResolved.kind === 'file_unresolved') {
        const title = String(inboundResolved.fileInfo?.title || '附件').trim();
        await enqueueOutboundReply(
          {
            type: 'text_reply',
            groupId: ex.groupId,
            senderWxid: ex.senderWxid,
            senderNick: ex.senderNick,
            originalContent: ex.originalContent,
            targetWxid: ex.groupId || ex.senderWxid,
            replyText: `已收到文件「${title}」，暂无法自动读取内容，请直接粘贴文本或重新发送纯文本下单。`,
            ruleName: 'inbound:file_unresolved',
          },
          logger
        );
        skipReason = 'file_attachment_unresolved';
      } else if (inboundResolved.kind === 'unsupported_appmsg') {
        skipReason = 'unsupported_appmsg';
      } else if (inboundResolved.kind === 'non_text') {
        skipReason = 'non_text';
      } else if (inboundResolved.text != null && String(inboundResolved.text).trim()) {
        orderText = String(inboundResolved.text).trim();
        if (inboundResolved.kind !== 'plain') {
          logger.info(
            `[inbound-file] resolved kind=${inboundResolved.kind} title=${inboundResolved.fileInfo?.title || '-'} len=${orderText.length}`
          );
        }
      }
      if (!skipReason) {
        pipelineRoute = classifyInboundForPipeline(orderText, {
          db,
          isInstruction: (t) => matchesInstructionOnlyLine(t, db),
        });
        if (pipelineRoute === 'drop') {
          skipReason = 'casual_chat';
        } else {
          commandResult = executeConfiguredCommand(db, wxGid, orderText, {
            senderWxid,
            wxMsgId: obj?.msgId != null ? String(obj.msgId) : '',
            wxNewMsgId: obj?.newMsgId != null ? String(obj.newMsgId) : '',
          });
        }
      }
      if (commandResult) {
        const replyText = commandResult.replyText;
        const job = {
          type: 'text_reply',
          groupId: ex.groupId,
          senderWxid,
          senderNick: ex.senderNick,
          originalContent: ex.originalContent,
          targetWxid: ex.groupId || ex.senderWxid,
          replyText,
          ruleName: `cmd:${cmdRouteDisplayLabel(commandResult.route)}`,
        };
        if (mergeableCmdReply(replyText) && ORDER_REPLY_MERGE_MS > 0) {
          scheduleMergedCommandReply(job, logger);
        } else {
          await flushOrderMerge(mergeKey, logger);
          await enqueueOutboundReply(job, logger);
        }
        skipReason = 'command_route_handled';
      }
    }

    // ---- 插件消息处理器 ----
    if (!skipReason && wxGid && orderText) {
      const senderWxid = resolveSenderWxid(ex) || ex.senderWxid || '';
      const senderNick = ex.senderNick || '';
      const pluginHandlers = pluginManager.getHandlers('inboundMessage');
      for (const handler of pluginHandlers) {
        try {
          const ctx = { db, logger, hookClient };
          const pluginReply = await handler(ctx, orderText, senderWxid, senderNick);
          if (pluginReply) {
            await enqueueOutboundReply(
              {
                type: 'text_reply',
                groupId: ex.groupId,
                senderWxid,
                senderNick,
                originalContent: ex.originalContent,
                targetWxid: ex.groupId || senderWxid,
                replyText: pluginReply,
                ruleName: 'plugin:handler',
              },
              logger
            );
            skipReason = 'plugin_handled';
            logger.info(`[plugin] replied room=${ex.groupId}: ${pluginReply.slice(0, 80)}`);
            break;
          }
        } catch (e) {
          logger.error(`[plugin] handler error: ${e.message}`);
        }
      }
    }

    if (!skipReason) {
      const rules = db
        .prepare(
          `SELECT * FROM custom_rules
           WHERE is_active = 1
             AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
           ORDER BY priority DESC`
        )
        .all();
      ruleHits = evaluateRules(rules, ex.content);
      for (const hit of ruleHits) {
        const r = db.prepare('SELECT * FROM custom_rules WHERE id = ?').get(hit.ruleId);
        if (!r) continue;
        const action = parseActionJson(r.action_json);
        const shouldSendReport = action.send_report === true || action.report === true;
        const directFilePath = String(action.filepath || action.file_path || '').trim();

        if (action.reply_text) {
          const replyText = String(action.reply_text);
          await enqueueOutboundReply(
            {
              type: 'text_reply',
              groupId: ex.groupId,
              senderWxid: ex.senderWxid,
              senderNick: ex.senderNick,
              originalContent: ex.originalContent,
              targetWxid: ex.groupId || ex.senderWxid,
              replyText,
              ruleName: r.name,
            },
            logger
          );
        }

        if (shouldSendReport || directFilePath) {
          await enqueueOutboundReply(
            {
              type: 'file_reply',
              groupId: ex.groupId,
              senderWxid: ex.senderWxid,
              senderNick: ex.senderNick,
              originalContent: ex.originalContent,
              ruleName: r.name,
              directFilePath,
              atTip: String(action.file_at_text || action.report_at_text || '请查收文件'),
            },
            logger
          );
        }
      }
      if (!commandResult && ruleHits.length === 0 && pipelineRoute === 'order') {
        const raw = String(ex.content || '').trim();
        if (raw && !isWeChatNonTextInbound(obj, raw)) {
          let replyText =
            buildInboundOrderParseFailureReply(db, wxGid, ex.content) ||
            buildUnrecognizedInboundMessageReply(ex.senderNick, ex.content, db);
          if (isGroupDebugRuleMissReplyEnabled(db, wxGid)) {
            const rulePart = buildRuleMissDebugReplyText(rules, ruleHits);
            const orderPart = buildInboundOrderMissDebugText(db, ex.content);
            const extra = [rulePart, orderPart].filter(Boolean).join('\n\n');
            if (extra) replyText = `${replyText}\n\n${extra}`;
          }
          await enqueueOutboundReply(
            {
              type: 'text_reply',
              groupId: ex.groupId,
              senderWxid: ex.senderWxid,
              senderNick: ex.senderNick,
              originalContent: ex.originalContent,
              targetWxid: ex.groupId || ex.senderWxid,
              replyText,
              ruleName: 'inbound:unrecognized',
            },
            logger
          );
          skipReason = 'unrecognized_inbound';
        }
      }
    }
  } else if (!skipReason) {
    const senderWxid = resolveSenderWxid(ex) || ex.senderWxid || '';
    if (parsePrivateHelpCommand(ex.content, db)) {
      await enqueueOutboundReply(
        {
          type: 'text_reply',
          senderWxid,
          targetWxid: senderWxid,
          replyText: buildPrivateHelpText(),
          ruleName: 'private:help',
        },
        logger
      );
      skipReason = 'private_help_handled';
      appendBotWorkLog(
        db,
        'info',
        `[private_help_handled] wxid=${senderWxid || '-'}`,
        null
      );
      return { logLevel: 'info', logLine: `TCP private help handled sender=${senderWxid || '-'}` };
    }
    const cmd = parsePrivateReportCommand(ex.content);
    if (cmd) {
      if (cmd.error) {
        await enqueueOutboundReply(
          {
            type: 'text_reply',
            senderWxid,
            targetWxid: senderWxid,
            replyText: cmd.error,
            ruleName: 'private:order-report',
          },
          logger
        );
        skipReason = 'private_report_invalid_command';
      } else {
        const normalized = normalizeChannelCategoryByRoutes(db, cmd.channelWord, cmd.categoryWord);
        cmd.channelWord = normalized.channelWord;
        cmd.categoryWord = normalized.categoryWord;
        const groupIds = getOwnedBoundGroups(db, senderWxid);
        if (groupIds.length === 0) {
          await enqueueOutboundReply(
            {
              type: 'text_reply',
              senderWxid,
              targetWxid: senderWxid,
              replyText: '暂无已绑定群，无法生成报表',
              ruleName: 'private:order-report',
            },
            logger
          );
          skipReason = 'private_report_no_owned_group';
        } else {
          const settlementDate = resolveReportSettlementDate(
            db,
            groupIds,
            cmd.channelWord,
            cmd.categoryWord,
            cmd.date
          );
          if (!settlementDate) {
            await enqueueOutboundReply(
              {
                type: 'text_reply',
                senderWxid,
                targetWxid: senderWxid,
                replyText: `未找到渠道「${cmd.channelWord}」${cmd.categoryWord ? `分类「${cmd.categoryWord}」` : ''}的订单数据`,
                ruleName: 'private:order-report',
              },
              logger
            );
            skipReason = 'private_report_no_orders';
          } else {
            const built = buildOrderReportWorkbook(db, {
              groupIds,
              channelWord: cmd.channelWord,
              categoryWord: cmd.categoryWord,
              mode: cmd.mode || '按号',
              settlementDate,
            });
            await enqueueOutboundReply(
              {
                type: 'text_reply',
                senderWxid,
                targetWxid: senderWxid,
                replyText: `报表已生成：渠道=${cmd.channelWord}，分类=${cmd.categoryWord || '全部'}，方式=${cmd.mode || '按号'}，期号=${settlementDate}，记录=${built.rowCount}`,
                ruleName: 'private:order-report',
              },
              logger
            );
            await enqueueOutboundReply(
              {
                type: 'file_reply',
                senderWxid,
                targetWxid: senderWxid,
                ruleName: 'private:order-report',
                directFilePath: built.filePath,
              },
              logger
            );
            skipReason = 'private_report_handled';
          }
        }
      }
    } else {
      // 私聊消息 - 插件老板指令处理
      const senderWxid = resolveSenderWxid(ex) || ex.senderWxid || '';
      const pluginBossHandlers = pluginManager.getHandlers('bossCommand');
      for (const handler of pluginBossHandlers) {
        try {
          const ctx = { db, logger, hookClient };
          const pluginReply = await handler(ctx, ex.content);
          if (pluginReply) {
            await enqueueOutboundReply(
              {
                type: 'text_reply',
                senderWxid,
                targetWxid: senderWxid,
                replyText: pluginReply,
                ruleName: 'plugin:boss',
              },
              logger
            );
            skipReason = 'plugin_boss_handled';
            logger.info(`[plugin-boss] replied to ${senderWxid}: ${pluginReply.slice(0, 80)}`);
            break;
          }
        } catch (e) {
          logger.error(`[plugin] boss handler error: ${e.message}`);
        }
      }
      if (!skipReason) {
        skipReason = 'no_group_id_private_or_empty';
      }
    }
  }

  const contentPreview = (ex.content || '').slice(0, 120);
  const isHookRespNoise = obj?.event_desc === 'tcpRespMessage' || Number(obj?.messageType) === 8;
  const isEmptyAuditPayload = !ex.groupId && !ex.senderWxid && !contentPreview;
  if (ex.groupId && /@chatroom/i.test(ex.groupId) && !isHookRespNoise && skipReason !== 'inbound_coalesce_buffer') {
    logGroupInbound(skipReason);
  }
  if (!isHookRespNoise && !isEmptyAuditPayload && skipReason !== 'inbound_coalesce_buffer') {
    recordInboundWorkSummary(db, ex, skipReason, ruleHits);
    db.prepare(
      `INSERT INTO message_audit (wx_group_id, sender_wxid, content_preview, raw_json, rule_hits)
       VALUES (?,?,?,?,?)`
    ).run(
      ex.groupId || null,
      ex.senderWxid || null,
      (ex.content || '').slice(0, 200),
      JSON.stringify(obj).slice(0, 8000),
      JSON.stringify({ hits: ruleHits, skip: skipReason })
    );
  }

  const logLine = `TCP msg sender_wxid=${ex.senderWxid || '-'} group=${ex.groupId || '-'} content='${contentPreview}' event=${ex.eventType} skip=${skipReason || '-'}`;
  const isGroupMsg = Boolean(ex.groupId && /@chatroom/i.test(ex.groupId));
  const inboundLogLevel =
    INBOUND_LOG_VERBOSE || (isGroupMsg && shouldLogAllGroupInbound()) ? 'info' : 'debug';

  // 注入刚启动时会有大量空帧/无业务意义帧，默认不打 info，避免刷屏。
  if (skipReason === 'no_group_id_private_or_empty' && !contentPreview && ex.eventType == null) {
    return { logLevel: 'debug', logLine: null };
  }
  if (skipReason) {
    return { logLevel: inboundLogLevel, logLine };
  }
  return { logLevel: inboundLogLevel, logLine };
}

const INBOUND_LAST_KEY = 'inbound_last_recv_at';
const INBOUND_COUNT_KEY = 'inbound_recv_count';

function bumpInboundRecvStats(db, ex) {
  if (!db || !ex?.groupId) return;
  const preview = String(ex.content || '').trim();
  if (!preview) return;
  try {
    const now = new Date().toISOString();
    const upsert = (key, value) => {
      const row = db.prepare('SELECT key FROM app_settings WHERE key = ?').get(key);
      if (row) {
        db.prepare(`UPDATE app_settings SET value = ?, updated_at = datetime('now') WHERE key = ?`).run(
          value,
          key
        );
      } else {
        db.prepare(`INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`).run(
          key,
          value
        );
      }
    };
    upsert(INBOUND_LAST_KEY, now);
    const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(INBOUND_COUNT_KEY);
    const n = Math.max(0, Number(row?.value || 0)) + 1;
    upsert(INBOUND_COUNT_KEY, String(n));
  } catch {
    /* app_settings 可能未就绪 */
  }
}

/** HTTP Hook 回调与 TCP 帧共用同一套入站处理逻辑 */
export async function dispatchInboundMessage(obj, { db, logger, hookClient }) {
  if (obj && typeof obj === 'object') {
    obj.__inboundChannel = 'http';
  }
  return processMessage(obj, db, logger, hookClient);
}

export function getInboundRecvStats(db) {
  try {
    const last = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(INBOUND_LAST_KEY);
    const cnt = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(INBOUND_COUNT_KEY);
    return {
      inbound_last_recv_at: last?.value != null ? String(last.value) : null,
      inbound_recv_count: Math.max(0, Number(cnt?.value || 0)),
    };
  } catch {
    return { inbound_last_recv_at: null, inbound_recv_count: 0 };
  }
}
