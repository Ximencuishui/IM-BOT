/**
 * 金额尾解析：支持阿拉伯、中文整数（如 五、六百、一千）、1千/2 万 等简写；
 * 尾缀与文中噪声字符支持「元/块/米/蒙/A」等（内置 + 后台扩展同义词）。
 */

const CN_DIGIT = (() => {
  const o = { 零: 0, 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, '○': 0, '〇': 0, 两: 2, 俩: 2, 贰: 2 };
  return (c) => (Object.prototype.hasOwnProperty.call(o, c) ? o[c] : -1);
})();

/** 无库时的兜底尾缀；正常运行时由 alias_config SET（别名中心）经 engine 注入 */
const BUILTIN_AMOUNT_UNITS = ['元', '块', '整', '角', '分', '米', '蒙', 'A', 'a', '斤'];

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function mergedUnitTokens(extraSynonyms = []) {
  const extra = Array.isArray(extraSynonyms) ? extraSynonyms : [];
  const raw = [...BUILTIN_AMOUNT_UNITS, ...extra.map((x) => String(x || '').trim()).filter(Boolean)];
  const seen = new Set();
  const out = [];
  for (const x of raw) {
    const s = String(x || '').trim();
    if (!s) continue;
    const k = s.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(s);
  }
  return out.sort((a, b) => b.length - a.length);
}

function stripTrailingUnits(s, extraSynonyms = []) {
  const tokens = mergedUnitTokens(extraSynonyms);
  if (tokens.length === 0) return String(s || '').trim();
  const re = new RegExp(`(?:${tokens.map(escapeRe).join('|')})+$`, 'gi');
  return String(s || '').trim().replace(re, '').trimEnd();
}

/** 连续剥尾单位（如 五A澳 → 先 A 再 澳若也在单位表） */
function stripTrailingUnitsLoop(s, extraSynonyms = []) {
  let t = String(s || '').trim();
  let prev;
  do {
    prev = t;
    t = stripTrailingUnits(t, extraSynonyms);
  } while (t !== prev);
  return t.trimEnd();
}

function removeInteriorUnits(s, extraSynonyms = []) {
  const tokens = mergedUnitTokens(extraSynonyms);
  if (tokens.length === 0) return String(s || '');
  const re = new RegExp(tokens.map(escapeRe).join('|'), 'gi');
  return String(s || '').replace(re, '');
}

/** 0-9 单字 */
function parseDigitChar(c) {
  const d = CN_DIGIT(c);
  if (d >= 0) return d;
  return -1;
}

/**
 * 解析 0-99（含 十/二十三/五），不含「百/千」。
 */
function parseBelow100(str) {
  const s0 = String(str || '').replace(/零|〇|○/g, '');
  if (!s0) return 0;
  if (/^\d{1,2}$/.test(s0)) {
    const n = parseInt(s0, 10);
    return n <= 99 ? n : -1;
  }
  if (s0.length === 1) {
    /* 单字「十」=10，勿走 parseDigitChar（否则一直失败，连「十斤」「各数十斤」都不可用） */
    if (s0 === '十') return 10;
    const d = parseDigitChar(s0[0]);
    return d < 0 ? -1 : d;
  }
  const j = s0.indexOf('十');
  if (j < 0) return -1;
  const a = s0.slice(0, j);
  const b = s0.slice(j + 1);
  const t = a ? parseDigitChar(a) : 1;
  if (a && t < 0) return -1;
  const o = b ? (b.length === 1 && parseDigitChar(b[0]) >= 0 ? parseDigitChar(b[0]) : parseBelow100(b)) : 0;
  if (b && o < 0) return -1;
  if (!a && t === 1) return 10 + o;
  if (a && t > 0) return t * 10 + o;
  return -1;
}

/**
 * 解析 0-9999 中文段：一千二百三十四、六百、十、一十二? → 用 百/十 分层。
 */
