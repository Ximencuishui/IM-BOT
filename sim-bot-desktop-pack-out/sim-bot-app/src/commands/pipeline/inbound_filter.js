/** PRD 3.1 入站过滤：数字标量 / 下单意图判定（各/元 别名来自 DB） */
import {
  listEachAlgoAliasWords,
  listSetAmountUnitSuffixWords,
} from '../alias_resolver.js';

export const INBOUND_ORDER_CN_AMOUNT_CLASS =
  '零○〇一二三四五六七八九十百千万兠两俩贰叁肆伍陆柒捌玖拾佰仟負';

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function inboundTextHasOrderDigits(s, db = null) {
  const t = String(s || '');
  if (/\d/.test(t)) return true;
  const eachWords = listEachAlgoAliasWords(db);
  for (const w of eachWords) {
    if (new RegExp(`${escapeRegExp(w)}\\s*[${INBOUND_ORDER_CN_AMOUNT_CLASS}]`, 'u').test(t)) {
      return true;
    }
  }
  const unitSuffix = listSetAmountUnitSuffixWords(db)
    .map(escapeRegExp)
    .filter(Boolean);
  if (unitSuffix.length) {
    const alt = unitSuffix.join('|');
    if (new RegExp(`[${INBOUND_ORDER_CN_AMOUNT_CLASS}]+\\s*(?:${alt})`, 'u').test(t)) {
      return true;
    }
  }
  return false;
}

/** 渠道+开+号码 / 开+特码：无「各」也须走指令，勿被 pipeline 当闲聊丢弃 */
export function looksLikeDrawCommandLine(s) {
  const t = String(s || '').trim();
  if (!t.includes('开')) return false;
  if (/^开\s*(?:0?[1-9]|[1-4][0-9])\s*号?\s*$/u.test(t)) return true;
  const m = t.match(/^(.+?)开([\s\S]+)$/u);
  if (!m) return false;
  return /\d/.test(String(m[2] || ''));
}

const INBOUND_ZODIAC_CLASS = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';

/**
 * 特码等：球号 + 空格 + 金额 + 可选金额单位（如 10 100A、06 50元），可无「各」。
 * 入站 pipeline 须识别，否则会当闲聊丢弃且无回执。
 */
function looksLikeBareBallAmountOrderLine(t, db = null) {
  const units = listSetAmountUnitSuffixWords(db)
    .map(escapeRegExp)
    .filter(Boolean);
  const unitAlt = units.length ? `(?:${units.join('|')})` : '(?:元|块|米|斤|蒙|A|a)?';
  const ball = '(?:0?[1-9]|[1-4][0-9])';
  const amt = '\\d+(?:\\.\\d+)?';
  const oneBall = new RegExp(`^${ball}\\s+${amt}${unitAlt}\\s*$`, 'iu');
  const multiBallTail = new RegExp(
    `^(?:${ball}(?:[\\s./、,，]+${ball})*)\\s+${amt}${unitAlt}\\s*$`,
    'iu'
  );
  for (const ln of String(t || '').split(/\r?\n+/)) {
    const line = String(ln || '').trim();
    if (!line) continue;
    if (oneBall.test(line) || multiBallTail.test(line)) return true;
  }
  return false;
}

/** 连肖/平特连肖 + 生肖串 + 金额（可无「各」，与引擎预处理一致） */
function looksLikeLianXiaoZodiacAmountLine(t) {
  const s = String(t || '').trim();
  if (!s) return false;
  if (!/(?:[二三四五]?连肖|连肖|平特三连)/u.test(s)) return false;
  if (!new RegExp(`[${INBOUND_ZODIAC_CLASS}]{2,}`).test(s)) return false;
  return (
    /\d/.test(s) ||
    new RegExp(`[${INBOUND_ZODIAC_CLASS}]+\\s*(?:\\d+|[${INBOUND_ORDER_CN_AMOUNT_CLASS}]+)`, 'u').test(s)
  );
}

/**
 * 01.100元、1.100、龙100、特肖龙100：点分球号+金额或生肖行末金额，可无「各」。
 * 与 engine 预处理 normalizeBallDotChineseYuanAmount / normalizeChainedZodiacBareAmountPass 对齐。
 */
function looksLikeBallDotOrZodiacAmountLine(t, db = null) {
  const units = listSetAmountUnitSuffixWords(db)
    .map(escapeRegExp)
    .filter(Boolean);
  const unitAlt = units.length ? `(?:${units.join('|')})` : '(?:元|块|米|斤|蒙|A|a)?';
  const ball = '(?:0?[1-9]|[1-4][0-9])';
  const cn = INBOUND_ORDER_CN_AMOUNT_CLASS;
  const amtPart = `(?:\\d{2,}|[${cn}]+)`;
  const ballDot = new RegExp(`^${ball}\\.${amtPart}${unitAlt}?\\s*$`, 'iu');
  const zodiacAmt = new RegExp(`^[${INBOUND_ZODIAC_CLASS}]${amtPart}${unitAlt}?\\s*$`, 'iu');
  const playZodiac = new RegExp(
    `^(?:特肖马|特肖|平特)[${INBOUND_ZODIAC_CLASS}]${amtPart}${unitAlt}?\\s*$`,
    'iu'
  );
  for (const ln of String(t || '').split(/\r?\n+/)) {
    const line = String(ln || '').trim();
    if (!line) continue;
    if (ballDot.test(line) || zodiacAmt.test(line) || playZodiac.test(line)) return true;
  }
  return false;
}

export function looksLikeInboundOrderAttempt(s, db = null) {
  const t = String(s || '').trim();
  if (looksLikeDrawCommandLine(t)) return false;
  if (!t || !inboundTextHasOrderDigits(t, db)) return false;
  if (/<appmsg\b/i.test(t) && (t.includes('<?xml') || /<msg\b/i.test(t))) return false;
  if (/<msg>\s*<emoji\b/i.test(t) || (/<emoji\b/i.test(t) && /<\/emoji>/i.test(t))) return false;
  if (looksLikeBareBallAmountOrderLine(t, db)) return true;
  if (looksLikeBallDotOrZodiacAmountLine(t, db)) return true;
  const eachWords = listEachAlgoAliasWords(db).sort((a, b) => b.length - a.length);
  for (const w of eachWords) {
    if (w && t.includes(w)) return true;
  }
  for (const ln of t.split(/\r?\n+/)) {
    if (looksLikeLianXiaoZodiacAmountLine(ln)) return true;
  }
  return looksLikeLianXiaoZodiacAmountLine(t);
}

export function isWeChatInboundFileXmlQuick(text) {
  const s = String(text || '');
  if (!/<appmsg\b/i.test(s)) return false;
  return /<type>\s*6\s*<\/type>/i.test(s);
}