function parseChineseSection9999(s, extraSynonyms = []) {
  s = String(s || '').replace(/[两俩]/g, '二');
  s = removeInteriorUnits(s, extraSynonyms);
  s = s.replace(/零|〇|○/g, '');
  if (!s) return 0;
  if (/^\d{1,4}$/.test(s)) {
    const n = parseInt(s, 10);
    if (n >= 0 && n <= 9999) return n;
    return -1;
  }
  const qi = s.indexOf('千');
  if (qi >= 0) {
    const left = s.slice(0, qi);
    const right = s.slice(qi + 1);
    const th = left ? (left.length === 1 ? parseDigitChar(left[0]) : -1) : 1;
    if (th < 0 || th > 9) return -1;
    const rest = parseChineseSection9999(right, extraSynonyms);
    if (rest < 0) return -1;
    return th * 1000 + rest;
  }
  const bai = s.indexOf('百');
  if (bai >= 0) {
    const left = s.slice(0, bai);
    const right = s.slice(bai + 1);
    const h = left ? (left.length === 1 ? parseDigitChar(left[0]) : -1) : 1;
    if (h < 0 || h > 9) return -1;
    const r = right ? parseBelow100(right) : 0;
    if (r < 0) return -1;
    return h * 100 + r;
  }
  return parseBelow100(s);
}

/**
 * 含「万/萬」的整数。二万零五 → 20005
 */
function parseChineseIntegerOnly(s, extraSynonyms = []) {
  const t = String(s || '')
    .replace(/[两俩]/g, '二')
    .trim();
  const cleaned = removeInteriorUnits(t, extraSynonyms);
  if (!cleaned) return null;
  if (/^[\d.]+$/.test(cleaned)) {
    const n = parseFloat(cleaned);
    return Number.isFinite(n) ? n : null;
  }
  const parts = cleaned.split(/[萬万]/);
  if (parts.length > 2) return null;
  if (parts.length === 1) {
    const v = parseChineseSection9999(parts[0], extraSynonyms);
    return v < 0 ? null : v;
  }
  const a = parts[0].trim();
  const b = parts[1].trim();
  const hi = a ? parseChineseSection9999(a, extraSynonyms) : 0;
  const lo = b ? parseChineseSection9999(b, extraSynonyms) : 0;
  if (hi < 0 || lo < 0) return null;
  return hi * 10000 + lo;
}

/**
 * 「各十」「各三十五」→「各10」「各35」，供引擎预处理与阿拉伯金额路径一致。
 */
export function expandChineseAmountAfterEachKeyword(s, extraSynonyms = []) {
  const expandGeCn = (m, cn, offset, whole, unitLen = 0) => {
    const v = tryParseAmountToken(cn, extraSynonyms);
    if (v == null || !Number.isFinite(Number(v)) || Number(v) <= 0) return m;
    const expanded = `各${Math.round(Number(v))}`;
    const afterMatch = whole.slice(offset + m.length + unitLen);
    if (GLUED_NEXT_TARGETS_HEAD_RE.test(afterMatch)) return `${expanded} `;
    return expanded;
  };
  let t = String(s || '').replace(
    /各([零〇○一二三四五六七八九十百千万两俩贰廿卅]+)\s*元/gu,
    (m, cn, offset, whole) => expandGeCn(m, cn, offset, whole)
  );
  /** 各三十块、各五十米：须整段吃掉尾单位，勿把「三十」拆成「三」 */
  t = t.replace(/各([零〇○一二三四五六七八九十百千万两俩贰廿卅]+)([元块米斤角分])/gu, (m, cn, unit, offset, whole) =>
    expandGeCn(m, cn, offset, whole, unit.length)
  );
  t = t.replace(
    /各([零〇○一二三四五六七八九十百千万两俩贰廿卅]+)(?![元块斤角分])/gu,
    (m, cn, offset, whole) => {
      const v = tryParseAmountToken(cn, extraSynonyms);
      if (v == null || !Number.isFinite(Number(v)) || Number(v) <= 0) return m;
      const expanded = `各${Math.round(Number(v))}`;
      const afterMatch = whole.slice(offset + m.length);
      /* 各十26/35元：「十」为本子句金额，26 为下一子句球号，勿粘连成 各1026 */
      if (GLUED_NEXT_TARGETS_HEAD_RE.test(afterMatch)) {
        return `${expanded} `;
      }
      return expanded;
    }
  );
  return t;
}

/**
 * 尝试将一段字符串解析为单金额（阿拉伯、中文、或 1千/2 万/1千2）。
 * @param {string} tail
 * @param {string[]} [extraSynonyms] 后台扩展单位（与内置合并）
 */
export function tryParseAmountToken(tail, extraSynonyms = []) {
  let t = String(tail || '').trim();
  t = stripTrailingUnitsLoop(t, extraSynonyms);
  /* 表格式：行末 100/、50# 等为分隔习惯，紧接在非单位后的 /# $ 不作为数字的一部分 */
  t = t.replace(/[/／#＃$＄]+$/u, '').trimEnd();
  t = stripTrailingUnitsLoop(t, extraSynonyms);
  if (!t) return null;
  t = t.replace(/[两俩]/g, '二');
  if (!t) return null;

  /* 勿把「04.35」误作小数 4.35：两位.两位且均在 01–49 时为球号分隔，由引擎先规范为空格再解析金额 */
  if (/^\d{2}\.\d{2}$/.test(t)) {
    const [as, bs] = t.split('.');
    const na = parseInt(as, 10);
    const nb = parseInt(bs, 10);
    if (
      Number.isInteger(na) &&
      Number.isInteger(nb) &&
      na >= 1 &&
      na <= 49 &&
      nb >= 1 &&
      nb <= 49
    ) {
      return null;
    }
  }

  if (/^[\d.]+$/.test(t)) {
    const n = parseFloat(t);
    return Number.isFinite(n) ? n : null;
  }
  const mk = t.match(/^(\d+)\s*千\s*(.*)?$/);
  if (mk) {
    const base = Number(mk[1]) * 1000;
    if (!Number.isFinite(base)) return null;
    if (!mk[2] || !String(mk[2]).trim()) return base;
    const rest = String(mk[2]).trim();
    if (/^\d+$/.test(rest)) return base + parseInt(rest, 10);
    const c = parseChineseIntegerOnly(rest, extraSynonyms);
    if (c == null) return null;
    return base + c;
  }
  const mw = t.match(/^(\d+)\s*[萬万]\s*(.*)?$/);
  if (mw) {
    const base = Number(mw[1]) * 10000;
    if (!Number.isFinite(base)) return null;
    if (!mw[2] || !String(mw[2]).trim()) return base;
    const rest = String(mw[2]).trim();
    if (/^\d+$/.test(rest)) return base + parseInt(rest, 10);
    const c = parseChineseIntegerOnly(rest, extraSynonyms);
    if (c == null) return null;
    return base + c;
  }

  return parseChineseIntegerOnly(t, extraSynonyms);
}

/** 与 engine 中 ORDER_NOISE_HEAD 一致，用于从左解析金额时剥前缀（避免循环依赖） */
const ORDER_NOISE_HEAD_FOR_AMOUNT =
  /^[，,。.、;；:：\s！!？?…~～*｜|·•【】\[\]()（）'"'`«»\u200B-\u200D\uFEFF]+/u;
/** 金额段结束后、下一子句或备注前允许的间隔（逗号、空白等） */
const AFTER_AMOUNT_HEAD_OK_RE =
  /^[\s，,。.、;；:：！!？?…~～*｜|·•【】\[\]()（）'"'`«»\u200B-\u200D\uFEFF]+/u;
/** 金额中含此类汉字（非仅「元/A」等单位），且后面粘连 「20/…」式下一段号码时，视为子句结束 */
const CN_NUM_IN_AMOUNT_RE = /[零○〇一二三四五六七八九十百千万萬两壹贰叁肆伍陆柒捌玖拾佰仟負]/u;
/** 下一段：以数字或 / 分号类号码列表开头（如 20、/21） */
const GLUED_NEXT_TARGETS_HEAD_RE = /^[/／]\d|^\d/u;
/** 下一段：直连生肖（鸡各二十「羊」猴兔…） */
const GLUED_NEXT_ZODIAC_HEAD_RE = /^[鼠牛虎兔龙龍蛇马羊猴鸡狗猪]/u;

function stripLeadingNoiseForAmount(raw) {
  let s = String(raw || '');
  let prev;
  do {
    prev = s;
    s = s.replace(ORDER_NOISE_HEAD_FOR_AMOUNT, '');
  } while (s !== prev);
  return s;
}

/**
 * 从字符串开头解析第一段金额（最长匹配），用于「…各二元，06…各五」等多组连写，避免 parseValueFromEnd 误取后面组的尾额。
 * @returns {{ value: number, rest: string } | null}
 */
export function parseValueFromStartAmount(rawAfter, opts = {}) {
  const extraSynonyms = opts.unitSynonyms || [];
  const afterTok = String(rawAfter || '');
  const t0 = stripLeadingNoiseForAmount(afterTok);
  const leadSkip = afterTok.length - t0.length;
  if (!t0) return null;
  const max = Math.min(128, t0.length);
  for (let len = max; len >= 1; len -= 1) {
    const prefix = t0.slice(0, len);
    const v = tryParseAmountToken(prefix, extraSynonyms);
    if (v == null || !Number.isFinite(v)) continue;
    const restChunk = t0.slice(len);
    /* 勿把「三十20」吃成 50：中文金额后粘连下一段号码时，不得把阿拉伯数字并入金额前缀 */
    if (/\d/.test(prefix) && CN_NUM_IN_AMOUNT_RE.test(prefix) && GLUED_NEXT_TARGETS_HEAD_RE.test(restChunk)) {
      continue;
    }
    if (!restChunk) {
      return { value: v, rest: afterTok.slice(leadSkip + len) };
    }
    const sepM = restChunk.match(AFTER_AMOUNT_HEAD_OK_RE);
    if (sepM) {
      const sepLen = sepM[0].length;
      const consumed = leadSkip + len + sepLen;
      return { value: v, rest: afterTok.slice(consumed) };
    }
    if (isGenericTrailingNoiseAfterAmount(restChunk)) {
      return { value: v, rest: afterTok.slice(leadSkip + len) };
    }
    if (isNonUnitTailAfterCompleteAmount(restChunk)) {
      return { value: v, rest: afterTok.slice(leadSkip + len) };
    }
    /* 35元14/15元：阿拉伯金额+单位后粘连下一子句球号 */
    if (/\d/.test(prefix) && GLUED_NEXT_TARGETS_HEAD_RE.test(restChunk)) {
      const rawPrefix = t0.slice(0, len);
      const tokens = mergedUnitTokens(extraSynonyms);
      const hadUnit = tokens.some((u) => new RegExp(`${escapeRe(u)}$`, 'i').test(rawPrefix));
      if (hadUnit) {
        return { value: v, rest: afterTok.slice(leadSkip + len) };
      }
    }
    /* 各三十20/21/…：纯中文金额后粘连下一段号码 */
    if (CN_NUM_IN_AMOUNT_RE.test(prefix) && GLUED_NEXT_TARGETS_HEAD_RE.test(restChunk)) {
      return { value: v, rest: afterTok.slice(leadSkip + len) };
    }
    /* 各二十羊猴兔…：纯中文金额后粘连下一段生肖 */
    if (CN_NUM_IN_AMOUNT_RE.test(prefix) && GLUED_NEXT_ZODIAC_HEAD_RE.test(restChunk)) {
      return { value: v, rest: afterTok.slice(leadSkip + len) };
    }
    continue;
  }
  return null;
}

/** 金额段之后：数字+金额单位已完整时，其后非下一选号/各/集合+金额段头 → 视为段结束 */
function isNonUnitTailAfterCompleteAmount(restChunk) {
  const ts = String(restChunk || '').trimStart();
  if (!ts) return true;
  if (GLUED_NEXT_TARGETS_HEAD_RE.test(ts)) return false;
  if (/^各/u.test(ts)) return false;
  if (GLUED_NEXT_ZODIAC_HEAD_RE.test(ts)) return false;
  return true;
}

/**
 * 金额紧后面的尾巴是否视为噪音（不参与金额、也不应含可继续写成数字的字符）。
 * 允许：空白、标点、符号、字母、以及非「数字义」的汉字（口语、备注等）。
 */
function isGenericTrailingNoiseAfterAmount(junk) {
  const t = String(junk || '');
  if (!t) return true;
  if (/[0-9０-９.+\-eE]/.test(t)) return false;
  if (/[零○〇一二三四五六七八九十百千万萬两壹贰叁肆伍陆柒捌玖拾佰仟負兆亿億]/.test(t)) return false;
  return /^[\s\p{P}\p{S}\p{L}\p{M}\u4e00-\u9fff]*$/u.test(t);
}

/** 与 engine.preNormalizeLottoTwoDigitDotChains 一致，避免环依赖 */
function preNormalizeLottoTwoDigitDotChainsLocal(s) {
  let t = String(s || '');
  let prev;
  do {
    prev = t;
    t = t.replace(/(\d{2})\.(\d{2})/g, (m, a, b) => {
      const na = parseInt(a, 10);
      const nb = parseInt(b, 10);
      if (!(na >= 1 && na <= 49 && nb >= 1 && nb <= 49)) return m;
      return `${a} ${b}`;
    });
  } while (t !== prev);
  t = t.replace(/(\d{1,2})\s+\.(\d{2,})/g, '$1 $2');
  return t;
}

/**
 * 勿把「04 3」+「5a」这类在空格后拆断两位球号；尾段若含字母等单位屑时尤易误切。
 */
function rejectSplitBreaksTwoDigitBallAcrossBoundary(beforeTrimEnd, tailRaw) {
  const b = String(beforeTrimEnd || '').trimEnd();
  const t = String(tailRaw || '');
  if (!b || !t) return false;
  const lb = b.slice(-1);
  const ft = t[0];
  if (!/\d/.test(lb) || !/\d/.test(ft)) return false;
  if (t.length > 1 && !/\D/u.test(t.slice(1))) return false;
  const combined = parseInt(lb + ft, 10);
  if (!(combined >= 1 && combined <= 49)) return false;
  const prev = b.length >= 2 ? b[b.length - 2] : '';
  return prev === ' ' || prev === '';
}

/**
 * 勿把「04 35」尾部的第二颗球号当成金额（parseValueFromEnd 会先吃到 35）。
 * 尾段若已为明确金额（含数字后的 A/a 等单位）则不适用。
 */
function rejectBallGridSecondPickAsAmount(fullStr, beforeTrimEnd, value, tailRaw, extraSynonyms) {
  if (value !== Math.floor(value)) return false;
  const vi = Math.floor(value);
  if (vi < 1 || vi > 49) return false;
  const parts = String(beforeTrimEnd || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length !== 1) return false;
  const b1 = parts[0];
  if (!/^\d{1,2}$/.test(b1)) return false;
  const n1 = parseInt(b1, 10);
  if (n1 < 1 || n1 > 49) return false;
  const tRaw = String(tailRaw || '').trim();
  /* 含中文金额词或数字后的 A/a（与元块等同）则视为明确金额尾，勿按「第二颗球」误拒 */
  if (/[元块斤分角整米蒙]|\d[aA]$/u.test(tRaw)) return false;
  const tStripped = stripTrailingUnitsLoop(tRaw, extraSynonyms);
  if (tStripped !== String(vi) && tStripped !== String(vi).padStart(2, '0')) return false;
  const esc = (s) => String(s || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const alt = vi < 10 ? `(?:0?${vi}|${String(vi).padStart(2, '0')})` : String(vi);
  const re = new RegExp(`^\\s*${esc(b1)}\\s+${alt}(?!\\d)`);
  return re.test(String(fullStr || ''));
}

/** 防误切：如「…第100期」中的阿拉伯段不应当作金额 */
function rejectSpuriousIssueNumberSplit(fullStr, totalLen, amountPart, junk) {
  const before = String(fullStr || '')
    .slice(0, Math.max(0, fullStr.length - totalLen))
    .trimEnd();
  if (!/第\s*$/u.test(before)) return false;
  const ap = String(amountPart || '').trim();
  if (!/^[\d.]+$/u.test(ap)) return false;
  return /^期/u.test(String(junk || ''));
}

/**
 * 「第…期」尾：不要把 00期 等拆成金额 0 + 期
 */
function rejectIssueTailFragmentSplit(before, junk) {
  if (!/^期/u.test(String(junk || ''))) return false;
  return /第\d*$/u.test(String(before || '').trimEnd());
}

/**
 * 从整段末尾切出最后一段可解析为金额的子串，返回 { value, before }。
 * 先尝试「整段后缀即金额」；否则尝试「金额前缀 + 任意可忽略尾部」（报上去、备注等）。
 * @param {string} s
 * @param {{ unitSynonyms?: string[] }} [opts]
 */
export function parseValueFromEnd(s, opts = {}) {
  const extraSynonyms = opts.unitSynonyms || [];
  let str = preNormalizeLottoTwoDigitDotChainsLocal(String(s || '').trim());
  if (!str) return null;
  const max = Math.min(128, str.length);
  for (let len = max; len >= 1; len -= 1) {
    const tail = str.slice(-len);
    if (!/[\d\u4e00-\u9fff.+-]/.test(tail) && !/[万千萬]/.test(tail)) {
      /* allow pure punct - skip */
    }
    const v = tryParseAmountToken(tail, extraSynonyms);
    if (v == null) continue;
    if (!Number.isFinite(v)) continue;
    if (rejectSpuriousIssueNumberSplit(str, len, tail, '')) continue;
    const before = str.slice(0, str.length - len).trimEnd();
    if (rejectSplitBreaksTwoDigitBallAcrossBoundary(before, tail)) continue;
    if (rejectBallGridSecondPickAsAmount(str, before, v, tail, extraSynonyms)) continue;
    return { value: v, before };
  }
  for (let totalLen = max; totalLen >= 1; totalLen -= 1) {
    const tail = str.slice(-totalLen);
    for (let amtLen = totalLen; amtLen >= 1; amtLen -= 1) {
      const amountPart = tail.slice(0, amtLen);
      const junk = tail.slice(amtLen);
      if (!isGenericTrailingNoiseAfterAmount(junk) && !isNonUnitTailAfterCompleteAmount(junk)) continue;
      const v = tryParseAmountToken(amountPart, extraSynonyms);
      if (v == null || !Number.isFinite(v)) continue;
      if (rejectSpuriousIssueNumberSplit(str, totalLen, amountPart, junk)) continue;
      const beforeCandidate = str.slice(0, str.length - totalLen).trimEnd();
      if (rejectIssueTailFragmentSplit(beforeCandidate, junk)) continue;
      if (rejectSplitBreaksTwoDigitBallAcrossBoundary(beforeCandidate, tail)) continue;
      if (rejectBallGridSecondPickAsAmount(str, beforeCandidate, v, tail, extraSynonyms)) continue;
      return { value: v, before: beforeCandidate };
    }
  }
  return null;
}
