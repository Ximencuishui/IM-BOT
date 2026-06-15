import { parseValueFromEnd, parseValueFromStartAmount, tryParseAmountToken, expandChineseAmountAfterEachKeyword } from './chinese_amount.js';
import {
  emitCanonicalOrderLine,
  inferClauseItemsTypeForAst,
  formatOrderLineAstDebugOneLine,
  extractOrderUnitsFromAst,
} from './order_line_ast.js';
import { appendOrderUnitLog } from './order_unit_log.js';
import { splitMessageParagraphs, DEFAULT_ORDER_REGION, DEFAULT_ORDER_PLAY } from './order_unit_scope.js';
import {
  inboundTextHasOrderDigits,
  looksLikeInboundOrderAttempt,
  isWeChatInboundFileXmlQuick,
} from './pipeline/inbound_filter.js';
import {
  listSynonymPairs,
  listSynonymAliasesForCanonical,
  resolveSynonymCanonical,
  buildAlgoAliasData,
  listSetAmountUnitSuffixWords,
  inferLianXiaoGroupSizeFromCategoryWord,
  isLianXiaoCategoryWord,
  listLianXiaoPlayPrefixTokensFromDb,
  listEachAlgoAliasWords,
  expandCollectionAliasesInTargetText,
  listCollectionAliasPairs,
} from './alias_resolver.js';
import { getParseCache } from './parse_cache.js';
import {
  isDrawDeferSummaryEnabled,
  saveGroupDrawCache,
  loadGroupDrawCache,
} from '../db/draw_cache.js';
export { inboundTextHasOrderDigits } from './pipeline/inbound_filter.js';

/** SQL 片段：仅统计真实下注行（排除派奖产生的虚增行） */
const CMD_ORDERS_BET_ONLY = `COALESCE(algo,'') NOT IN ('发货命中','开奖命中')`;

function safeJsonParseArray(v) {
  if (!v) return [];
  try {
    const arr = JSON.parse(v);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

const SUPPORTED_STEPS = new Set([
  'identity',
  'algo',
  'sum',
  'avg',
  'count',
  'max',
  'min',
  'round',
  'floor',
  'ceil',
  'clamp',
  'unique',
  'sort_asc',
  'sort_desc',
  'each_add',
  'each_sub',
  'each_mul',
  'each_div',
  'order',
  'union',
  'intersect',
  'diff',
  'pick',
  'to_values',
  'zodiac_age',
  'age_zodiac',
  '生肖岁数',
  '岁数生肖',
  'zodiac_age_range',
  '生肖岁数范围',
]);

/** 中文别名 / 常用别称 → 内部规范名（parse 后再规范化） */
const STEP_ALIAS_TO_CANONICAL = new Map([
  ['恒等', 'identity'],
  ['原样', 'identity'],
  ['透传', 'identity'],
  ['算法', 'algo'],
  ['求和', 'sum'],
  ['合计', 'sum'],
  ['均值', 'avg'],
  ['平均', 'avg'],
  ['平均值', 'avg'],
  ['计数', 'count'],
  ['数量', 'count'],
  ['最大', 'max'],
  ['最大值', 'max'],
  ['最小', 'min'],
  ['最小值', 'min'],
  ['四舍五入', 'round'],
  ['保留小数', 'round'],
  ['下取整', 'floor'],
  ['向下取整', 'floor'],
  ['上取整', 'ceil'],
  ['向上取整', 'ceil'],
  ['限幅', 'clamp'],
  ['裁剪', 'clamp'],
  ['去重', 'unique'],
  ['升序', 'sort_asc'],
  ['从小到大', 'sort_asc'],
  ['降序', 'sort_desc'],
  ['从大到小', 'sort_desc'],
  ['逐项加', 'each_add'],
  ['逐项减', 'each_sub'],
  ['逐项乘', 'each_mul'],
  ['逐项除', 'each_div'],
  ['下单', 'order'],
  ['并集', 'union'],
  ['合集', 'union'],
  ['交集', 'intersect'],
  ['差集', 'diff'],
  ['按位取值', 'pick'],
  ['提取', 'pick'],
  ['转数值', 'to_values'],
  ['转数值序列', 'to_values'],
  ['数值序列', 'to_values'],
]);

function canonicalStepName(raw) {
  const k = String(raw || '').trim();
  if (!k) return k;
  if (SUPPORTED_STEPS.has(k)) return k;
  return STEP_ALIAS_TO_CANONICAL.get(k) || k;
}

const MAX_PIPELINE_DEPTH = 32;

/** 仅在括号深度为 0 时按 | 拆分，用于子流水线与括号组合 */
function splitPipelineByTopLevelPipe(expr) {
  const s = String(expr || '').trim();
  if (!s) return [];
  const parts = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < s.length; i += 1) {
    const c = s[i];
    if (c === '(') depth += 1;
    else if (c === ')') depth -= 1;
    if (c === '|' && depth === 0) {
      parts.push(s.slice(start, i).trim());
      start = i + 1;
    }
  }
  parts.push(s.slice(start).trim());
  return parts.filter(Boolean);
}

/** 整段为一对最外层括号包裹时，返回内层字符串，否则 null */
function unwrapOuterParenGroup(s) {
  const t = String(s || '').trim();
  if (!t.startsWith('(')) return null;
  let depth = 0;
  for (let i = 0; i < t.length; i += 1) {
    if (t[i] === '(') depth += 1;
    else if (t[i] === ')') {
      depth -= 1;
      if (depth === 0) {
        if (i !== t.length - 1) return null;
        return t.slice(1, i).trim();
      }
    }
  }
  return null;
}

function stripParenLayersToInnerPipeline(seg) {
  let s = String(seg || '').trim();
  if (!s) return s;
  while (true) {
    const inner = unwrapOuterParenGroup(s);
    if (inner == null) break;
    s = inner;
  }
  return s;
}

function assertBalancedParens(expr) {
  let depth = 0;
  for (let i = 0; i < expr.length; i += 1) {
    const c = expr[i];
    if (c === '(') depth += 1;
    else if (c === ')') {
      depth -= 1;
      if (depth < 0) return false;
    }
  }
  return depth === 0;
}

function normalizeGuideWord(v) {
  return String(v || '').replace(/^\^+/, '').trim();
}

/** 「一门」～「五门」/「1门」等为集合名；裸「门」或「门特」= 澳门口语渠道 + 特 */
function isNumericMenCollectionPrefix(s) {
  return /^[一二三四五1-5]门/u.test(String(s || ''));
}

function resolveMenMacauGuideWord(db) {
  if (!db) return '新澳门';
  const { guide } = getEffectiveDefaultOrderGuideCategory(db, null);
  const g = String(guide || '').trim();
  if (g && assertActiveGlobalOrderRoute(db, g, '特')) return g;
  if (assertActiveGlobalOrderRoute(db, '新澳门', '特')) return '新澳门';
  if (assertActiveGlobalOrderRoute(db, '老澳门', '特')) return '老澳门';
  return g || '新澳门';
}

/** 断行合并前：本行可独立成单（渠道/门特/香+球号等），勿与上一行揉成一句 */
function lineLooksLikeNewOrderLineStart(db, line, wxGroupId = null) {
  let s = applyLongestGuidePrefixReplacement(db, String(line || '').trim());
  s = normalizeRoutePrefixWithSynonyms(db, s);
  if (contentMatchesAnyRoute(db, s, wxGroupId)) return true;
  const globalPeel = peelRoutePrefixFromLine(s, buildSortedRoutePrefixes(db));
  if (globalPeel?.prefix) {
    if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
      ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, s);
    }
    return true;
  }
  const hoisted = hoistEmbeddedGuideChannelBeforeBallsEach(db, s, wxGroupId);
  let resolved = resolveOrderContentWithDefaultPrefix(db, hoisted, wxGroupId);
  resolved = normalizeRoutePrefixWithSynonyms(db, resolved);
  return contentMatchesAnyRoute(db, resolved, wxGroupId);
}

/** 行首「门特」「门，」→ 默认澳门渠道 + 特（与集合「X门」区分） */
function expandMenTeMacauChannelPrefix(db, text) {
  const guide = resolveMenMacauGuideWord(db);
  if (!guide) return String(text || '');
  return String(text || '')
    .split('\n')
    .map((rawLn) => {
      let s = String(rawLn || '');
      if (!s.trim()) return rawLn;
      if (isNumericMenCollectionPrefix(s.trim())) return rawLn;
      if (/^门特/u.test(s.trim())) {
        return s.replace(/^(\s*)门特/u, `$1${guide}特`);
      }
      if (/^门[，,。.、:：;；\s]/u.test(s.trim())) {
        return s.replace(/^(\s*)门/u, `$1${guide}`);
      }
      return rawLn;
    })
    .join('\n');
}

/** 同一条消息内按「规范化渠道 + 分类」合并回执时的分组键 */
function routeGroupKey(route) {
  const g = normalizeGuideWord(route?.guide_word);
  const c = String(route?.category_word || '').trim();
  return `${g}|||${c}`;
}

/** 金额单位尾缀：统一 alias_config SET（别名中心） */
function getOrderAmountUnitSynonyms(db) {
  if (!db) return [];
  const seen = new Set();
  const out = [];
  for (const x of listSetAmountUnitSuffixWords(db)) {
    const k = String(x || '').trim();
    if (!k) continue;
    const low = k.toLowerCase();
    if (seen.has(low)) continue;
    seen.add(low);
    out.push(k);
  }
  return out;
}

/** 全局有效路由（去重 guide+category） */
function listDistinctActiveRoutePairs(db) {
  const rows = listActiveCmdRoutes(db);
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    const g = String(r.guide_word || '').trim();
    const c = String(r.category_word || '').trim();
    if (!g || !c) continue;
    const k = `${g}\0${c}`;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push({ guide_word: g, category_word: c });
  }
  return out;
}

/** 整行仅为渠道规范词（下一行再写玩法+生肖） */
function lineIsGuideWordOnly(db, text) {
  const raw = String(text || '').trim();
  if (raw === '港' || raw === '香') {
    const ok = listDistinctActiveRoutePairs(db).some((r) => normalizeGuideWord(r.guide_word) === '香港');
    return ok ? '香港' : '';
  }
  let s = applyLongestGuidePrefixReplacement(db, raw);
  s = normalizeRoutePrefixWithSynonyms(db, s);
  const gn = normalizeGuideWord(s);
  if (!gn || s !== gn) return '';
  const ok = listDistinctActiveRoutePairs(db).some((r) => normalizeGuideWord(r.guide_word) === gn);
  return ok ? gn : '';
}

/** 整行仅为玩法分类（或分类别名），下一行再写生肖组/金额 */
function lineIsCategoryAliasOnly(db, text, wxGroupId = null) {
  let s = applyLongestGuidePrefixReplacement(db, String(text || '').trim());
  s = normalizeRoutePrefixWithSynonyms(db, s);
  if (!s) return '';
  const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
  const detected = detectLineRoutePrefix(s, routePrefixes);
  if (detected) {
    const peeled = peelRoutePrefixFromLine(s, routePrefixes);
    if (peeled && !String(peeled.rest || '').trim()) return peeled.prefix;
  }
  const { guide } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
  const ng = normalizeGuideWord(guide);
  if (ng) {
    const aliasExpanded = tryExpandLeadingCategoryAliasWithDefaultGuide(db, s, ng, wxGroupId);
    if (aliasExpanded) {
      const peeled = peelRoutePrefixFromLine(aliasExpanded, routePrefixes);
      if (peeled && !String(peeled.rest || '').trim()) return peeled.prefix;
    }
  }
  const canon = resolveCategoryHintWithSynonyms(db, s);
  if (canon && ng) {
    const candidate = `${ng}${canon}`;
    if (contentMatchesAnyRoute(db, candidate, wxGroupId)) {
      const det = detectLineRoutePrefix(candidate, routePrefixes);
      if (det) return det.prefix;
    }
  }
  return '';
}

function buildGuideStartReplacementList(db) {
  const list = [];
  const seen = new Set();
  const push = (from, toNorm) => {
    if (!from || !toNorm) return;
    const k = `${from}=>${toNorm}`;
    if (seen.has(k)) return;
    seen.add(k);
    list.push({ from, to: toNorm });
  };
  for (const r of listDistinctActiveRoutePairs(db)) {
    const raw = String(r.guide_word || '').trim();
    const norm = normalizeGuideWord(raw);
    if (!norm) continue;
    push(norm, norm);
    if (raw && raw !== norm) push(raw, norm);
  }
  let syns = listSynonymPairs(db, 'guide_word');
  for (const s of syns) {
    const canon = String(s.canonical_word || '').trim();
    const al = String(s.alias_word || '').trim();
    if (!canon || !al) continue;
    const toNorm = normalizeGuideWord(canon);
    if (!toNorm) continue;
    push(normalizeGuideWord(al), toNorm);
    if (al !== normalizeGuideWord(al)) push(al, toNorm);
  }
  list.sort((a, b) => b.from.length - a.from.length);
  return list;
}

function applyLongestGuidePrefixReplacement(db, content) {
  const c = String(content || '').trim();
  if (!c) return c;
  if (c === '港' || c === '香') {
    const ok = listDistinctActiveRoutePairs(db).some((r) => normalizeGuideWord(r.guide_word) === '香港');
    if (ok) return '香港';
  }
  const list = buildGuideStartReplacementList(db);
  for (const { from, to } of list) {
    if (!c.startsWith(from)) continue;
    /** 勿用单字「澳/奥」吃掉句首「澳门…」（库内未必登记「澳门」别名） */
    const blocked = list.some(
      (x) => x.from.length > from.length && x.from.startsWith(from) && c.startsWith(x.from)
    );
    if (blocked) continue;
    if ((from === '澳' || from === '奥' || from === '噢') && /^门/u.test(c.slice(from.length))) continue;
    return to + c.slice(from.length);
  }
  return c;
}

/** 句首口语「澳门特」→ 规范「新澳门特」（老澳门须写全「老澳门特」） */
function normalizeLeadingMacauTeRouteShorthand(s) {
  return String(s || '')
    .split('\n')
    .map((ln) => {
      const t = String(ln || '').trim();
      if (!t) return ln;
      if (t.startsWith('新澳门特') || t.startsWith('老澳门特')) return t;
      if (t.startsWith('澳门特')) return `新澳门特${t.slice(3)}`;
      return ln;
    })
    .join('\n');
}

/** 球号表前装饰性生肖 emoji（如 🐴11.12…），剥除不参与解析 */
const ZODIAC_EMOJI_DECOR_RE =
  /🐭|🐮|🐯|🐰|🐲|🐍|🐎|🐴|🐐|🐵|🐔|🐶|🐷/gu;

function stripZodiacEmojiDecoration(s) {
  return String(s || '').replace(ZODIAC_EMOJI_DECOR_RE, '');
}

function normalizeRoutePrefixWithSynonyms(db, content) {
  const c0 = String(content || '').trim();
  if (!c0) return c0;
  const routes = listDistinctActiveRoutePairs(db);
  let catSynRows = listSynonymPairs(db, 'category_word');
  const catToAliases = new Map();
  for (const r of routes) {
    const cat = String(r.category_word || '').trim();
    if (!cat) continue;
    if (!catToAliases.has(cat)) catToAliases.set(cat, new Set());
    catToAliases.get(cat).add(cat);
  }
  for (const s of catSynRows) {
    const canon = String(s.canonical_word || '').trim();
    const al = String(s.alias_word || '').trim();
    if (!canon || !al) continue;
    if (!catToAliases.has(canon)) catToAliases.set(canon, new Set());
    catToAliases.get(canon).add(al);
  }
  const guideRepl = buildGuideStartReplacementList(db);
  const prefixes = [];
  for (const r of routes) {
    const gNorm = normalizeGuideWord(r.guide_word);
    const catCanon = String(r.category_word || '').trim();
    if (!gNorm || !catCanon) continue;
    const gVariants = new Set([gNorm]);
    const rawG = String(r.guide_word || '').trim();
    if (rawG) gVariants.add(rawG);
    for (const { from, to } of guideRepl) {
      if (to === gNorm) gVariants.add(from);
    }
    const cSet = catToAliases.get(catCanon) || new Set([catCanon]);
    const canonPrefix = `${gNorm}${catCanon}`;
    for (const gv of gVariants) {
      for (const cv of cSet) {
        const prefix = `${gv}${cv}`;
        prefixes.push({ prefix, canon: canonPrefix });
      }
    }
  }
  prefixes.sort((a, b) => b.prefix.length - a.prefix.length);
  for (const p of prefixes) {
    if (c0.startsWith(p.prefix)) return p.canon + c0.slice(p.prefix.length);
  }
  return c0;
}

function resolveGuideHintWithSynonyms(db, hint) {
  const h0 = String(hint || '').trim();
  if (!h0 || !db) return h0;
  try {
    const row =
      resolveSynonymCanonical(db, 'guide_word', h0) ||
      resolveSynonymCanonical(db, 'guide_word', normalizeGuideWord(h0));
    if (row) return row;
  } catch {
    /* empty */
  }
  return h0;
}

function resolveCategoryHintWithSynonyms(db, hint) {
  const h0 = String(hint || '').trim();
  if (!h0 || !db) return h0;
  try {
    const row = resolveSynonymCanonical(db, 'category_word', h0);
    if (row) return row;
  } catch {
    /* empty */
  }
  return h0;
}

/**
 * 未写渠道时句首若是分类别名（如「二连肖」「二连」→ 连肖），若直接插默认「特」会得到「新澳门特二连肖…」，
 * normalizeRoutePrefixWithSynonyms 无法纠正（中间隔着「特」）。此处按最长别名匹配并拼默认渠道 + 规范分类。
 */
function routeCandidateAccepted(db, candidate, wxGroupId) {
  const cand = String(candidate || '').trim();
  if (!cand) return false;
  if (contentMatchesAnyRoute(db, cand, wxGroupId)) return true;
  if (!contentMatchesAnyRoute(db, cand, null)) return false;
  if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
    ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, cand);
    return contentMatchesAnyRoute(db, cand, wxGroupId);
  }
  return true;
}

/** 句首为玩法分类（四连肖、二连…）时拼默认渠道 + 规范分类，勿插默认「特」 */
function tryExpandLeadingCategoryAliasWithDefaultGuide(db, unprefixedContent, normalizedGuide, wxGroupId) {
  const c = String(unprefixedContent || '').trim();
  const ng = String(normalizedGuide || '').trim();
  if (!c || !ng) return null;
  for (const { suf, canon } of listCategorySuffixesToCanonical(db)) {
    if (!c.startsWith(suf)) continue;
    const rest = c.slice(suf.length);
    const candidate = `${ng}${canon}${rest}`;
    if (routeCandidateAccepted(db, candidate, wxGroupId)) return candidate;
  }
  return null;
}

/** 玩法分类后缀 → 规范 category_word（含同义词别名），长词优先 */
function listCategorySuffixesToCanonical(db) {
  if (!db) return [];
  return getParseCache(db, 'categorySuffixes', () => listCategorySuffixesToCanonicalImpl(db));
}

function listCategorySuffixesToCanonicalImpl(db) {
  const rows = db
    .prepare(
      `SELECT DISTINCT category_word FROM cmd_routes
       WHERE is_active = 1 AND TRIM(IFNULL(category_word, '')) <> ''
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id, '')) = '' OR wx_group_id = '__global__')`
    )
    .all();
  const canons = rows
    .map((r) => String(r.category_word || '').trim())
    .filter(Boolean);
  const pairs = [];
  const seen = new Set();
  const add = (suf, canon) => {
    const s = String(suf || '').trim();
    const c = String(canon || '').trim();
    if (!s || !c || seen.has(`${s}\0${c}`)) return;
    seen.add(`${s}\0${c}`);
    pairs.push({ suf: s, canon: c });
  };
  for (const canon of canons) {
    add(canon, canon);
    try {
      const syns = listSynonymAliasesForCanonical(db, 'category_word', canon);
      for (const alias_word of syns) {
        add(String(alias_word || '').trim(), canon);
      }
    } catch {
      /* empty */
    }
  }
  pairs.sort((a, b) => b.suf.length - a.suf.length);
  return pairs;
}

function assertActiveGlobalOrderRoute(db, guideWord, categoryWord) {
  const g = String(guideWord || '').trim();
  const c = String(categoryWord || '').trim();
  if (!g || !c) return false;
  const ok = db
    .prepare(
      `SELECT 1 FROM cmd_routes
       WHERE is_active = 1 AND guide_word = ? AND category_word = ?
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id, '')) = '' OR wx_group_id = '__global__')
       LIMIT 1`
    )
    .get(g, c);
  return Boolean(ok);
}

function upsertAppSettingValue(db, key, value) {
  db.prepare(
    `INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
     ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')`
  ).run(String(key), String(value ?? ''));
}

function guideWordHasActiveGlobalRoute(db, g) {
  const gw = String(g || '').trim();
  if (!gw) return false;
  const ok = db
    .prepare(
      `SELECT 1 FROM cmd_routes
       WHERE is_active = 1 AND guide_word = ?
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id, '')) = '' OR wx_group_id = '__global__')
       LIMIT 1`
    )
    .get(gw);
  return Boolean(ok);
}

function listActiveCmdRoutes(db) {
  return db
    .prepare(
      `SELECT guide_word, category_word FROM cmd_routes
       WHERE is_active = 1
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
       ORDER BY priority DESC, id DESC`
    )
    .all();
}

function groupUsesStrictPlayRoutes(db, wxGroupId) {
  if (!wxGroupId) return false;
  const g = db
    .prepare(`SELECT strict_play_routes FROM wx_groups WHERE wx_group_id = ? AND is_active = 1`)
    .get(wxGroupId);
  return Boolean(g) && Number(g.strict_play_routes ?? 0) === 1;
}

/** strict 群下单解析时仅考虑已开启的全局路由组合 */
function listActiveCmdRoutesForOrderParse(db, wxGroupId) {
  const all = listActiveCmdRoutes(db);
  if (!wxGroupId || !groupUsesStrictPlayRoutes(db, wxGroupId)) return all;
  let rows;
  try {
    rows = db
      .prepare(
        `SELECT guide_word, category_word FROM wx_group_route_enables WHERE wx_group_id = ? AND is_enabled = 1`
      )
      .all(wxGroupId);
  } catch {
    rows = [];
  }
  if (!rows?.length) return [];
  const enabled = new Set(
    rows.map((r) => `${String(r.guide_word || '').trim()}\0${String(r.category_word || '').trim()}`)
  );
  return all.filter((r) =>
    enabled.has(`${String(r.guide_word || '').trim()}\0${String(r.category_word || '').trim()}`)
  );
}

function fallbackDefaultGuideCategoryFromRoutes(db) {
  const row = db
    .prepare(
      `SELECT guide_word, category_word FROM cmd_routes
       WHERE is_active = 1
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
       ORDER BY
         CASE WHEN guide_word = '新澳门' AND category_word = '特' THEN 0 ELSE 1 END,
         priority DESC, id DESC
       LIMIT 1`
    )
    .get();
  if (!row) return { guide: '', category: '' };
  return {
    guide: String(row.guide_word || '').trim(),
    category: String(row.category_word || '').trim(),
  };
}

function getEffectiveDefaultOrderGuideCategory(db, wxGroupId) {
  if (!wxGroupId || !groupUsesStrictPlayRoutes(db, wxGroupId)) {
    const gRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_guide_word');
    const cRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_category_word');
    let guide = String(gRow?.value || '').trim();
    let category = String(cRow?.value || '').trim();
    if (!guide || !category) {
      const fb = fallbackDefaultGuideCategoryFromRoutes(db);
      if (!guide) guide = fb.guide;
      if (!category) category = fb.category;
    }
    return { guide, category };
  }
  let rows;
  try {
    rows = db
      .prepare(
        `SELECT guide_word, category_word FROM wx_group_route_enables WHERE wx_group_id = ? AND is_enabled = 1 ORDER BY guide_word ASC, category_word ASC`
      )
      .all(wxGroupId);
  } catch {
    rows = [];
  }
  const prefer = rows.find((r) => String(r.guide_word) === '新澳门' && String(r.category_word) === '特');
  if (prefer) return { guide: '新澳门', category: '特' };
  if (rows[0]) {
    return {
      guide: String(rows[0].guide_word || '').trim(),
      category: String(rows[0].category_word || '').trim(),
    };
  }
  return fallbackDefaultGuideCategoryFromRoutes(db);
}

/** 某渠道下已启用类型的 category_word（长词优先，便于前缀匹配） */
function listCategoryPrefixesForGuide(db, guideWordRaw) {
  const g = String(guideWordRaw || '').trim();
  if (!g) return [];
  const rows = db
    .prepare(
      `SELECT DISTINCT category_word FROM cmd_routes
       WHERE is_active = 1
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
         AND guide_word = ?`
    )
    .all(g);
  return rows
    .map((r) => String(r.category_word || '').trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
}

/** 全局路由中出现的渠道词（去重），用于「句首已是某渠道、未写类型」时按该渠道补默认分类 */
function listDistinctGuideWordsFromGlobalRoutes(db) {
  const seen = new Set();
  const out = [];
  for (const r of listActiveCmdRoutes(db)) {
    const g = String(r.guide_word || '').trim();
    if (!g || seen.has(g)) continue;
    seen.add(g);
    out.push(g);
  }
  return out;
}

/** 路由里的渠道起始串（规范词 + 库内原始词），长词优先，避免只识别 app_settings 默认渠道 */
function buildSortedGuideRoutePrefixes(db) {
  const guides = listDistinctGuideWordsFromGlobalRoutes(db);
  const items = [];
  for (const raw of guides) {
    const norm = normalizeGuideWord(raw);
    items.push({ prefix: norm, guideRaw: raw });
    if (raw && raw !== norm) items.push({ prefix: raw, guideRaw: raw });
  }
  items.sort((a, b) => b.prefix.length - a.prefix.length);
  return items;
}

/** 某渠道在未写分类时默认插入的类型词（非 strict：优先特；strict：该渠道已开路由里优先特） */
function defaultCategoryWordForGuide(db, guideWordRaw, wxGroupId) {
  const g = String(guideWordRaw || '').trim();
  if (!g) return '';
  if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
    let rows;
    try {
      rows = db
        .prepare(
          `SELECT category_word FROM wx_group_route_enables WHERE wx_group_id = ? AND is_enabled = 1 AND guide_word = ? ORDER BY category_word ASC`
        )
        .all(wxGroupId, g);
    } catch {
      rows = [];
    }
    const cats = rows.map((r) => String(r.category_word || '').trim()).filter(Boolean);
    if (cats.includes('特')) return '特';
    if (cats[0]) return cats[0];
    /** strict 群尚未勾选该渠道玩法时，仍按全局路由推断默认分类，避免误套 app 默认渠道（如写成「香港」却变成「新澳门特香港…」） */
    return defaultCategoryWordForGuide(db, g, null);
  }
  const te = db
    .prepare(
      `SELECT 1 FROM cmd_routes
       WHERE is_active = 1 AND guide_word = ? AND category_word = '特'
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
       LIMIT 1`
    )
    .get(g);
  if (te) return '特';
  const prefs = listCategoryPrefixesForGuide(db, g);
  return prefs[0] || '';
}

/** strict 群下某渠道可用的分类前缀（与下单解析启用表一致） */
function listCategoryPrefixesForGuideOrderParse(db, guideWordRaw, wxGroupId) {
  const base = listCategoryPrefixesForGuide(db, guideWordRaw);
  if (!wxGroupId || !groupUsesStrictPlayRoutes(db, wxGroupId)) return base;
  let rows;
  try {
    rows = db
      .prepare(
        `SELECT category_word FROM wx_group_route_enables WHERE wx_group_id = ? AND is_enabled = 1 AND guide_word = ?`
      )
      .all(wxGroupId, guideWordRaw);
  } catch {
    return base;
  }
  const enabled = new Set(rows.map((r) => String(r.category_word || '').trim()).filter(Boolean));
  return base.filter((cat) => enabled.has(cat));
}

/** 内容是否以某条已启用「渠道+类型」前缀开头（strict 群仅匹配已开玩法） */
function contentMatchesAnyRoute(db, content, wxGroupId = null) {
  const c = String(content || '').trim();
  if (!c) return false;
  const list = wxGroupId ? listActiveCmdRoutesForOrderParse(db, wxGroupId) : listActiveCmdRoutes(db);
  for (const r of list) {
    const guide = normalizeGuideWord(r.guide_word);
    const category = String(r.category_word || '').trim();
    if (!guide || !category) continue;
    if (!c.startsWith(guide)) continue;
    const rest = c.slice(guide.length).trim();
    if (!rest.startsWith(category)) continue;
    if (category === '特' && /^肖/u.test(rest.slice(category.length))) continue;
    return true;
  }
  return false;
}

/** 可自数据段末尾剥除的渠道+类型尾缀（同义词+渠道+类型，长词优先） */
function listPeelSuffixDescriptors(db) {
  const rows = listActiveCmdRoutes(db);
  const acc = [];
  for (const r of rows) {
    const gRaw = String(r.guide_word || '').trim();
    const c = String(r.category_word || '').trim();
    if (!gRaw || !c) continue;
    const gNorm = normalizeGuideWord(gRaw);
    const prepend = `${gNorm}${c}`;
    const peels = new Set(
      [`${gNorm}${c}`, `${gRaw}${c}`].filter((x) => x && String(x).length >= 1)
    );
    for (const peel of peels) acc.push({ peel, prepend });
    try {
      const routesForThisGuide = rows.filter(
        (x) => normalizeGuideWord(String(x.guide_word || '').trim()) === gNorm
      );
      const ucatsAll = [
        ...new Set(
          routesForThisGuide.map((x) => String(x.category_word || '').trim()).filter(Boolean)
        ),
      ];
      const syns = listSynonymPairs(db, 'guide_word').filter(
        (r) => r.canonical_word === gRaw || r.canonical_word === gNorm
      );
      for (const { alias_word } of syns) {
        const a = String(alias_word || '').trim();
        if (!a) continue;
        acc.push({ peel: `${a}${c}`, prepend });
        if (ucatsAll.length === 1) acc.push({ peel: a, prepend });
      }
    } catch {
      /* 表可能无 scope */
    }
  }
  acc.sort((a, b) => b.peel.length - a.peel.length);
  const seen = new Set();
  const out = [];
  for (const x of acc) {
    if (!x.peel || seen.has(x.peel)) continue;
    seen.add(x.peel);
    out.push(x);
  }
  return out;
}

/** 整行仅为「渠道+类型」提示（写在段末独立一行） */
function matchRouteOnlyLine(db, line) {
  const t = stripLeadingOrderNoise(String(line || '').trim());
  if (!t) return null;
  for (const { peel, prepend } of listPeelSuffixDescriptors(db)) {
    if (t === peel) return { blockPrepend: prepend };
  }
  const rows = listActiveCmdRoutes(db);
  const byNorm = new Map();
  for (const r of rows) {
    const g = String(r.guide_word || '').trim();
    const ng = normalizeGuideWord(g);
    if (!byNorm.has(ng)) byNorm.set(ng, []);
    byNorm.get(ng).push(r);
  }
  const hint = resolveGuideHintWithSynonyms(db, t);
  for (const [ng, rlist] of byNorm) {
    const cats = [
      ...new Set(rlist.map((x) => String(x.category_word || '').trim()).filter(Boolean)),
    ];
    if (cats.length !== 1) continue;
    if (
      t === ng ||
      (hint && hint !== t && hint === ng) ||
      rlist.some((r) => String(r.guide_word || '').trim() === t)
    ) {
      return { blockPrepend: `${ng}${cats[0]}` };
    }
  }
  return null;
}

/** 剥去块末尾仅含渠道/类型的行，返回正文行与应在每行前补上的「渠道+类型」 */
function peelTrailingRouteOnlyLinesFromBlock(db, rawLines) {
  const lines = rawLines
    .map((x) => stripLeadingOrderNoise(String(x || '').trim()))
    .filter(Boolean);
  if (lines.length === 0) return { contentLines: [], blockPrepend: null };
  let i = lines.length - 1;
  let blockPrepend = null;
  while (i >= 0) {
    const m = matchRouteOnlyLine(db, lines[i]);
    if (!m) break;
    blockPrepend = m.blockPrepend;
    i -= 1;
  }
  return { contentLines: lines.slice(0, i + 1), blockPrepend };
}

/** 数据段末尾可剥渠道尾缀（金额词之后仍挂着渠道简称，如 …各数五A澳） */
function peelTrailingRouteFromDataSegment(db, s) {
  let t = trimTrailingOrderNoise(String(s || '').trimEnd());
  if (!t) return String(s || '');
  for (const { peel } of listPeelSuffixDescriptors(db)) {
    if (peel.length >= 2 && t.endsWith(peel) && t.length > peel.length) {
      const head = trimTrailingOrderNoise(t.slice(0, t.length - peel.length));
      if (head) return head;
    }
  }
  return String(s || '').trim();
}

/**
 * 口语里「A澳」等：算法+中文/阿拉伯金额+字母单位后紧跟渠道简称「澳」
 */
function peelLooseAotaChannelTailFromData(s) {
  let t = trimTrailingOrderNoise(String(s || '').trimEnd());
  if (!t || !/澳$/u.test(t)) return String(s || '').trim();
  if (!/(各|各数|各号|每号|各个|个数|每各|个个)/.test(t)) return String(s || '').trim();
  const head = trimTrailingOrderNoise(t.slice(0, -1));
  if (head.length < 2) return String(s || '').trim();
  return head;
}

/** 类型已在「渠道+特」上时出现，数据段又写「澳特/奥特…」的重复口语 */
function stripRedundantAoTeHeaderFromDataSegment(s) {
  return String(s || '')
    .replace(/^(?:奥|澳)特/u, '')
    .trimStart();
}

function ensureRoutedOrderLine(db, line, blockPrepend, wxGroupId = null) {
  let s = stripLeadingOrderNoise(String(line || '').trim());
  if (isOrderDeclaredTotalNoiseLine(s)) return s;
  s = stripBatchForwardMessageLinePrefix(s);
  s = stripTrailingInlineOrderSummary(s);
  s = s.replace(/#\s*澳$/u, '澳');
  if (!s) return s;
  let t = trimTrailingOrderNoise(s);
  for (const { peel, prepend } of listPeelSuffixDescriptors(db)) {
    if (peel.length >= 2 && t.endsWith(peel) && t.length > peel.length) {
      const head = trimTrailingOrderNoise(t.slice(0, t.length - peel.length));
      if (head) {
        s = `${prepend}${head}`;
        t = trimTrailingOrderNoise(s);
        break;
      }
    }
  }
  s = peelLooseAotaChannelTailFromData(s);
  s = hoistTrailingCategoryAfterZodiacs(db, s);
  s = hoistEmbeddedGuideChannelBeforeBallsEach(db, s, wxGroupId);
  let guideProbe = applyLongestGuidePrefixReplacement(db, s);
  guideProbe = normalizeRoutePrefixWithSynonyms(db, guideProbe);
  const onlyGw = lineIsGuideWordOnly(db, guideProbe);
  if (onlyGw) return onlyGw;
  if (!contentMatchesAnyRoute(db, s, wxGroupId) && blockPrepend) {
    s = `${blockPrepend}${s}`;
  }
  if (!contentMatchesAnyRoute(db, s, wxGroupId)) {
    const globalDet = detectLineRoutePrefix(s, buildSortedRoutePrefixes(db));
    if (globalDet?.guide && globalDet?.category) {
      if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
        ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, s);
      }
    } else {
      s = resolveOrderContentWithDefaultPrefix(db, s, wxGroupId);
    }
  }
  s = hoistTrailingCategoryAfterZodiacs(db, s);
  s = normalizeRoutePrefixWithSynonyms(db, s);
  return s;
}

/**
 * 未写全「渠道+玩法分类」时的拼接规则（与群内约定一致）：
 * - 未指定渠道 → 用 app_settings 默认渠道；未指定分类 → 用默认分类。
 * - strict 卡密新绑群 → 用本群已开玩法中的默认对（优先新澳门·特）。
 * - 已指定渠道、未指定分类 → 该渠道 + 默认分类（rest 已以其它已启用分类开头时不再插默认分类；句首渠道可与 app 默认渠道不同，如 glue「澳」+「马1」→ 新澳门马1 → 新澳门特马1）。
 * - 未指定渠道、句内已带出非默认玩法（如仅有「平特」关键词的「猴平特100」）→ 默认渠道 + 该玩法（见 hoistTrailingCategoryAfterZodiacs），不得再套默认「特」。
 * - 句首为分类别名（如「二连肖虎羊100」「二连虎羊100」）→ 默认渠道 + 规范分类 + 余下正文（见 tryExpandLeadingCategoryAliasWithDefaultGuide）。
 */
function spaceRouteCategoryBeforeLeadingBall(rest) {
  const r = String(rest || '').trim();
  if (!r) return r;
  if (/^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])(?:各|$)/u.test(r)) return ` ${r}`;
  return r;
}

function resolveOrderContentWithDefaultPrefix(db, content, wxGroupId = null) {
  const c = String(content || '').trim();
  if (!c) return c;
  if (contentMatchesAnyRoute(db, c, wxGroupId)) return c;

  const hoistedGuidePlay = hoistLeadingGuideBeforePlayCategory(db, c, wxGroupId);
  if (hoistedGuidePlay !== c) return hoistedGuidePlay;

  const hoistedEarly = hoistTrailingCategoryAfterZodiacs(db, c);
  if (contentMatchesAnyRoute(db, hoistedEarly, wxGroupId)) return hoistedEarly;

  const { guide: guideRaw, category: categoryRaw } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
  if (!guideRaw || !categoryRaw) return c;
  const ok = db
    .prepare(
      `SELECT 1 FROM cmd_routes
       WHERE is_active = 1 AND guide_word = ? AND category_word = ?
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
       LIMIT 1`
    )
    .get(guideRaw, categoryRaw);
  if (!ok) return c;
  const ng = normalizeGuideWord(guideRaw);
  if (!ng || !categoryRaw) return c;

  const sortedGuidePrefixes = buildSortedGuideRoutePrefixes(db);
  for (const { prefix: gp, guideRaw: matchedGuideRaw } of sortedGuidePrefixes) {
    if (!c.startsWith(gp)) continue;
    const rest = c.slice(gp.length).trim();
    const ngLocal = normalizeGuideWord(matchedGuideRaw);
    const defCat = defaultCategoryWordForGuide(db, matchedGuideRaw, wxGroupId);
    if (!defCat) continue;
    if (!rest) return `${ngLocal}${defCat}`;
    if (rest.startsWith(defCat)) return `${ngLocal}${rest}`;
    const cats = listCategoryPrefixesForGuideOrderParse(db, matchedGuideRaw, wxGroupId);
    for (const cat of cats) {
      if (rest.startsWith(cat)) return c;
    }
    return `${ngLocal}${defCat}${spaceRouteCategoryBeforeLeadingBall(rest)}`;
  }

  // 已含玩法分类起首（如 hoist 后的「平特猴100」）：只补渠道，勿插默认类型
  const hoistCats = listHoistCandidateCategories(db).sort((a, b) => b.length - a.length);
  for (const cat of hoistCats) {
    if (!c.startsWith(cat)) continue;
    const withGuide = `${ng}${c}`;
    if (contentMatchesAnyRoute(db, withGuide, wxGroupId)) return withGuide;
  }

  const aliasExpanded = tryExpandLeadingCategoryAliasWithDefaultGuide(db, c, ng, wxGroupId);
  if (aliasExpanded) return aliasExpanded;

  /** 句首已是规范分类词（如四连肖）时禁止再套默认「特」 */
  for (const { suf, canon } of listCategorySuffixesToCanonical(db)) {
    if (!c.startsWith(suf)) continue;
    const rest = c.slice(suf.length);
    const candidate = `${ng}${canon}${rest}`;
    if (routeCandidateAccepted(db, candidate, wxGroupId)) return candidate;
  }

  /** 句首已是其它渠道（如「香港12…」）时只补该渠道的默认分类，勿再套 app 默认「新澳门特」 */
  for (const { prefix: gp, guideRaw: matchedGuideRaw } of buildSortedGuideRoutePrefixes(db)) {
    if (gp === ng || !c.startsWith(gp)) continue;
    const rest = c.slice(gp.length).trim();
    const ngLocal = normalizeGuideWord(matchedGuideRaw);
    const defCat = defaultCategoryWordForGuide(db, matchedGuideRaw, wxGroupId);
    if (!defCat) continue;
    if (!rest) return `${ngLocal}${defCat}`;
    if (rest.startsWith(defCat)) return `${ngLocal}${rest}`;
    const cats = listCategoryPrefixesForGuideOrderParse(db, matchedGuideRaw, wxGroupId);
    for (const cat of cats) {
      if (rest.startsWith(cat)) return c;
    }
    return `${ngLocal}${defCat}${spaceRouteCategoryBeforeLeadingBall(rest)}`;
  }

  if (contentShouldSkipDefaultTeCategory(db, c)) {
    const aliasExpanded = tryExpandLeadingCategoryAliasWithDefaultGuide(db, c, ng, wxGroupId);
    if (aliasExpanded) return aliasExpanded;
    return `${ng}${c}`;
  }

  return `${ng}${categoryRaw}${spaceRouteCategoryBeforeLeadingBall(c)}`;
}

/** 句首已是玩法/波色/平特等时勿套默认「特」 */
function lineHasLeadingPlayCategoryHint(db, unprefixed) {
  const c = String(unprefixed || '').trim();
  if (!c || !db) return false;
  for (const { suf } of listCategorySuffixesToCanonical(db)) {
    if (suf && c.startsWith(suf)) return true;
  }
  if (/^(?:单|双)(?:各|\d)/u.test(c)) return true;
  return /^(?:[绿红蓝]波|平特|平尾|三有|三友|四有|四友|单双|连肖|连码|[二三四五]连)/u.test(c);
}

/** 句内已含玩法/波色/尾头/渠道简称等时勿插默认「特」 */
function contentShouldSkipDefaultTeCategory(db, unprefixed) {
  if (lineHasLeadingPlayCategoryHint(db, unprefixed)) return true;
  const c = String(unprefixed || '').trim();
  if (!c) return false;
  if (/^(?:新奥|新奥特|港|香|澳|噢|门[，,])/u.test(c)) return true;
  if (/(?:三中三|二中二|五不中|连码|平特|单双|半波|[二三四五]连肖|[绿红蓝]波|家肖|野肖|家禽|野兽|大数|小数|\d头|\d尾)/u.test(c)) {
    return true;
  }
  if (/^[红蓝绿]/.test(c) && /各/u.test(c)) return true;
  if (/^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])(?:[.。．、\-\s][\d]{1,2})+.*各/u.test(c)) return true;
  return false;
}

/**
 * 「澳门平特三连肖…」「港四连肖…」：渠道简称 + 玩法分类起首，补全为可匹配路由前缀。
 */
function hoistLeadingGuideBeforePlayCategory(db, content, wxGroupId = null) {
  const c0 = String(content || '').trim();
  if (!c0 || contentMatchesAnyRoute(db, c0, wxGroupId)) return c0;
  const suffixes = buildGuideChannelTrailingSuffixes(db);
  for (const suf of suffixes) {
    if (!suf || !c0.startsWith(suf)) continue;
    const rest = c0.slice(suf.length).trimStart();
    if (!rest) continue;
    let gNorm = normalizeGuideWord(resolveGuideHintWithSynonyms(db, suf) || suf);
    if (String(suf).trim() === '澳门') {
      const gRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_guide_word');
      const prefer = normalizeGuideWord(String(gRow?.value || '').trim());
      if (prefer && assertActiveGlobalOrderRoute(db, prefer, '特')) gNorm = prefer;
      else if (assertActiveGlobalOrderRoute(db, '新澳门', '特')) gNorm = '新澳门';
    }
    for (const { suf: catSuf, canon } of listCategorySuffixesToCanonical(db)) {
      if (!catSuf || !rest.startsWith(catSuf)) continue;
      const candidate = `${gNorm}${canon}${rest.slice(catSuf.length)}`;
      if (routeCandidateAccepted(db, candidate, wxGroupId)) return candidate;
    }
  }
  return c0;
}

/** 路由展示/日志用：主引导词 + 分类词（不再使用 route_name） */
export function cmdRouteDisplayLabel(route) {
  const g = String(route?.guide_word ?? '').trim();
  const c = String(route?.category_word ?? '').trim();
  const joined = `${g}${c}`.trim();
  return joined || 'route';
}

function parseNumber(v) {
  const s = String(v ?? '').trim();
  if (!s) return null;
  /** 下单：ASCII/全角「-」不作为负号，仅作普通字符 */
  if (/^[\u002D\uFF0D]/.test(s)) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function uniqueNumbers(list) {
  return [...new Set(list.map((x) => Number(x)).filter((n) => Number.isFinite(n)))];
}

/** 号码列表中「两数字间」可出现的任意分隔（无计算语义，一律视作列表通配） */
const ORDER_TARGET_INTERT_DIGIT_SEP_CLASS =
  '.\\-*＊_\\\\、,，;；/｜\\s\\uff0c\\uff0d\\uff0f\\u3001＋=%<>^&$#@_｀';

/** 号码列表中的任意分隔符 → 空格，便于「1.2.6.9」「1#2=3」「11+17+27」等解析；去掉首部点/逗号便于「.44.43…」 */
function normalizeOrderTargetSeparators(s) {
  let t = String(s || '').trim();
  const leadTrail = new RegExp(`^[${ORDER_TARGET_INTERT_DIGIT_SEP_CLASS}]+`, 'g');
  const between = new RegExp(
    `(\\d)(?:[${ORDER_TARGET_INTERT_DIGIT_SEP_CLASS}]|/)+(?=\\d)`,
    'g'
  );
  const trail = new RegExp(`[${ORDER_TARGET_INTERT_DIGIT_SEP_CLASS}]+$`, 'g');
  t = t.replace(leadTrail, '');
  t = t.replace(between, '$1 ').replace(/\s+/g, ' ').trim();
  t = t.replace(trail, '');
  return t.trim();
}

/** 「双数/单数」口语 → 库内集合名「双/单」（与「单双」玩法一致） */
function normalizeOddEvenColloquialTargets(s) {
  return String(s || '').replace(/双数/g, '双').replace(/单数/g, '单');
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function listInstructionAliasPhrases(db, canonicalWord) {
  const key = String(canonicalWord || '').trim();
  if (!db || !key) return [];
  try {
    const fromDb = listSynonymAliasesForCanonical(db, 'instruction', key).filter(Boolean);
    return fromDb.sort((a, b) => b.length - a.length);
  } catch {
    return [];
  }
}

function instructionAltPattern(db, canonicalWord) {
  const phrases = listInstructionAliasPhrases(db, canonicalWord);
  if (phrases.length === 0) return '';
  return phrases.map(escapeRegExp).join('|');
}

/** 「查设置」「查玩法」等与完整指令等价（查询类加「查」前缀） */
function expandChaInstructionAliases(raw, db) {
  let s0 = String(raw || '').trim();
  const compact0 = s0.replace(/\s+/g, '');
  const oneToOne = [
    ['查设置', '查询群配置'],
    ['查询设置', '查询群配置'],
    ['查玩法', '玩法'],
    ['查询玩法', '玩法'],
    ['查赔率', '赔率表'],
  ];
  for (const [a, b] of oneToOne) {
    if (compact0 === a) return b;
  }
  if (compact0.startsWith('查') && compact0.length > 2) {
    const rest = compact0.slice(1);
    const altQ = instructionAltPattern(db, 'query_group_config');
    if (altQ && new RegExp(`^(?:${altQ})$`, 'u').test(rest)) {
      return rest;
    }
    const altOdds = instructionAltPattern(db, 'odds_table');
    if (altOdds && new RegExp(`^(?:${altOdds})$`, 'u').test(rest)) {
      return rest;
    }
    const altPlay = instructionAltPattern(db, 'list_play_modes');
    if (altPlay && new RegExp(`^(?:${altPlay})$`, 'u').test(rest)) {
      return rest;
    }
    const altOrders = instructionAltPattern(db, 'order_query');
    if (altOrders && new RegExp(`^(?:${altOrders})$`, 'u').test(rest)) {
      return rest;
    }
    const altDetail = instructionAltPattern(db, 'order_query_detail');
    if (altDetail && new RegExp(`^(?:${altDetail})$`, 'u').test(rest)) {
      return rest;
    }
  }
  return s0;
}

/** 群/私聊：全文 trimmed 后与帮助类指令一一对应 */
export function matchesHelpInstruction(text, db) {
  const alt = instructionAltPattern(db, 'help');
  if (!alt) return false;
  return new RegExp(`^(?:${alt})$`, 'u').test(String(text || '').trim());
}

function getAlgoAliasData(db) {
  return getParseCache(db, 'algoAliasData', () => buildAlgoAliasData(db));
}

function stripTrailingAlgoToken(s, orderedTokens) {
  const t = String(s || '').trimEnd();
  for (const tok of orderedTokens) {
    if (t.endsWith(tok)) {
      return { targetRaw: t.slice(0, -tok.length).trimEnd(), algoToken: tok };
    }
  }
  return null;
}

/** 目标与算法词之间仅噪声时仍剥出算法词（如 01#02$各数100） */
function stripTrailingAlgoTokenPermissive(s, orderedTokens) {
  const t0 = trimTrailingOrderNoise(String(s || '').trimEnd());
  if (!t0) return null;
  for (const tok of orderedTokens) {
    if (!t0.endsWith(tok)) continue;
    const end = t0.length - tok.length;
    let j = end;
    while (j > 0 && isOrderNoiseChar(t0[j - 1])) j -= 1;
    if (j === end) continue;
    const head = t0.slice(0, j).trimEnd();
    if (!head) continue;
    return { targetRaw: head, algoToken: tok };
  }
  return null;
}

function splitItemList(targetRaw) {
  const normalized = normalizeOrderTargetSeparators(String(targetRaw || ''));
  const parts = normalized
    .split(/[,\s，、]+/)
    .map((x) => x.trim())
    .filter(Boolean);
  if (parts.length === 0) return [];
  const nums = parts.map(parseNumber);
  if (nums.some((n) => n == null)) return [];
  return nums;
}

/**
 * 集合口语尾缀：如「红波」对应库中集合名「红」（波色）；校验 category 避免「家禽波」误命中「家禽」。
 */
const COLLECTION_TRAILING_SUFFIX_RULES = [{ suffix: '波', categoryMustBe: '波色' }];

function parseSetNames(db, targetRaw, allSetNames) {
  let clean = String(targetRaw || '').trim();
  if (db) clean = expandCollectionAliasesInTargetText(db, clean);
  if (!clean) return [];
  const directByDelimiters = clean
    .split(/[,\s，、·•\u30FB\uFF65]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (directByDelimiters.length > 1 && directByDelimiters.every((n) => allSetNames.includes(n))) {
    return directByDelimiters;
  }
  const sorted = [...allSetNames].sort((a, b) => b.length - a.length);
  const tryGreedy = (segment) => {
    const s = String(segment || '').trim();
    if (!s) return null;
    const result = [];
    let cursor = s;
    while (cursor) {
      const name = sorted.find((n) => cursor.startsWith(n));
      if (!name) return null;
      result.push(name);
      cursor = cursor.slice(name.length);
    }
    return result;
  };

  let parsed = tryGreedy(clean);
  if (parsed) return parsed;

  if (db) {
    for (const rule of COLLECTION_TRAILING_SUFFIX_RULES) {
      const suf = String(rule.suffix || '');
      const catMust = String(rule.categoryMustBe || '').trim();
      if (!suf || clean.length <= suf.length || !clean.endsWith(suf)) continue;
      const trimmed = clean.slice(0, -suf.length).trim();
      if (!trimmed) continue;
      const cand = tryGreedy(trimmed);
      if (!cand || cand.length === 0) continue;
      if (catMust && !collectionSetNamesAllInCategory(db, cand, catMust)) {
        const waveColors = cand.length > 0 && cand.every((n) => ['红', '绿', '蓝'].includes(n));
        if (!waveColors) continue;
      }
      return cand;
    }
  }

  return [];
}

/** 口语「红蓝数」→ 集合并集运算符；保留「龙猪虎的红蓝」供生肖∩波色解析 */
function expandColloquialWaveTargetText(s) {
  let t = String(s || '').replace(/红蓝双/g, '红|蓝|双');
  t = t.replace(/红蓝数/g, '红|蓝');
  t = t.replace(/(?<![\u4e00-\u9fff的])红蓝(?!数|双)/g, '红|蓝');
  t = t.replace(/红蓝绿波/g, '红|蓝|绿');
  return t;
}

/** 「龙猪虎的红蓝数各50」：生肖 ∩（红∪蓝）号码 */
function tryResolveZodiacDeWaveTargetItems(db, pre, allSetNames) {
  void allSetNames;
  const zx = PREPROC_ZODIAC_CLASS;
  const m = String(pre || '')
    .trim()
    .match(new RegExp(`^([${zx}]+)的\\s*(红蓝|红|蓝|绿)\\s*(?:波|数)?\\s*$`, 'u'));
  if (!m) return null;
  const zodiacBalls = [];
  for (const z of parseZodiacTokens(m[1])) {
    zodiacBalls.push(...zodiacBallNumbersForOrder(z, new Date(), 1, 49));
  }
  const zSet = new Set(zodiacBalls);
  const colorSets = m[2] === '红蓝' ? ['红', '蓝'] : [m[2]];
  let colorBalls = [];
  for (const sn of colorSets) {
    colorBalls.push(...resolveSetItems(db, sn));
  }
  const hit = uniqueNumbers(colorBalls.filter((b) => zSet.has(b)));
  if (hit.length > 0) return hit;
  /** 生肖与波色无交集时（如口播「龙猪虎的红蓝」实指红+蓝波号码）→ 按红/蓝/绿波全集 */
  if (colorBalls.length > 0) return uniqueNumbers(colorBalls);
  return null;
}

/** 是否所有集合名在库中均为指定 set_category（全局库 wx_group_id IS NULL） */
function collectionSetNamesAllInCategory(db, setNames, categoryWord) {
  const cat = String(categoryWord || '').trim();
  if (!db || !cat || !Array.isArray(setNames) || setNames.length === 0) return false;
  const placeholders = setNames.map(() => '?').join(',');
  const rows = db
    .prepare(
      `SELECT set_name, set_category FROM cmd_collections
       WHERE wx_group_id IS NULL AND is_active = 1 AND set_name IN (${placeholders})`
    )
    .all(...setNames);
  if (rows.length !== setNames.length) return false;
  return rows.every((r) => String(r?.set_category || '').trim() === cat);
}

function parseZodiacTokens(targetRaw) {
  const clean = String(targetRaw || '').trim();
  if (!clean) return [];
  const zodiacChars = new Set(ZODIAC_ORDER);
  const byDelimiters = clean
    .split(/[,\s，、·•]+/)
    .map((x) => x.trim())
    .filter(Boolean);
  if (
    byDelimiters.length > 0 &&
    byDelimiters.every((x) => zodiacChars.has(normalizeZodiacHanChar(x)))
  ) {
    return byDelimiters.map((x) => normalizeZodiacHanChar(x));
  }
  const compact = clean.replace(/[,\s，、·•]/g, '');
  if (!compact) return [];
  const chars = [...compact].map(normalizeZodiacHanChar);
  if (!chars.every((x) => zodiacChars.has(x))) return [];
  return chars;
}

/** 整段（去分隔符后）是否仅为连续生肖单字 */
function isCompactZodiacOnly(s) {
  const t = String(s || '').replace(/[,\s，、·•]/g, '');
  if (!t) return false;
  const zt = parseZodiacTokens(t);
  return zt.length > 0 && zt.length === [...t].length;
}

/** 全局路由里的分类词，长的优先，便于先匹配「特肖马」再「特肖」 */
function listHoistCandidateCategories(db) {
  return db
    .prepare(
      `SELECT DISTINCT category_word FROM cmd_routes
       WHERE is_active = 1
         AND TRIM(IFNULL(category_word,'')) <> ''
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')`
    )
    .all()
    .map((r) => String(r.category_word || '').trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
}

/** 「新奥特」误插单字分类后紧跟真实分类+生肖时，剥掉多出来的「特」等 */
function stripWrongLeadingCategoryBeforeZodiacs(mid, targetCat, allCats) {
  const m = String(mid || '').trim();
  const sorted = [...allCats].sort((a, b) => b.length - a.length);
  for (const sc of sorted) {
    if (!sc || sc === targetCat) continue;
    if (!m.startsWith(sc)) continue;
    const rest = m.slice(sc.length);
    const zc = rest.replace(/[,\s，、·•]/g, '');
    if (zc && isCompactZodiacOnly(zc)) return rest.trim();
  }
  return m;
}

/**
 * 口语「龙猪猴特肖各十」：生肖串 + 玩法分类 + 金额。
 * 规范为「默认渠道 + 分类 + 生肖串 + 其余」，并纠正「新奥特龙猪猴特肖」类误拼。
 * 「特」（特码）与「平特」等在路由里是不同 category_word，互不相同；提起时优先长分类，避免平特句粘在默认「特」后。
 */
function hoistTrailingCategoryAfterZodiacs(db, content) {
  const c0 = String(content || '').trim();
  if (!c0 || contentMatchesAnyRoute(db, c0)) return c0;

  const cats = listHoistCandidateCategories(db);
  if (cats.length === 0) return c0;

  const tryHoistUnprefixed = (c) => {
    const body = String(c || '').trim();
    if (!body) return null;
    const sortedCats = [...cats].sort((a, b) => b.length - a.length);
    for (const cat of sortedCats) {
      if (!body.startsWith(cat)) continue;
      const after = body.slice(cat.length);
      let i = 0;
      const chs = [...after];
      while (i < chs.length) {
        const nz = normalizeZodiacHanChar(chs[i]);
        if (!ZODIAC_ORDER.includes(nz)) break;
        i += 1;
      }
      if (i >= 2) {
        const zRun = after.slice(0, i);
        if (isCompactZodiacOnly(zRun)) {
          const tail = after.slice(i);
          return `${cat}${zRun}${tail}`;
        }
      }
    }
    for (const cat of cats) {
      const idx = body.indexOf(cat);
      if (idx < 1) continue;
      const headRaw = body.slice(0, idx);
      const tail = body.slice(idx + cat.length).trim();
      const mid = stripWrongLeadingCategoryBeforeZodiacs(headRaw.trim(), cat, cats);
      const zCompact = mid.replace(/[,\s，、·•]/g, '');
      if (!isCompactZodiacOnly(zCompact)) continue;
      return `${cat}${zCompact}${tail}`;
    }
    return null;
  };

  const gRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_guide_word');
  const ng = normalizeGuideWord(String(gRow?.value || '').trim());

  if (!ng) {
    const h0 = tryHoistUnprefixed(c0);
    return h0 || c0;
  }

  if (c0.startsWith(ng)) {
    const rest = c0.slice(ng.length).trim();
    // 先尝试提起「默认特 + 猴平特100」类误拼，避免误信 rest 已以合法分类开头而直接返回
    const h = tryHoistUnprefixed(rest);
    if (h) return `${ng}${h}`;
    if (cats.some((cat) => rest.startsWith(cat))) return c0;
    return c0;
  }

  const h = tryHoistUnprefixed(c0);
  if (h) return `${ng}${h}`;
  return c0;
}

/**
 * 未写渠道时「31.43.41香港各20」类：球号串后直接跟渠道词再「各」→ 视为该渠道下单，未写玩法则用默认分类（与 app_settings 默认分类一致，一般为特）。
 * 须在 resolveOrderContentWithDefaultPrefix 之前调用，避免先被默认成「新澳门特」。
 */
function hoistEmbeddedGuideChannelBeforeBallsEach(db, content, wxGroupId = null) {
  const c0 = String(content || '').trim();
  if (!c0 || contentMatchesAnyRoute(db, c0, wxGroupId)) return c0;

  let s = preNormalizeLottoTwoDigitDotChains(c0);
  const suffixes = buildGuideChannelTrailingSuffixes(db);
  const { category: defaultCatRaw } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
  const cat = String(defaultCatRaw || '特').trim() || '特';

  for (const suf of suffixes) {
    if (!suf) continue;
    const esc = escapeRegExp(suf);
    const m = s.match(new RegExp(`^([\\d\\s.，、·•]+)${esc}(各.*)$`, 'u'));
    if (!m) continue;
    const ballsRaw = m[1].trimEnd();
    const tailFromGe = m[2];
    const ballsNorm = preNormalizeLottoTwoDigitDotChains(ballsRaw);
    if (!isNumericBallTargetListOnly(ballsNorm)) continue;

    let canon = resolveGuideHintWithSynonyms(db, suf);
    if (!canon) canon = String(suf).trim();
    let gNorm = normalizeGuideWord(canon);
    if (!gNorm) continue;
    if (!assertActiveGlobalOrderRoute(db, gNorm, cat)) {
      if (String(suf).trim() === '澳门') {
        const gRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_guide_word');
        const prefer = normalizeGuideWord(String(gRow?.value || '').trim());
        if (prefer && assertActiveGlobalOrderRoute(db, prefer, cat)) gNorm = prefer;
        else if (assertActiveGlobalOrderRoute(db, '新澳门', cat)) gNorm = '新澳门';
        else if (assertActiveGlobalOrderRoute(db, '老澳门', cat)) gNorm = '老澳门';
        else continue;
      } else continue;
    }
    if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
      const allow = listActiveCmdRoutesForOrderParse(db, wxGroupId);
      const ok = allow.some((r) => normalizeGuideWord(r.guide_word) === gNorm && r.category_word === cat);
      if (!ok) continue;
    }
    const ballsTxt = normalizeOrderTargetSeparators(ballsNorm.trim());
    return `${gNorm}${cat}${ballsTxt}${tailFromGe}`;
  }
  return c0;
}

function intersectNumbers(a, b) {
  const bSet = new Set(b);
  return a.filter((x) => bSet.has(x));
}

function diffNumbers(a, b) {
  const bSet = new Set(b);
  return a.filter((x) => !bSet.has(x));
}

function applyAlgo(items, algoToken, value, categoryWord = '') {
  const algo = String(algoToken || '').trim();
  const cat = String(categoryWord || '').trim();
  // 下单语义：算法决定金额符号/取值，不应把“号码”参与金额计算
  if (algo === '各') {
    /** 平特连码：一组 2～3 个球号共用一个金额（各组10），非每球各 10 */
    if (cat === '连码' && items.length >= 2 && items.length <= 3) {
      return items.map((item, i) => ({ item, value: i === 0 ? value : 0 }));
    }
    return items.map((item) => ({ item, value }));
  }
  if (algo === '加' || algo === '+') {
    return items.map((item) => ({ item, value }));
  }
  if (algo === '减') {
    return items.map((item) => ({ item, value: -value }));
  }
  if (algo === '乘' || algo === '*' || algo === 'x' || algo === 'X') {
    return items.map((item) => ({ item, value }));
  }
  if (algo === '除' || algo === '/') {
    return items.map((item) => ({ item, value: value === 0 ? null : value }));
  }
  return [];
}

function parseStep(step) {
  const m = String(step || '')
    .trim()
    .match(/^([\p{L}_][\p{L}\p{N}_]*)(?:\((.*)\))?$/u);
  if (!m) return { name: String(step || '').trim(), args: [] };
  const args = m[2]
    ? m[2]
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
    : [];
  return { name: m[1], args };
}

function parseDateArg(raw) {
  const s = String(raw || '').trim();
  if (!s) return new Date();
  const normalized = s.replace(/\./g, '-').replace(/\//g, '-');
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return new Date();
  return d;
}

function isLikelyDateArg(raw) {
  const s = String(raw || '').trim();
  return /^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}$/.test(s);
}

const ZODIAC_ORDER = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪'];

/** 繁体/异体 → 与 ZODIAC_ORDER 一致的单字（微信或粘贴语文可能混用） */
const ZODIAC_CHAR_ALIASES = {
  龍: '龙',
  馬: '马',
  豬: '猪',
  雞: '鸡',
  鷄: '鸡',
  𤠣: '猴',
};

function normalizeZodiacHanChar(c) {
  const ch = String(c || '');
  if (!ch) return ch;
  return ZODIAC_CHAR_ALIASES[ch] || ch;
}

/** 整段文本中的生肖异体字替换（须在 PREPROC_ZODIAC_CLASS 正则之前执行） */
export function normalizeZodiacAliasCharsInText(s) {
  let t = String(s || '');
  for (const [from, to] of Object.entries(ZODIAC_CHAR_ALIASES)) {
    if (!from || !to || from === to) continue;
    t = t.split(from).join(to);
  }
  return t;
}

/** 特肖/特肖马按肖下注：不落具体球号；item_value 用 51–62 表示十二生肖（与特码 01–49 区分） */
const TE_XIAO_ZODIAC_ITEM_MIN = 51;
const TE_XIAO_ZODIAC_ITEM_MAX = 62;

function teXiaoZodiacItemCode(zodiacHan) {
  const z = normalizeZodiacHanChar(String(zodiacHan || '').trim());
  const idx = ZODIAC_ORDER.indexOf(z);
  return idx >= 0 ? TE_XIAO_ZODIAC_ITEM_MIN + idx : NaN;
}

function isTeXiaoZodiacItemSlot(itemValue) {
  const n = Math.floor(Number(itemValue));
  return Number.isFinite(n) && n >= TE_XIAO_ZODIAC_ITEM_MIN && n <= TE_XIAO_ZODIAC_ITEM_MAX;
}

function zodiacFromTeXiaoItemSlot(itemValue) {
  const n = Math.floor(Number(itemValue));
  if (!isTeXiaoZodiacItemSlot(n)) return '';
  return ZODIAC_ORDER[n - TE_XIAO_ZODIAC_ITEM_MIN] || '';
}

function zodiacOfYear(year) {
  const index = ((year - 4) % 12 + 12) % 12;
  return ZODIAC_ORDER[index];
}

function zodiacIndexOfYear(year) {
  return ((Number(year) - 4) % 12 + 12) % 12;
}

/**
 * 特码 01–49：按结单自然年，以当年生肖为起点逆序轮转（01 属当年肖，该肖共 5 个号）。
 * 与同文件中「出生年份生肖」的 zodiacOfYear(y-age) 不同，二者不可混用。
 */
export function zodiacOfBallForSettlementYear(ball, year) {
  const n = Math.floor(Number(ball));
  if (!Number.isFinite(n) || n < 1) return '';
  const yi = zodiacIndexOfYear(year);
  const j = (yi - (n - 1) + 12 * 10) % 12;
  return ZODIAC_ORDER[j] || '';
}

function zodiacAgesForDate(zodiac, refDate, minAge = 1, maxAge = 120) {
  const z = normalizeZodiacHanChar(String(zodiac || '').trim());
  if (!ZODIAC_ORDER.includes(z)) return [];
  const y = refDate.getFullYear();
  const out = [];
  for (let age = minAge; age <= maxAge; age += 1) {
    if (zodiacOfYear(y - age) === z) out.push(age);
  }
  return out;
}

/** 特码下单：列出 refDate 所在年份、区间内属于该生肖的全部球号（01–49 轮转规则见 zodiacOfBallForSettlementYear） */
function zodiacBallNumbersForOrder(zodiac, refDate, minBall = 1, maxBall = 49) {
  const z = normalizeZodiacHanChar(String(zodiac || '').trim());
  if (!ZODIAC_ORDER.includes(z)) return [];
  const y = refDate.getFullYear();
  const lo = Math.max(1, Math.floor(minBall));
  const hi = Math.min(49, Math.floor(maxBall));
  const out = [];
  for (let n = lo; n <= hi; n += 1) {
    if (zodiacOfBallForSettlementYear(n, y) === z) out.push(n);
  }
  return out;
}

function zodiacByAge(age, refDate) {
  const n = Number(age);
  if (!Number.isFinite(n) || n < 0) return '';
  return zodiacOfYear(refDate.getFullYear() - Math.floor(n));
}

function asObjectSeries(current) {
  return current
    .map((x) => {
      if (typeof x === 'object' && x !== null && 'value' in x) {
        const n = Number(x.value);
        if (!Number.isFinite(n)) return null;
        return { item: x.item, value: n };
      }
      const n = Number(x);
      if (!Number.isFinite(n)) return null;
      return { item: n, value: n };
    })
    .filter(Boolean);
}

function toNumericSeries(current) {
  return current
    .map((x) => (typeof x === 'object' && x !== null ? Number(x.value) : Number(x)))
    .filter((n) => Number.isFinite(n));
}

function mapSeries(current, fn) {
  return current.map((x) => {
    if (typeof x === 'object' && x !== null && 'value' in x) {
      return { ...x, value: fn(Number(x.value), x) };
    }
    const n = Number(x);
    return Number.isFinite(n) ? fn(n, x) : x;
  });
}

function resolveArgNumber(arg, context) {
  const token = String(arg || '').trim();
  if (!token) return 0;
  if (token === 'value') return Number(context.value || 0);
  const n = Number(token);
  return Number.isFinite(n) ? n : 0;
}

function parseSetRefToken(token) {
  const m = String(token || '').trim().match(/^(?:集合|set)\.(.+)$/i);
  return m ? String(m[1] || '').trim() : '';
}

function parseVarRefToken(token) {
  const m = String(token || '').trim().match(/^(?:变量|var)\.(.+)$/i);
  return m ? String(m[1] || '').trim() : '';
}

function resolveVarNumber(arg, context) {
  const token = String(arg || '').trim();
  const varName = parseVarRefToken(token);
  if (varName) {
    const n = Number(context.resolveVar ? context.resolveVar(varName) : 0);
    return Number.isFinite(n) ? n : 0;
  }
  return resolveArgNumber(token, context);
}

function resolveItemsArg(arg, context, fallback) {
  const token = String(arg || '').trim();
  if (!token) return fallback;
  const setName = parseSetRefToken(token);
  if (setName) {
    return uniqueNumbers(context.resolveSet(setName)).map((n) => ({ item: n, value: n }));
  }
  return fallback;
}

function normalizePipelineOutput(current) {
  if (!Array.isArray(current)) return [];
  return current.map((x) =>
    typeof x === 'object' && x !== null && 'value' in x
      ? { item: x.item, value: x.value }
      : { item: Number(x), value: Number(x) }
  );
}

function applyFormulaPipeline(pipelineExpr, context, depth = 0) {
  if (depth > MAX_PIPELINE_DEPTH) return [];
  const expr = String(pipelineExpr || '').trim() || 'identity|algo';
  if (!assertBalancedParens(expr)) return [];
  const segments = splitPipelineByTopLevelPipe(expr);
  let current = context.items;

  for (const seg of segments) {
    const trimmed = seg.trim();
    if (!trimmed) continue;

    const stripped = stripParenLayersToInnerPipeline(trimmed);
    if (stripped !== trimmed) {
      current = applyFormulaPipeline(stripped, { ...context, items: current }, depth + 1);
      continue;
    }

    const { name: rawName, args } = parseStep(stripped);
    const name = canonicalStepName(rawName);
    if (name === 'identity') {
      continue;
    }
    if (name === 'algo') {
      current = applyAlgo(current, context.algo, context.value, context.categoryWord);
      continue;
    }
    if (name === 'sum') {
      const total = current.reduce((acc, x) => acc + Number(x.value ?? x), 0);
      current = [{ item: 'SUM', value: total }];
      continue;
    }
    if (name === 'avg') {
      if (current.length === 0) {
        current = [{ item: 'AVG', value: 0 }];
      } else {
        const total = current.reduce((acc, x) => acc + Number(x.value ?? x), 0);
        current = [{ item: 'AVG', value: total / current.length }];
      }
      continue;
    }
    if (name === 'count') {
      current = [{ item: 'COUNT', value: current.length }];
      continue;
    }
    if (name === 'max') {
      const values = toNumericSeries(current);
      current = [{ item: 'MAX', value: values.length ? Math.max(...values) : 0 }];
      continue;
    }
    if (name === 'min') {
      const values = toNumericSeries(current);
      current = [{ item: 'MIN', value: values.length ? Math.min(...values) : 0 }];
      continue;
    }
    if (name === 'round') {
      const digits = Math.max(0, Math.floor(resolveArgNumber(args[0] ?? '0', context)));
      const base = 10 ** digits;
      current = mapSeries(current, (n) => Math.round(n * base) / base);
      continue;
    }
    if (name === 'floor') {
      current = mapSeries(current, (n) => Math.floor(n));
      continue;
    }
    if (name === 'ceil') {
      current = mapSeries(current, (n) => Math.ceil(n));
      continue;
    }
    if (name === 'clamp') {
      const min = resolveArgNumber(args[0], context);
      const max = resolveArgNumber(args[1], context);
      current = mapSeries(current, (n) => Math.max(min, Math.min(max, n)));
      continue;
    }
    if (name === 'unique') {
      const values = uniqueNumbers(toNumericSeries(current));
      current = values.map((n) => ({ item: n, value: n }));
      continue;
    }
    if (name === 'sort_asc') {
      current = asObjectSeries(current).sort((a, b) => a.value - b.value);
      continue;
    }
    if (name === 'sort_desc') {
      current = asObjectSeries(current).sort((a, b) => b.value - a.value);
      continue;
    }
    if (name === 'each_add') {
      const base = args.length >= 2 ? resolveItemsArg(args[0], context, current) : current;
      const by = resolveVarNumber(args.length >= 2 ? args[1] : args[0], context);
      current = mapSeries(base, (n) => n + by);
      continue;
    }
    if (name === 'each_sub') {
      const base = args.length >= 2 ? resolveItemsArg(args[0], context, current) : current;
      const by = resolveVarNumber(args.length >= 2 ? args[1] : args[0], context);
      current = mapSeries(base, (n) => n - by);
      continue;
    }
    if (name === 'each_mul') {
      const base = args.length >= 2 ? resolveItemsArg(args[0], context, current) : current;
      const by = resolveVarNumber(args.length >= 2 ? args[1] : args[0], context);
      current = mapSeries(base, (n) => n * by);
      continue;
    }
    if (name === 'each_div') {
      const base = args.length >= 2 ? resolveItemsArg(args[0], context, current) : current;
      const by = resolveVarNumber(args.length >= 2 ? args[1] : args[0], context);
      current = mapSeries(base, (n) => (by === 0 ? null : n / by));
      continue;
    }
    if (name === 'order') {
      // 显式下单步骤，保持为 item/value 对供落库使用
      current = asObjectSeries(current);
      continue;
    }
    if (name === 'union') {
      let merged = [];
      for (const setName of args) merged.push(...context.resolveSet(setName));
      current = uniqueNumbers(merged);
      continue;
    }
    if (name === 'intersect') {
      if (args.length < 2) continue;
      let out = uniqueNumbers(context.resolveSet(args[0]));
      for (let i = 1; i < args.length; i += 1) {
        out = intersectNumbers(out, uniqueNumbers(context.resolveSet(args[i])));
      }
      current = out;
      continue;
    }
    if (name === 'diff') {
      if (args.length < 2) continue;
      const left = uniqueNumbers(context.resolveSet(args[0]));
      const right = uniqueNumbers(context.resolveSet(args[1]));
      current = diffNumbers(left, right);
      continue;
    }
    if (name === 'pick') {
      const baseSetName = args[0];
      if (!baseSetName) continue;
      const base = context.resolveSet(baseSetName);
      const idx = args
        .slice(1)
        .map((x) => Number(x))
        .filter((x) => Number.isFinite(x));
      current = uniqueNumbers(
        idx.map((i) => base[i - 1]).filter((x) => Number.isFinite(Number(x)))
      );
      continue;
    }
    if (name === 'to_values') {
      current = toNumericSeries(current);
      continue;
    }
    if (name === 'zodiac_age' || name === '生肖岁数') {
      const zodiac = String(args[0] || '').trim();
      const second = args[1] ?? '';
      const third = args[2] ?? '';
      const fourth = args[3] ?? '';
      const hasDateArg = isLikelyDateArg(second);
      const refDate = hasDateArg ? parseDateArg(second) : new Date();
      const minAge = hasDateArg ? resolveArgNumber(third || '1', context) : resolveArgNumber(second || '1', context);
      const maxAge = hasDateArg ? resolveArgNumber(fourth || '120', context) : resolveArgNumber(third || '120', context);
      const ages = zodiacAgesForDate(zodiac, refDate, Math.max(1, Math.floor(minAge)), Math.max(1, Math.floor(maxAge)));
      current = ages.map((age) => ({ item: age, value: age }));
      continue;
    }
    if (name === 'zodiac_age_range' || name === '生肖岁数范围') {
      const zodiac = String(args[0] || '').trim();
      const minAge = Math.max(1, Math.floor(resolveArgNumber(args[1] || '1', context)));
      const maxAge = Math.max(1, Math.floor(resolveArgNumber(args[2] || '120', context)));
      const refDate = parseDateArg(args[3] || '');
      const ages = zodiacAgesForDate(zodiac, refDate, minAge, maxAge);
      current = ages.map((age) => ({ item: age, value: age }));
      continue;
    }
    if (name === 'age_zodiac' || name === '岁数生肖') {
      const age = resolveArgNumber(args[0], context);
      const refDate = parseDateArg(args[1] || '');
      const zodiac = zodiacByAge(age, refDate);
      current = [{ item: `age_${Math.floor(age)}`, value: zodiac || '' }];
    }
  }
  return normalizePipelineOutput(current);
}

export function validateFormulaPipeline(pipelineExpr, depth = 0) {
  if (depth > MAX_PIPELINE_DEPTH) {
    return { ok: false, error: '公式括号嵌套过深' };
  }
  const raw = String(pipelineExpr || '').trim();
  if (!raw) return { ok: false, error: 'pipeline_expr 不能为空' };
  if (!assertBalancedParens(raw)) {
    return { ok: false, error: '括号不成对，请检查 ( ) 是否匹配' };
  }
  const segments = splitPipelineByTopLevelPipe(raw);
  if (segments.length === 0) return { ok: false, error: 'pipeline_expr 至少包含一个步骤' };

  const flatSteps = [];

  for (const seg of segments) {
    const trimmed = seg.trim();
    if (!trimmed) return { ok: false, error: '存在空步骤' };

    const stripped = stripParenLayersToInnerPipeline(trimmed);
    if (stripped !== trimmed) {
      const sub = validateFormulaPipeline(stripped, depth + 1);
      if (!sub.ok) return sub;
      if (Array.isArray(sub.steps)) flatSteps.push(...sub.steps);
      continue;
    }
    if (splitPipelineByTopLevelPipe(stripped).length > 1) {
      const sub = validateFormulaPipeline(stripped, depth + 1);
      if (!sub.ok) return sub;
      if (Array.isArray(sub.steps)) flatSteps.push(...sub.steps);
      continue;
    }

    const { name: rawName, args } = parseStep(stripped);
    const name = canonicalStepName(rawName);
    if (!SUPPORTED_STEPS.has(name)) {
      return { ok: false, error: `不支持的步骤: ${rawName}` };
    }
    flatSteps.push({ name, args });
    const arityRules = {
      pick: [2, Infinity],
      clamp: [2, 2],
      round: [0, 1],
      each_add: [1, 2],
      each_sub: [1, 2],
      each_mul: [1, 2],
      each_div: [1, 2],
      order: [0, 0],
      union: [1, Infinity],
      intersect: [2, Infinity],
      diff: [2, 2],
      zodiac_age: [1, 4],
      age_zodiac: [1, 2],
      生肖岁数: [1, 4],
      岁数生肖: [1, 2],
      zodiac_age_range: [3, 4],
      生肖岁数范围: [3, 4],
    };
    if (arityRules[name]) {
      const [min, max] = arityRules[name];
      if (args.length < min || args.length > max) {
        return { ok: false, error: `步骤 ${name} 参数个数不合法，期望 ${min}~${max}` };
      }
    }
  }
  return { ok: true, steps: flatSteps };
}

function formatResultRowForReply(row) {
  const v = row.value == null ? 'NaN' : row.value;
  return `${row.item}:${v}`;
}

function renderDefaultReply(route, payload) {
  const template =
    route.reply_template || '命中{route}：目标{targets}，算法{algo}，数值{value}，结果{result}';
  const resultText = payload.results.map((x) => formatResultRowForReply(x)).join(' ');
  return template
    .replaceAll('{route}', cmdRouteDisplayLabel(route))
    .replaceAll('{targets}', payload.targetLabel)
    .replaceAll('{algo}', payload.algo)
    .replaceAll('{value}', String(payload.value))
    .replaceAll('{result}', resultText);
}

function resolveSetItems(db, setName, depth = 0) {
  if (depth > 6) return [];
  const row = db
    .prepare(
      `SELECT * FROM cmd_collections
       WHERE is_active = 1 AND set_name = ? AND wx_group_id IS NULL
       ORDER BY id DESC LIMIT 1`
    )
    .get(setName);
  if (!row) return [];
  const directItems = safeJsonParseArray(row.items_json);
  if (directItems.length > 0) {
    const expanded = [];
    for (const raw of directItems) {
      const n = Number(raw);
      if (Number.isFinite(n)) {
        expanded.push(n);
        continue;
      }
      const token = String(raw || '').trim();
      if (!token) continue;
      const zodiacTokens = parseZodiacTokens(token);
      if (zodiacTokens.length === 0) continue;
      for (const z of zodiacTokens) {
        expanded.push(...zodiacBallNumbersForOrder(z, new Date(), 1, 49));
      }
    }
    return uniqueNumbers(expanded);
  }
  const indexes = safeJsonParseArray(row.derive_indexes_json).map((x) => Number(x));
  if (!row.source_set_name || indexes.length === 0) return [];
  const source = resolveSetItems(db, row.source_set_name, depth + 1);
  if (source.length === 0) return [];
  const picked = indexes
    .map((idx) => source[idx - 1])
    .filter((v) => Number.isFinite(Number(v)));
  return uniqueNumbers(picked);
}

function resolveSetNamesWithOperators(db, targetRaw, allSetNames) {
  const text = String(targetRaw || '').trim();
  if (!text) return [];
  const opMatch = text.match(/[&|+\-交并差]/);
  if (!opMatch) {
    const names = parseSetNames(db, text, allSetNames);
    if (names.length === 0) return [];
    let merged = [];
    for (const n of names) merged.push(...resolveSetItems(db, n));
    // 无显式集合运算符时，保留重复项以支持“家禽牛马”这类叠加语义
    return merged;
  }

  const normalized = text
    .replaceAll('并', '|')
    .replaceAll('交', '&')
    .replaceAll('差', '-')
    .replace(/\s+/g, '');
  const waveParity = normalized.match(/^([绿红蓝])[|｜]([单双])$/u);
  if (waveParity) {
    const preset = uniqueNumbers(resolveSetItems(db, `${waveParity[1]}${waveParity[2]}`));
    if (preset.length) return preset;
    const wave = uniqueNumbers(
      resolveSetItems(db, `${waveParity[1]}波`).length
        ? resolveSetItems(db, `${waveParity[1]}波`)
        : resolveSetItems(db, waveParity[1])
    );
    const par = uniqueNumbers(resolveSetItems(db, waveParity[2]));
    if (wave.length && par.length) return intersectNumbers(wave, par);
  }
  const tokens = normalized.split(/([&|+\-])/).filter(Boolean);
  let current = [];
  let pendingOp = '|';
  for (const token of tokens) {
    if (/^[&|+\-]$/.test(token)) {
      pendingOp = token;
      continue;
    }
    const names = parseSetNames(db, token, allSetNames);
    if (names.length === 0) return [];
    let operand = [];
    for (const n of names) operand.push(...resolveSetItems(db, n));
    operand = uniqueNumbers(operand);
    if (current.length === 0) {
      current = operand;
      continue;
    }
    if (pendingOp === '&') current = intersectNumbers(current, operand);
    else if (pendingOp === '-') current = diffNumbers(current, operand);
    else current = uniqueNumbers([...current, ...operand]);
  }
  return uniqueNumbers(current);
}

function resolveMixedTargetItems(db, targetRaw, allSetNames) {
  const text = String(targetRaw || '').trim();
  if (!text) return [];
  const sortedSetNames = [...allSetNames].sort((a, b) => b.length - a.length);
  const unionTokens = text.split(/[,\s，、]+/).map((x) => x.trim()).filter(Boolean);
  const out = [];
  for (const token of unionTokens) {
    const directSet = resolveSetNamesWithOperators(db, token, allSetNames);
    if (directSet.length > 0) {
      out.push(...directSet);
      continue;
    }
    const zodiacOnly = parseZodiacTokens(token);
    if (zodiacOnly.length > 0) {
      for (const z of zodiacOnly) out.push(...zodiacBallNumbersForOrder(z, new Date(), 1, 49));
      continue;
    }
    const n = Number(token);
    if (Number.isFinite(n)) {
      out.push(n);
      continue;
    }
    // 支持“集合名+生肖+数字”连续拼写，例如：家禽牛12
    let cursor = token;
    let ok = true;
    while (cursor) {
      const setName = sortedSetNames.find((name) => cursor.startsWith(name));
      if (setName) {
        out.push(...resolveSetItems(db, setName));
        cursor = cursor.slice(setName.length);
        continue;
      }
      const firstChar = cursor[0];
      const zCanon = normalizeZodiacHanChar(firstChar);
      if (ZODIAC_ORDER.includes(zCanon)) {
        out.push(...zodiacBallNumbersForOrder(zCanon, new Date(), 1, 49));
        cursor = cursor.slice(1);
        continue;
      }
      const mNum = cursor.match(/^\d+(?:\.\d+)?/);
      if (mNum) {
        out.push(Number(mNum[0]));
        cursor = cursor.slice(mNum[0].length);
        continue;
      }
      ok = false;
      break;
    }
    if (!ok) return [];
  }
  // 保留重复号码，使「家禽红单」重叠号在「各」算法下按集合各计一份（如 19 => 5+5）
  return out;
}

function getLianXiaoGroupSize(categoryWord) {
  return inferLianXiaoGroupSizeFromCategoryWord(categoryWord);
}

function isLianXiaoCategory(categoryWord) {
  return isLianXiaoCategoryWord(categoryWord);
}
const TE_XIAO_ZODIAC_ONLY_CATEGORIES = new Set(['特肖', '特肖马']);

function tryResolveConcatenatedWeiTailTargetItems(db, pre, allSetNames) {
  const compact = String(pre || '')
    .replace(/[\s,，、·•\u30FB\uFF65]+/g, '')
    .trim();
  if (!compact || !/(?:\d{1,2}尾)/.test(compact)) return null;
  const names = compact.match(/\d{1,2}尾/g) || [];
  if (names.length === 0) return null;
  let merged = [];
  for (const n of names) {
    let items = [];
    const parsed = parseSetNames(db, n, allSetNames);
    if (parsed.length > 0) {
      for (const sn of parsed) items.push(...resolveSetItems(db, sn));
    } else {
      items = resolveLianMaWeiTuoBallPool(db, n);
    }
    if (items.length === 0) return null;
    merged.push(...items);
  }
  return uniqueNumbers(merged);
}

function resolveCommandTargetItems(db, targetRaw, allSetNames, categoryWord = '') {
  const cat = String(categoryWord || '').trim();
  let pre = normalizeIdeographicCommaSeparators(String(targetRaw || '').trim());
  pre = normalizeOddEvenColloquialTargets(normalizeOrderTargetSeparators(pre));
  pre = pre.replace(/([绿红蓝])\s+([单双])\b/gu, '$1|$2');
  pre = stripEmbeddedBaoxiaoNoise(pre);
  pre = expandColloquialWaveTargetText(pre);
  const itemList = splitItemList(pre);
  if (itemList.length > 0) {
    if (cat === '特') return itemList;
    return uniqueNumbers(itemList);
  }

  const zodiacWave = tryResolveZodiacDeWaveTargetItems(db, pre, allSetNames);
  if (zodiacWave && zodiacWave.length > 0) return zodiacWave;

  const directSets = resolveSetNamesWithOperators(db, pre, allSetNames);
  if (directSets.length > 0) return directSets;

  const weiTails = tryResolveConcatenatedWeiTailTargetItems(db, pre, allSetNames);
  if (weiTails && weiTails.length > 0) return weiTails;

  if (isLianXiaoCategory(cat)) {
    const zCompact = pre.replace(/[,\s，、·•。.]/g, '');
    if (zCompact && isCompactZodiacOnly(zCompact)) {
      return [0];
    }
  }

  if (TE_XIAO_ZODIAC_ONLY_CATEGORIES.has(cat)) {
    const zTx = parseZodiacTokens(pre);
    if (zTx.length > 0) {
      const codes = [];
      let ok = true;
      for (const z of zTx) {
        const code = teXiaoZodiacItemCode(z);
        if (!Number.isFinite(code)) {
          ok = false;
          break;
        }
        codes.push(code);
      }
      if (ok && codes.length > 0) return uniqueNumbers(codes);
      return [];
    }
  }

  const zodiacTokens = parseZodiacTokens(pre);
  if (zodiacTokens.length > 0) {
    const now = new Date();
    let ages = [];
    for (const zodiac of zodiacTokens) ages.push(...zodiacBallNumbersForOrder(zodiac, now, 1, 49));
    return uniqueNumbers(ages);
  }

  return resolveMixedTargetItems(db, pre, allSetNames);
}

/** 契约/预览：将目标段解析为 01–49 球号列表（含集合交并、生肖展号、红|单 等） */
export function resolveOrderTargetBallNumbers(db, targetRaw, categoryWord = '特') {
  if (!db) return [];
  const allSetNames = db
    .prepare(
      `SELECT DISTINCT set_name FROM cmd_collections
       WHERE is_active = 1 AND (wx_group_id IS NULL OR trim(coalesce(wx_group_id,'')) = '')`
    )
    .all()
    .map((x) => String(x.set_name || '').trim())
    .filter(Boolean);
  return resolveCommandTargetItems(db, targetRaw, allSetNames, categoryWord);
}

function collapseResultRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  const map = new Map();
  for (const row of rows) {
    const item = Number(row?.item);
    const value = Number(row?.value);
    if (!Number.isFinite(item) || !Number.isFinite(value)) continue;
    const tl = String(row?.targetLabel ?? '').trim();
    const key = item === 0 && tl ? `0:${tl}` : String(item);
    const prev = Number(map.get(key) || 0);
    map.set(key, prev + value);
  }
  return Array.from(map.entries())
    .map(([key, value]) => {
      if (key.startsWith('0:')) {
        return { item: 0, value, targetLabel: key.slice(2) };
      }
      return { item: Number(key), value };
    })
    .sort(
      (a, b) =>
        a.item - b.item || String(a.targetLabel || '').localeCompare(String(b.targetLabel || ''), 'zh-CN')
    );
}

function sumPayloadResults(payload) {
  const rows = payload?.results;
  if (!Array.isArray(rows)) return 0;
  return rows.reduce((acc, r) => acc + Number(r?.value || 0), 0);
}

/** 下单回执：每项为同一渠道+分类下的累加金额；多项为 +a+b+… */
function formatPlusTermsFromTotals(totals) {
  const parts = [];
  for (const n of totals) {
    const x = Number(n);
    if (!Number.isFinite(x)) parts.push('+0');
    else parts.push(`+${Math.round(x)}`);
  }
  return parts.join('');
}

/** 撤回回执：与下单 +a+b 对应，输出 -a-b */
function formatMinusTermsFromTotals(totals) {
  const parts = [];
  for (const n of totals) {
    const x = Number(n);
    const v = !Number.isFinite(x) ? 0 : Math.round(x);
    parts.push(`-${v}`);
  }
  return parts.join('');
}

/** 纯「+金额1+金额2…」摘抄（引用回执），勿当下单解析 */
function looksLikePlusOnlyReceiptLine(s) {
  const t = String(s || '')
    .trim()
    .replace(/\s+/g, '')
    .replace(/＋/g, '+');
  if (!t || t.length < 2) return false;
  return /^\+?\d+(?:\.\d+)?(?:\+\d+(?:\.\d+)?)*$/.test(t);
}

/** 段首声明合计或误套默认「特」的 +金额 行，勿参与预处理/解析 */
function isOrderDeclaredTotalNoiseLine(s) {
  const t = String(s || '').trim();
  if (!t) return true;
  if (looksLikePlusOnlyReceiptLine(t)) return true;
  const compact = t.replace(/\s+/g, '');
  if (/^新澳门特\d{2,}$/.test(compact) && !/各|各数/u.test(t)) return true;
  return false;
}

/** 「昵称 HH:MM@昵称 +45+30+35」整行摘抄，勿当下单 */
function looksLikeAtPlusReceiptLine(s) {
  const t = String(s || '').trim().replace(/\s+/g, ' ');
  if (!t || t.length < 6) return false;
  return /^[\u4e00-\u9fffA-Za-z0-9·]{1,24}\s+\d{1,2}:\d{2}\s*@[\u4e00-\u9fffA-Za-z0-9·]{1,24}\s+\+\d+(?:\+\d+)*$/u.test(
    t
  );
}

/** 单号行尾部粘贴的他人引战回执「…陈工BIU 23:57@纪呵呵 +45+30+35」（与单号可无空格粘连） */
function stripTrailingEmbeddedAtPlusReceipt(s) {
  return String(s || '').replace(
    /\s*[\u4e00-\u9fffA-Za-z0-9·]{1,24}\s+\d{1,2}:\d{2}\s*@[\u4e00-\u9fffA-Za-z0-9·]{1,24}\s+\+\d+(?:\+\d+)*\s*$/u,
    ''
  );
}

/**
 * 合并转发/多条闲聊粘成一段时，常在「上一条尾部」与「下一条 昵称 HH:MM」之间无换行。
 * 在嵌入的「昵称 + 空格 + HH:MM」前插入换行（排除 HH:MM:SS 中的前两段）。
 * 约束：至少 3 字昵称；首字不为「数」、tempered 段无「各」「数」；英文首字左侧非汉字；CJK 首字不为「澳」；
 * 「各」紧挨金额中文（如 各三十五）时勿把「三十五…昵称」断行。
 */
function insertNewlinesBeforeEmbeddedChatTimestamps(s) {
  /** 首字为 A-Z 时左侧不得为汉字；CJK 首字排除「澳」避免 五A澳纪呵呵 误读成昵称 澳纪呵呵 */
  const nickCore =
    '((?:(?<![\\u4e00-\\u9fff])[A-Za-z]|[\\u4e00-\\u656f\\u6571-\\u6fb2\\u6fb4-\\u9fff])(?:(?!各|数)[\\u4e00-\\u9fffA-Za-z0-9·]){2,19})\\s+(\\d{1,2}:\\d{2})(?!:\\d{2})';
  /** 「各三十五」后接「陈工BIU 23:57」时勿把陈工BIU 当昵称（避免在 五 后断行） */
  const notAfterCnAmountTail =
    '(?<![零一二三四五六七八九十百千万亿两廿卅〇壹贰叁肆伍陆柒捌玖拾佰仟])';
  const nickTime = new RegExp(
    `(?<=[\\d!！。，,；;、@\\u4e00-\\u9fffA-Za-z])(?<![各]数)(?<!\u5404)${notAfterCnAmountTail}${nickCore}`,
    'gu'
  );
  const nickTimeAfterAo = new RegExp(`(?<=\\u6fb3)(?<![各]数)${nickCore}`, 'gu');
  return String(s || '')
    .replace(nickTime, (full, name, time, offset, whole) => {
      const n = String(name);
      if (/^数\d/.test(n)) return full;
      const prev = offset > 0 ? String(whole)[offset - 1] : '';
      if (/[\u4e00-\u9fff]/.test(prev) && /^[\u4e00-\u9fff][A-Za-z]{2,}/.test(n)) return full;
      return `\n${n} ${time}`;
    })
    .replace(nickTimeAfterAo, '\n$1 $2');
}

/** 「23:20」与紧接的下报单数字粘成「23:2011+17」时在时间后断行（避免误匹配 23:20 内的 3:20）；亦处理「23:57.44.43…」点号分号码 */
function insertNewlineAfterGluedClockTime(s) {
  return String(s || '').replace(
    /(?<!\d)(\d{1,2}:\d{2})(?=(?:\d+(?:[\*\+]|各))|\.\d)/gu,
    '$1\n'
  );
}

/**
 * 修复「各10」与「39各60」粘成「各1039各」：两位金额 + 两位球号(01–49) + 「各」。
 * 以及已拆出空格但仍单行的情况「各10 39各60」→ 断行，避免整段被当作一条子句解析失败。
 */
function splitGluedEachAmountThenBallEach(s) {
  let t = String(s || '');
  t = t.replace(/各(\d{2})([1-4][0-9])(各)/gu, '各$1\n$2$3');
  t = t.replace(/各(\d{2})\s+([1-4][0-9])(各)/gu, '各$1\n$2$3');
  return t;
}

/**
 * 行首「昵称/标识 + HH:MM + 可选逗号」；合并消息里常见。可循环剥多层；再剥「@昵称 」。
 */
function stripLineLeadingChatTimestamp(raw) {
  let s = String(raw || '').trim();
  let prev;
  do {
    prev = s;
    s = s
      .replace(/^[\u4e00-\u9fffA-Za-z0-9·]{1,24}\s+\d{1,2}:\d{2}\s*[，,、]?\s*/u, '')
      .replace(/^@[\u4e00-\u9fffA-Za-z0-9·]{1,24}\s+/u, '')
      .trim();
  } while (s !== prev);
  return s;
}

/** 行首为点分球号链（如 01.03.05…48.各1），勿当合并转发「序号.」逐段剥除 */
function lineStartsWithDotSeparatedLottoBallChain(s) {
  const t = String(s || '').trim();
  if (!t) return false;
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return new RegExp(`^${ball}(?:\\.${ball})+`, 'u').test(t);
}

/**
 * 少数导出/粘贴会有；微信合并转发成一段时通常无此类前缀，仅作兼容。
 */
function stripBatchForwardMessageLinePrefix(raw) {
  let s = String(raw || '').trim();
  let prev;
  do {
    prev = s;
    s = s
      .replace(/^(?:消息|图片|视频|语音|文件|聊天记录|联系人)\s*[：:]\s*/iu, '')
      .trim();
    if (
      !/^\d{1,2}(?:\.\d{1,2})+(?:头|尾)/u.test(s) &&
      !lineStartsWithDotSeparatedLottoBallChain(s)
    ) {
      s = s.replace(/^\d{1,3}[.．、:：)\]］]\s*/u, '').trim();
    }
  } while (s !== prev);
  return s;
}

/** 行尾「，一共185」「澳特。一共170」中与下单无关的合计尾巴 */
function stripTrailingInlineOrderSummary(s) {
  let t = trimTrailingOrderNoise(String(s || '').trim());
  let prev;
  do {
    prev = t;
    t = t
      .replace(/[，,。.、]?\s*一共\s*\d+\s*([。.…~～]|…)?\s*$/u, '')
      .replace(/[，,。.、]?\s*合计\s*\d+\s*([。.…~～]|…)?\s*$/u, '')
      .replace(/[，,。.、]?\s*总共\s*\d+\s*([Aa元块米斤]|…|[。.…~～])?\s*$/u, '')
      .replace(/[，,。.、]?\s*共\s*\d+\s*([。.…~～]|…)?\s*$/u, '')
      .replace(/[Aa]?\s*总共\s*\d+\s*[Aa]?\s*$/u, '')
      .trim();
  } while (t !== prev);
  return t.trim();
}

/** 合并/批量转发成一段时往往没有「消息：」；记录在 Hook 里可能无换行，仅汉字时间戳断行不够时在此撕开边界 */
function splitGluedMergeForwardedSnippets(s) {
  let t = String(s || '');
  t = t.replace(/\u2028/g, '\n').replace(/\u2029/g, '\n');
  t = t.replace(/(?:^|\n)\s*-{4,}\s*(?=\n|$)/gu, '\n');
  const zx = '[鼠牛虎兔龙蛇马羊猴鸡狗猪]';
  t = t.replace(new RegExp(`各数(\\d+)(?=${zx})`, 'gu'), '各数$1\n');
  t = t.replace(new RegExp(`各位(\\d+)(?=${zx})`, 'gu'), '各位$1\n');
  t = t.replace(new RegExp(`各号(\\d+)(?=${zx})`, 'gu'), '各号$1\n');
  t = t.replace(new RegExp(`各(\\d+)(?=${zx})`, 'gu'), '各$1\n');
  t = t.replace(
    /各数(\d+)(?=(?:0?[1-9]|[12]\d|[34][0-9])(?:[.\-+*＊]|[*+]))/gu,
    '各数$1\n'
  );
  t = t.replace(
    /(?<=[斤米])\s*(?=(?:0?[1-9]|[12]\d|[34][0-9])(?:[.\-+*＊]|\d{2}|各))/gu,
    '\n'
  );
  return t;
}

/** 全角 ASCII 区 → 半角（含全角空格） */
function normalizeInstructionFullwidthAscii(s) {
  let t = String(s || '');
  t = t.replace(/[\uFF01-\uFF5E]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0));
  t = t.replace(/\u3000/g, ' ');
  return t;
}

/** 金额后的装饰单位（米、块等）紧挨「各」后的数字时剥掉，便于拆条与解析 */
function stripDecorativeAmountUnitsAfterGe(s, unitSynonyms = []) {
  const extra = Array.isArray(unitSynonyms) ? unitSynonyms.map((x) => String(x || '').trim()).filter(Boolean) : [];
  const seen = new Set();
  const toks = [];
  for (const x of extra) {
    const k = x.toLowerCase();
    if (!x || seen.has(k)) continue;
    seen.add(k);
    toks.push(x);
  }
  toks.sort((a, b) => b.length - a.length);
  if (!toks.length) return s;
  const rePart = toks.map((x) => escapeRegExp(x)).join('|');
  return String(s || '').replace(new RegExp(`(各\\d+(?:\\.\\d+)?)(?:${rePart})+`, 'gu'), '$1');
}

/**
 * 「01十块」「3五块」→「01各10」「3各5」：球号(01–49)后紧接中文/口语金额、且尚未写「各」时，补「各」并阿拉伯化金额。
 * 纯数字金额不转换，避免「108」被误拆成「10各8」；「08 09」球表间的空格后不转换。
 */
function normalizeBallPlusCnAmountToGeForm(s, unitSynonyms) {
  const extra = Array.isArray(unitSynonyms) ? unitSynonyms : [];
  const t = String(s || '');
  if (!t) return s;
  const re = /(?<![0-9０-９各])((?:0[1-9]|[1-4][0-9]|[1-9]))(?!\d)(?!各)/gu;
  /** @type {{ start: number; end: number; replacement: string }[]} */
  const matches = [];
  let m;
  while ((m = re.exec(t)) !== null) {
    const ballStr = m[1];
    const ballNum = parseInt(ballStr, 10);
    if (!(ballNum >= 1 && ballNum <= 49)) continue;
    let j = m.index + m[0].length;
    if (j < t.length && (t[j] === ' ' || t[j] === '\t')) {
      const nx = t[j + 1];
      if (!nx) continue;
      if (/[0-9０-９]/.test(nx)) continue;
      j += 1;
    }
    if (j >= t.length) continue;
    const fs = parseValueFromStartAmount(t.slice(j), { unitSynonyms: extra });
    if (!fs || !Number.isFinite(Number(fs.value)) || Number(fs.value) <= 0) continue;
    const amtVal = Math.round(Number(fs.value));
    const chunk = t.slice(j);
    const consumedLen = chunk.length - fs.rest.length;
    if (consumedLen < 1) continue;
    const amtRaw = chunk.slice(0, consumedLen).trim();
    if (/^\d+$/u.test(amtRaw)) continue;
    const restAfterAmt = chunk.slice(consumedLen);
    const ra = restAfterAmt.replace(/^[\s，,、。.]+/u, '');
    if (ra && /^[0-9０-９]/.test(ra)) continue;
    matches.push({
      start: m.index,
      end: j + consumedLen,
      replacement: `${ballStr}各${amtVal}`,
    });
  }
  matches.sort((a, b) => a.start - b.start);
  const picked = [];
  let lastEnd = -1;
  for (const x of matches) {
    if (x.start < lastEnd) continue;
    picked.push(x);
    lastEnd = x.end;
  }
  picked.sort((a, b) => b.start - a.start);
  let out = t;
  for (const x of picked) {
    out = `${out.slice(0, x.start)}${x.replacement}${out.slice(x.end)}`;
  }
  return out;
}

const PREPROC_BALL_TOKEN_RE = /^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])$/;

function parseLottoBallToken(tok) {
  const t = String(tok || '').trim();
  if (!PREPROC_BALL_TOKEN_RE.test(t)) return null;
  const n = parseInt(t, 10);
  if (!(n >= 1 && n <= 49)) return null;
  return n;
}

/**
 * 「2 50」「10 100」→「02各50」「10各100」：单行仅「球号+空格+阿拉伯金额」、未写「各」时补全。
 * 不写「各」的纯数字金额原由 normalizeBallPlusCnAmountToGeForm 跳过；本规则专补此类口语。
 * 「08 09」等双球号表不转换；「26 38 50 60」等多 token 交给 tryRewriteTeDataRestSpaceBallsThenAmountWords。
 */
function normalizeBallSpaceDigitAmountToGeForm(s) {
  const convertLine = (line) => {
    const raw = String(line || '');
    const t = raw.trim();
    if (!t || /各|各位|各数|各号/u.test(t)) return raw;
    const toks = t.split(/\s+/).filter(Boolean);
    if (toks.length !== 2) return raw;
    const ballNum = parseLottoBallToken(toks[0]);
    if (ballNum == null) return raw;
    const amtRaw = String(toks[1] || '')
      .replace(/(元|块|米|刀|闷|蒙)+$/u, '')
      .trim();
    if (!/^\d+(?:\.\d+)?$/u.test(amtRaw)) return raw;
    const amt = Number(amtRaw);
    if (!Number.isFinite(amt) || amt <= 0) return raw;
    if (parseLottoBallToken(amtRaw) != null && amt <= 49 && amtRaw.length <= 2) return raw;
    const unit = String(toks[1] || '').match(/(元|块|米|刀|闷|蒙)+$/u)?.[0] || '';
    return `${String(ballNum).padStart(2, '0')}各${amt}${unit}`;
  };
  if (!String(s || '').includes('\n')) return convertLine(s);
  return String(s || '')
    .split('\n')
    .map((ln) => convertLine(ln))
    .join('\n');
}

/** 「16.18各10米 26各25」→ 在「各…」金额及可选单位后的空白处断行；「各30 01十块」→ 球号+中文金额尾段同理 */
function splitInlineOrderClausesAfterAmountTrailingSpace(s) {
  let t = String(s || '').replace(
    /([各]\d+(?:\.\d+)?)([元块米斤Aa闷蒙整角分]*)\s+(?=(?:\d{1,2})(?:[\s,，、.·]\d{1,2})*\s*各)/gu,
    '$1$2\n'
  );
  const afterBallCn = '(?:十|拾|块|元|米|各|[零○〇一二三四五六七八九十百千万两俩])';
  t = t.replace(
    new RegExp(
      `([各]\\d+(?:\\.\\d+)?)([元块米斤Aa闷蒙整角分]*)\\s+(?=((?:0?[1-9]|[12]\\d|3[0-9]|4[0-9]))${afterBallCn})`,
      'gu'
    ),
    '$1$2\n'
  );
  /** 「…各50 绿波各25」「…各50.绿波各25」：各+金额后接波色词 */
  t = t.replace(
    /((?:各数|各位|各号|各个|各)\d+(?:\.\d+)?)([元块米斤Aa闷蒙整角分]*)\s+(?=[绿红蓝](?:波|数)?)/gu,
    '$1$2\n'
  );
  t = t.replace(
    /((?:各数|各位|各号|各个)\d+(?:\.\d+)?)([元块米斤Aa闷蒙整角分]*)\s+(?=(?:\d{2})(?:[.\s]\d{2})+|\d{2}\s+\d{2})/gu,
    '$1$2\n'
  );
  t = t.replace(
    /([各]\d+(?:\.\d+)?)([元块米斤Aa闷蒙整角分]*)\s+(?=\d{2}(?:[.\s]\d{2})+)/gu,
    '$1$2\n'
  );
  t = t.replace(
    /(各\d+(?:\.\d+)?)([元块米斤Aa闷蒙整角分]+)(?=(?:0?[1-9]|[12]\d|3[0-9]|4[0-9]))/gu,
    '$1$2\n'
  );
  return t;
}

/** 预处理：生肖单字集合（与 normalizeOrderStreamText 句读一致） */
const PREPROC_ZODIAC_CLASS = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';

/** 口语/输入误把「各数」「各位」等算法词拆开（如 龙各 数5A）→ 合并为库内同义词 token */
function glueSpacedAlgoKeywordChars(s) {
  let t = String(s || '');
  const zx = PREPROC_ZODIAC_CLASS;
  /** 「龙蛇是各数10」：生肖与「各」之间的口语「是」 */
  t = t.replace(new RegExp(`([${zx}])是\\s*(?=各)`, 'gu'), '$1');
  /** 「各20一个数」「各10一个数」= 各+金额（口语尾缀，勿与算法别名「一个」混淆） */
  t = t.replace(/(各(?:数|位|号|个)?)\s*(\d+(?:\.\d+)?)\s*一个数/gu, '$1$2');
  t = t.replace(/(\d+(?:\.\d+)?)\s*一个数/gu, '$1');
  t = t.replace(/每个号/gu, '各');
  t = t.replace(/每个数\s*各/gu, '各');
  t = t.replace(/每个\s*各/gu, '各');
  t = t.replace(/每个数/gu, '');
  /** 球号表后口语倒装「数各25米」→「各25米」（勿误伤「每个数各」） */
  t = t.replace(/(?<!个)数各/gu, '各');
  t = t.replace(/各\s*组/gu, '各');
  t = t.replace(/各\s*数/gu, '各数');
  t = t.replace(/各数\s+(?=\d)/gu, '各数');
  t = t.replace(/各\s*位/gu, '各位');
  t = t.replace(/各\s*位\s*数/gu, '各位数');
  t = t.replace(/各\s*号/gu, '各号');
  t = t.replace(/各\s*个/gu, '各个');
  t = t.replace(/各\s+(?=\d)/gu, '各');
  return t;
}

/** 球号后「名」作「各」的误写（如 …49名5斤 → …49各5斤） */
function normalizeMingTypoAsEachBeforeAmount(s) {
  return String(s || '').replace(
    /(?<![0-9０-９各])(0?[1-9]|[12]\d|3[0-9]|4[0-9])名(\d+(?:\.\d+)?)/gu,
    '$1各$2'
  );
}

/**
 * 数据段内「鸡羊猴特各数…」：路由已是「特」时，生肖串与算法词之间的冗余「特」去掉（鸡羊猴特各数10 → 鸡羊猴各数10）。
 */
function stripRedundantTeBetweenZodiacAndGeInData(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(s || '').replace(
    new RegExp(`([${zx}]{2,14})特(?=(?:各数|各位|各号|各个|个数|各))`, 'gu'),
    '$1'
  );
}

const PREPROC_GE_ANCHOR_AFTER_BALLS = '(?:各|各数|各位|各号|各个|个数|一个)';

/**
 * 「02 09 13 25 38特码各5」：球号表后口语「特码/特」与路由「特」重复，剥除后再接各+金额。
 * 仅处理玩法「特」的同义尾缀，勿剥平特/特肖等其它分类。
 */
function stripRedundantTeCategoryAfterNumericBallsBeforeGe(s, db = null) {
  const ge = PREPROC_GE_ANCHOR_AFTER_BALLS;
  const ball = PREPROC_BALL_TOKEN;
  const suffixes = new Set(['特码']);
  if (db) {
    try {
      for (const { suf, canon } of listCategorySuffixesToCanonical(db)) {
        if (String(canon || '').trim() === '特' && suf) suffixes.add(String(suf).trim());
      }
    } catch {
      /* empty */
    }
  } else {
    suffixes.add('特');
  }
  let t = String(s || '');
  const ordered = [...suffixes].filter(Boolean).sort((a, b) => b.length - a.length);
  for (const suf of ordered) {
    if (suf === '平特') continue;
    const esc = escapeRegExp(suf);
    t = t.replace(
      new RegExp(`((?:${ball})(?:\\s+(?:${ball}))*)${esc}(?=\\s*${ge})`, 'gu'),
      '$1'
    );
  }
  return t;
}

/** 长串句号/省略号视为分段；去掉明显非下单字符（保留中英文数字与常用分隔） */
function stripOutOfRangeOrderNoiseChars(s) {
  return String(s || '')
    .replace(/[.。．…·•]{3,}/g, '\n')
    .replace(/[^\S\r\n\u4e00-\u9fff0-9０-９A-Za-z|&+\-／/，、：:；;！!？?各数号尾块元米斤\s]/gu, '');
}

/** 新奥 / 新奥特 / 噢待码 → 默认澳门渠道（行首或独占一行） */
function expandXinAoAoTeChannelShorthand(db, s) {
  let ng = '新澳门';
  try {
    const { guide } = getEffectiveDefaultOrderGuideCategory(db, null);
    ng = normalizeGuideWord(guide) || ng;
  } catch {
    /* empty */
  }
  return String(s || '')
    .split('\n')
    .map((rawLn) => {
      let t = String(rawLn || '');
      const lead = t.match(/^(\s*)/u)?.[1] || '';
      const body = t.slice(lead.length);
      if (/^新奥特/u.test(body)) return `${lead}${body.replace(/^新奥特/u, `${ng}特`)}`;
      if (/^新奥(?!门)/u.test(body)) return `${lead}${body.replace(/^新奥/u, ng)}`;
      if (/^噢待码/u.test(body)) return `${lead}${body.replace(/^噢待码/u, ng)}`;
      if (/^待码/u.test(body)) return `${lead}${body.replace(/^待码/u, ng)}`;
      return rawLn;
    })
    .join('\n');
}

/** 1头 2头 3头各10 → 1头|2头|3头各10（避免后续步骤只保留末段） */
function collapseMultiHeadWeiTargetsToPipeUnion(s) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  return String(s || '').replace(
    new RegExp(`((?:\\d[尾头]\\s*){2,})(各(?:\\d+(?:\\.\\d+)?|[${cnAmt}]+))`, 'gu'),
    (_m, heads, ge) => {
      const parts = String(heads || '')
        .trim()
        .split(/\s+/)
        .filter(Boolean);
      if (parts.length < 2) return _m;
      return `${parts.join('|')}${ge}`;
    }
  );
}

const WEI_TOU_DIGIT_SEP_CLASS = '[-–~～至到.。．、\\s]+';

/** 2-8尾 / 5.6.7尾 / 2.8头：分隔符仅拆分列表，不展开区间、不作小数 */
function splitWeiOrTouDigitSeparators(s) {
  return String(s || '').replace(
    /(\d(?:\s*[-–~～至到.。．、\s]\s*\d)+)\s*(尾|头)/gu,
    (m, body, suf) => {
      const digits = String(body || '')
        .split(new RegExp(WEI_TOU_DIGIT_SEP_CLASS, 'gu'))
        .map((d) => d.trim())
        .filter(Boolean);
      if (digits.length < 2) return m;
      return digits.map((d) => `${d}${suf}`).join('');
    }
  );
}

/** 5.6.7尾数各10 → 5尾6尾7尾数各10（「尾数」合集前分隔符仅拆分） */
function splitSeparatedDigitsBeforeWeiShuCollectionName(s) {
  return String(s || '').replace(
    /(\d(?:\s*[-–~～至到.。．、\s]\s*\d)+)尾数/gu,
    (_m, body) => {
      const digits = String(body || '')
        .split(new RegExp(WEI_TOU_DIGIT_SEP_CLASS, 'gu'))
        .filter(Boolean);
      if (digits.length < 2) return _m;
      return digits.map((d) => `${d}尾`).join('');
    }
  );
}

/** 口语「包」后常见集合/选号目标（无 db 时的静态兜底，长词优先） */
const BAO_STRIP_STATIC_PREFIX_TARGETS = [
  '红波双',
  '绿波双',
  '蓝波双',
  '红波单',
  '绿波单',
  '蓝波单',
  '红波',
  '绿波',
  '蓝波',
  '单数',
  '双数',
  '家肖',
  '野肖',
  '家禽',
  '野兽',
  '尾数',
  '大数',
  '小数',
  '大单',
  '大双',
  '小单',
  '小双',
  '合单',
  '合双',
  '合大',
  '合小',
  '大',
  '小',
  '单',
  '双',
];

function listBaoStripPrefixTargets(db) {
  const seen = new Set();
  const out = [];
  const push = (w) => {
    const t = String(w || '').trim();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  };
  for (const w of BAO_STRIP_STATIC_PREFIX_TARGETS) push(w);
  if (db) {
    try {
      const rows = db
        .prepare(`SELECT DISTINCT set_name FROM cmd_collections WHERE trim(set_name) <> ''`)
        .all();
      for (const r of rows) push(r.set_name);
    } catch {
      /* empty */
    }
    for (const { alias_word, standard_word } of listCollectionAliasPairs(db)) {
      push(alias_word);
      push(standard_word);
    }
  }
  return out.sort((a, b) => b.length - a.length);
}

function cachedBaoStripPrefixTargets(db) {
  return getParseCache(db, 'baoStripPrefixTargets', () => listBaoStripPrefixTargets(db));
}

/**
 * 「包」= 选集合前缀：包2-8尾 / 包家禽 / 包红波 / 包兔 等 → 剥「包」后走合集/生肖解析
 */
function normalizeBaoCollectionPrefix(s, db = null) {
  let t = String(s || '');
  const baoGap = '(?:\\s|[\\u00B7\\u30FB\\u2027\\uFF65\\uFE50\\uFE51\\u4E36、，,])*?';
  t = t.replace(/包肖/gu, '');
  t = t.replace(
    new RegExp(`包${baoGap}(?=\\d\\s*[-–~～至到.。．、\\s]\\s*\\d\\s*(?:尾|头))`, 'gu'),
    ''
  );
  t = t.replace(new RegExp(`包${baoGap}(?=\\d{1,2}(?:尾|头))`, 'gu'), '');
  for (const target of cachedBaoStripPrefixTargets(db)) {
    t = t.replace(new RegExp(`包${baoGap}(?=${escapeRegExp(target)})`, 'gu'), '');
  }
  const zx = PREPROC_ZODIAC_CLASS;
  t = t.replace(new RegExp(`包${baoGap}(?=[${zx}])`, 'gu'), '');
  return t;
}

const DEFAULT_SEGMENT_TOTAL_MARKERS = ['=', '共', '统共', '一共', '合计', '合'];

function listAmountSegmentTotalMarkerWords(db) {
  const seen = new Set();
  const out = [];
  const push = (w) => {
    const t = String(w || '').trim();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  };
  for (const m of DEFAULT_SEGMENT_TOTAL_MARKERS) push(m);
  if (db) {
    try {
      const rows = db
        .prepare(`SELECT alias_word, standard_word FROM alias_config WHERE category = 'SEGMENT_TOTAL'`)
        .all();
      for (const r of rows) {
        push(r.standard_word);
        push(r.alias_word);
      }
    } catch {
      /* empty */
    }
  }
  return out.sort((a, b) => b.length - a.length);
}

/** 各5A=10 / 各5A共10：剥掉声明合计尾缀，供解析；expectedTotal 供下单后校验 */
export function peelDeclaredSegmentTotalFromLine(line, db) {
  const s0 = String(line || '').trim();
  if (!s0) return { line: s0, expectedTotal: null };
  const markers = listAmountSegmentTotalMarkerWords(db);
  const markerPat = markers.map((x) => escapeRegExp(x)).join('|');
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const re = new RegExp(
    `^([\\s\\S]*?各(?:数|位|号|个)?)(\\d+(?:\\.\\d+)?|[${cnAmt}]+)([Aa元块米斤]*)\\s*(?:${markerPat})\\s*(\\d+(?:\\.\\d+)?)\\s*[。.]?\\s*$`,
    'u'
  );
  const m = s0.match(re);
  if (!m) return { line: s0, expectedTotal: null };
  const expected = Number(m[4]);
  if (!Number.isFinite(expected)) return { line: s0, expectedTotal: null };
  const stripped = `${m[1]}${m[2]}${m[3] || ''}`.trimEnd();
  return { line: stripped, expectedTotal: expected };
}

function validateDeclaredSegmentTotalAgainstPayload(expectedTotal, result) {
  if (expectedTotal == null || !Number.isFinite(expectedTotal)) return null;
  if (!result?.payload?.results?.length) return null;
  const sum = sumPayloadResults(result.payload);
  const exp = Math.round(expectedTotal * 100) / 100;
  const got = Math.round(sum * 100) / 100;
  if (Math.abs(got - exp) <= 0.009) return null;
  return `金额合计不符：声明合计 ${formatAmount(exp)}，按注数×单注计算 ${formatAmount(got)}`;
}

/** 蛇平各100 / 蛇平100 → 平特蛇各100 */
function normalizeZodiacPingTeShorthand(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(s || '')
    .replace(new RegExp(`([${zx}])平(?=各)`, 'gu'), '平特$1')
    .replace(new RegExp(`([${zx}])平(\\d+(?:\\.\\d+)?)(?![\\d各])`, 'gu'), '平特$1各$2');
}

/** 猪数15 / 门鼠数各100 → 猪数各15 */
function normalizeZodiacShuImplicitGeAmount(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(s || '').replace(
    new RegExp(`([${zx}])数\\s*(\\d+(?:\\.\\d+)?)(?!\\s*各)`, 'gu'),
    '$1数各$2'
  );
}

/** 平特虎100 / 平特虎100A / 平特虎100元 → 平特虎各100 */
function normalizePingTeZodiacTrailingAmount(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(s || '').replace(
    new RegExp(`(平特[${zx}]+)(\\d+(?:\\.\\d+)?)([Aa元块米]*)?(?!\\s*各)`, 'gu'),
    '$1各$2'
  );
}

/** 球表.各十五元、30.35.各十五元 */
function normalizeDotBallListGeChineseYuanAmount(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '').replace(
    new RegExp(`(${ball}(?:\\.${ball})+)\\.各([\\d${cnAmt}]+)(?:\\s*元)?`, 'gu'),
    (m, ballsPart, amtRaw) => dotBallListToEachGeLines(ballsPart, amtRaw, unitSynonyms) || m
  );
}

/** 01.100元、01.100、18.六十元 → 球号各金额（有点分金额段时前面按选号；01–49 双球点分且无单位时不改） */
function normalizeBallDotChineseYuanAmount(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '').replace(
    new RegExp(`(${ball})\\.([\\d${cnAmt}]+)(\\s*(?:元|块|米|斤))?`, 'gu'),
    (m, b, amtRaw, unit) => {
      const amt = parsePreprocessInlineAmount(amtRaw, unitSynonyms);
      if (amt == null) return m;
      const nb = parseInt(String(b), 10);
      if (!(nb >= 1 && nb <= 49)) return m;
      const hasUnit = Boolean(String(unit || '').trim());
      const amtDigits = String(amtRaw || '').trim();
      if (/^\d{1,2}$/.test(amtDigits)) {
        const n2 = parseInt(amtDigits, 10);
        if (n2 >= 1 && n2 <= 49 && !hasUnit) return m;
      }
      return `${String(nb).padStart(2, '0')}各${amt}`;
    }
  );
}

/** 点分球表已拆为空格后，行末 2 位以上裸数字作金额（01 02 100 → 01 02各100） */
function normalizeBallListTrailingBareAmount(s) {
  const ballTok = /^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])$/;
  const convertLine = (line) => {
    const raw = String(line || '');
    const t = raw.trim();
    if (!t || /各|各位|各数|各号/u.test(t)) return raw;
    const parts = t.split(/\s+/).filter(Boolean);
    if (parts.length < 2) return raw;
    const lastRaw = parts[parts.length - 1];
    const lastCore = lastRaw.replace(/(元|块|米|斤|刀|闷|蒙)+$/u, '');
    if (!/^\d{2,}(?:\.\d+)?$/u.test(lastCore)) return raw;
    const amt = Number(lastCore);
    if (!Number.isFinite(amt) || amt <= 0) return raw;
    if (/^\d{1,2}$/.test(lastCore)) {
      const n = parseInt(lastCore, 10);
      if (n >= 1 && n <= 49) return raw;
    }
    for (const p of parts.slice(0, -1)) {
      if (!ballTok.test(p)) return raw;
    }
    const unit = String(lastRaw).match(/(元|块|米|斤|刀|闷|蒙)+$/u)?.[0] || '';
    return `${parts.slice(0, -1).join(' ')}各${lastCore}${unit}`;
  };
  if (!String(s || '').includes('\n')) return convertLine(s);
  return String(s || '')
    .split('\n')
    .map((ln) => convertLine(ln))
    .join('\n');
}

/** 特肖龙100、平特虎100元 → 玩法+单生肖+行末金额 */
function normalizeCategoryZodiacTrailingBareAmount(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  let t = String(s || '');
  for (const cat of ['特肖马', '特肖', '平特']) {
    t = t.replace(
      new RegExp(`(${cat})([${zx}])${amt}(?:元|[Aa块米斤])?(?![\\d各尾号])`, 'gu'),
      '$1$2各$3'
    );
  }
  return t;
}

/** 三中三05.15.22各10 → 三中三 05 15 22各10 */
function expandLianMaZhongPlayDotBallsBeforeGe(s) {
  return String(s || '').replace(
    /(三中三|三中二|二中二|五不中)(\d{2}(?:\.\d{2})+)(各)/gu,
    (_m, play, ballPart, ge) => {
      const balls = [...String(ballPart || '').matchAll(/\d{2}/g)].map((x) => x[0]);
      if (balls.length < 2) return _m;
      return `${play} ${balls.join(' ')}${ge}`;
    }
  );
}

/** 5尾 6尾 7尾各十 → 平尾5尾 6尾 7尾各十（各数/各位/各号 走特码，勿抬平尾） */
function hoistMultiWeiTailLineToPingWei(s) {
  return String(s || '')
    .split('\n')
    .map((ln) => {
      const t = String(ln || '').trim();
      if (!t || /平尾|平特尾/u.test(t)) return ln;
      const compact = t.replace(/\s+/g, '');
      if (!/^(\d尾)+各(?!数|位|号|个)/u.test(compact)) return ln;
      return `平尾${t}`;
    })
    .join('\n');
}

/** 单100/双100 → 单双单各100 与 单双双各100（两行） */
function expandDanShuangSlashBareAmountLines(s) {
  const raw = String(s || '').trim();
  if (!/(?:^|[\\/／])(?:单|双)\d+/u.test(raw)) return raw;
  const parts = raw.split(/[\\/／]/).map((x) => String(x || '').trim()).filter(Boolean);
  if (parts.length < 1) return raw;
  const lines = [];
  for (const p of parts) {
    const m = p.match(/^(单|双)\s*(\d+(?:\.\d+)?)/u);
    if (!m) return raw;
    lines.push(`单双${m[1]}各${m[2]}`);
  }
  return lines.length > 0 ? lines.join('\n') : raw;
}

/** 行内连码玩法（三中三/五不中）无「连码」前缀时补上（渠道由 resolve 补，expandFushi 负责展码） */
function hoistInlineLianMaZhongPlayPrefix(s) {
  return String(s || '')
    .split('\n')
    .map((ln) => {
      const t = String(ln || '').trim();
      if (!t) return ln;
      if (/(?:三中三|三中二|二中二|五不中)/u.test(t) && !/连码/u.test(t)) {
        return `连码${t}`;
      }
      return ln;
    })
    .join('\n');
}

/** 32号15、24号18号48号各10元 */
function normalizeBallHaoTrailingAmount(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  let t = String(s || '');
  t = t.replace(
    new RegExp(`((?:${ball}号)+)各([\\d${cnAmt}]+)(?:\\s*元)?`, 'gu'),
    (m, ballsPart, amtRaw) => {
      const amt = parsePreprocessInlineAmount(amtRaw, unitSynonyms);
      if (amt == null) return m;
      const balls = [...ballsPart.matchAll(/(\d{1,2})号/g)]
        .map((x) => parseInt(x[1], 10))
        .filter((n) => n >= 1 && n <= 49)
        .map((n) => String(n).padStart(2, '0'));
      if (!balls.length) return m;
      return `${balls.join('.')}各${amt}`;
    }
  );
  t = t.replace(
    new RegExp(`(${ball})号\\s*([\\d${cnAmt}]+)(?:\\s*元)(?![\\d${cnAmt}号])`, 'gu'),
    (m, b, amtRaw) => {
      const amt = parsePreprocessInlineAmount(amtRaw, unitSynonyms);
      if (amt == null) return m;
      const nb = parseInt(String(b), 10);
      if (!(nb >= 1 && nb <= 49)) return m;
      return `${String(nb).padStart(2, '0')}各${amt}`;
    }
  );
  return t;
}

/** 46.各10、07.各100、25.各三十：球号与「各」之间的点分仅作分隔 */
function normalizeBallDotBeforeGe(s) {
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '').replace(new RegExp(`(?<![0-9０-９])(${ball})\\.各`, 'gu'), '$1各');
}

/** 32各35 牛狗猪各五：金额段后紧接生肖各注，断行 */
function splitZodiacGeClauseAfterAmountLine(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(s || '').replace(
    new RegExp(`(各\\d+(?:\\.\\d+)?)([元块米斤Aa]*)\\s+([${zx}]+\\s*各)`, 'gu'),
    '$1$2\n$3'
  );
}

/** 虎平500A、二连鸡兔100A → 平特/连肖 + 各金额 */
function normalizeZodiacPingTeOrLianXiaoTrailingAAmount(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  const lines = String(s || '').split(/\r?\n/);
  const out = lines.map((rawLn) => {
    let ln = String(rawLn || '').trim();
    if (!ln) return ln;
    ln = ln.replace(
      new RegExp(`^([${zx}])平(\\d+(?:\\.\\d+)?)\\s*A\\s*$`, 'u'),
      '新澳门平特$1各$2'
    );
    ln = ln.replace(
      new RegExp(`^二连([${zx}]{2})(\\d+(?:\\.\\d+)?)\\s*A\\s*(?:澳)?\\s*$`, 'u'),
      '新澳门连肖$1各$2'
    );
    ln = ln.replace(
      new RegExp(`(连肖[${zx}]{2}各\\d+)\\s+(?:平特)?(?:二)?连([${zx}]{2})(\\d+(?:\\.\\d+)?)(?:\\s*A)?(?:澳)?\\s*$`, 'u'),
      '$1\n新澳门连肖$2各$3'
    );
    return ln;
  });
  return out.join('\n');
}

/** 46.各10、25.各三十：按行规范化球号.各金额 */
function normalizePerLineBallDotGeAmount(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '')
    .split('\n')
    .map((ln) => {
      let t = normalizeBallDotBeforeGe(String(ln || '').trim());
      t = t.replace(
        new RegExp(
          `^((?:新澳门|香港|澳门|老澳门)\\s*特?\\s*)?(${ball})\\.各([\\d${cnAmt}]+)([元块米斤]*)?`,
          'u'
        ),
        (m, guide, b, amtRaw, unit) => {
          const amt = parsePreprocessInlineAmount(amtRaw, unitSynonyms);
          if (amt == null) return m;
          const nb = parseInt(String(b), 10);
          if (!(nb >= 1 && nb <= 49)) return m;
          return `${guide || ''}${String(nb).padStart(2, '0')}各${amt}${unit || ''}`;
        }
      );
      return t;
    })
    .join('\n');
}

/** 共74A、买特、共一百三十元 等汇总口癖 */
function stripInlineOrderSummaryNoise(s) {
  return String(s || '')
    .replace(/[，,]\s*共\s*\d+\s*A\b/giu, '')
    .replace(/\b共\s*\d+\s*A\b/giu, '')
    .replace(/买特/gu, '')
    .replace(/共[零〇○一二三四五六七八九十百千万两俩]+元?/gu, '');
}

/** 各5A47、各10a10 → 各5A 47 */
function insertSpaceAfterGeAmountAffixBeforeBalls(s) {
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '')
    .replace(new RegExp(`(各\\d+(?:\\.\\d+)?)([Aa])(?=${ball})`, 'gu'), '$1$2 ')
    .replace(new RegExp(`(各\\d+(?:\\.\\d+)?)([Aa])(\\d{2})`, 'gu'), '$1$2 $3');
}

/** 句首「新」+玩法（新四连肖 / 新 平特二连）→ 新澳门 */
function expandLeadingXinGuideShorthand(s) {
  return String(s || '')
    .replace(/^新\s+(?=[平连二三四五六三四友有])/u, '新澳门')
    .replace(/^新(?=[四五六连三四平])/u, '新澳门');
}

/** 渠道与玩法分类之间的空白（新澳门 平特二连 → 新澳门平特二连） */
function collapseGuidePlayCategoryWhitespace(db, s) {
  let t = String(s || '');
  if (!db || !t) return t;
  const routes = listDistinctActiveRoutePairs(db);
  for (const r of routes) {
    const g = normalizeGuideWord(r.guide_word);
    const cat = String(r.category_word || '').trim();
    if (!g || !cat) continue;
    const variants = new Set([cat]);
    try {
      for (const al of listSynonymAliasesForCanonical(db, 'category_word', cat)) {
        variants.add(String(al || '').trim());
      }
    } catch {
      /* empty */
    }
    const escG = escapeRegExp(g);
    for (const cv of variants) {
      if (!cv) continue;
      t = t.replace(new RegExp(`^${escG}\\s+${escapeRegExp(cv)}`, 'u'), `${g}${cv}`);
    }
  }
  return t;
}

/** 「绿波单各10/平特尾…」：斜杠分段为多条（非球号 01/02） */
function splitSlashSeparatedOrderSegments(s) {
  const raw = String(s || '');
  if (!/[\\/／]/.test(raw)) return raw;
  const parts = raw.split(/[\\/／]/).map((x) => String(x || '').trim()).filter(Boolean);
  if (parts.length < 2) return raw;
  const orderish = (p) =>
    /各|各数|平特|平尾|连肖|连码|[二三四五]连|三有|三友|波|尾|号/u.test(p) ||
    /\d{1,2}(?:号|尾)/u.test(p) ||
    /^(?:单|双)\s*\d+/u.test(p);
  if (!parts.every(orderish)) return raw;
  return parts.join('\n');
}

/** 各算法别名（每组、一个…）→ 规范「各」，词表来自 alias_config */
function normalizeEachAlgoAliasWordsToCanonical(s, db) {
  if (!db) return String(s || '');
  const pairs = getParseCache(db, 'eachAliasPairs', () =>
    listSynonymPairs(db, 'algo').filter((r) => String(r.canonical_word || '') === '各' && String(r.alias_word || '') !== '各')
  );
  let t = String(s || '');
  const ordered = [...pairs].sort((a, b) => b.alias_word.length - a.alias_word.length);
  for (const { alias_word } of ordered) {
    const a = String(alias_word || '').trim();
    if (!a) continue;
    t = t.split(a).join('各');
  }
  return t;
}

/** 口语「绿波单/红波双」→ 波色集合交单双（库内集合名 绿/红/蓝 + 单/双） */
function normalizeCompoundWaveDanTargets(s) {
  return String(s || '').replace(/([绿红蓝])波([单双])/gu, '$1|$2');
}

/** 「红波各5」→ 默认渠道+半波+红各5 */
function hoistWaveColorBoShuLines(db, text, wxGroupId = null) {
  if (!db) return String(text || '');
  const { guide } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
  const ng = normalizeGuideWord(guide) || '新澳门';
  return String(text || '')
    .split('\n')
    .map((ln) => {
      const t = String(ln || '').trim();
      const m = t.match(/^([绿红蓝])波各([\s\S]+)$/u);
      if (!m) return ln;
      const candidate = `${ng}半波${m[1]}各${m[2]}`;
      return routeCandidateAccepted(db, candidate, wxGroupId) ? candidate : ln;
    })
    .join('\n');
}

/** 「绿波单各10」→ 默认渠道 + 单双玩法 + 绿|单各10 */
function hoistWaveDanShuangPlayLines(db, text, wxGroupId = null) {
  if (!db) return String(text || '');
  const { guide } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
  const ng = normalizeGuideWord(guide) || '新澳门';
  return String(text || '')
    .split('\n')
    .map((ln) => {
      const t = String(ln || '').trim();
      if (!t || contentMatchesAnyRoute(db, t, wxGroupId)) return ln;
      const m = t.match(/^([绿红蓝])[\s|｜]*([单双])([\s\S]+)$/u);
      if (!m) return ln;
      const candidate = `${ng}单双${m[1]}|${m[2]}${m[3]}`;
      return routeCandidateAccepted(db, candidate, wxGroupId) ? candidate : ln;
    })
    .join('\n');
}

/** 「平特三连牛羊蛇100 牛虎狗100」：同玩法多组生肖+金额拆成多行 */
function expandRepeatedPlayZodiacAmountGroupsText(text, db) {
  if (!db) return String(text || '');
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  const lines = String(text || '').split('\n');
  const out = [];
  for (const ln of lines) {
    const t0 = String(ln || '').trim();
    if (!t0) {
      out.push(ln);
      continue;
    }
    const routePrefixes = buildSortedRoutePrefixes(db);
    const det = detectLineRoutePrefix(t0, routePrefixes);
    if (!det) {
      out.push(ln);
      continue;
    }
    const peeled = peelRoutePrefixFromLine(t0, routePrefixes);
    if (!peeled) {
      out.push(ln);
      continue;
    }
    const head = `${det.prefix}`;
    const body = String(peeled.rest || '').trim();
    const gs = getLianXiaoGroupSize(det.category);
    if (!gs) {
      out.push(ln);
      continue;
    }
    const re = new RegExp(`([${zx}]{${gs}})\\s+${amt}`, 'gu');
    const hits = [...body.matchAll(re)];
    if (hits.length < 2) {
      out.push(ln);
      continue;
    }
    for (const h of hits) out.push(`${head}${h[1]}各${h[2]}`);
  }
  return out.join('\n');
}

function resolvePlayCategoryFromDbToken(db, tok) {
  const key = String(tok || '').trim();
  if (!key || !db) return { category: '', groupSize: 0 };
  const map = getParseCache(db, 'playCategoryTokenMap', () => {
    const m = new Map();
    for (const { suf, canon } of listCategorySuffixesToCanonicalImpl(db)) {
      m.set(suf, {
        category: canon,
        groupSize: inferLianXiaoGroupSizeFromCategoryWord(canon),
      });
    }
    return m;
  });
  if (map.has(key)) return map.get(key);
  const fb = resolveFushiLianXiaoCategoryToken(key);
  return { category: fb.category, groupSize: fb.groupSize };
}

function splitZodiacGroupsFromTextBlock(block, groupSize) {
  const gs = Math.floor(Number(groupSize));
  if (!gs || gs < 2) return [];
  const zx = PREPROC_ZODIAC_CLASS;
  const out = [];
  const chunks = String(block || '')
    .replace(/[，,。.；;：:]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean);
  for (const ch of chunks) {
    const zc = ch.replace(new RegExp(`[^${zx}]`, 'gu'), '');
    if (!zc || !isCompactZodiacOnly(zc)) continue;
    if (zc.length === gs) out.push(zc);
    else if (zc.length > gs && zc.length % gs === 0) {
      for (let i = 0; i < zc.length; i += gs) out.push(zc.slice(i, i + gs));
    }
  }
  return out;
}

/** 一行内多段「四连肖/五连肖」+ 多组生肖 + 尾端共用「各/每组+金额」→ 拆成多行 */
function expandOneLineLianXiaoMultiPlaySharedAmount(line, db) {
  let s0 = String(line || '').trim();
  if (!s0 || !db) return s0;
  if (s0.includes('\n')) {
    return s0
      .split('\n')
      .map((ln) => expandOneLineLianXiaoMultiPlaySharedAmount(ln, db))
      .join('\n');
  }
  s0 = s0.replace(
    /\s+(?:(?:新澳门|澳门|香港)?特)?(?:[1-5一二三四五])\s*头\s*各(?:组)?\s*[\d一二三四五六七八九十百千万两俩]+(?:元|块|米|斤)?\s*$/u,
    ''
  );
  const playTokens = listLianXiaoPlayPrefixTokensFromDb(db);
  if (!playTokens.length) return s0;
  const playPat = playTokens.map((t) => escapeRegExp(t)).join('|');
  if (!new RegExp(playPat, 'u').test(s0)) return s0;
  const geWords = listEachAlgoAliasWords(db);
  if (!geWords.includes('各')) geWords.push('各');
  const gePat = geWords.map((w) => escapeRegExp(w)).join('|');
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const tailRe = new RegExp(`(${gePat})([\\d${cnAmt}]+)(?:元|米|块|斤|A)?\\s*$`, 'u');
  const tm = s0.match(tailRe);
  if (!tm) return s0;
  const fushiSuffix = expandPingTeLianXiaoFushiSuffixOneLine(s0);
  if (fushiSuffix !== s0) return fushiSuffix;
  const tailGe = `各${tm[2]}`;
  const body = s0.slice(0, tm.index).trim();
  const zx = PREPROC_ZODIAC_CLASS;
  const multiImplicitAmt = body.match(
    new RegExp(`[${zx}]{2,14}\\s*(?:各\\s*)?(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`, 'gu')
  );
  if (multiImplicitAmt && multiImplicitAmt.length > 1) return s0;
  let guidePrefix = '';
  let rest = body;
  const guideList = buildGuideStartReplacementList(db);
  for (const { from, to } of guideList) {
    if (!rest.startsWith(from)) continue;
    guidePrefix = to;
    rest = rest.slice(from.length);
    break;
  }
  if (!guidePrefix) {
    guidePrefix = inferGuidePrefixFromOrderBlock(s0, db);
  }
  const rePlay = new RegExp(`(${playPat})`, 'gu');
  const sections = [];
  let m;
  let lastIdx = 0;
  while ((m = rePlay.exec(rest)) !== null) {
    if (m.index > lastIdx) sections.push({ type: 'gap', text: rest.slice(lastIdx, m.index) });
    sections.push({ type: 'play', token: m[1], index: m.index });
    lastIdx = m.index + m[1].length;
  }
  if (lastIdx < rest.length) sections.push({ type: 'gap', text: rest.slice(lastIdx) });
  const playSections = sections.filter((x) => x.type === 'play');
  if (playSections.length < 1) return s0;
  const outLines = [];
  for (let i = 0; i < playSections.length; i += 1) {
    const playTok = playSections[i].token;
    const { category, groupSize } = resolvePlayCategoryFromDbToken(db, playTok);
    if (!category || !groupSize) continue;
    const start = playSections[i].index + playTok.length;
    const end = i + 1 < playSections.length ? playSections[i + 1].index : rest.length;
    const zBlock = rest.slice(start, end);
    const groups = splitZodiacGroupsFromTextBlock(zBlock, groupSize);
    for (const g of groups) {
      outLines.push(`${guidePrefix}${category}${g}${tailGe}`);
    }
  }
  return outLines.length > 1 ? outLines.join('\n') : s0;
}

function expandLianXiaoMultiPlayGroupsSharedAmountText(text, db) {
  if (!db) return String(text || '');
  return String(text || '')
    .split('\n')
    .map((ln) => expandOneLineLianXiaoMultiPlaySharedAmount(ln, db))
    .join('\n');
}

/** 末行「各组五十」作用于上文多段连肖块 */
function inferGuidePrefixFromOrderBlock(block, db) {
  const head = String(block || '')
    .split('\n')
    .map((l) => String(l || '').trim())
    .find(Boolean);
  if (head === '香港' || head === '港' || head === '香') return '香港';
  if (head === '新澳门' || head === '澳门' || head === '澳') return '新澳门';
  if (head === '老澳门') return '老澳门';
  if (/^香港/.test(head)) return '香港';
  if (/^新澳门/.test(head)) return '新澳门';
  if (/^老澳门/.test(head)) return '老澳门';
  const { guide } = getEffectiveDefaultOrderGuideCategory(db, null);
  return normalizeGuideWord(guide) || '新澳门';
}

function expandTrailingGeZuOnPriorLianBlocks(text, db) {
  if (!db) return String(text || '');
  const lines = String(text || '')
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((l) => String(l || '').trim())
    .filter(Boolean);
  if (lines.length < 2) return text;
  const tail = lines[lines.length - 1];
  const tm = tail.match(/^各(?:组)?\s*([\d一二三四五六七八九十百千万两俩]+)\s*(?:元|块|米|斤)?$/u);
  if (!tm) return text;
  const amt = tm[1];
  const body = lines.slice(0, -1).join('\n');
  const ng = inferGuidePrefixFromOrderBlock(body, db);
  const playTokens = listLianXiaoPlayPrefixTokensFromDb(db);
  const playPat = playTokens.map((t) => escapeRegExp(t)).join('|');
  const re = new RegExp(
    `(${playPat})\\s*([\\s\\S]*?)(?=\\n\\s*(?:${playPat})\\s*(?:\\n|$)|(?:${playPat})|$)`,
    'gu'
  );
  const out = [];
  let m;
  while ((m = re.exec(body)) !== null) {
    const playTok = m[1];
    const { category, groupSize } = resolvePlayCategoryFromDbToken(db, playTok);
    if (!category || !groupSize) continue;
    let zBlock = String(m[2] || '')
      .replace(/[。.]/g, ' ')
      .replace(/\n[\s\S]*$/, '');
    zBlock = zBlock.replace(
      new RegExp(`\\s*(?:[1-5]连肖|四连肖|五连肖|三连肖|二连肖)\\s*各(?:组)?\\s*[\\d一二三四五六七八九十百千万两俩]+\\s*$`, 'u'),
      ''
    );
    const groups = splitZodiacGroupsFromTextBlock(zBlock, groupSize);
    for (const g of groups) {
      out.push(`${ng}${category}${g}各${amt}`);
    }
  }
  return out.length ? out.join('\n') : text;
}

/** 全文末「…生肖表 4连肖各组20」→ 按连肖组数拆条 */
function expandInlineTrailingLianXiaoGeZu(text, db) {
  if (!db) return String(text || '');
  const cn = '一二三四五六七八九十百千万两俩';
  const m = String(text || '').match(
    new RegExp(
      `([\\s\\S]*?)\\s*(?:[1-5]连肖|四连肖|五连肖|三连肖|二连肖)\\s*各(?:组)?\\s*([\\d${cn}]+)\\s*$`,
      'u'
    )
  );
  if (!m) return text;
  const playTok = m[0].match(/(?:[1-5]连肖|四连肖|五连肖|三连肖|二连肖)/u)?.[0] || '四连肖';
  const { category, groupSize } = resolvePlayCategoryFromDbToken(db, playTok);
  if (!category || !groupSize) return text;
  const zx = PREPROC_ZODIAC_CLASS;
  const zFlat = String(m[1] || '').replace(new RegExp(`[^${zx}]`, 'gu'), '');
  if (zFlat.length < groupSize * 2) return text;
  const ng = inferGuidePrefixFromOrderBlock(m[1], db);
  const groups = [];
  for (let i = 0; i + groupSize <= zFlat.length; i += groupSize) {
    groups.push(zFlat.slice(i, i + groupSize));
  }
  if (!groups.length) return text;
  return groups.map((g) => `${ng}${category}${g}各${m[2]}`).join('\n');
}

/** 多行生肖表 + 末行「4连肖各20」→ 按四肖一组拆条 */
function expandMultilineZodiacThenLianXiaoGe(text, db) {
  if (!db) return String(text || '');
  let t = expandInlineTrailingLianXiaoGeZu(text, db);
  if (t !== text) return t;
  const raw = String(t || '').replace(/\r\n/g, '\n');
  const lines = raw.split('\n').map((l) => String(l || '').trim()).filter(Boolean);
  if (lines.length < 2) return text;
  const tail = lines[lines.length - 1];
  let tailM = tail.match(/^(?:[1-5]连肖|四连肖|五连肖|三连肖|二连肖)\s*各(?:组)?\s*([\d一二三四五六七八九十百千万两俩]+)/u);
  let zLines = lines.slice(0, -1);
  if (!tailM) return text;
  const playTok =
    tail.match(/(?:[1-5]连肖|四连肖|五连肖|三连肖|二连肖)/u)?.[0] || '四连肖';
  const { category, groupSize } = resolvePlayCategoryFromDbToken(db, playTok);
  if (!category || !groupSize) return text;
  const amt = tailM[1];
  const zx = PREPROC_ZODIAC_CLASS;
  const zFlat = zLines
    .join('')
    .replace(new RegExp(`[^${zx}]`, 'gu'), '');
  if (zFlat.length < groupSize * 2) return text;
  const ng = inferGuidePrefixFromOrderBlock(zLines.join('\n'), db);
  const groups = [];
  for (let i = 0; i + groupSize <= zFlat.length; i += groupSize) {
    groups.push(zFlat.slice(i, i + groupSize));
  }
  if (!groups.length) return text;
  return groups.map((g) => `${ng}${category}${g}各${amt}`).join('\n');
}

/** 平特三连/平特二连/平尾等：生肖组或组+空格+金额 补「各」 */
function normalizePlayCategoryImplicitGeAmount(s, db) {
  let t = normalizeLianXiaoTrailingAmountToGe(s, db);
  if (!db) return t;
  const tokens = getParseCache(db, 'implicitGePlayTokens', () => {
    const set = new Set();
    for (const { suf } of listCategorySuffixesToCanonicalImpl(db)) {
      if (suf) set.add(suf);
    }
    return [...set].sort((a, b) => b.length - a.length);
  });
  if (!tokens.length) return t;
  const zx = PREPROC_ZODIAC_CLASS;
  const playPat = tokens.map((x) => escapeRegExp(x)).join('|');
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  t = t.replace(
    new RegExp(`(${playPat})\\s+([${zx}]{2,14})\\s+${amt}(?![\\d各尾号元块米斤A])`, 'gu'),
    '$1$2各$3'
  );
  t = t.replace(
    new RegExp(`(${playPat})\\s*([${zx}]{2,14})${amt}(?![\\d各尾号元块米斤A])`, 'gu'),
    '$1$2各$3'
  );
  return normalizeChainedZodiacBareAmountPass(t);
}

/** 连肖/平特段内「龙虎50 虎羊50」链式裸金额 → 各+金额（与玩法前缀无关） */
function normalizeChainedZodiacBareAmountPass(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  let t = String(s || '');
  for (const gs of [5, 4, 3, 2, 1]) {
    const re = new RegExp(
      `([${zx}]{${gs}})(?:各\\s*)?${amt}(?:\\s*(?:元|[Aa块米斤]))?(?![\\d各尾号])`,
      'gu'
    );
    t = t.replace(re, '$1各$2');
  }
  return t;
}

/** 同玩法「牛羊蛇各100 牛虎狗100」→ 断行，避免后组被默认「特」吞掉 */
function splitSamePlayRepeatedZodiacAmountLines(s, db) {
  if (!db) return String(s || '');
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  let t = String(s || '');
  for (const { suf } of listCategorySuffixesToCanonicalImpl(db)) {
    const gs = inferLianXiaoGroupSizeFromCategoryWord(
      resolveCategoryHintWithSynonyms(db, suf) || suf
    );
    if (!gs) continue;
    const esc = escapeRegExp(suf);
    const re = new RegExp(
      `(${esc})\\s*([${zx}]{${gs}})(?:各\\s*)?${amt}\\s+([${zx}]{${gs}})\\s+${amt}`,
      'gu'
    );
    t = t.replace(re, '$1$2各$3\n$1$4各$5');
  }
  return t;
}

/** 一行内：先给当前玩法段补全「生肖+裸金额」→「生肖各金额」，再在嵌入其它玩法前断行 */
function expandPlaySegmentImplicitGeAndSplitLines(text, db) {
  if (!db) return String(text || '');
  const sufs = listCategorySuffixesToCanonicalImpl(db)
    .map((x) => x.suf)
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
  if (!sufs.length) return String(text || '');
  const playPat = sufs.map((x) => escapeRegExp(x)).join('|');
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  const zx = PREPROC_ZODIAC_CLASS;
  const out = [];
  for (const rawLn of String(text || '').split('\n')) {
    let ln = applyLongestGuidePrefixReplacement(db, String(rawLn || '').trim());
    if (!ln) {
      out.push(rawLn);
      continue;
    }
    const routePrefixes = buildSortedRoutePrefixes(db);
    const det = detectLineRoutePrefix(ln, routePrefixes);
    if (!det) {
      out.push(rawLn);
      continue;
    }
    const peeled = peelRoutePrefixFromLine(ln, routePrefixes);
    if (!peeled) {
      out.push(rawLn);
      continue;
    }
    let body = String(peeled.rest || '').trim();
    const embed = body.search(new RegExp(`\\s+(?=${playPat})`));
    let segA = embed >= 0 ? body.slice(0, embed).trim() : body;
    const segB = embed >= 0 ? body.slice(embed).trim() : '';
    const gs = getLianXiaoGroupSize(det.category);
    if (gs && isLianXiaoCategory(det.category) && segA) {
      const re = new RegExp(`([${zx}]{${gs}})(?:各\\s*)?${amt}`, 'gu');
      segA = segA.replace(re, '$1各$2');
    }
    let lineA = `${det.prefix}${segA}`;
    if (!segB) {
      out.push(lineA);
      continue;
    }
    out.push(lineA);
    out.push(`${det.guide}${segB}`);
  }
  return out.join('\n');
}

/** 装饰性渠道尾标「#澳」，不影响金额与算法 */
function stripHashMarkAoNoise(s) {
  return String(s || '').replace(/#[\s\uFEFF]*澳/gu, '');
}

/**
 * 两位球号之间的连字符视为**两个号码**的分隔（如 08-17 →「08」「17」），不展开为区间内全部号码；勿匹配更长数字串。
 */
function expandHyphenSeparatedBallRanges(s) {
  return String(s || '').replace(
    new RegExp(`(?<![0-9０-９])(0?[1-9]|[12]\\d|3[0-9]|4[0-9])[-－~～](0?[1-9]|[12]\\d|3[0-9]|4[0-9])(?![0-9０-９])`, 'g'),
    (m, a, b) => {
      const na = parseInt(a, 10);
      const nb = parseInt(b, 10);
      if (!(na >= 1 && na <= 49 && nb >= 1 && nb <= 49)) return m;
      return `${String(na).padStart(2, '0')} ${String(nb).padStart(2, '0')}`;
    }
  );
}

/** 两位球号间多条连字符（如 01--02--14）视为分隔，与单连字符「两球」规则一致 */
const PREPROC_BALL_TOKEN = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';

function collapseRunsOfHyphensBetweenBallTokens(s) {
  const re = new RegExp(`(${PREPROC_BALL_TOKEN})[-－]{2,}(${PREPROC_BALL_TOKEN})(?![0-9０-９])`, 'gu');
  let t = String(s || '');
  let guard = 0;
  let prev;
  do {
    prev = t;
    t = t.replace(re, (m, a, b) => {
      const na = parseInt(a, 10);
      const nb = parseInt(b, 10);
      if (!(na >= 1 && na <= 49 && nb >= 1 && nb <= 49)) return m;
      return `${String(na).padStart(2, '0')} ${String(nb).padStart(2, '0')}`;
    });
    guard += 1;
  } while (t !== prev && guard < 64);
  return t;
}

/** 「10-30文」「22-100文」「27-20文47-20文」：球号-金额口语 */
function normalizeBallHyphenTrailingAmount(s) {
  let t = String(s || '');
  const withUnit = new RegExp(`(?<![0-9０-９])(${PREPROC_BALL_TOKEN})[-－](\\d+)(?:文|元|块|米|斤)`, 'gu');
  let guard = 0;
  while (guard++ < 32) {
    const prev = t;
    t = t.replace(withUnit, '$1各$2');
    if (t === prev) break;
  }
  t = t.replace(
    new RegExp(`(?<![0-9０-９])(${PREPROC_BALL_TOKEN})[-－](\\d{3,})(?![0-9０-９-])`, 'gu'),
    '$1各$2'
  );
  return t;
}

/**
 * 「08--150A澳」：连字符后是明显金额（非 01–49 两位球号）时收成「08各150」
 */
function normalizeDoubleHyphenBallToLargeAmount(s) {
  const re = new RegExp(`(?<![0-9０-９])(${PREPROC_BALL_TOKEN})[-－]{2,}([0-9０-９]{2,})`, 'gu');
  return String(s || '').replace(re, (m, b, amtRaw) => {
    const amtDigits = amtRaw.replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
    const amt = parseInt(amtDigits, 10);
    if (!Number.isFinite(amt)) return m;
    const nb = parseInt(String(b), 10);
    if (!(nb >= 1 && nb <= 49)) return m;
    if (amt >= 1 && amt <= 49 && amtDigits.length <= 2) return m;
    if (amt <= 49 && amtDigits.length === 2) return m;
    return `${String(nb).padStart(2, '0')}各${amt}`;
  });
}

function parsePreprocessInlineAmount(amtRaw, unitSynonyms = []) {
  const t = String(amtRaw || '').trim();
  if (!t) return null;
  const v = tryParseAmountToken(t, unitSynonyms);
  if (v != null && Number.isFinite(Number(v)) && Number(v) > 0) return Math.round(Number(v));
  return null;
}

function dotBallListToEachGeLines(ballsPart, amtRaw, unitSynonyms = []) {
  const balls = String(ballsPart || '')
    .split(/[.\s,，、]+/)
    .map((b) => parseLottoBallToken(b))
    .filter((n) => n != null);
  const amt = parsePreprocessInlineAmount(amtRaw, unitSynonyms);
  if (balls.length === 0 || amt == null) return null;
  return balls.map((n) => `${String(n).padStart(2, '0')}各${amt}`).join(' ');
}

/**
 * 点分球号表 + 口语金额：15.27.每一个数三十A、05…43.各数五A奥、23.47一个10 等。
 */
function normalizeDotBallListColloquialEachAmount(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  let t = String(s || '');
  t = t.replace(
    new RegExp(
      `(${ball}(?:\\.${ball})+)\\.各数([\\d${cnAmt}]+)(?:\\s*A\\s*(?:奥|澳)|A(?:奥|澳))?`,
      'gu'
    ),
    (m, ballsPart, amtRaw) => dotBallListToEachGeLines(ballsPart, amtRaw, unitSynonyms) || m
  );
  t = t.replace(
    new RegExp(`(${ball}(?:\\.${ball})+)\\.(?:每一个数|每个数)\\s*([\\d${cnAmt}]+)\\s*A?`, 'gu'),
    (m, ballsPart, amtRaw) => dotBallListToEachGeLines(ballsPart, amtRaw, unitSynonyms) || m
  );
  t = t.replace(
    new RegExp(`(?:^|(?<=[^0-9０-９]))(${ball}(?:\\.${ball})+)一个\\s*([\\d${cnAmt}]+)`, 'gu'),
    (m, _pre, ballsPart, amtRaw) => dotBallListToEachGeLines(ballsPart, amtRaw, unitSynonyms) || m
  );
  return t;
}

/**
 * 「23 47，一个10」：多球号后口语「一个+金额」视为「各+金额」并拆成逐号各注。
 */
function normalizeBallListYiGeKouYuAsEachGe(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  const re = new RegExp(
    `^(${ball}(?:[\\s,，、.]+${ball})+)\\s*(?:[，,]\\s*)?一个\\s*(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`,
    'u'
  );
  return String(s || '').replace(re, (m, ballsPart, amtRaw) => {
    const out = dotBallListToEachGeLines(ballsPart, amtRaw, unitSynonyms);
    return out && out.includes('各') ? out : m;
  });
}

/** 「各二十A一个」「各50A一个」等口语尾巴，避免挡在中文金额归一化之前 */
function stripGeAmountTrailingAoYiGeNoise(s) {
  const cn = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  return String(s || '').replace(
    new RegExp(`(各数|各位|各号|各个|个数|各)\\s*((?:\\d+(?:\\.\\d+)?|[${cn}]+))(?:\\s*元)?\\s*A\\s*一个`, 'gu'),
    '$1$2'
  );
}

/**
 * 句首「澳门，正文」：去掉口语逗号并把「澳门」落实为后台可下单渠道（与 hoistEmbedded 口径一致），便于未写「新澳门特」时仍能走默认分类。
 */
function expandLeadingLooseMacauChannelLine(db, text, wxGroupId = null) {
  const s0 = String(text || '').trim();
  const zx = PREPROC_ZODIAC_CLASS;
  let m = s0.match(/^(澳门|新澳门|老澳门)[，,。.、:：;；\s]+([\s\S]+)$/u);
  if (!m) {
    m = s0.match(new RegExp(`^(澳门|新澳门|老澳门)([${zx}][\\s\\S]*)$`, 'u'));
  }
  if (!m) return text;
  const inter = m[1];
  const rest = String(m[2] || '').trim();
  if (!rest) return text;
  const { category: defaultCatRaw } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
  const cat = String(defaultCatRaw || '特').trim() || '特';

  let gNorm = normalizeGuideWord(inter);
  if (inter === '澳门') {
    const canon = resolveGuideHintWithSynonyms(db, '澳门');
    gNorm = normalizeGuideWord(String(canon || '').trim()) || gNorm;
    if (!assertActiveGlobalOrderRoute(db, gNorm, cat)) {
      const gRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_guide_word');
      const prefer = normalizeGuideWord(String(gRow?.value || '').trim());
      if (prefer && assertActiveGlobalOrderRoute(db, prefer, cat)) gNorm = prefer;
      else if (assertActiveGlobalOrderRoute(db, '新澳门', cat)) gNorm = '新澳门';
      else if (assertActiveGlobalOrderRoute(db, '老澳门', cat)) gNorm = '老澳门';
      else return text;
    }
  } else if (!assertActiveGlobalOrderRoute(db, gNorm, cat)) {
    return text;
  }

  if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
    const allow = listActiveCmdRoutesForOrderParse(db, wxGroupId);
    const ok = allow.some((r) => normalizeGuideWord(r.guide_word) === gNorm && r.category_word === cat);
    if (!ok) return text;
  }

  const out = `${gNorm}${rest}`;
  if (out === s0) return text;
  return out;
}

function filterInboundParseFailureBannerLines(lines) {
  return (Array.isArray(lines) ? lines : String(lines || '').split(/\r?\n/)).filter((ln) => {
    const t = String(ln || '').trim();
    if (!t) return true;
    if (/^[\u2588\u25A0\s]*【此消息有问题，不计入】[\u2588\u25A0\s]*$/u.test(t)) return false;
    if (/^【无法识别内容】$/u.test(t)) return false;
    if (/^[\u2588\u25A0]{3,}$/u.test(t)) return false;
    return true;
  });
}

/** 群友二次转发「未识别」回执时去掉横幅行，并逐行落实「澳门，…」渠道（真实下单往往在单独一行）。 */
function stripKnownInboundParseFailureDecorations(raw) {
  return filterInboundParseFailureBannerLines(raw)
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** 调试回执用原文：保留换行，仅剥 @ 与未识别横幅行 */
function prepareDebugOriginalMessageText(raw, db) {
  let s = stripWeChatAtPrefix(String(raw || ''), db);
  s = s.replace(/^\uFEFF/g, '').replace(/[\u200B-\u200D\uFEFF]/g, '');
  return filterInboundParseFailureBannerLines(s).join('\n');
}

/** 管理/查单等短指令正文：剥 @ 与未识别横幅，勿走下单预处理（避免「清空」→「新澳门特清空」） */
function prepareInboundInstructionText(raw, db) {
  let s = stripWeChatAtPrefix(String(raw || ''), db);
  s = s.replace(/^\uFEFF/g, '').replace(/[\u200B-\u200D\uFEFF]/g, '');
  return stripKnownInboundParseFailureDecorations(s.trim());
}

/** 明显畸形口令：生肖后误写 0、三位及以上号码当各注（如 360各20） */
export function inboundOrderContentLooksMalformed(raw) {
  const t = String(raw || '').trim();
  if (!t) return false;
  const zx = PREPROC_ZODIAC_CLASS;
  if (new RegExp(`[${zx}]0[${zx}0-9]`, 'u').test(t)) return true;
  if (/(?:^|[\s，,;；\n\r])0[.\s，,、]/u.test(t)) return true;
  if (/\.(\d{3,})(?:各|各数)/u.test(t)) return true;
  if (/(?:^|[\s\-－])(\d{3,})(?=[\-－\s]*各)/u.test(t)) return true;
  if (/(?:^|[\s，,;；\n\r])(?:[1-9]\d{2,})(?=\s*各)/u.test(t)) return true;
  return false;
}

/** 整行仅为后台 instruction 同义词（清空、群配置、帮助…），勿套默认渠道+特 */
export function matchesInstructionOnlyLine(text, db) {
  const t = prepareInboundInstructionText(text, db);
  if (!t) return false;
  const firstLine = t.split(/\r?\n/)[0].trim();
  if (matchesDrawCommandLine(firstLine, db) || matchesDrawCommandLine(t, db)) {
    return true;
  }
  const check = (canonical) => {
    const alt = instructionAltPattern(db, canonical);
    return alt && new RegExp(`^(?:${alt})$`, 'u').test(firstLine);
  };
  if (
    check('clear_order') ||
    check('help') ||
    check('order_query') ||
    check('order_query_detail') ||
    check('query_group_config') ||
    check('odds_table') ||
    check('list_play_modes') ||
    check('set_var') ||
    check('settlement_summary')
  ) {
    return true;
  }
  if (extractGroupConfigBulkBody(db, t) != null && !String(resolveGroupConfigBulkBody(db, t) || '').trim()) {
    return true;
  }
  if (parseGroupStatisticsReportIntent(t, db) || parseWaterReportIntent(t, db)) {
    return true;
  }
  if (matchesDebugOrderReplyToggleLine(firstLine, db) || matchesDebugOrderReplyToggleLine(t, db)) {
    return true;
  }
  if (matchesDebugRuleMissReplyToggleLine(firstLine, db) || matchesDebugRuleMissReplyToggleLine(t, db)) {
    return true;
  }
  if (matchesOwnerOrderToggleLine(firstLine, db) || matchesOwnerOrderToggleLine(t, db)) {
    return true;
  }
  if (matchesDefaultOrderAdminLine(firstLine, db) || matchesDefaultOrderAdminLine(t, db)) {
    return true;
  }
  return false;
}

/** 剥下单预处理误套的「渠道+分类」前缀，便于识别 报表 / 水报表 */
function stripLeadingRoutePrefixForInstructionParse(lineText, db, wxGroupId = null) {
  const peeled = peelRoutePrefixFromLine(
    String(lineText || '').trim(),
    buildSortedRoutePrefixesForGroup(db, wxGroupId)
  );
  if (!peeled) return String(lineText || '').trim();
  const rest = String(peeled.rest || '').trim();
  return rest || String(lineText || '').trim();
}

function expandLooseMacauChannelLines(db, text, wxGroupId) {
  return String(text || '')
    .split(/\r?\n+/)
    .map((ln) => {
      const t = String(ln || '');
      if (!t.trim()) return t;
      return expandLeadingLooseMacauChannelLine(db, t, wxGroupId);
    })
    .join('\n');
}

/** 「26、38各10」→「26各10\n38各10」 */
function splitIdeographicCommaBallListBeforeGe(s) {
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩';
  return String(s || '')
    .split('\n')
    .map((rawLn) => {
      const ln = String(rawLn || '').trim();
      if (!ln) return rawLn;
      const m = ln.match(
        new RegExp(`^(${ball}(?:[、，,]\\s*${ball})+)\\s*各(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`, 'u')
      );
      if (!m) return rawLn;
      const amt = m[2];
      const balls = m[1].split(/[、，,]/).map((x) => x.trim()).filter(Boolean);
      if (balls.length < 2) return rawLn;
      return balls.map((b) => `${b}各${amt}`).join('\n');
    })
    .join('\n');
}

/** 「牛羊特各数10，马龙特各数5」：仅在上段已为「特各数+金额」时断行 */
function splitCommaBeforeZodiacTeGeShuClause(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  return String(s || '').replace(
    new RegExp(`(特各数(?:\\d+|[${cnAmt}]+))([，,])\\s*(?=([${zx}]){1,14}特各数)`, 'gu'),
    '$1\n'
  );
}

/** 「蛇猴兔猪各数10，羊鸡狗各数5」：仅在上段已为「各数+金额」时断行，避免「牛，鸡…」连肖误拆 */
function splitCommaBeforeZodiacGeShuClause(s) {
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  return String(s || '').replace(
    new RegExp(`(各数(?:\\d+|[${cnAmt}]+))([，,])\\s*(?=([${zx}]){2,14}各数)`, 'gu'),
    '$1\n'
  );
}

/** 「…各三十，01十块」→ 逗号后为「球号+中文金额」尾段（去掉逗号以免尾读干扰探测/解析）。
 * 例外：英文明细表「04,…,33,41各30」中逗号仅为球号分隔，勿断行（否则「41各30」落下行致整单被误切）。
 */
function splitCommaBeforeBallCnAmountClause(s) {
  const re =
    /[，,]\s*(?=((?:0?[1-9]|[12]\d|3[0-9]|4[0-9]))(?:十|拾|块|元|米|各|[零○〇一二三四五六七八九十百千万两俩]))/gu;
  return String(s || '').replace(re, (full, _ball, offset, whole) => {
    let k = offset - 1;
    let leftDigits = '';
    while (k >= 0) {
      const ch = whole[k];
      if (/[0-9]/.test(ch)) leftDigits = ch + leftDigits;
      else if (/[０-９]/.test(ch))
        leftDigits = String.fromCharCode(ch.charCodeAt(0) - 0xfee0) + leftDigits;
      else break;
      k--;
    }
    if (leftDigits.length < 1 || leftDigits.length > 2) return '\n';
    const leftNum = parseInt(leftDigits, 10);
    if (!(leftNum >= 1 && leftNum <= 49)) return '\n';
    const afterComma = whole.slice(offset + full.length).trimStart();
    /* 仅「左为一位球号 + 逗号 + 右为球号+各+阿拉伯金额」时保留逗号；「各三十，01各十」左缘非纯 1～2 位球号仍会断行 */
    if (/^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])各[0-9０-９]/u.test(afterComma)) return full;
    return '\n';
  });
}

/** 渠道独占行勿与下行揉成一句，保留给 glueStandaloneGuideLineWithFollowing */
function mergeOrderLineBreaksBeforeGeAnchors(s, unitSynonyms, db) {
  const raw = String(s || '');
  if (!raw.includes('\n')) return s;
  const blocks = raw.split(/\r?\n+/);
  if (blocks.length <= 1) return s;
  const extra = Array.isArray(unitSynonyms) ? unitSynonyms : [];
  const endsWithCompleteGeClause = (chunk) => {
    const t = trimTrailingOrderNoise(String(chunk || '').trim());
    if (!t || !/(各|各数|各位|各号|各个|个数)/u.test(t)) return false;
    const vEnd = parseValueFromEnd(t, { unitSynonyms: extra });
    if (!vEnd) return false;
    const before = trimTrailingOrderNoise(vEnd.before);
    return Boolean(before && /(各|各数|各位|各号|各个|个数)/u.test(before));
  };
  const out = [];
  let buf = '';
  for (const b of blocks) {
    const line = String(b || '').trim();
    if (!line) continue;
    if (looksLikePlusOnlyReceiptLine(line)) {
      if (buf) {
        out.push(buf);
        buf = '';
      }
      out.push(line);
      continue;
    }
    if (!buf) {
      buf = line;
      continue;
    }
    if (looksLikePlusOnlyReceiptLine(buf)) {
      out.push(buf);
      buf = line;
      continue;
    }
    if (db && lineIsGuideWordOnly(db, buf)) {
      out.push(buf);
      buf = line;
      continue;
    }
    if (endsWithCompleteGeClause(buf)) {
      out.push(buf);
      buf = line;
    } else if (
      /(?:^|\s)(?:新澳门|澳门|香港)?特?[1-5一二三四五]头\s*各/u.test(line) ||
      /(?:^|\s)(?:新澳门|澳门|香港)?\d{1,2}尾\s*各/u.test(line)
    ) {
      out.push(buf);
      buf = line;
    } else if (
      /^(?:[12]\d|3[0-9]|4[0-9]|0?[1-9])[\\/／](?:\d+|[零一二三四五六七八九十百千万两俩]+)(?:元|块|米|斤)?$/u.test(
        line
      )
    ) {
      out.push(buf);
      buf = line;
    } else if (
      db &&
      (lineLooksLikeNewOrderLineStart(db, line, null) ||
        lineIsGuideWordOnly(db, line) ||
        /^(?:包)?\s*[1-5一二三四五]\s*头\s*各/u.test(line) ||
        /^(?:包)?\s*\d{1,2}\s*尾\s*各/u.test(line))
    ) {
      out.push(buf);
      buf = line;
    } else {
      buf = `${buf} ${line}`;
    }
  }
  if (buf) out.push(buf);
  return out.join('\n');
}

/** 「19 23 28/10元」→「19 23 28各10元」（连码/三中三球表尾斜杠金额） */
function normalizeBallListSlashTrailingAmount(s) {
  const ball = '(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '').replace(
    new RegExp(`((?:${ball})(?:\\s+${ball}){1,14})\\s*[\\/／]\\s*(\\d{2,})(?:元|块|米|斤)?`, 'gu'),
    '$1各$2'
  );
}

/** 「14.300#.04.22各50#」→「14各300」「04.22各50」 */
function normalizeBallDotLargeAmountHashMarker(s) {
  const ball = '(0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  return String(s || '')
    .replace(
      new RegExp(`(?:^|[\\s\\n])${ball}\\.(\\d{2,})#`, 'gmu'),
      (_m, b, a) => {
        const nb = parseInt(String(b), 10);
        if (!(nb >= 1 && nb <= 49)) return _m;
        return `\n${String(nb).padStart(2, '0')}各${a}`;
      }
    )
    .replace(/各(\d+)\.(0?\d{1,2}(?:\.\d{1,2})+各)/gu, '各$1\n$2');
}

/** 仅「03/10」「27/20」这类整行球号/金额斜杠（勿伤 19/23 球号表或 28/10元） */
function normalizeBallSlashAmountPerLine(s, unitSynonyms = []) {
  const ballToken = '(?:[12]\\d|3[0-9]|4[0-9]|0?[1-9])';
  const ballAmtLine =
    new RegExp(`^${ballToken}[\\\\/／](?:\\d{2,}|[零○〇一二三四五六七八九十百千万两俩]+)(?:元|块|米|斤)?$`, 'u');
  if (!String(s || '').includes('/')) return s;
  const lineRe = new RegExp(`^${ballToken}[\\\\/／](\\d+)(?:元|块|米|斤)?$`, 'u');
  return String(s || '')
    .split(/\r?\n/)
    .map((ln) => {
      const t = String(ln || '').trim();
      const m = t.match(lineRe);
      if (!m) return ln;
      const nb = parseInt(t.match(new RegExp(`^${ballToken}`))?.[0] || '0', 10);
      if (!(nb >= 1 && nb <= 49)) return ln;
      return `${String(nb).padStart(2, '0')}各${m[1]}`;
    })
    .join('\n');
}

/** 「26/35元」「14/十五元」：无显式各词时，球号/金额/单位 用斜杠作噪声分隔 → 各+金额+单位 */
function normalizeImplicitEachBallSlashAmountUnit(s, unitSynonyms = []) {
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const units = [...STRIP_ONE_UNIT_BUILTIN, ...(Array.isArray(unitSynonyms) ? unitSynonyms : [])]
    .map((x) => String(x || '').trim())
    .filter(Boolean);
  const seen = new Set();
  const toks = [];
  for (const u of units) {
    const k = u.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    toks.push(u);
  }
  toks.sort((a, b) => b.length - a.length);
  const unitPart = toks.length ? toks.map((x) => escapeRegExp(x)).join('|') : '';
  const ball = '(0?[1-9]|[12]\\d|3[0-9]|4[0-9])';
  const amt = `(\\d+(?:\\.\\d+)?|[${cnAmt}]+)`;
  const unitSuffix = unitPart ? `(?:${unitPart})?` : '';
  const re = new RegExp(`(?<![0-9０-９])${ball}[\\/／]+${amt}${unitSuffix}`, 'gu');
  return String(s || '').replace(re, (_m, b, a, unit) => {
    const nb = parseInt(String(b), 10);
    if (!(nb >= 1 && nb <= 49)) return _m;
    const amtDigits = String(a || '').replace(/[０-９]/g, (c) =>
      String.fromCharCode(c.charCodeAt(0) - 0xfee0)
    );
    if (/^\d{1,2}$/.test(amtDigits)) {
      const na = parseInt(amtDigits, 10);
      if (na >= 1 && na <= 49) return _m;
    }
    return `${String(nb).padStart(2, '0')}各${a}${unit || ''}`;
  });
}

/** 连肖行尾阿拉伯金额无「各」时补「各」（玩法前缀来自 cmd_routes + 同义词） */
function normalizeLianXiaoTrailingAmountToGe(s, db) {
  const tokens = db ? listLianXiaoPlayPrefixTokensFromDb(db) : [];
  if (!tokens.length) return String(s || '');
  const zx = PREPROC_ZODIAC_CLASS;
  const playPat = tokens.map((t) => escapeRegExp(t)).join('|');
  return String(s || '').replace(
    new RegExp(`(${playPat})([${zx}]{2,})(\\d+(?:\\.\\d+)?)(?![\\d各]|\\s*元|\\s*块|\\s*米)`, 'gu'),
    '$1$2各$3'
  );
}

/**
 * 预处理：全角→半角、各+中文金额→阿拉伯、列表分隔符统一、两位点号球号、行内拆条、剥装饰单位。
 * 须在 normalizeOrderStreamText 内最先执行（依赖 db 取金额单位同义词）。
 */
function preprocessOrderInstructionText(raw, db) {
  let s = String(raw || '');
  if (typeof s.normalize === 'function') s = s.normalize('NFKC');
  s = normalizeZodiacAliasCharsInText(s);
  s = normalizeBaoCollectionPrefix(s, db);
  s = splitWeiOrTouDigitSeparators(s);
  s = normalizeBallDotLargeAmountHashMarker(s);
  {
    const zx = PREPROC_ZODIAC_CLASS;
    s = s.replace(
      new RegExp(`([${zx}]{4,14})平特(?:四连肖|四连)(\\d+(?:\\.\\d+)?)`, 'gu'),
      '新澳门平特四连肖$1各$2'
    );
    s = s.replace(
      new RegExp(`([${zx}]{4})平特四连(\\d+(?:\\.\\d+)?)(?![\\d各])`, 'gu'),
      '新澳门平特四连肖$1各$2'
    );
  }
  s = normalizeBallDotBeforeGe(s);
  s = splitZodiacGeClauseAfterAmountLine(s);
  s = normalizeZodiacPingTeOrLianXiaoTrailingAAmount(s);
  s = splitSeparatedDigitsBeforeWeiShuCollectionName(s);
  s = s.replace(/复试/gu, '复式');
  s = s.replace(/每组/gu, '各');
  {
    const zx = PREPROC_ZODIAC_CLASS;
    s = s.replace(
      new RegExp(
        `([${zx}]{2,})[，,、]\\s*各\\s*(\\d+)[，,、]\\s*((?:\\d{1,2}[.]){2,}\\d{1,2}各\\d+)`,
        'gu'
      ),
      '$1各$2\n$3'
    );
  }
  s = s.replace(/(\d{2})\.(\d{2})\.\s*各位/gu, '$1.$2 各位');
  s = s.replace(/[（(]\s*(0?[1-9]|[12]\d|3[0-9])\s*[）)]\s*(?:\r?\n\s*)?(\d+)\s*元/gu, '$1各$2');
  s = s.replace(/特\s*(0?\d{1,2})\s+(\d+)\s*元/gu, '特$1各$2');
  s = s.replace(
    /((?:0?[1-9]|[12]\d|3[0-9])(?:[/／](?:0?[1-9]|[12]\d|3[0-9]))+)(各[零○〇一二三四五六七八九十百千万两俩]+)(?=\/)/gu,
    (_, balls, ge) => `${balls.replace(/[/／]/g, ' ')}${ge}\n`
  );
  s = s.replace(
    /((?:0?[1-9]|[12]\d|3[0-9])(?:[/／](?:0?[1-9]|[12]\d|3[0-9]))+)\s*\/\s*各/gu,
    (_, balls) => `${balls.replace(/[/／]/g, ' ')}各`
  );
  s = s.replace(
    /((?:0?[1-9]|[12]\d|3[0-9])(?:[/／](?:0?[1-9]|[12]\d|3[0-9])){2,})各/gu,
    (m, balls) => `${balls.replace(/[/／]/g, ' ')}各`
  );
  s = s.replace(/，{2,}/g, '\n');
  s = s.replace(/各10元一个/gu, '各10\n');
  s = s.replace(/各五十块一个/gu, '各50\n');
  s = s.replace(/各号(\d+)(?:米|元|块|斤)(?=\d{1,2}[\/／])/gu, '各$1\n');
  s = s.replace(/(米|元|块|斤)(?=\d{1,2}[/／])/gu, '\n');
  s = s.replace(/(\d)号(\d+)(?:米|元|块|斤)(?=[/／]|$)/gu, '$1各$2');
  s = s.replace(/(\d{2}(?:\.\d{2})+)\.十\s*A/giu, '$1各10');
  s = s.replace(/(\d{2}(?:\.\d{2})+)十A/giu, '$1各10');
  s = s.replace(/各(\d+)[qQ](?=\d)/gu, '各$1\n');
  s = s.replace(/数各/gu, '各');
  s = s.replace(/各四十(?=\d)/gu, '各40\n');
  s = s.replace(/各二十五/gu, '各25');
  s = s.replace(/各二十五(?=\d)/gu, '各25\n');
  {
    const cnAmt = '零○〇一二三四五六七八九十百千万两俩';
    s = s.replace(
      new RegExp(`(各(?:[${cnAmt}]+|\\d{2,}))(?=(?:0?[1-9]|[12]\\d|3[0-9])(?:[/／.]|$))`, 'gu'),
      '$1\n'
    );
  }
  s = s.replace(/(平尾\d尾各\d+)\s+(?=(?:0?[1-9]|[12]\d)各)/gu, '$1\n');
  s = s.replace(/平特尾(\d)尾一百/gu, '平尾$1尾各100');
  s = s.replace(/平尾(\d)尾一百/gu, '平尾$1尾各100');
  s = s.replace(/包0头各号(\d+)(?:米|元|块|斤)?/gu, '新澳门特0头各$1\n');
  s = s.replace(/^(?:包)?\s*0\s*头\s*各号?(\d+)/gmu, '新澳门特0头各$1');
  s = s.replace(
    /(\d{1,2})[/／](\d{1,2})[/／](\d{1,2})[/／]各号?(\d+)/gu,
    (_, a, b, c, amt) => `${a}各${amt} ${b}各${amt} ${c}各${amt}\n`
  );
  {
    const cnAmt = '零○〇一二三四五六七八九十百千万两俩';
    s = s.replace(
      new RegExp(`(各[${cnAmt}]+)(?=(?:0?[1-9]|[12]\\d|3[0-9])(?:[/／]))`, 'gu'),
      '$1\n'
    );
  }
  s = s.replace(/\s\.\s*(\d{1,2})\s*-{2,}/gu, ' $1 ');
  s = s.replace(/(米|元|块|斤)(\d{1,2})[-－](\d{1,2})/gu, '$1 $2-$3');
  s = s.replace(/(\d{1,2})\s*-\s*(\d{1,2})一个号(\d{2,3})(?:米|元|块|斤)?/gu, '$1.$2各$3');
  s = s.replace(/(\d{1,2})一个号(\d{2,3})(?:米|元|块|斤)?/gu, '$1各$2');
  s = s.replace(/^(\d{1,2})=(\d{2,})(?:门)?$/gmu, '新澳门特$1各$2');
  {
    const zx = PREPROC_ZODIAC_CLASS;
    s = s.replace(new RegExp(`([${zx}])[，,]\\s*([${zx}])数各(\\d+)`, 'gu'), '$1$2各$3');
  }
  s = s.replace(/篮/gu, '蓝');
  s = s.replace(/([绿红蓝])波特/gu, '$1波');
  s = s.replace(/([绿红蓝])波数/gu, '$1波');
  s = s.replace(
    /蓝绿双(?:数)?\s*各\s*(\d+(?:\.\d+)?)/gu,
    '新澳门单双蓝|双各$1\n新澳门单双绿|双各$1'
  );
  s = s.replace(/([绿红蓝])([单双])(?=各)/gu, '$1|$2');
  s = s.replace(
    /蓝绿\s*([12])\s*[，,、]\s*([12])\s*头\s*单\s*数?\s*各\s*(\d+)/gu,
    '新澳门单双蓝|绿|$1头|$2头|单各$3'
  );
  s = s.replace(/蓝绿\s*([12])\s*头\s*单\s*数?\s*各\s*(\d+)/gu, '新澳门单双蓝|绿|$1头|单各$2');
  s = s.replace(/([一二三四五])(头)/gu, (_, d, suf) => {
    const map = { 一: '1', 二: '2', 三: '3', 四: '4', 五: '5' };
    return `${map[d] || d}${suf}`;
  });
  s = s.replace(/平特\s*(\d)\s*尾\s*(\d+)\s*(?:米|元|块|斤)?/gu, '平尾$1尾各$2');
  s = s.replace(/平尾(\d)尾各(\d+)/gu, '平尾$1尾各$2\n');
  s = s.replace(/快/gu, '块');
  s = s.replace(/(?<![0-9０-９])(0?[1-9]|[12]\d|3[0-9]|4[0-9])买(\d+(?:\.\d+)?)/gu, '$1各$2');
  s = s.replace(/各一个/gu, '各');
  s = s.replace(/各数一百/gu, '各100');
  s = s.replace(/各一百/gu, '各100');
  s = s.replace(/各百/gu, '各100');
  s = s.replace(/写\s*(?:奥门|噢门|澳门)/gu, '新澳门');
  s = s.replace(/(?:奥门|噢门)(?=[，,。\s]|$)/gu, '新澳门');
  s = s.replace(/([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]+)每个数\s*(\d+(?:\.\d+)?)\s*(?:块|元|块钱)/gu, '$1各$2');
  s = s.replace(/每个数\s*(\d+(?:\.\d+)?)\s*(?:块|元|块钱)/gu, '各$1');
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  s = s.replace(/\.{3,}/g, '\n');
  s = s.replace(/(?<!\.)\.{2}(?!\.)/g, '.');
  s = normalizeBallSlashAmountPerLine(s, []);
  s = s.replace(
    /(各(?:\d+|[零〇○一二三四五六七八九十百千万两俩]+))\s+(?=(?:包)?[1-5一二三四五]头\s*各)/gu,
    '$1\n'
  );
  s = s.replace(/^(?:包)?\s*([1-5一二三四五])\s*头\s*各/gmu, '新澳门特$1头各');
  s = s.replace(
    /^((?:\d{1,2}尾\s*)+)(各数|各位|各号)/gmu,
    '新澳门特$1$2'
  );
  s = splitIdeographicCommaBallListBeforeGe(s);
  s = s.replace(
    /(特|特码|平特)(?=(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])各)/gu,
    '$1 '
  );
  s = normalizeBallListSlashTrailingAmount(s);
  s = s.replace(/([绿红蓝])单(?=各)/gu, '$1|单');
  s = s.replace(/([绿红蓝])双(?=各)/gu, '$1|双');
  s = normalizeInstructionFullwidthAscii(s);
  s = stripOutOfRangeOrderNoiseChars(s);
  s = normalizeIdeographicCommaSeparators(s);
  s = stripZodiacEmojiDecoration(s);
  s = expandLeadingXinGuideShorthand(s);
  if (db) {
    try {
      s = expandXinAoAoTeChannelShorthand(db, s);
    } catch {
      /* empty */
    }
  }
  s = normalizeLeadingMacauTeRouteShorthand(s);
  if (db) {
    try {
      s = expandMenTeMacauChannelPrefix(db, s);
    } catch {
      /* empty */
    }
  }
  s = hoistMultiWeiTailLineToPingWei(s);
  s = s.replace(/各数(\d{2,})/gu, '各$1');
  s = expandDanShuangSlashBareAmountLines(s);
  s = normalizeZodiacPingTeShorthand(s);
  s = glueSpacedAlgoKeywordChars(s);
  s = stripEmbeddedBaoxiaoNoise(s);
  s = stripInlineOrderSummaryNoise(s);
  if (db) {
    s = collapseGuidePlayCategoryWhitespace(db, s);
  }
  let unitSynonymsEarly = [];
  try {
    unitSynonymsEarly = db ? getOrderAmountUnitSynonyms(db) : [];
  } catch {
    unitSynonymsEarly = [];
  }
  try {
    s = expandChineseAmountAfterEachKeyword(s, unitSynonymsEarly);
  } catch {
    /* empty */
  }
  s = normalizePerLineBallDotGeAmount(s, unitSynonymsEarly);
  s = applyOrderUnitAmountBoundaryPerLine(s, db);
  if (db) {
    s = normalizeEachAlgoAliasWordsToCanonical(s, db);
  }
  s = normalizeCompoundWaveDanTargets(s);
  if (db) {
    s = hoistWaveDanShuangPlayLines(db, s);
    s = hoistWaveColorBoShuLines(db, s);
  }
  s = splitSlashSeparatedOrderSegments(s);
  {
    const zx = PREPROC_ZODIAC_CLASS;
    /** 五连肖鸡猪虎蛇猴/鸡虎蛇羊鼠各五十：「/」分隔两组生肖，勿与球号 01/02 混淆 */
    s = s.replace(new RegExp(`([${zx}])[\\/／]([${zx}])`, 'gu'), '$1 $2');
  }
  s = stripGeAmountTrailingAoYiGeNoise(s);
  let unitSynonyms = unitSynonymsEarly.length ? unitSynonymsEarly : [];
  if (!unitSynonyms.length) {
    try {
      unitSynonyms = db ? getOrderAmountUnitSynonyms(db) : [];
    } catch {
      unitSynonyms = [];
    }
  }
  s = normalizeDotBallListColloquialEachAmount(s, unitSynonyms);
  s = normalizeDotBallListGeChineseYuanAmount(s, unitSynonyms);
  s = normalizeBallDotBeforeGe(s);
  s = normalizeBallDotChineseYuanAmount(s, unitSynonyms);
  s = normalizeBallHaoTrailingAmount(s, unitSynonyms);
  s = normalizeBallListYiGeKouYuAsEachGe(s, unitSynonyms);
  s = normalizeCategoryZodiacTrailingBareAmount(s);
  s = normalizeZodiacShuImplicitGeAmount(s);
  s = normalizePingTeZodiacTrailingAmount(s);
  s = expandLianMaZhongPlayDotBallsBeforeGe(s);
  s = insertSpaceAfterGeAmountAffixBeforeBalls(s);
  s = collapseMultiHeadWeiTargetsToPipeUnion(s);
  s = normalizeBallDotLargeAmountHashMarker(s);
  s = normalizeBallSlashAmountPerLine(s, unitSynonyms);
  s = normalizeImplicitEachBallSlashAmountUnit(s, unitSynonyms);
  if (db) {
    try {
      s = mergeOrderLineBreaksBeforeGeAnchors(s, unitSynonyms, db);
    } catch {
      /* empty */
    }
  }
  s = stripHashMarkAoNoise(s);
  s = normalizeBallHyphenTrailingAmount(s);
  s = collapseRunsOfHyphensBetweenBallTokens(s);
  s = normalizeDoubleHyphenBallToLargeAmount(s);
  s = expandHyphenSeparatedBallRanges(s);
  s = stripRedundantTeCategoryAfterNumericBallsBeforeGe(s, db);
  s = splitCommaBeforeZodiacTeGeShuClause(s);
  s = splitCommaBeforeZodiacGeShuClause(s);
  s = splitCommaBeforeBallCnAmountClause(s);
  s = normalizeBallSlashAmountPerLine(s, unitSynonyms);
  s = normalizeBallListSlashTrailingAmount(s);
  s = normalizeImplicitEachBallSlashAmountUnit(s, unitSynonyms);
  s = s.replace(/(\d{1,2})#(\d+(?:\.\d+)?)(?:元)?/gu, '$1各$2');
  s = s.replace(/(\d{1,2})\.(\d{2,})A\s*$/gmu, '$1各$2');
  s = s.replace(/(\d{1,2})\s+(\d{2,})A\s*$/gmu, '$1各$2');
  s = s.replace(/(\d)\s*[\/／]\s*(?=\d)/g, '$1,');
  s = s.replace(/(\d)\s*\+\s*(?=\d)/g, '$1,');
  s = s.replace(/(\d)\s*-\s*(?=\d)/g, '$1 ');
  s = preNormalizeLottoTwoDigitDotChains(s);
  s = normalizeBallListTrailingBareAmount(s);
  s = normalizeMingTypoAsEachBeforeAmount(s);
  s = normalizePlayCategoryImplicitGeAmount(s, db);
  if (db) {
    s = splitSamePlayRepeatedZodiacAmountLines(s, db);
    try {
      s = expandPlaySegmentImplicitGeAndSplitLines(s, db);
    } catch {
      /* empty */
    }
  }
  s = stripRedundantTeBetweenZodiacAndGeInData(s);
  s = replaceOrderTextPunctuationWithSpacesExceptTrailingAmountPerLine(s, unitSynonyms);
  try {
    s = normalizeBallPlusCnAmountToGeForm(s, unitSynonyms);
  } catch {
    /* empty */
  }
  s = normalizeBallSpaceDigitAmountToGeForm(s);
  s = splitInlineOrderClausesAfterAmountTrailingSpace(s);
  s = stripDecorativeAmountUnitsAfterGe(s, unitSynonyms);
  try {
    s = hoistInlineLianMaZhongPlayPrefix(s);
    s = expandFushiLianXiaoAndLianMaPerLine(s, db);
  } catch {
    /* empty */
  }
  if (db) {
    try {
      s = expandTrailingGeZuOnPriorLianBlocks(s, db);
      s = expandMultilineZodiacThenLianXiaoGe(s, db);
      s = expandLianXiaoMultiPlayGroupsSharedAmountText(s, db);
      s = expandRepeatedPlayZodiacAmountGroupsText(s, db);
    } catch {
      /* empty */
    }
  }
  s = s.replace(/\s+(?=新澳门单双[绿红蓝]\|)/gu, '\n');
  s = normalizePerLineBallDotGeAmount(s, unitSynonyms);
  return s;
}

/** 流式/多段拼接：统一换行并将「/n」视为换行（部分环境无真换行） */
function normalizeOrderStreamText(raw, db = null) {
  let s = String(raw || '');
  if (db) {
    try {
      s = preprocessOrderInstructionText(s, db);
    } catch (e) {
      console.warn('preprocessOrderInstructionText:', e?.message || e);
    }
  } else if (typeof s.normalize === 'function') {
    s = s.normalize('NFKC');
    s = normalizeInstructionFullwidthAscii(s);
  }
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  s = s.replace(/\s*\/n\s*/g, '\n');
  s = s.replace(/各各/gu, '各');
  {
    const zx = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';
    s = s.replace(new RegExp(`。(?=\\s*[${zx}])`, 'gu'), '\n');
    // 英文句号作条款分隔（如 羊蛇特各数20.猴猪特各数10）；勿匹配小数点：要求点前为数字、点后为生肖
    s = s.replace(new RegExp(`(?<=\\d)\\.(?=\\s*[${zx}])`, 'gu'), '\n');
    s = s.replace(/(?<=\d)\.(?=\s*[绿红蓝])/gu, '\n');
  }
  s = insertNewlinesBeforeEmbeddedChatTimestamps(s);
  s = splitGluedMergeForwardedSnippets(s);
  s = insertNewlineAfterGluedClockTime(s);
  s = splitGluedEachAmountThenBallEach(s);
  return s;
}

/** 空行分隔：用于 peel/多块文案；回执金额按 route_group 同类合并后输出 */
function splitInstructionBlocks(text) {
  const s = String(text || '').trim();
  if (!s) return [];
  return s
    .split(/\r?\n(?:\s*\r?\n)+/)
    .map((b) => String(b || '').trim())
    .filter(Boolean);
}

/**
 * 渠道名单独占一行（可夹空行）时与下一行合并，避免块拆分或默认渠道误套。
 * 须在 ensureRoutedOrderLine 逐行处理之前调用。
 */
function glueStandaloneGuideLineWithFollowing(db, text, wxGroupId = null) {
  const raw = String(text || '').replace(/\r\n/g, '\n');
  const lines = raw.split('\n');
  const out = [];
  for (let i = 0; i < lines.length; i += 1) {
    const rawLn = String(lines[i] || '');
    let chunk = stripLeadingOrderNoise(rawLn.trim());
    chunk = stripBatchForwardMessageLinePrefix(chunk);
    chunk = stripTrailingInlineOrderSummary(chunk);
    if (!chunk) {
      out.push(rawLn);
      continue;
    }
    let probe = applyLongestGuidePrefixReplacement(db, chunk);
    probe = normalizeRoutePrefixWithSynonyms(db, probe);
    const onlyGw = lineIsGuideWordOnly(db, probe);
    if (onlyGw) {
      let j = i + 1;
      const bodyParts = [];
      while (j < lines.length) {
        let nextRaw = stripLeadingOrderNoise(String(lines[j] || '').trim());
        nextRaw = stripBatchForwardMessageLinePrefix(nextRaw);
        nextRaw = stripTrailingInlineOrderSummary(nextRaw);
        if (!nextRaw) {
          j += 1;
          continue;
        }
        let probeNext = applyLongestGuidePrefixReplacement(db, nextRaw);
        probeNext = normalizeRoutePrefixWithSynonyms(db, probeNext);
        if (lineIsGuideWordOnly(db, probeNext)) break;
        if (matchesInstructionOnlyLine(nextRaw, db)) break;
        bodyParts.push(nextRaw);
        j += 1;
      }
      if (bodyParts.length) {
        out.push(`${onlyGw}\n${bodyParts.join('\n')}`);
        i = j - 1;
        continue;
      }
    }
    out.push(rawLn);
  }
  return out.join('\n');
}

/**
 * 玩法分类独占一行（如「三友」「三连肖」）时与后续生肖组行、尾行「各组30米」合并为一条下单行。
 */
function glueStandaloneCategoryAliasLineWithFollowing(db, text, wxGroupId = null) {
  const raw = String(text || '').replace(/\r\n/g, '\n');
  const lines = raw.split('\n');
  const out = [];
  for (let i = 0; i < lines.length; i += 1) {
    const rawLn = String(lines[i] || '');
    let chunk = stripLeadingOrderNoise(rawLn.trim());
    chunk = stripBatchForwardMessageLinePrefix(chunk);
    chunk = stripTrailingInlineOrderSummary(chunk);
    if (!chunk) {
      out.push(rawLn);
      continue;
    }
    let probe = applyLongestGuidePrefixReplacement(db, chunk);
    probe = normalizeRoutePrefixWithSynonyms(db, probe);
    const siSanOnly = isSiSanLianXiaoPlayAliasLine(probe);
    const catPrefix = siSanOnly ? '__si_san__' : lineIsCategoryAliasOnly(db, probe, wxGroupId);
    if (!catPrefix) {
      out.push(rawLn);
      continue;
    }
    const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
    const zodiacParts = [];
    let tailLine = '';
    let j = i + 1;
    while (j < lines.length) {
      let ln = stripLeadingOrderNoise(String(lines[j] || '').trim());
      ln = stripBatchForwardMessageLinePrefix(ln);
      ln = stripTrailingInlineOrderSummary(ln);
      if (!ln) {
        j += 1;
        continue;
      }
      ln = applyLongestGuidePrefixReplacement(db, ln);
      ln = normalizeRoutePrefixWithSynonyms(db, ln);
      if (lineIsCategoryAliasOnly(db, ln, wxGroupId) || isSiSanLianXiaoPlayAliasLine(ln)) break;
      if (lineIsGuideWordOnly(db, ln)) break;
      const standalone = ensureRoutedOrderLine(db, ln, '', wxGroupId);
      if (contentMatchesAnyRoute(db, standalone, wxGroupId) && detectLineRoutePrefix(standalone, routePrefixes)) {
        break;
      }
      const zc = ln.replace(/[,\s，、·•]/g, '');
      if (zc && isCompactZodiacOnly(zc)) {
        zodiacParts.push(zc);
        j += 1;
        continue;
      }
      tailLine = ln;
      j += 1;
      break;
    }
    if (zodiacParts.length === 0) {
      out.push(rawLn);
      continue;
    }
    if (siSanOnly) {
      const playLead = String(probe || '').trim();
      const merged = expandSiSanLianXiaoDualPlayOneLine(
        `${playLead}${zodiacParts.join('')}${tailLine}`.replace(/\s+/g, ' ').trim()
      );
      out.push(merged);
    } else {
      out.push(`${catPrefix}${zodiacParts.join('')}${tailLine}`.replace(/\s+/g, ' ').trim());
    }
    i = j - 1;
  }
  return out.join('\n');
}

/** 除 glue 外，每行句首「香→香港」等同义词须在拆块前展开 */
function applyGuideSynonymsToEachLine(db, text) {
  const parts = String(text || '').replace(/\r\n/g, '\n').split('\n');
  const out = [];
  for (const rawLn of parts) {
    let chunk = stripLeadingOrderNoise(rawLn.trim());
    chunk = stripBatchForwardMessageLinePrefix(chunk);
    chunk = stripTrailingInlineOrderSummary(chunk);
    if (!chunk) {
      out.push(rawLn);
      continue;
    }
    chunk = applyLongestGuidePrefixReplacement(db, chunk);
    chunk = normalizeRoutePrefixWithSynonyms(db, chunk);
    out.push(chunk);
  }
  return out.join('\n');
}

/**
 * 续行本身已是「球号(01–49)+各+阿拉伯金额」整句时单独成行：
 * - 勿用「。」粘到上行尾（glueOrphanContinuationLinesToPreviousRoute）；
 * - mergeAdjacentUnparsedOrderLines 在缓冲上一行未探测成功时，勿再与下一行空格拼成一句。
 */
function lineLooksLikeStandaloneBallEachAmountLine(ln) {
  const t = String(ln || '').trim();
  return /^(?:0[1-9]|[1-4][0-9]|[1-9])各\d+(?:\.\d+)?$/u.test(t);
}

/** 孤行仅为空格分隔球号（1～49），勿用「。」粘到上行尾，便于与下一行「金额列」配对 */
function lineIsSpaceSeparatedBallsOnlyForGlueOrphan(ln) {
  const t = String(ln || '').trim();
  if (!t) return false;
  const parts = t.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return false;
  for (const b of parts) {
    if (!/^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])$/.test(b)) return false;
  }
  return true;
}

/** 表格粘贴：点分/空格球号行（预处理前也可能为 12.14.15） */
function lineIsDotOrSpaceBallGridForGlueOrphan(ln) {
  const t = String(ln || '').trim();
  if (!t) return false;
  return /^[\d.\s]+$/u.test(t);
}

/** 孤行以各/各位/各位数…+金额结尾（续上一行球表） */
function lineIsEachAlgoAmountOnlyForGlueOrphan(ln, db) {
  const t = String(ln || '').trim();
  if (!t || !/(?:各|各位|各数|各号|各个|个数)/u.test(t)) return false;
  return restStartsWithEligibleEachAlgoLine(t, db);
}

/** 孤行为「10元 20元」等纯金额列（逐项可为阿拉伯数字+可选单位） */
function lineIsSpaceSeparatedAmountColumnForGlueOrphan(ln) {
  let t = trimTrailingOrderNoise(stripLeadingOrderNoise(String(ln || '').trim()));
  if (!t) return false;
  const parts = t.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return false;
  for (const p of parts) {
    const p2 = String(p)
      .replace(/(元|块|米|刀)+$/u, '')
      .trim();
    if (!/^(\d+(?:\.\d+)?)$/u.test(p2)) return false;
    const n = Number(p2);
    if (!Number.isFinite(n) || n < 0) return false;
  }
  return true;
}

function extractGuideWordFromRoutePrefix(db, prefix, wxGroupId = null) {
  const p = String(prefix || '').trim();
  if (!p) return '';
  const only = lineIsGuideWordOnly(db, p);
  if (only) return only;
  const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
  const det = detectLineRoutePrefix(p, routePrefixes);
  return det ? det.guide : '';
}

/**
 * normalizeOrderStreamText 将「。」断行后，后续行可能只剩生肖+金额而无渠道玩法前缀，续接上一行 peel 出的「渠道+分类」。
 */
function glueOrphanContinuationLinesToPreviousRoute(db, text, wxGroupId = null) {
  /** strict 群：续行识别须用全局路由，勿因本群仅开「新澳门·特」把「香港四连肖」套成默认前缀 */
  const routePrefixes =
    wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)
      ? buildSortedRoutePrefixes(db)
      : buildSortedRoutePrefixesForGroup(db, wxGroupId);
  const rawLines = String(text || '').replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let prevPrefix = '';
  for (const rawLn of rawLines) {
    let ln = stripLeadingOrderNoise(String(rawLn || '').trim());
    ln = stripBatchForwardMessageLinePrefix(ln);
    ln = stripTrailingInlineOrderSummary(ln);
    if (!ln) {
      out.push('');
      continue;
    }
    ln = applyLongestGuidePrefixReplacement(db, ln);
    ln = normalizeRoutePrefixWithSynonyms(db, ln);
    const peeled = peelRoutePrefixFromLine(ln, routePrefixes);
    if (peeled) {
      prevPrefix = peeled.prefix;
      out.push(ln);
      continue;
    }
    if (lineIsDotOrSpaceBallGridForGlueOrphan(ln)) {
      if (prevPrefix) {
        out.push(ln);
        continue;
      }
      const hoistedBall = hoistEmbeddedGuideChannelBeforeBallsEach(db, ln, wxGroupId);
      let resolvedBall = resolveOrderContentWithDefaultPrefix(db, hoistedBall, wxGroupId);
      resolvedBall = normalizeRoutePrefixWithSynonyms(db, resolvedBall);
      const detBall = detectLineRoutePrefix(resolvedBall, routePrefixes);
      prevPrefix = detBall ? detBall.prefix : '';
      out.push(resolvedBall);
      continue;
    }
    if (lineIsEachAlgoAmountOnlyForGlueOrphan(ln, db)) {
      if (prevPrefix) {
        out.push(ln);
        continue;
      }
    }
    if (prevPrefix && !peeled) {
      const guideFromPrev = extractGuideWordFromRoutePrefix(db, prevPrefix, wxGroupId);
      if (guideFromPrev && !lineIsGuideWordOnly(db, ln)) {
        const ho = hoistEmbeddedGuideChannelBeforeBallsEach(db, ln, wxGroupId);
        let res = resolveOrderContentWithDefaultPrefix(db, ho, wxGroupId);
        res = normalizeRoutePrefixWithSynonyms(db, res);
        if (!detectLineRoutePrefix(res, routePrefixes)) {
          out.push(`${guideFromPrev}${ln}`);
          continue;
        }
      }
    }
    if (lineLooksLikeNewOrderLineStart(db, ln, wxGroupId)) {
      if (matchesInstructionOnlyLine(ln, db)) {
        prevPrefix = '';
        out.push(ln);
        continue;
      }
      const globalPeelOrphan = peelRoutePrefixFromLine(ln, buildSortedRoutePrefixes(db));
      if (globalPeelOrphan?.prefix) {
        if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
          ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, ln);
        }
        prevPrefix = globalPeelOrphan.prefix;
        out.push(ln);
        continue;
      }
      const hoistedOrphan = hoistEmbeddedGuideChannelBeforeBallsEach(db, ln, wxGroupId);
      let resolvedOrphan = resolveOrderContentWithDefaultPrefix(db, hoistedOrphan, wxGroupId);
      resolvedOrphan = normalizeRoutePrefixWithSynonyms(db, resolvedOrphan);
      const det = detectLineRoutePrefix(resolvedOrphan, routePrefixes);
      prevPrefix = det ? det.prefix : '';
      out.push(resolvedOrphan);
      continue;
    }
    if (lineLooksLikeStandaloneBallEachAmountLine(ln)) {
      out.push(ln);
      continue;
    }
    if (prevPrefix && !contentMatchesAnyRoute(db, ln, wxGroupId)) {
      if (
        lineIsSpaceSeparatedBallsOnlyForGlueOrphan(ln) ||
        lineIsDotOrSpaceBallGridForGlueOrphan(ln) ||
        lineIsEachAlgoAmountOnlyForGlueOrphan(ln, db) ||
        lineIsSpaceSeparatedAmountColumnForGlueOrphan(ln)
      ) {
        out.push(ln);
        continue;
      }
      if (out.length > 0 && String(out[out.length - 1] || '').trim()) {
        out[out.length - 1] = `${out[out.length - 1]}。${ln}`;
      } else {
        out.push(`${prevPrefix}${ln}`);
      }
      continue;
    }
    out.push(ln);
  }
  return out.join('\n');
}

/**
 * 行首/行尾/段内「噪声」：句读、装饰、用户随机粘贴符号。
 * 不参与语义、不做运算，解析时仅作通配剥离；与「目标 / 算法词 / 金额」三锚点匹配配合使用。
 */
const ORDER_NOISE_CLASS =
  "\u2588\u25A0，,。.、;；:：\\s！!？?…~～*｜|·•【】\\[\\]()（）'\"`«»\u200B-\u200D\uFEFF=%<>^&$#@_｀";

const ORDER_NOISE_HEAD_RE = new RegExp(`^[${ORDER_NOISE_CLASS}]+`, 'u');
const ORDER_NOISE_TAIL_RE = new RegExp(`[${ORDER_NOISE_CLASS}]+$`, 'u');
/** 算法词与金额之间、目标与算法词之间（宽松剥尾）仅允许此类字符（金额词由 parseValueFromEnd 另行处理） */
const ORDER_NOISE_SPAN_RE = new RegExp(`[${ORDER_NOISE_CLASS}]`, 'gu');
const ORDER_NOISE_ONE_CHAR_RE = new RegExp(`^[${ORDER_NOISE_CLASS}]$`, 'u');

function isOrderNoiseChar(ch) {
  const c = String(ch ?? '');
  if (!c) return false;
  return ORDER_NOISE_ONE_CHAR_RE.test(c);
}

/** 口语尾巴（非单字标点类），剥除后才解析尾额 */
const ORDER_NOISE_TRAILING_PHRASES = [];

/** 口语「包肖」为噪音；「包+集合/尾头/生肖」已在 normalizeBaoCollectionPrefix 处理 */
function stripEmbeddedBaoxiaoNoise(s) {
  return String(s || '').replace(/包肖/gu, '').trim();
}

/** 群聊常见分隔：丶(U+30FB)、· 等 → 空格，便于「1尾丶4尾」拆成集合名（勿吞换行，避免「+100」段首合计与下行粘成一句） */
function normalizeIdeographicCommaSeparators(s) {
  const raw = String(s || '');
  const collapseInlineWs = (ln) =>
    String(ln || '')
      .replace(/[\u00B7\u30FB\u2027\uFF65\uFE50\uFE51\u4E36]/g, ' ')
      .replace(/[ \t\u00A0\u3000]+/g, ' ')
      .trim();
  if (!raw.includes('\n')) return collapseInlineWs(raw);
  return raw
    .split('\n')
    .map((ln) => collapseInlineWs(ln))
    .join('\n');
}

function trimTrailingOrderNoise(raw) {
  let s = String(raw || '').trimEnd();
  let prev;
  do {
    prev = s;
    s = s.replace(ORDER_NOISE_TAIL_RE, '').trimEnd();
    s = s.replace(/[\/／]+$/u, '').trimEnd();
    for (const p of ORDER_NOISE_TRAILING_PHRASES) {
      if (s.endsWith(p)) s = s.slice(0, -p.length).trimEnd();
    }
  } while (s !== prev);
  return s;
}

/**
 * 下单单元金额段边界（特征相对明显，不靠口语尾缀词表）：
 * 1. 各词 + 允许符号 + 数字（阿拉伯/中文）+ 可选金额单位；
 * 2. 数字解析完成后若紧跟金额单位词，单位纳入本段；
 * 3. 选号/集合 + 裸金额：01–49 阿拉伯球号 + 中文数字金额；生肖串 + 阿拉伯金额（其后无另一明显金额段头）。
 */
const AMOUNT_CN_CHAR_CLASS = '零○〇一二三四五六七八九十百千万两俩贰廿卅';

/** 段后是否像「下一金额段/选号/各」起点（有则当前裸金额不截断为段尾） */
function looksLikeObviousNextAmountSegmentHead(t, db) {
  let s = String(t || '').trimStart();
  s = s.replace(/^[\s.．。…·\-－—_|#＃,，、]+/u, '').trimStart();
  if (!s) return false;
  if (/^各/u.test(s)) return true;
  const ball = PREPROC_BALL_TOKEN;
  const zx = PREPROC_ZODIAC_CLASS;
  if (new RegExp(`^${ball}[-－]\\d+`, 'u').test(s)) return true;
  if (new RegExp(`^${ball}(?:[、，,.\s](?:${ball}))*\\s*各`, 'u').test(s)) return true;
  if (new RegExp(`^(?:0?[1-9]|[12]\\d|3[0-9]|4[0-9])(?:\\s|$|[/／.])`, 'u').test(s)) return true;
  if (new RegExp(`^[${zx}]`, 'u').test(s)) return true;
  if (
    /^(?:平特)?[二三四五六]连(?:肖)?|三中三|三中二|二中二|复式(?:三|二)连肖|五不中|七不中|九不中|十不中|十二不中/u.test(
      s
    )
  ) {
    return true;
  }
  if (new RegExp(`^[${zx}]{2,}\\d`, 'u').test(s)) return true;
  try {
    const { orderedTokens, aliasToCanonical } = getAlgoAliasData(db);
    for (const tok of orderedTokens) {
      if (s.startsWith(tok) && isPerTargetAmountAlgoToken(tok, aliasToCanonical)) return true;
    }
  } catch {
    /* empty */
  }
  return false;
}

/** 金额数字后可选单位词纳入段尾 */
function extendAmountSegmentEndWithUnit(s, end, unitSynonyms) {
  const rest = stripOneLeadingAmountUnit(String(s || '').slice(end), unitSynonyms);
  return String(s || '').length - rest.length;
}

/** 各词 + 符号 + 数字 + 单位 */
function findGeAlgoAmountSegmentEndFromIndex(text, idx, db) {
  const { aliasToCanonical, orderedTokens } = getAlgoAliasData(db);
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  let best = -1;
  for (const tok of orderedTokens) {
    if (!text.startsWith(tok, idx)) continue;
    if (!isPerTargetAmountAlgoToken(tok, aliasToCanonical)) continue;
    const afterTok = text.slice(idx + tok.length);
    const intr = tryIntrinsicPerTargetAmountFromTok(tok, unitSynonyms, aliasToCanonical);
    if (intr != null) {
      let end = idx + tok.length;
      end = extendAmountSegmentEndWithUnit(text, end, unitSynonyms);
      if (end > best) best = end;
      continue;
    }
    const fs = parseValueFromStartAmount(afterTok, { unitSynonyms });
    if (!fs || !Number.isFinite(Number(fs.value))) continue;
    const consumedInAfter = afterTok.length - String(fs.rest || '').length;
    let end = idx + tok.length + consumedInAfter;
    end = extendAmountSegmentEndWithUnit(text, end, unitSynonyms);
    if (end > best) best = end;
  }
  return best;
}

/** 01–49 球号 + 中文裸金额（无各） */
function findBallCnBareAmountSegmentEnd(s, db) {
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  const ball = PREPROC_BALL_TOKEN;
  const cn = AMOUNT_CN_CHAR_CLASS;
  let best = -1;
  const re = new RegExp(`(?<![0-9０-９各])(${ball})(?!\\s*各)([${cn}]+)`, 'gu');
  for (const m of s.matchAll(re)) {
    const amtStart = m.index + m[1].length;
    const fs = parseValueFromStartAmount(m[2], { unitSynonyms });
    if (!fs || !Number.isFinite(Number(fs.value))) continue;
    const consumed = m[2].length - String(fs.rest || '').length;
    let end = amtStart + consumed;
    end = extendAmountSegmentEndWithUnit(s, end, unitSynonyms);
    const tail = s.slice(end);
    if (looksLikeObviousNextAmountSegmentHead(tail, db)) continue;
    if (end > best) best = end;
  }
  return best;
}

/** 生肖串 + 阿拉伯裸金额（其后无另一明显金额段） */
function findZodiacArabicBareAmountSegmentEnd(s, db) {
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  const zx = PREPROC_ZODIAC_CLASS;
  let best = -1;
  const re = new RegExp(`([${zx}]{2,14})(\\d+(?:\\.\\d+)?)`, 'gu');
  for (const m of s.matchAll(re)) {
    const amtRaw = m[2];
    const amt = parseFloat(amtRaw);
    if (!Number.isFinite(amt) || amt <= 0) continue;
    const digits = amtRaw.replace(/\D/g, '');
    if (digits.length <= 2 && amt >= 1 && amt <= 49) {
      const after = s.slice(m.index + m[0].length);
      if (/^[.．\s](?:0?[1-9]|[12]\d|3[0-9]|4[0-9])/u.test(after)) continue;
    }
    let end = m.index + m[0].length;
    end = extendAmountSegmentEndWithUnit(s, end, unitSynonyms);
    const tail = s.slice(end);
    if (looksLikeObviousNextAmountSegmentHead(tail, db)) continue;
    if (end > best) best = end;
  }
  return best;
}

/**
 * 下单单元金额段：仅「各」类算法词（canonical=各）+ 数字金额；玩法/路由词（特、平特…）不算。
 */
function isPerTargetAmountAlgoToken(tok, aliasToCanonical) {
  return aliasToCanonical.get(tok) === '各';
}

/**
 * 自 idx 起匹配「算法词 + 金额段」并返回该段结束位置（不含之后内容）。
 */
function findAmountSegmentEndFromIndex(text, idx, db) {
  return findGeAlgoAmountSegmentEndFromIndex(text, idx, db);
}

function findLastAmountSegmentEnd(text, db) {
  const s = String(text || '');
  let best = -1;
  for (let idx = 0; idx < s.length; idx += 1) {
    const end = findGeAlgoAmountSegmentEndFromIndex(s, idx, db);
    if (end > best) best = end;
  }
  for (const end of [
    findBallCnBareAmountSegmentEnd(s, db),
    findZodiacArabicBareAmountSegmentEnd(s, db),
  ]) {
    if (end > best) best = end;
  }
  return best;
}

/**
 * 金额段之后的同行尾巴：仅地区/玩法词可仍属本下单单元；否则视为无效或下一单元起点。
 * @returns {{ unitTail: string, restForChain: string }}
 */
function classifyTailAfterAmountSegment(tail, db, wxGroupId = null) {
  let t = String(tail || '').trimStart();
  t = t.replace(/^[\s.．。…·\-－—_|#＃,，、]+/u, '').trimStart();
  if (!t) return { unitTail: '', restForChain: '' };
  if (isInterferenceOnlySegment(t)) return { unitTail: '', restForChain: '' };

  const routePrefixes = wxGroupId
    ? buildSortedRoutePrefixesForGroup(db, wxGroupId)
    : buildSortedRoutePrefixes(db);
  if (detectLineRoutePrefix(t, routePrefixes)) {
    return { unitTail: t.trim(), restForChain: '' };
  }

  const { channel, rest: afterChannel } = splitLeadingChannelWord(db, t);
  if (channel) {
    const playTail = String(afterChannel || '').trim();
    if (!playTail) return { unitTail: channel, restForChain: '' };
    const gNorm = normalizeGuideWord(channel);
    const cats = listDistinctActiveRoutePairs(db)
      .filter((r) => normalizeGuideWord(r.guide_word) === gNorm)
      .map((r) => String(r.category_word || '').trim())
      .filter(Boolean);
    if (cats.some((c) => playTail === c || playTail.startsWith(c))) {
      return { unitTail: t.trim(), restForChain: '' };
    }
  }

  const pre = preNormalizeLottoTwoDigitDotChains(t);
  if (looksLikeObviousNextAmountSegmentHead(pre, db)) {
    return { unitTail: '', restForChain: t };
  }

  return { unitTail: '', restForChain: '' };
}

/** 截掉最后一个金额段之后、不符合地区/玩法特征的无效同行内容 */
function truncateLineAfterOrderUnitAmount(line, db, wxGroupId = null) {
  const raw = String(line || '');
  if (!raw.trim()) return raw;
  const s = normalizeBallDotBeforeGe(preNormalizeLottoTwoDigitDotChains(raw.trim()));
  if (
    /^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])(?:[、，,.\s](?:0?[1-9]|[12]\d|3[0-9]|4[0-9]))*各/u.test(
      s
    )
  ) {
    return s;
  }
  const amtEnd = findLastAmountSegmentEnd(s, db);
  if (amtEnd < 0) return raw;
  const head = s.slice(0, amtEnd);
  const tailRaw = s.slice(amtEnd);
  const { unitTail, restForChain } = classifyTailAfterAmountSegment(tailRaw, db, wxGroupId);
  if (restForChain?.trim()) {
    const headPart = unitTail ? `${head}${unitTail}` : head;
    return `${headPart.trimEnd()}\n${restForChain.trimStart()}`.trimEnd();
  }
  return unitTail ? `${head}${unitTail}`.trimEnd() : head.trimEnd();
}

function applyOrderUnitAmountBoundaryPerLine(s, db, wxGroupId = null) {
  return String(s || '')
    .split('\n')
    .map((ln) => truncateLineAfterOrderUnitAmount(ln, db, wxGroupId))
    .join('\n');
}

/** 诊断：单行金额段形态（供样本批量分析脚本） */
function findMaxGeAlgoAmountSegmentEnd(s, db) {
  let best = -1;
  for (let idx = 0; idx < s.length; idx += 1) {
    const end = findGeAlgoAmountSegmentEndFromIndex(s, idx, db);
    if (end > best) best = end;
  }
  return best;
}

/**
 * @returns {{
 *   normalized: string,
 *   amountEnd: number,
 *   featureType: string,
 *   featureEnds: { ge: number, ballCn: number, zodiacAr: number },
 *   head: string,
 *   tailRaw: string,
 *   tailClass: { unitTail: string, restForChain: string },
 *   tailNextHead: boolean,
 *   truncatedLine: string,
 * }}
 */
export function analyzeAmountSegmentMorphologyOneLine(line, db, wxGroupId = null) {
  const raw = String(line || '');
  const s = normalizeBallDotBeforeGe(preNormalizeLottoTwoDigitDotChains(raw.trim()));
  const geEnd = findMaxGeAlgoAmountSegmentEnd(s, db);
  const ballEnd = findBallCnBareAmountSegmentEnd(s, db);
  const zodiacEnd = findZodiacArabicBareAmountSegmentEnd(s, db);
  const amountEnd = Math.max(geEnd, ballEnd, zodiacEnd);
  let featureType = '无金额段';
  if (amountEnd >= 0) {
    const winners = [];
    if (geEnd === amountEnd && geEnd >= 0) winners.push('A:各词+数字(+单位)');
    if (ballEnd === amountEnd && ballEnd >= 0) winners.push('B:球号+中文裸金额');
    if (zodiacEnd === amountEnd && zodiacEnd >= 0) winners.push('C:生肖串+阿拉伯裸金额');
    featureType = winners.length ? winners.join(' | ') : '金额段(未分类)';
  }
  const head = amountEnd >= 0 ? s.slice(0, amountEnd) : s;
  const tailRaw = amountEnd >= 0 ? s.slice(amountEnd) : '';
  const tailClass =
    amountEnd >= 0
      ? classifyTailAfterAmountSegment(tailRaw, db, wxGroupId)
      : { unitTail: '', restForChain: '' };
  const tailNextHead = looksLikeObviousNextAmountSegmentHead(
    preNormalizeLottoTwoDigitDotChains(tailRaw),
    db
  );
  return {
    normalized: s,
    amountEnd,
    featureType,
    featureEnds: { ge: geEnd, ballCn: ballEnd, zodiacAr: zodiacEnd },
    head,
    tailRaw,
    tailClass,
    tailNextHead,
    truncatedLine: truncateLineAfterOrderUnitAmount(raw, db, wxGroupId),
  };
}

/** 对全文（含多行）做金额段形态分析 */
export function analyzeAmountSegmentMorphology(text, db, wxGroupId = null) {
  const pre = preprocessInboundOrderContent(db, text, wxGroupId) || String(text || '');
  const lines = pre.split('\n');
  return {
    preprocessed: pre,
    lines: lines.map((ln, i) => ({
      lineIndex: i + 1,
      rawLine: ln,
      ...analyzeAmountSegmentMorphologyOneLine(ln, db, wxGroupId),
    })),
  };
}

function isInterferenceOnlySegment(raw) {
  const t = String(raw || '').trim();
  if (!t) return true;
  return t.replace(ORDER_NOISE_SPAN_RE, '') === '';
}

/** 内嵌「各十」后若紧接中文数字开头，实为「各十五元」等，勿吞掉「十」 */
const INTRINSIC_EACH_BAD_CONTINUATION_RE = /^[一二三四五六七八九两俩贰]/u;

const STRIP_ONE_UNIT_BUILTIN = ['元', '块', '整', '角', '分', '米', '蒙', 'A', 'a', '斤'];

/** 「各五元」内嵌金额后剥掉可选单位，否则剩余「元，…」无法进入下一子句 */
function stripOneLeadingAmountUnit(rest, unitSynonyms) {
  let s = String(rest || '').trimStart();
  const units = [...STRIP_ONE_UNIT_BUILTIN, ...(Array.isArray(unitSynonyms) ? unitSynonyms : [])]
    .map((x) => String(x || '').trim())
    .filter(Boolean);
  const seen = new Set();
  const sorted = [];
  for (const u of units) {
    const k = u.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    sorted.push(u);
  }
  sorted.sort((a, b) => b.length - a.length);
  for (const u of sorted) {
    if (s.startsWith(u)) return s.slice(u.length).trimStart();
  }
  return s;
}

/** 行尾「表格式」尾缀（与 tryParseAmountToken 一致）+ 金额单位，最长在前 */
function buildAmountProtectUnitTokensLongestFirst(unitSynonyms) {
  const raw = [...STRIP_ONE_UNIT_BUILTIN, ...(Array.isArray(unitSynonyms) ? unitSynonyms : [])]
    .map((x) => String(x || '').trim())
    .filter(Boolean);
  const seen = new Set();
  const out = [];
  for (const x of raw) {
    const k = x.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(x);
  }
  return out.sort((a, b) => b.length - a.length);
}

/** 无单位/符号尾缀时，纯 1–49（含两位球号）更像球号而非尾额，勿划入保护区 */
function isLikelyBallNumberOnlyTail(numericPart, hadAmountAffix) {
  if (hadAmountAffix) return false;
  const num = String(numericPart || '');
  if (/[.]/.test(num)) return false;
  const ascii = num.replace(/[０-９]/gu, (c) => String.fromCharCode(c.codePointAt(0) - 0xfee0));
  if (!/^\d+$/.test(ascii)) return false;
  const n = parseInt(ascii, 10);
  if (!Number.isInteger(n) || n < 1 || n > 49) return false;
  return true;
}

/** 紧随行尾数字段之后：仅空白 + 金额单位 + 任意 Unicode 标点/符号（可穿插） */
function restIsOnlyUnitsWhitespaceAndSymbols(rest, unitSynonyms) {
  let t = String(rest || '');
  const units = buildAmountProtectUnitTokensLongestFirst(unitSynonyms);
  for (let guard = 0; guard < 500; guard++) {
    const t0 = t;
    t = t.replace(/^\s+/u, '');
    let hit = false;
    for (const u of units) {
      if (u && t.startsWith(u)) {
        t = t.slice(u.length);
        hit = true;
        break;
      }
    }
    if (hit) continue;
    const m = t.match(/^[\p{P}\p{S}]+/u);
    if (m) {
      t = t.slice(m[0].length);
      continue;
    }
    if (t === t0) break;
  }
  return t.length === 0;
}

function stripTrailingPsRunUpTo(s, j) {
  if (!(j > 0)) return j;
  const pref = s.slice(0, j);
  const m = pref.match(/[\p{P}\p{S}]+$/u);
  return m ? j - m[0].length : j;
}

/**
 * 行尾保护区起点：自右向左为「数字〔+小数点〕+ 可选金额单位 + 任意非空符号（\p{P}\p{S}，多码点亦可）」交替至段首；
 * 数字后的余部须仅为空白、单位与标点/符号；避免将裸 1–49 球号误判为尾额。
 */
function findProtectedTrailingAmountStart(lineCore, unitSynonyms) {
  const s = String(lineCore || '').replace(/\s+$/u, '');
  if (!s) return 0;

  const units = buildAmountProtectUnitTokensLongestFirst(unitSynonyms);
  let j = s.length;

  j = stripTrailingPsRunUpTo(s, j);

  for (let guard = 0; guard < 200; guard++) {
    let matched = false;
    for (const u of units) {
      if (u && j >= u.length && s.slice(j - u.length, j) === u) {
        j -= u.length;
        matched = true;
        break;
      }
    }
    if (!matched) break;
  }

  j = stripTrailingPsRunUpTo(s, j);

  while (j > 0 && /\s/u.test(s[j - 1])) {
    j--;
  }

  let dotSeen = false;
  const digitEnd = j;
  while (j > 0) {
    const ch = s[j - 1];
    if (/[0-9０-９]/.test(ch)) {
      j--;
      continue;
    }
    if ((ch === '.' || ch === '．') && !dotSeen) {
      dotSeen = true;
      j--;
      continue;
    }
    break;
  }
  if (j === digitEnd) return s.length;

  const tail = s.slice(j);
  const numMatch = tail.match(/^([0-9０-９]+(?:[.．][0-9０-９]+)?)([\s\S]*)$/u);
  if (!numMatch) return s.length;

  const rest = numMatch[2] || '';
  if (!restIsOnlyUnitsWhitespaceAndSymbols(rest, unitSynonyms)) return s.length;

  const v = tryParseAmountToken(tail, unitSynonyms);
  if (v == null || !Number.isFinite(v) || !(v > 0)) {
    const numAsc = numMatch[1].replace(/[０-９]/gu, (c) => String.fromCharCode(c.codePointAt(0) - 0xfee0));
    const vLoose = parseFloat(numAsc);
    if (!Number.isFinite(vLoose) || !(vLoose > 0)) return s.length;
  }

  const hadAffix = rest.replace(/\s+/gu, '').length > 0;
  if (isLikelyBallNumberOnlyTail(numMatch[1], hadAffix)) return s.length;
  return j;
}

/** 除「夹在两位数字间的小数点」外，将标点/符号类换为空格并压空白 */
function replacePunctuationWithSpaceInOrderHead(head) {
  const str = String(head || '');
  return str
    .replace(/[\p{P}\p{S}]/gu, (ch, offset) => {
      if (ch === '|' || ch === '｜') return ch;
      if ((ch === '.' || ch === '．') && offset > 0 && offset < str.length - 1) {
        const prev = str[offset - 1];
        const next = str[offset + 1];
        if (/[0-9０-９]/.test(prev) && /[0-9０-９]/.test(next)) return ch;
      }
      return ' ';
    })
    .replace(/[ \t\u00A0\u3000]+/gu, ' ');
}

/** 单行：仅行尾金额词整段保留原样，其余 Unicode 标点/符号换为空格（与 preprocessOrderInstructionText 联用） */
function replaceOrderLinePunctuationWithSpacesExceptTrailingAmount(line, unitSynonyms) {
  const m = String(line || '').match(/^([\s\S]*?)(\s*)$/u);
  const body = m ? m[1] : '';
  const trailWs = m ? m[2] : '';
  if (!body) return line;

  const trimmedEnd = body.trimEnd();
  const midPad = body.slice(trimmedEnd.length);
  const ps = findProtectedTrailingAmountStart(trimmedEnd, unitSynonyms);
  const head = trimmedEnd.slice(0, ps);
  const tail = trimmedEnd.slice(ps);
  return replacePunctuationWithSpaceInOrderHead(head) + tail + midPad + trailWs;
}

function replaceOrderTextPunctuationWithSpacesExceptTrailingAmountPerLine(text, unitSynonyms) {
  return String(text || '')
    .split('\n')
    .map((ln) => replaceOrderLinePunctuationWithSpacesExceptTrailingAmount(ln, unitSynonyms))
    .join('\n');
}

/**
 * 「各五」「各十」「各三十五」等：金额写在算法词里（与单独「各」+ 尾金额不同）
 */
function tryIntrinsicPerTargetAmountFromTok(tok, unitSynonyms, aliasToCanonical) {
  if (!tok || !tok.startsWith('各')) return null;
  if (aliasToCanonical.get(tok) !== '各') return null;
  const body = tok.slice(1);
  if (!body) return null;
  let v = tryParseAmountToken(body, unitSynonyms);
  if (!Number.isFinite(v) || v <= 0) {
    if (body === '十') v = 10;
    else if (body === '百') v = 100;
    else return null;
  }
  return v;
}

/** 连续生肖后直接跟金额、无显式「各」时（如 兔虎鼠二十五块）按「各」解析第一条子句 */
function tryImplicitEachCompactZodiacClauseFromLeft(s, db) {
  const str = String(s || '').trim();
  if (!str) return null;
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  const max = Math.min(128, str.length);
  for (let len = max; len >= 1; len -= 1) {
    const tail = str.slice(-len);
    if (!/[\d\u4e00-\u9fff.+-]/.test(tail) && !/[万千萬]/.test(tail)) continue;
    const v = tryParseAmountToken(tail, unitSynonyms);
    if (v == null || !Number.isFinite(v)) continue;
    const before = trimTrailingOrderNoise(str.slice(0, str.length - len).trim());
    const zCompact = before.replace(/[,\s，、·•]/g, '');
    if (!before || !isCompactZodiacOnly(zCompact)) continue;
    const tgt0 = normalizeOrderTargetSeparators(before.trim());
    if (!tgt0) continue;
    return {
      parsed: { targetRaw: tgt0, algo: '各', value: Number(v) },
      rest: '',
    };
  }
  return null;
}

/**
 * 自左取第一条「目标 + 算法词 + 金额」（链式：…18各五44…47各五25…各十43…各三十五）。
 * 语义口径同 parseDataSegment：目标与算法词紧挨或中间仅 ORDER_NOISE；符号不具运算含义。
 */
function takeFirstClauseFromLeft(rawS, db, parseOpts = {}) {
  const s = preNormalizeLottoTwoDigitDotChains(String(rawS || '').trim());
  if (!s) return null;

  const { aliasToCanonical, orderedTokens } = getAlgoAliasData(db);
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  const rg = normalizeGuideWord(parseOpts?.routedGuideNorm || '');

  let best = null;

  for (let idx = 0; idx < s.length; idx += 1) {
    for (const tok of orderedTokens) {
      if (!s.startsWith(tok, idx)) continue;
      if (aliasToCanonical.get(tok) == null) continue;
      if (!isPerTargetAmountAlgoToken(tok, aliasToCanonical)) continue;

      const targetPart = s.slice(0, idx);
      if (!String(targetPart || '').trim()) continue;

      let tp = trimTrailingOrderNoise(targetPart).trim();
      tp = stripTrailingChannelNoiseAfterNumericBalls(db, tp, rg);
      const tgt = normalizeOrderTargetSeparators(tp);
      if (!tgt) continue;

      const afterTok = s.slice(idx + tok.length);
      const intr = tryIntrinsicPerTargetAmountFromTok(tok, unitSynonyms, aliasToCanonical);

      if (intr != null) {
        let restAfterTok = String(afterTok || '').trimStart();
        if (tok.length > 1 && INTRINSIC_EACH_BAD_CONTINUATION_RE.test(restAfterTok)) {
          continue;
        }
        restAfterTok = stripOneLeadingAmountUnit(restAfterTok, unitSynonyms);
        const { restForChain } = classifyTailAfterAmountSegment(
          restAfterTok,
          db,
          parseOpts?.wxGroupId ?? null
        );
        const rest = stripLeadingOrderNoise(restForChain).trimStart();
        const cand = {
          idx,
          tokLen: tok.length,
          parsed: {
            targetRaw: tgt,
            algo: aliasToCanonical.get(tok),
            value: intr,
          },
          rest,
        };
        if (!best || idx < best.idx || (idx === best.idx && tok.length > best.tokLen)) {
          best = { idx, tokLen: tok.length, ...cand };
        }
        continue;
      }

      const algo = aliasToCanonical.get(tok);
      let value;
      let rest;
      if (algo === '各') {
        const fs = parseValueFromStartAmount(afterTok, { unitSynonyms });
        if (fs && Number.isFinite(Number(fs.value))) {
          value = Number(fs.value);
          const { restForChain } = classifyTailAfterAmountSegment(
            fs.rest,
            db,
            parseOpts?.wxGroupId ?? null
          );
          rest = stripLeadingOrderNoise(restForChain).trimStart();
          const cand = {
            idx,
            tokLen: tok.length,
            parsed: { targetRaw: tgt, algo, value },
            rest,
          };
          if (!best || idx < best.idx || (idx === best.idx && tok.length > best.tokLen)) {
            best = { idx, tokLen: tok.length, ...cand };
          }
          continue;
        }
      }

      const after0 = trimTrailingOrderNoise(stripLeadingOrderNoise(afterTok));
      if (!after0) continue;
      const vEnd = parseValueFromEnd(after0, { unitSynonyms });
      if (!vEnd || !isInterferenceOnlySegment(vEnd.before)) continue;
      value = Number(vEnd.value);
      if (!Number.isFinite(value)) continue;

      rest = s.slice(idx + tok.length + after0.length).trimStart();
      const cand = {
        idx,
        tokLen: tok.length,
        parsed: { targetRaw: tgt, algo, value },
        rest,
      };
      if (!best || idx < best.idx || (idx === best.idx && tok.length > best.tokLen)) {
        best = { idx, tokLen: tok.length, ...cand };
      }
    }
  }

  if (best) return { parsed: best.parsed, rest: best.rest };
  return tryImplicitEachCompactZodiacClauseFromLeft(s, db);
}

/**
 * 下单「数据段」子句模型（与 takeFirstClauseFromLeft / parseAllDataSegmentClauses 一致）：
 *
 * 一条子句 = **目标**（特码球号 01–49 / 生肖 / 玩法内集合名等） + **算法词**（库内 cmd 同义词，如 各、各数、各位…） + **金额**
 * （阿拉伯或中文金额；可有元、块、斤、闷等单位，单位不参与运算，仅作尾锚）。
 *
 * **无显式算法词**时，仍按「各」理解：目标与金额之间以 **换行、任意噪声符号、或金额单位词** 为界，
 * 即「目标 + 金额 +（换行|符号|单位）」；符号一律无计算语义，仅作分隔通配。
 *
 * **段间噪声**：目标列表内部、目标与算法词之间、算法词与金额之间，可出现随机句读或粘贴符号；
 * 解析只匹配「目标 / 算法词 / 金额」三锚点，其余走 isInterferenceOnlySegment、normalizeOrderTargetSeparators、
 * stripTrailingAlgoTokenPermissive 等通配剥离，不把 `+ - * /` 等当作运算。
 *
 * 规则1：自尾 parseValueFromEnd 锚金额，再自尾剥算法词（含目标与算法词间仅噪声的宽松剥尾）。
 * 规则2：自右向左找算法词 token，要求 token 与尾额之间整段为噪声；左侧归一为 targetRaw。
 */
function parseDataSegment(dataSegment, db, parseOpts = {}) {
  const rg = normalizeGuideWord(parseOpts?.routedGuideNorm || '');
  let s0 = applyOrderUnitAmountBoundaryPerLine(
    stripLeadingOrderNoise(String(dataSegment || '').trim()),
    db,
    parseOpts?.wxGroupId ?? null
  );
  s0 = stripLeadingRedundantChannelInterjection(s0);
  s0 = stripRedundantAoTeHeaderFromDataSegment(s0);
  if (!s0) return null;
  s0 = peelTrailingRouteFromDataSegment(db, s0);
  s0 = peelLooseAotaChannelTailFromData(s0);
  s0 = String(s0 || '').trim();
  if (!s0) return null;
  s0 = preNormalizeLottoTwoDigitDotChains(s0);
  /* 整段只有 01–49 号码列表、无「各」与金额尾缀时：勿把末位数字当金额，应与下一行（含 各/金额）合并 */
  if (isNumericBallTargetListOnly(s0)) return null;
  const { aliasToCanonical, orderedTokens } = getAlgoAliasData(db);
  const unitSynonyms = getOrderAmountUnitSynonyms(db);

  const packParsed = (stripped, value) => {
    const canonical = aliasToCanonical.get(stripped.algoToken);
    if (canonical == null) return null;
    const n = Number(value);
    if (!Number.isFinite(n)) return null;
    const targetRaw = normalizeOrderTargetSeparators(String(stripped.targetRaw || '').trim());
    if (!targetRaw) return null;
    return { targetRaw, algo: canonical, value: n };
  };

  // 规则1：整段自尾解析金额，再剥除算法词前的尾随干扰
  const vEnd1 = parseValueFromEnd(s0, { unitSynonyms });
  if (vEnd1) {
    const before1 = trimTrailingOrderNoise(vEnd1.before);
    const stripped1 =
      stripTrailingAlgoToken(before1, orderedTokens) ||
      stripTrailingAlgoTokenPermissive(before1, orderedTokens);
    if (stripped1) {
      const cleaned = {
        ...stripped1,
        targetRaw: stripTrailingChannelNoiseAfterNumericBalls(db, stripped1.targetRaw, rg),
      };
      const out = packParsed(cleaned, vEnd1.value);
      if (out) return out;
    }
    const zImp = before1.replace(/[,\s，、·•]/g, '');
    if (before1.trim() && isCompactZodiacOnly(zImp)) {
      const tgtZ = normalizeOrderTargetSeparators(before1.trim());
      if (tgtZ) {
        const n = Number(vEnd1.value);
        if (Number.isFinite(n)) return { targetRaw: tgtZ, algo: '各', value: n };
      }
    }
    if (before1.trim()) {
      const headNum = stripTrailingChannelNoiseAfterNumericBalls(db, before1.trim(), rg);
      if (headNum && isNumericBallTargetListOnly(headNum)) {
        const tgtN = normalizeOrderTargetSeparators(headNum);
        const n = Number(vEnd1.value);
        if (tgtN && Number.isFinite(n)) return { targetRaw: tgtN, algo: '各', value: n };
      }
    }
  }

  // 规则2：自右向左尝试「… + 算法词 + [干扰]* + 金额(+可选金额词)」，要求尾段被金额穷尽且无实义残留
  for (const tok of orderedTokens) {
    let fromPos = s0.length;
    while (fromPos >= 0) {
      const idx = s0.lastIndexOf(tok, fromPos);
      if (idx < 0) break;
      const head = s0.slice(0, idx);
      let tail = stripLeadingOrderNoise(s0.slice(idx + tok.length));
      tail = trimTrailingOrderNoise(tail);
      if (!tail) {
        fromPos = idx - 1;
        continue;
      }
      const vEnd2 = parseValueFromEnd(tail, { unitSynonyms });
      if (!vEnd2 || !isInterferenceOnlySegment(vEnd2.before)) {
        fromPos = idx - 1;
        continue;
      }
      if (aliasToCanonical.get(tok) == null) {
        fromPos = idx - 1;
        continue;
      }
      const value = Number(vEnd2.value);
      if (!Number.isFinite(value)) {
        fromPos = idx - 1;
        continue;
      }
      const headClean = stripTrailingChannelNoiseAfterNumericBalls(db, head, rg);
      const targetRaw = normalizeOrderTargetSeparators(trimTrailingOrderNoise(headClean).trim());
      if (!targetRaw) {
        fromPos = idx - 1;
        continue;
      }
      return { targetRaw, algo: aliasToCanonical.get(tok), value };
    }
  }

  return null;
}

/** 「羊鼠鸡狗猴。牛鸡羊猴蛇各一百」：前段仅生肖、末段带金额时，共用算法与金额 */
function tryParseZodiacPeriodSharedTailClauses(s0, db) {
  const piece = String(s0 || '').trim();
  if (!piece) return null;
  const parts = piece
    .split(/。(?=\s*[鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬])/u)
    .map((x) => x.trim())
    .filter(Boolean);
  if (parts.length < 2) return null;
  const lastPiece = parts[parts.length - 1];
  let lastParsed = parseDataSegment(lastPiece, db);
  if (!lastParsed) {
    const tLeft = takeFirstClauseFromLeft(lastPiece, db);
    if (tLeft) lastParsed = tLeft.parsed;
  }
  if (!lastParsed) return null;
  const { algo, value } = lastParsed;
  if (algo == null || !Number.isFinite(Number(value))) return null;
  const out = [];
  for (let i = 0; i < parts.length - 1; i += 1) {
    const head = parts[i];
    const zc = head.replace(/[,\s，、·•]/g, '');
    if (!isCompactZodiacOnly(zc)) return null;
    out.push({
      targetRaw: normalizeOrderTargetSeparators(head.trim()),
      algo,
      value: Number(value),
    });
  }
  out.push(lastParsed);
  return out;
}

function combinationsPickK(items, k) {
  const arr = Array.isArray(items) ? items : [];
  const kk = Math.floor(Number(k));
  if (kk <= 0 || kk > arr.length) return [];
  const out = [];
  const pick = (start, buf) => {
    if (buf.length === kk) {
      out.push(buf.slice());
      return;
    }
    for (let i = start; i <= arr.length - (kk - buf.length); i += 1) {
      buf.push(arr[i]);
      pick(i + 1, buf);
      buf.pop();
    }
  };
  pick(0, []);
  return out;
}

function resolveFushiLianXiaoCategoryToken(tok) {
  const t = String(tok || '').trim();
  if (!t) return { category: '', groupSize: 0 };
  const dm = t.match(/^([2-5])连肖$/u);
  if (dm) {
    const n = Number(dm[1]);
    const catByN = { 2: '连肖', 3: '三连肖', 4: '四连肖', 5: '五连肖' };
    if (catByN[n]) return { category: catByN[n], groupSize: n };
  }
  if (t === '平特二连肖' || t === '平特二连') return { category: '平特二连', groupSize: 2 };
  if (t === '平特三连肖' || t === '平特三连') return { category: '平特三连', groupSize: 3 };
  if (t === '复式三连肖' || t === '复式三连') return { category: '复式三连肖', groupSize: 3 };
  if (t === '三有' || t === '三友') return { category: '三连肖', groupSize: 3 };
  if (t === '三连肖' || t === '三连') return { category: '三连肖', groupSize: 3 };
  if (t === '四连肖' || t === '四连' || t === '四有' || t === '四友' || t === '平特四连肖' || t === '平特四连') {
    return { category: '四连肖', groupSize: 4 };
  }
  if (t === '五连肖' || t === '五连') return { category: '五连肖', groupSize: 5 };
  if (t === '连肖' || t === '二连肖' || t === '二连') return { category: '连肖', groupSize: 2 };
  return { category: '', groupSize: 0 };
}

/** 三四连肖/三四有/三四友：复式同时展开「三连肖 C(n,3) + 四连肖 C(n,4)」，共用尾端金额 */
function isSiSanLianXiaoPlayAliasLine(s) {
  return /^(?:复式\s*)?三四(?:连)?(?:肖)?(?:有|友)?$/u.test(String(s || '').trim());
}

function matchSiSanLianXiaoDualPlayLine(line) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(line || '').match(
    new RegExp(`^(?:复式\\s*)?三四(?:连)?(?:肖)?(?:有|友)?\\s*([${zx}]+)\\s*(各[\\s\\S]+)$`, 'u')
  );
}

function expandSiSanLianXiaoDualPlayOneLine(line) {
  const s0 = String(line || '').trim();
  const m = matchSiSanLianXiaoDualPlayLine(s0);
  if (!m) return s0;
  const zt = parseZodiacTokens(m[1]);
  if (zt.length < 3) return s0;
  const tail = String(m[2] || '').trim();
  const lines = [];
  const combos3 = combinationsPickK(zt, 3);
  for (const zs of combos3) {
    lines.push(`三连肖${zs.join('')}${tail}`);
  }
  if (zt.length >= 4) {
    const combos4 = combinationsPickK(zt, 4);
    for (const zs of combos4) {
      lines.push(`四连肖${zs.join('')}${tail}`);
    }
  }
  return lines.length > 0 ? lines.join('\n') : s0;
}

/** n 肖复式：平特三连/三有/复试三有 + 超过 k 个生肖 → C(n,k) 组展开（无「复式」前缀亦生效） */
function expandMultiZodiacLianXiaoComboLine(line) {
  let s0 = String(line || '').trim();
  s0 = s0.replace(/^复试/u, '复式');
  const guidePat = '(?:(?:新澳门|香港|澳门|老澳门)\\s*)?';
  const zx = PREPROC_ZODIAC_CLASS;
  const playTok = '(?:复式\\s*)?(?:平特三连(?:肖)?|三连肖|三有|三友)';
  const m = s0.match(
    new RegExp(`^${guidePat}${playTok}\\s*([${zx}]+)\\s*((?:各|每组)[\\s\\S]+)$`, 'u')
  );
  if (!m) return String(line || '').trim();
  const categoryTok = /平特三连/u.test(m[0])
    ? '平特三连'
    : /复式|复试|三有|三友/u.test(m[0])
      ? '复式三连肖'
      : '三连肖';
  const { category, groupSize } = resolveFushiLianXiaoCategoryToken(categoryTok);
  if (!category || groupSize < 2) return String(line || '').trim();
  const zodiacs = parseZodiacTokens(m[1]);
  if (zodiacs.length <= groupSize) return String(line || '').trim();
  const combos = combinationsPickK(zodiacs, groupSize);
  if (combos.length <= 1) return String(line || '').trim();
  const tail = String(m[2] || '').replace(/^每组/u, '各').trim();
  const guide = (s0.match(/^(新澳门|香港|澳门|老澳门)/u) || [])[0] || '';
  return combos.map((zs) => `${guide}${category}${zs.join('')}${tail}`).join('\n');
}

/** 「平特二连复式猪羊狗猴各50」：玩法在前、复式在后 → C(n,2) 全组合展开 */
function expandPingTeLianXiaoFushiSuffixOneLine(line) {
  const s0 = String(line || '').trim().replace(/^复试/u, '复式');
  const zx = PREPROC_ZODIAC_CLASS;
  const guidePat = '(?:(新澳门|香港|澳门|老澳门)\\s*)?';
  const tailPat = `(各[\\s\\S]+)$`;
  const m =
    s0.match(
      new RegExp(`^${guidePat}(平特[二三四五]连(?:肖)?)\\s*复式\\s*([${zx}]+)\\s*${tailPat}`, 'u')
    ) ||
    s0.match(
      new RegExp(`^${guidePat}([二三四五]连(?:肖)?)\\s*复式\\s*([${zx}]+)\\s*${tailPat}`, 'u')
    );
  if (!m) return String(line || '').trim();
  const guide = String(m[1] || '').trim();
  const playTok = String(m[2] || '').trim();
  const { category, groupSize } = resolveFushiLianXiaoCategoryToken(playTok);
  if (!category || groupSize < 2) return s0;
  const zodiacs = parseZodiacTokens(m[3]);
  if (zodiacs.length < groupSize) return s0;
  const combos = combinationsPickK(zodiacs, groupSize);
  if (combos.length <= 1) return s0;
  const tail = String(m[4] || '').trim();
  return combos.map((zs) => `${guide}${category}${zs.join('')}${tail}`).join('\n');
}

/** 复式连肖/平特连肖：从 n 肖中取 k 肖的全部组合，尾端共用「各+金额」 */
function expandFushiLianXiaoOneLine(line) {
  const s0 = String(line || '').trim();
  const pingTeFushi = expandPingTeLianXiaoFushiSuffixOneLine(s0);
  if (pingTeFushi !== s0) return pingTeFushi;
  const multi = expandMultiZodiacLianXiaoComboLine(s0);
  if (multi !== s0) return multi;
  const s1 = s0.replace(/^复试/u, '复式');
  if (!s1.includes('复式')) return s0;
  if (matchSiSanLianXiaoDualPlayLine(s1)) return expandSiSanLianXiaoDualPlayOneLine(s1);
  const zx = PREPROC_ZODIAC_CLASS;
  const m = s1.match(
    new RegExp(
      `^复式\\s*(平特[二三四五]连(?:肖)?|平特三连(?:肖)?|[二三四五]连(?:肖)?|连肖)\\s*([${zx}]+)\\s*(各[\\s\\S]+)$`,
      'u'
    )
  );
  if (!m) return s0;
  const { category, groupSize } = resolveFushiLianXiaoCategoryToken(m[1]);
  if (!category || groupSize < 2) return s0;
  const zodiacs = parseZodiacTokens(m[2]);
  if (zodiacs.length < groupSize) return s0;
  const combos = combinationsPickK(zodiacs, groupSize);
  if (combos.length <= 1) return s0;
  const tail = String(m[3] || '').trim();
  const groups = combos.map((zs) => zs.join('')).join(' ');
  return `${category}${groups}${tail}`;
}

function resolveLianMaZhongPlayGroupSize(tok) {
  const t = String(tok || '')
    .replace(/\s/g, '')
    .replace(/[2２]/g, '二')
    .replace(/[3３]/g, '三');
  if (t === '二中二') return 2;
  if (t === '三中三' || t === '三中二' || t === '中三') return 3;
  return 0;
}

/** 连码球号列表：支持 01-02-03、点分、空格 */
function parseHyphenSeparatedBallList(seg) {
  let t = String(seg || '').trim();
  t = t.replace(/(\d)\s*[-－]\s*(?=\d)/g, '$1 ');
  return splitItemList(normalizeOrderTargetSeparators(t));
}

function expandLianMaFushiCombos(balls, groupSize, tail) {
  const gs = Math.floor(Number(groupSize));
  if (!gs || balls.length < gs) return null;
  const combos = combinationsPickK(balls, gs);
  if (combos.length <= 1) return null;
  const tailS = String(tail || '').trim();
  return combos
    .map((bs) => `连码${bs.map((b) => String(b).padStart(2, '0')).join(' ')}${tailS}`)
    .join('\n');
}

/** 集合未入库时的尾数球表（与 seed 尾数集合一致） */
const LIANMA_WEI_TAIL_FALLBACK = {
  0: [10, 20, 30, 40],
  1: [1, 11, 21, 31, 41],
  2: [2, 12, 22, 32, 42],
  3: [3, 13, 23, 33, 43],
  4: [4, 14, 24, 34, 44],
  5: [5, 15, 25, 35, 45],
  6: [6, 16, 26, 36, 46],
  7: [7, 17, 27, 37, 47],
  8: [8, 18, 28, 38, 48],
  9: [9, 19, 29, 39, 49],
};

function resolveLianMaWeiTuoBallPool(db, specRaw) {
  const raw = String(specRaw || '').trim();
  const weiM = raw.match(/^(\d)尾$/u);
  if (weiM) {
    const setName = `${weiM[1]}尾`;
    if (db) {
      const fromDb = uniqueNumbers(resolveSetItems(db, setName));
      if (fromDb.length > 0) return fromDb;
    }
    return LIANMA_WEI_TAIL_FALLBACK[weiM[1]] ? [...LIANMA_WEI_TAIL_FALLBACK[weiM[1]]] : [];
  }
  const compact = raw.replace(/[,\s，、·•]/g, '');
  if (compact && isCompactZodiacOnly(compact)) {
    const out = [];
    for (const z of parseZodiacTokens(compact)) {
      out.push(...zodiacBallNumbersForOrder(z, new Date(), 1, 49));
    }
    return uniqueNumbers(out);
  }
  return [];
}

/** 连码胆拖：二中二4尾拖8尾各组10、二中二4尾拖猪各组10 → 胆×拖 展开为多行连码 */
function expandLianMaWeiTuoZhongPlayOneLine(line, db) {
  const s0 = String(line || '').trim();
  if (!s0.includes('拖')) return s0;
  const headPat = '(?:(?:平特连码|连码)\\s*)?';
  const playPat = '(?:二中二|三中三|三中二|中三|2中2|3中3|3中2|2中二|3中三|3中二)';
  const m = s0.match(
    new RegExp(
      `^${headPat}${playPat}(\\d)尾拖(?:(\\d)尾|([${PREPROC_ZODIAC_CLASS}]+))\\s*(各[\\s\\S]+)$`,
      'u'
    )
  );
  if (!m) return s0;
  const playTok = String(s0.match(new RegExp(playPat, 'u'))?.[0] || '');
  const groupSize = resolveLianMaZhongPlayGroupSize(playTok);
  if (groupSize !== 2) return s0;
  const danBalls = resolveLianMaWeiTuoBallPool(db, `${m[1]}尾`);
  const tuoSpec = m[2] ? `${m[2]}尾` : String(m[3] || '').trim();
  const tuoBalls = resolveLianMaWeiTuoBallPool(db, tuoSpec);
  if (danBalls.length === 0 || tuoBalls.length === 0) return s0;
  const tailS = String(m[4] || '').trim();
  const lines = [];
  for (const a of danBalls) {
    for (const b of tuoBalls) {
      if (a === b) continue;
      lines.push(`连码${String(a).padStart(2, '0')} ${String(b).padStart(2, '0')}${tailS}`);
    }
  }
  return lines.length > 0 ? lines.join('\n') : s0;
}

/**
 * 平特连码复式：复式三中三1-2-3-4各组10 → C(n,3) 条连码各 10（玩法名即二中二/三中三/三中二/中三）。
 */
function expandFushiLianMaZhongPlayOneLine(line) {
  let s0 = String(line || '').trim();
  const guideM = s0.match(/^(新澳门|香港|澳门|老澳门)\s*/u);
  const guidePrefix = guideM ? guideM[0] : '';
  if (guidePrefix) s0 = s0.slice(guidePrefix.length).trim();
  const headPat = '(?:(?:平特连码|连码)\\s*)?';
  const playPat = '(?:二中二|三中三|三中二|中三|2中2|3中3|3中2|2中二|3中三|3中二)';
  const ballsPat = '[\\d\\s.,，、·•\\-－]+';
  const m =
    s0.match(
      new RegExp(`^${headPat}复式\\s*${playPat}\\s*(${ballsPat})\\s*(各[\\s\\S]+)$`, 'u')
    ) ||
    s0.match(new RegExp(`^${headPat}${playPat}\\s*(${ballsPat})\\s*(各[\\s\\S]+)$`, 'u'));
  if (!m) return String(line || '').trim();
  const playTok = String(s0.match(new RegExp(playPat, 'u'))?.[0] || '');
  const groupSize = resolveLianMaZhongPlayGroupSize(playTok);
  if (!groupSize) return String(line || '').trim();
  const balls = parseHyphenSeparatedBallList(m[1]);
  if (balls.length < groupSize) return String(line || '').trim();
  const tailS = String(m[2] || '').trim();
  if (balls.length === groupSize) {
    const one = `连码${balls.map((b) => String(b).padStart(2, '0')).join(' ')}${tailS}`;
    return guidePrefix ? `${guidePrefix}${one}` : one;
  }
  const expanded = expandLianMaFushiCombos(balls, groupSize, tailS);
  if (!expanded) return String(line || '').trim();
  return guidePrefix
    ? expanded
        .split('\n')
        .map((ln) => `${guidePrefix}${ln}`)
        .join('\n')
    : expanded;
}

/** 复式连码：从 n 码中取 k 码的全部组合（默认二中；可写「复式三中连码」） */
function expandFushiLianMaOneLine(line) {
  const s0 = String(line || '').trim();
  const zhong = expandFushiLianMaZhongPlayOneLine(s0);
  if (zhong !== s0) return zhong;
  if (!s0.includes('复式') || !s0.includes('连码')) return s0;
  const m = s0.match(/^复式\s*(?:(二|三|2|3)中(?:[二三2-3])?\s*)?连码\s*([\d\s.,，、·•\-－]+)\s*(各[\s\S]+)$/u);
  if (!m) return s0;
  let groupSize = 2;
  const gHint = String(m[1] || '').trim();
  if (gHint === '三' || gHint === '3') groupSize = 3;
  const balls = parseHyphenSeparatedBallList(m[2]);
  if (balls.length < groupSize) return s0;
  const expanded = expandLianMaFushiCombos(balls, groupSize, m[3]);
  return expanded || s0;
}

function expandFushiLianXiaoAndLianMaPerLine(text, db = null) {
  return String(text || '')
    .split('\n')
    .flatMap((ln) => {
      let s = expandSiSanLianXiaoDualPlayOneLine(ln);
      return s.split('\n').flatMap((sub) => {
        sub = expandLianMaWeiTuoZhongPlayOneLine(sub, db);
        sub = expandFushiLianMaZhongPlayOneLine(sub);
        sub = expandFushiLianXiaoOneLine(sub);
        sub = expandFushiLianMaOneLine(sub);
        return sub.split('\n').filter((x) => String(x || '').trim());
      });
    })
    .join('\n');
}

/**
 * 「鸡猪狗牛 鸡猪狗蛇。各100」类：多组生肖连写、尾端共用「各+金额」，按玩法字数均分（句号被换行吞掉时仍可靠）。
 */
function tryParseLianXiaoSharedAmountClauses(s0, db, categoryWord) {
  const cat = String(categoryWord || '').trim();
  const groupSize = getLianXiaoGroupSize(cat);
  if (!groupSize || !isLianXiaoCategory(cat)) return null;
  const piece = String(s0 || '').trim();
  if (!piece) return null;
  const single = parseDataSegment(piece, db);
  if (!single || !Number.isFinite(Number(single.value))) return null;
  const algo = single.algo;
  const value = Number(single.value);
  const groups = splitZodiacGroupsFromTextBlock(String(single.targetRaw || ''), groupSize);
  if (groups.length > 1) {
    return groups.map((g) => ({ targetRaw: g, algo, value }));
  }
  const compact = String(single.targetRaw || '').replace(/[,\s，、·•。.]/g, '');
  if (!compact || !isCompactZodiacOnly(compact)) return null;
  if (compact.length % groupSize !== 0) return null;
  if (compact.length === groupSize) return null;
  const out = [];
  for (let i = 0; i < compact.length; i += groupSize) {
    out.push({ targetRaw: compact.slice(i, i + groupSize), algo, value });
  }
  return out.length > 0 ? out : null;
}

/** 「连肖 龙虎50 虎羊50 …」：玩法下多组「生肖+裸金额」链式子句 */
function tryParseLianXiaoChainedImplicitAmountClauses(s0, db, categoryWord) {
  const cat = String(categoryWord || '').trim();
  const groupSize = getLianXiaoGroupSize(cat);
  if (!groupSize || !isLianXiaoCategory(cat)) return null;
  const piece = String(s0 || '').trim();
  if (!piece) return null;
  const zx = PREPROC_ZODIAC_CLASS;
  const cnAmt = '零○〇一二三四五六七八九十百千万两俩贰廿卅';
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  const re = new RegExp(
    `([${zx}]{${groupSize}})(?:各\\s*)?(\\d+(?:\\.\\d+)?|[${cnAmt}]+)(?![\\d])`,
    'gu'
  );
  const hits = [...piece.matchAll(re)];
  if (hits.length < 2) return null;
  const out = [];
  for (const h of hits) {
    const v = tryParseAmountToken(String(h[2] || ''), unitSynonyms);
    if (v == null || !Number.isFinite(Number(v))) return null;
    out.push({ targetRaw: h[1], algo: '各', value: Number(v) });
  }
  return out.length > 0 ? out : null;
}

/** 连码：多组球号连写、尾端共用「各+金额」（含复式展开后的 01 02 01 03 …各10） */
function tryParseLianMaSharedAmountClauses(s0, db, categoryWord) {
  if (String(categoryWord || '').trim() !== '连码') return null;
  const piece = String(s0 || '').trim();
  if (!piece) return null;
  const single = parseDataSegment(piece, db);
  if (!single || !Number.isFinite(Number(single.value))) return null;
  const balls = splitItemList(String(single.targetRaw || '').trim());
  if (balls.length < 2) return null;
  let groupSize = 0;
  const uniqN = new Set(balls).size;
  if (balls.length === 3) groupSize = 3;
  else if (balls.length > 3 && balls.length % 3 === 0 && uniqN >= balls.length * 0.75) groupSize = 3;
  else if (balls.length % 2 === 0) groupSize = 2;
  if (!groupSize || balls.length === groupSize) return null;
  const algo = single.algo;
  const value = Number(single.value);
  const out = [];
  for (let i = 0; i < balls.length; i += groupSize) {
    const chunk = balls.slice(i, i + groupSize);
    if (chunk.length !== groupSize) break;
    out.push({
      targetRaw: chunk.map((b) => String(b).padStart(2, '0')).join(' '),
      algo,
      value,
    });
  }
  return out.length > 1 ? out : null;
}

/**
 * 「五连虎鸡兔猴猪。猴猪鸡兔鼠各50」：口语在连带生肖间断句，连肖玩法下合并为连续生肖再接「各」。
 * 仅当句段以「三四五连」起首时才合并，避免误伤「羊鼠鸡狗猴。牛鸡羊猴蛇各一百」等句号分句。
 */
function collapseLianXiaoZodiacPeriodAfterPlayWord(s0) {
  const zx = PREPROC_ZODIAC_CLASS;
  return String(s0 || '').replace(
    new RegExp(
      `([三四五]连(?:肖)?[${zx}]+)[。.](?=[${zx}]+\\s*(?:各|各数|各位|各号|各个|个数))`,
      'gu'
    ),
    '$1'
  );
}

function matchLeadingSanSiWuLianFromDataChunk(chunk) {
  const m = String(chunk || '').match(/^([三四五]连)(?:肖)?/u);
  if (!m) return null;
  const map = { 三: '三连肖', 四: '四连肖', 五: '五连肖' };
  const category = map[m[1][0]];
  if (!category) return null;
  return { category, leaderLen: m[0].length };
}

/**
 * 同一路由行首为连肖时，数据段内再出现「三四五连+生肖」视为新开连肖玩法（如先四连肖再五连肖），
 * 拆成多条独立下单行，避免整段被当作第一条玩法的 payload。
 */
function fanOutEmbeddedLianXiaoOrderLines(db, wxGroupId, lineText) {
  const text = String(lineText || '').trim();
  if (!text || !db) return [text];
  const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
  const detected = detectLineRoutePrefix(text, routePrefixes);
  if (!detected || !isLianXiaoCategory(detected.category)) return [text];
  const peeled = peelRoutePrefixFromLine(text, routePrefixes);
  if (!peeled || !String(peeled.rest || '').trim()) return [text];
  const guide = detected.guide;
  const firstCat = detected.category;
  const zx = PREPROC_ZODIAC_CLASS;
  const reEmbed = new RegExp(
    `(?:\\s+|(?<=[${zx}])[。.])(?=[三四五]连(?:肖)?[${zx}])`,
    'gu'
  );
  let data = String(peeled.rest || '').trim();
  const splitIdx = [];
  for (const m of data.matchAll(reEmbed)) splitIdx.push(m.index);
  if (splitIdx.length === 0) return [text];
  const chunks = [];
  let start = 0;
  for (const idx of splitIdx) {
    chunks.push(data.slice(start, idx).trim());
    start = idx;
  }
  chunks.push(data.slice(start).trim());
  const out = [];
  for (let i = 0; i < chunks.length; i += 1) {
    const chunk0 = String(chunks[i] || '').trim();
    if (!chunk0) continue;
    const chunk = collapseLianXiaoZodiacPeriodAfterPlayWord(chunk0);
    if (i === 0) {
      out.push(`${guide}${firstCat}${chunk}`);
      continue;
    }
    const inf = matchLeadingSanSiWuLianFromDataChunk(chunk);
    if (!inf) return [text];
    const rest = String(chunk.slice(inf.leaderLen || 0) || '').trimStart();
    out.push(`${guide}${inf.category}${rest}`);
  }
  return out.length > 1 ? out : [text];
}

/**
 * 多条「纯球表 + 各 + 金额」子句金额一致时，可能是 takeFirstClauseFromLeft 被库内较前算法词误切；
 * 若整段 parseDataSegment 得到同额单条且球号个数一致，则合并为一条（例：04,…,33,41各30 勿拆成 前六码+41各30）。
 */
function clausesAllNumericGeSameValue(clauses) {
  if (!Array.isArray(clauses) || clauses.length < 2) return false;
  let v;
  for (const c of clauses) {
    if (String(c?.algo || '') !== '各') return false;
    const tr = String(c?.targetRaw || '').trim();
    if (!isNumericBallTargetListOnly(tr)) return false;
    const n = Number(c.value);
    if (!Number.isFinite(n)) return false;
    if (v === undefined) v = n;
    else if (v !== n) return false;
  }
  return true;
}

function tryMergeChainedNumericGeToMonolithic(s0, clauses, db, parseOpts) {
  if (!clausesAllNumericGeSameValue(clauses)) return null;
  const whole = parseDataSegment(s0, db, parseOpts);
  if (!whole || String(whole.algo || '') !== '各') return null;
  if (Number(whole.value) !== Number(clauses[0].value)) return null;
  const wHead = String(whole.targetRaw || '').trim();
  if (!isNumericBallTargetListOnly(wHead)) return null;
  const nWhole = splitItemList(wHead).length;
  const nChain = clauses.reduce((acc, c) => acc + splitItemList(String(c.targetRaw || '').trim()).length, 0);
  if (nWhole !== nChain || nWhole < 2) return null;
  return [whole];
}

/** 一行内多组「目标+各+金额」连写时的全部子句（自左向右顺序）；子句语义模型见 parseDataSegment。 */
function parseAllDataSegmentClauses(dataSegment, db, parseOpts = {}) {
  let s0 = applyOrderUnitAmountBoundaryPerLine(
    stripLeadingOrderNoise(String(dataSegment || '').trim()),
    db,
    parseOpts?.wxGroupId ?? null
  );
  s0 = stripLeadingRedundantChannelInterjection(s0);
  s0 = stripRedundantAoTeHeaderFromDataSegment(s0);
  if (!s0) return [];
  s0 = peelTrailingRouteFromDataSegment(db, s0);
  s0 = peelLooseAotaChannelTailFromData(s0);
  s0 = String(s0 || '').trim();
  if (!s0) return [];
  s0 = preNormalizeLottoTwoDigitDotChains(s0);
  const periodShared = tryParseZodiacPeriodSharedTailClauses(s0, db);
  if (periodShared && periodShared.length > 0) return periodShared;

  const catOpt = String(parseOpts?.categoryWord || '').trim();
  if (isLianXiaoCategory(catOpt)) {
    const collapsed = collapseLianXiaoZodiacPeriodAfterPlayWord(s0);
    if (collapsed !== s0) s0 = collapsed;
  }
  const lianChained = tryParseLianXiaoChainedImplicitAmountClauses(s0, db, catOpt);
  if (lianChained && lianChained.length > 0) return lianChained;
  const lianChunked = tryParseLianXiaoSharedAmountClauses(s0, db, catOpt);
  if (lianChunked && lianChunked.length > 0) return lianChunked;
  const lianMaChunked = tryParseLianMaSharedAmountClauses(s0, db, catOpt);
  if (lianMaChunked && lianMaChunked.length > 0) return lianMaChunked;

  /** 仅出现一个「各」时整段必是单条子句；先走 parseDataSegment，避免 takeFirstClauseFromLeft 被库内靠前算法词误切成「前几码 + 尾码各」 */
  const geCharCount = (String(s0).match(/各/gu) || []).length;
  if (geCharCount === 1) {
    const monolithic = parseDataSegment(s0, db, parseOpts);
    if (monolithic) return [monolithic];
  }

  const clauses = [];
  let work = s0;
  for (let guard = 0; guard < 64; guard += 1) {
    const next = takeFirstClauseFromLeft(work, db, parseOpts);
    if (!next) break;
    clauses.push(next.parsed);
    work = stripLeadingOrderNoise(String(next.rest || '').trim());
    if (!work) break;
  }
  if (clauses.length === 0) {
    const single = parseDataSegment(s0, db, parseOpts);
    if (single) return [single];
  } else {
    const merged = tryMergeChainedNumericGeToMonolithic(s0, clauses, db, parseOpts);
    if (merged) return merged;
  }
  return clauses;
}

/**
 * 「特肖马100」：玩法名为「特肖马」（末字为生肖），数据段只有金额时把末字生肖补成投注目标再解析。
 */
function tryParseClausesWithTrailingCategoryZodiac(db, categoryWord, dataSegment) {
  const cat = String(categoryWord || '').trim();
  const ds = String(dataSegment || '').trim();
  if (!cat || !ds) return null;
  if (parseAllDataSegmentClauses(ds, db, { categoryWord: cat }).length > 0) return null;
  const lastCp = [...cat].pop();
  if (!lastCp) return null;
  const z = normalizeZodiacHanChar(lastCp);
  if (!ZODIAC_ORDER.includes(z)) return null;
  const merged = `${z}${ds}`;
  const clauses = parseAllDataSegmentClauses(merged, db, { categoryWord: cat });
  return clauses.length > 0 ? clauses : null;
}

function parseTargetKeywordMatchers(db, targetRaw, allSetNames) {
  const text = normalizeOddEvenColloquialTargets(normalizeOrderTargetSeparators(String(targetRaw || '').trim()));
  if (!text) return [];
  const sortedSetNames = [...allSetNames].sort((a, b) => b.length - a.length);
  const chunks = text.split(/[,\s，、·•]+/).map((x) => x.trim()).filter(Boolean);
  const out = [];
  const pushMatcher = (label, nums) => {
    const values = uniqueNumbers((Array.isArray(nums) ? nums : []).map((x) => Number(x)).filter((x) => Number.isFinite(x)));
    if (!label || values.length === 0) return;
    out.push({ label, nums: values });
  };
  for (const chunk of chunks) {
    let cursor = chunk;
    while (cursor) {
      const setName = sortedSetNames.find((name) => cursor.startsWith(name));
      if (setName) {
        pushMatcher(setName, resolveSetItems(db, setName));
        cursor = cursor.slice(setName.length);
        continue;
      }
      const first = cursor[0];
      const z0 = normalizeZodiacHanChar(first);
      if (ZODIAC_ORDER.includes(z0)) {
        pushMatcher(z0, zodiacBallNumbersForOrder(z0, new Date(), 1, 49));
        cursor = cursor.slice(1);
        continue;
      }
      const mNum = cursor.match(/^\d+(?:\.\d+)?/);
      if (mNum) {
        const n = Number(mNum[0]);
        if (Number.isFinite(n)) pushMatcher(String(Math.floor(n)), [n]);
        cursor = cursor.slice(mNum[0].length);
        continue;
      }
      if (cursor[0] && ORDER_NOISE_ONE_CHAR_RE.test(cursor[0])) {
        cursor = cursor.slice(1);
        continue;
      }
      cursor = cursor.slice(1);
    }
  }
  return out;
}

function resolveBatchTargetRaw(batch, db) {
  const content = String(batch?.content || '').trim();
  if (!content) return '';
  const guide = String(batch?.guideWord || '').trim();
  const category = String(batch?.categoryWord || '').trim();
  let body = content;
  if (guide && body.startsWith(guide)) body = body.slice(guide.length).trim();
  if (category && body.startsWith(category)) body = body.slice(category.length).trim();
  if (category === '特') body = stripLeadingOralMenAfterTeDataSegment(body);
  const parsed = parseDataSegment(body, db) || parseDataSegment(content, db);
  return parsed?.targetRaw ? String(parsed.targetRaw).trim() : '';
}

function parseDataSegmentFromBatchContent(batch, db) {
  const content = String(batch?.content || '').trim();
  if (!content) return null;
  const guide = String(batch?.guideWord || '').trim();
  const category = String(batch?.categoryWord || '').trim();
  let body = content;
  if (guide && body.startsWith(guide)) body = body.slice(guide.length).trim();
  if (category && body.startsWith(category)) body = body.slice(category.length).trim();
  if (category === '特') body = stripLeadingOralMenAfterTeDataSegment(body);
  return parseDataSegment(body, db) || parseDataSegment(content, db);
}

function orderedKeywordLabelsForItem(keywordMatchers, item) {
  const n = Number(item);
  if (!Number.isFinite(n)) return [];
  const labels = [];
  const seen = new Set();
  for (const m of keywordMatchers) {
    if (m.nums.includes(n) && !seen.has(m.label)) {
      seen.add(m.label);
      labels.push(m.label);
    }
  }
  return labels;
}

function formatOrderItemLineWithKeywords(keywordMatchers, item, amount, { algo, unitValue, zodiacRef } = {}) {
  const labels = orderedKeywordLabelsForItem(keywordMatchers, item);
  let extra = '';
  const algoStr = String(algo || '').trim();
  if (algoStr === '各' && Number.isFinite(Number(unitValue)) && labels.length > 0) {
    const u = Number(unitValue);
    extra = `（${labels.map((l) => `${l}+${formatAmount(u)}`).join('，')}）`;
  } else if (labels.length > 0) {
    extra = `（${labels.join('，')}）`;
  }
  return `${formatTicketItemLabel(item, zodiacRef)}${extra} => ${formatAmount(amount)}`;
}

function detectLineRoutePrefix(lineText, routePrefixes) {
  const text = String(lineText || '').trim();
  if (!text) return null;
  for (const p of routePrefixes) {
    if (!text.startsWith(p.matchPrefix)) continue;
    if (p.category === '特') {
      const rest = text.slice(p.matchPrefix.length);
      if (/^肖/u.test(rest)) continue;
    }
    return p;
  }
  return null;
}

function buildSortedRoutePrefixes(db) {
  const routes = db
    .prepare(
      `SELECT guide_word, category_word
       FROM cmd_routes
       WHERE is_active = 1
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')`
    )
    .all();
  return routes
    .map((r) => ({
      guide: normalizeGuideWord(r.guide_word),
      category: String(r.category_word || '').trim(),
    }))
    .filter((x) => x.guide && x.category)
    .map((x) => {
      const prefix = `${x.guide}${x.category}`;
      return { ...x, prefix, matchPrefix: prefix };
    })
    .sort((a, b) => b.prefix.length - a.prefix.length);
}

function buildSortedRoutePrefixesForGroup(db, wxGroupId) {
  return getParseCache(db, `routePrefixes:${wxGroupId ?? ''}`, () =>
    buildSortedRoutePrefixesForGroupImpl(db, wxGroupId)
  );
}

function buildSortedRoutePrefixesForGroupImpl(db, wxGroupId) {
  const routes = listActiveCmdRoutesForOrderParse(db, wxGroupId);
  let catSynRows = listSynonymPairs(db, 'category_word');
  const catToAliases = new Map();
  for (const r of routes) {
    const cat = String(r.category_word || '').trim();
    if (!cat) continue;
    if (!catToAliases.has(cat)) catToAliases.set(cat, new Set([cat]));
  }
  for (const s of catSynRows) {
    const canon = String(s.canonical_word || '').trim();
    const al = String(s.alias_word || '').trim();
    if (!canon || !al || !catToAliases.has(canon)) continue;
    catToAliases.get(canon).add(al);
  }
  const guideRepl = buildGuideStartReplacementList(db);
  /** @type {{ guide: string; category: string; prefix: string; matchPrefix: string }[]} */
  const entries = [];
  for (const r of routes) {
    const gNorm = normalizeGuideWord(r.guide_word);
    const catCanon = String(r.category_word || '').trim();
    if (!gNorm || !catCanon) continue;
    const gVariants = new Set([gNorm]);
    const rawG = String(r.guide_word || '').trim();
    if (rawG) gVariants.add(rawG);
    for (const { from, to } of guideRepl) {
      if (to === gNorm) gVariants.add(from);
    }
    const cSet = catToAliases.get(catCanon) || new Set([catCanon]);
    const prefixCanonical = `${gNorm}${catCanon}`;
    for (const gv of gVariants) {
      for (const cv of cSet) {
        const matchPrefix = `${gv}${cv}`;
        entries.push({
          guide: gNorm,
          category: catCanon,
          prefix: prefixCanonical,
          matchPrefix,
        });
      }
    }
  }
  entries.sort((a, b) => b.matchPrefix.length - a.matchPrefix.length);
  return entries;
}

/**
 * 数据段在「特」类玩法后多读一「门」（无后台「特门」分类）；仅当「门」后为空白/号码/各 等时剥掉。
 */
function stripLeadingOralMenAfterTeDataSegment(residual0) {
  const rest = String(residual0 || '');
  if (!rest.startsWith('门')) return residual0;
  const tail = rest.slice(1);
  if (tail === '') return '';
  if (/^\s+$/.test(tail)) return tail.trim();
  if (/^\s*[\d．.]/.test(tail) || /^\s*各/u.test(tail)) return tail.trimStart();
  return residual0;
}

function peelRoutePrefixFromLine(lineText, routePrefixes) {
  const detected = detectLineRoutePrefix(lineText, routePrefixes);
  if (!detected) return null;
  const text = String(lineText || '').trim();
  let rest = text.slice(detected.matchPrefix.length).trim();
  if (detected.prefix.endsWith('特')) {
    rest = stripLeadingOralMenAfterTeDataSegment(rest);
  }
  rest = String(rest || '').trim();
  return { prefix: detected.prefix, rest };
}

/**
 * 重度结构化：从已路由行拆出地区/玩法/子句（目标+算法+金额），供规范串回写。
 * 解析语义与 executeSingleConfiguredCommand 内 parseAllDataSegmentClauses 一致。
 */
function buildOrderLineStructuralAst(db, wxGroupId, lineText) {
  const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
  const text = String(lineText || '').trim();
  if (!text || !db) return null;
  const detected = detectLineRoutePrefix(text, routePrefixes);
  if (!detected) return null;
  const peeled = peelRoutePrefixFromLine(text, routePrefixes);
  if (!peeled) return null;
  const guide = detected.guide;
  const category = detected.category;
  let dataSegment = String(peeled.rest || '').trim();
  if (category === '特') dataSegment = String(stripLeadingOralMenAfterTeDataSegment(dataSegment) || '').trim();
  dataSegment = String(dataSegment || '').trim();
  if (!dataSegment) return null;
  let clauses = parseAllDataSegmentClauses(dataSegment, db, { routedGuideNorm: guide, categoryWord: category });
  if (clauses.length === 0) {
    const retry = tryParseClausesWithTrailingCategoryZodiac(db, category, dataSegment);
    if (retry && retry.length > 0) clauses = retry;
  }
  if (clauses.length === 0) return null;
  return {
    kind: 'order_line_v1',
    channel: guide,
    play: category,
    clauses: clauses.map((p) => ({
      targetRaw: p.targetRaw,
      algo: p.algo,
      value: p.value,
      itemsType: inferClauseItemsTypeForAst(category, p.targetRaw),
    })),
    rawLine: text,
  };
}

/** 能解析出 AST 时改写为规范串，否则保持原行（与块内逐行执行一致） */
function applyStructuralCanonicalLine(db, wxGroupId, lineText) {
  const ast = buildOrderLineStructuralAst(db, wxGroupId, lineText);
  const canon = ast ? emitCanonicalOrderLine(ast) : null;
  return canon || String(lineText || '').trim();
}

/** 仅号码网格行（点分、空格），下一行可能是「各位10元」 */
function isPureBallGridSegment(rest) {
  const t = String(rest || '').trim();
  if (!t) return false;
  return /^[\d.\s]+$/u.test(t);
}

/** 多行 buf 中每一段均为「空格分隔的 1～49 球号」时，展开为球号列表（无点号链）；否则 null */
function stackedSpaceSeparatedBallTokens(buf) {
  if (!Array.isArray(buf) || buf.length === 0) return null;
  const tokens = [];
  for (const segment of buf) {
    const t = String(segment || '').trim();
    if (!t) return null;
    for (const b of t.split(/\s+/).filter(Boolean)) {
      if (!/^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])$/.test(b)) return null;
      tokens.push(b);
    }
  }
  return tokens.length > 0 ? tokens : null;
}

/**
 * 「10元 20元」「10 20」等：与上一行空格球号列对齐，合成「26各10 38各20」
 */
function parseSpaceSeparatedAmountRow(rest) {
  let t = trimTrailingOrderNoise(stripLeadingOrderNoise(String(rest || '').trim()));
  if (!t) return null;
  const parts = t.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return null;
  const out = [];
  for (const p of parts) {
    const p2 = String(p)
      .replace(/(元|块|米|刀)+$/u, '')
      .trim();
    const m = p2.match(/^(\d+(?:\.\d+)?)$/);
    if (!m) return null;
    const n = Number(m[1]);
    if (!Number.isFinite(n) || n < 0) return null;
    out.push(n);
  }
  return out;
}

/** 「特」数据段「26 38 10元 20元」→「26各10 38各20」（前半均为球号、后半均为金额且个数一致；合并行被空格拼接时） */
function tryRewriteTeDataRestSpaceBallsThenAmountWords(rest) {
  const t = String(rest || '').trim();
  if (!t || /各|各位|各数|各号/u.test(t)) return null;
  const toks = t.split(/\s+/).filter(Boolean);
  if (toks.some((x) => /[.]/.test(x))) return null;
  const n = toks.length;
  if (n < 2) return null;
  for (let k = 1; k < n; k++) {
    const left = toks.slice(0, k);
    const right = toks.slice(k);
    if (left.length !== right.length) continue;
    if (!left.every((b) => /^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])$/.test(b))) continue;
    if (right.every((b) => parseLottoBallToken(b) != null)) continue;
    const amtStr = right.join(' ');
    const amounts = parseSpaceSeparatedAmountRow(amtStr);
    if (!amounts || amounts.length !== right.length) continue;
    return left.map((b, i) => `${b}各${amounts[i]}`).join(' ');
  }
  return null;
}

/** 「11 12 13 … 48 各5」：多球号 + 尾端单次「各+金额」→ 逐号各注 */
function tryRewriteTeDataRestBallsThenTrailingEachAmount(rest) {
  let t = trimTrailingOrderNoise(stripLeadingOrderNoise(String(rest || '').trim()));
  if (!t) return null;
  t = t.replace(/每个\s*各/gu, '各');
  const toks = t.split(/\s+/).filter(Boolean);
  if (toks.length < 2) return null;
  const last = toks[toks.length - 1];
  const m = last.match(/^各(\d+(?:\.\d+)?)$/u);
  if (!m) return null;
  const amt = m[1];
  const balls = toks.slice(0, -1);
  if (!balls.every((b) => /^(?:0?[1-9]|[12]\d|3[0-9]|4[0-9])$/.test(b))) return null;
  return balls
    .map((b) => {
      const n = parseInt(b, 10);
      return `${String(n).padStart(2, '0')}各${amt}`;
    })
    .join(' ');
}

function normalizeTeRouteSpaceBallAmountTableSameLine(lineText, routePrefixes) {
  const text = String(lineText || '').trim();
  if (!text) return text;
  const detected = detectLineRoutePrefix(text, routePrefixes);
  if (!detected || detected.category !== '特') return text;
  const peeled = peelRoutePrefixFromLine(text, routePrefixes);
  if (!peeled) return text;
  const rw =
    tryRewriteTeDataRestSpaceBallsThenAmountWords(peeled.rest) ||
    tryRewriteTeDataRestBallsThenTrailingEachAmount(peeled.rest);
  if (!rw) return text;
  return `${peeled.prefix}${rw}`.replace(/\s+/g, ' ').trim();
}

/**
 * 多行纯号码 + 随后一行「各位…算法+金额」合并为单行下单（表格粘贴）
 */
function mergeBallGridLinesWithAlgo(lines, routePrefixes, db = null) {
  const rows = Array.isArray(lines) ? lines : [];
  const out = [];
  let i = 0;
  while (i < rows.length) {
    const peeled = peelRoutePrefixFromLine(rows[i], routePrefixes);
    if (!peeled || !isPureBallGridSegment(peeled.rest)) {
      out.push(rows[i]);
      i++;
      continue;
    }
    const { prefix } = peeled;
    const buf = [peeled.rest.trim()];
    let j = i + 1;
    let merged = null;
    while (j < rows.length) {
      const rowJ = String(rows[j] || '').trim();
      const pn = peelRoutePrefixFromLine(rowJ, routePrefixes);
      let nextRest = '';
      if (pn) {
        if (pn.prefix !== prefix) break;
        nextRest = String(pn.rest || '').trim();
      } else {
        nextRest = rowJ;
      }
      if (isPureBallGridSegment(nextRest)) {
        buf.push(nextRest);
        j++;
        continue;
      }
      const ballToks = stackedSpaceSeparatedBallTokens(buf);
      const amounts = parseSpaceSeparatedAmountRow(nextRest);
      if (ballToks && amounts && ballToks.length === amounts.length) {
        merged = `${prefix}${ballToks.map((b, k) => `${b}各${amounts[k]}`).join(' ')}`
          .replace(/\s+/g, ' ')
          .trim();
      } else if (
        db &&
        (lineIsEachAlgoAmountOnlyForGlueOrphan(nextRest, db) ||
          restStartsWithEligibleEachAlgoLine(nextRest, db))
      ) {
        merged = `${prefix}${buf.join(' ')} ${nextRest}`.replace(/\s+/g, ' ').trim();
      } else {
        merged = `${prefix}${buf.join(' ')} ${nextRest}`.replace(/\s+/g, ' ').trim();
      }
      j++;
      break;
    }
    if (merged) {
      out.push(merged);
      i = j;
    } else {
      for (let k = i; k < i + buf.length && k < rows.length; k++) out.push(rows[k]);
      i += buf.length;
    }
  }
  return out;
}

/** 下一行是否为「按目标一份金额」算法起头且后跟可解析金额（含 各十 等内嵌额） */
function restStartsWithEligibleEachAlgoLine(rest, db) {
  const s0 = trimTrailingOrderNoise(stripLeadingOrderNoise(String(rest || '').trim()));
  if (!s0) return false;
  const { aliasToCanonical, orderedTokens } = getAlgoAliasData(db);
  const unitSynonyms = getOrderAmountUnitSynonyms(db);
  for (const tok of orderedTokens) {
    if (!s0.startsWith(tok)) continue;
    if (aliasToCanonical.get(tok) !== '各') continue;
    if (tryIntrinsicPerTargetAmountFromTok(tok, unitSynonyms, aliasToCanonical) != null) return true;
    const afterTok = s0.slice(tok.length);
    const fs = parseValueFromStartAmount(afterTok, { unitSynonyms });
    if (fs && Number.isFinite(Number(fs.value))) return true;
  }
  return false;
}

/**
 * 多行：上一行路由下仅连续生肖，下一行同路由以各/各位…+金额 → 并为单行（如「鸡」换行「各位10」）
 */
function mergeZodiacHeadLinesWithEachAlgo(lines, routePrefixes, db) {
  const rows = Array.isArray(lines) ? lines : [];
  const out = [];
  let i = 0;
  while (i < rows.length) {
    const cur = String(rows[i] || '').trim();
    if (!cur) {
      i++;
      continue;
    }
    const peeled = peelRoutePrefixFromLine(cur, routePrefixes);
    if (!peeled || i + 1 >= rows.length) {
      out.push(cur);
      i++;
      continue;
    }
    const zodiacRest = String(peeled.rest || '').trim();
    if (!isCompactZodiacOnly(zodiacRest)) {
      out.push(cur);
      i++;
      continue;
    }
    const next = String(rows[i + 1] || '').trim();
    const pn = peelRoutePrefixFromLine(next, routePrefixes);
    if (!pn || pn.prefix !== peeled.prefix) {
      out.push(cur);
      i++;
      continue;
    }
    const algoRest = String(pn.rest || '').trim();
    if (!restStartsWithEligibleEachAlgoLine(algoRest, db)) {
      out.push(cur);
      i++;
      continue;
    }
    out.push(`${peeled.prefix}${zodiacRest}${algoRest}`);
    i += 2;
  }
  return out;
}

/** 汇总尾巴「一共185」「共46元」等，不参与下单 */
function isOrderSummaryFooterLine(lineText, routePrefixes) {
  let t = String(lineText || '').trim();
  const peeled = peelRoutePrefixFromLine(lineText, routePrefixes);
  if (peeled) t = peeled.rest.trim();
  return (
    /^一共\s*\d+\s*元?\s*$/u.test(t) ||
    /^合计\s*\d+/u.test(t) ||
    /^共\s*\d+\s*元?\s*$/u.test(t)
  );
}

function normalizeMultilineCommandLines(db, rawLines, routePrefixesArg, wxGroupId = null) {
  const routePrefixes = routePrefixesArg || buildSortedRoutePrefixesForGroup(db, wxGroupId);
  let currentPrefix = '';
  let pendingGuideNorm = '';
  const rows = Array.isArray(rawLines) ? rawLines : [];
  const out = [];
  for (const line of rows) {
    let text = String(line || '').trim();
    if (!text) {
      out.push('');
      continue;
    }
    text = applyLongestGuidePrefixReplacement(db, text);
    text = normalizeRoutePrefixWithSynonyms(db, text);
    const guideOnly = lineIsGuideWordOnly(db, text);
    if (guideOnly) {
      pendingGuideNorm = guideOnly;
      out.push('');
      continue;
    }
    if (pendingGuideNorm) {
      text = `${pendingGuideNorm}${text}`;
      pendingGuideNorm = '';
    }
    const detected = detectLineRoutePrefix(text, routePrefixes);
    if (detected) {
      currentPrefix = detected.prefix;
      if (text === detected.prefix || text === detected.matchPrefix) {
        out.push('');
        continue;
      }
      out.push(text);
      continue;
    }
    if (currentPrefix) {
      /** 本行可单独成单（如「猴平特100」）时勿拼上一行的渠道+分类，避免变成「新澳门特猴平特100」 */
      const standalone = ensureRoutedOrderLine(db, text, '', wxGroupId);
      if (contentMatchesAnyRoute(db, standalone, wxGroupId)) {
        const det2 = detectLineRoutePrefix(standalone, routePrefixes);
        if (det2) currentPrefix = det2.prefix;
        out.push(standalone);
        continue;
      }
      const glued = `${currentPrefix}${text}`;
      const repaired = hoistTrailingCategoryAfterZodiacs(db, glued);
      if (contentMatchesAnyRoute(db, repaired, wxGroupId)) {
        const det2 = detectLineRoutePrefix(repaired, routePrefixes);
        if (det2) currentPrefix = det2.prefix;
        out.push(repaired);
        continue;
      }
      out.push(glued);
      continue;
    }
    out.push(text);
  }
  return out;
}

function dateToYmd(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function persistOrderRows(
  db,
  { wxGroupId, senderWxid, route, content, payload, settlementDate, orderBatchId, wxMsgId = '', wxNewMsgId = '' }
) {
  if (!wxGroupId || !senderWxid || !Array.isArray(payload?.results) || payload.results.length === 0) return;
  const wxM = String(wxMsgId || '').trim() || null;
  const wxN = String(wxNewMsgId || '').trim() || null;
  const stmt = db.prepare(
    `INSERT INTO cmd_orders
    (order_batch_id, wx_group_id, sender_wxid, guide_word, category_word, target_label, algo, cmd_value, item_value, order_amount, settlement_date, content_preview, wx_msg_id, wx_new_msg_id, created_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))`
  );
  for (const row of payload.results) {
    const itemValue = Number(row.item);
    const orderAmount = Number(row.value);
    if (!Number.isFinite(itemValue) || !Number.isFinite(orderAmount)) continue;
    stmt.run(
      String(orderBatchId || ''),
      wxGroupId,
      senderWxid,
      String(route?.guide_word || '').trim(),
      String(route?.category_word || '').trim(),
      String(
        (row.targetLabel != null && String(row.targetLabel).trim() !== ''
          ? row.targetLabel
          : payload.targetLabel) || ''
      ).trim(),
      String(payload.algo || ''),
      Number(payload.value || 0),
      itemValue,
      orderAmount,
      String(settlementDate || dateToYmd(new Date())),
      String(content || '').slice(0, 240),
      wxM,
      wxN
    );
  }
}

/**
 * 撤回一条微信消息对应的下单：删除匹配行并返回与下单 +a+b 对称的 -a-b 文案。
 */
export function revokeOrdersForWxMessage(db, { wxGroupId, senderWxid, wxMsgId = '', wxNewMsgId = '' }) {
  void senderWxid;
  const g = String(wxGroupId || '').trim();
  const mid = String(wxMsgId || '').trim();
  const nid = String(wxNewMsgId || '').trim();
  if (!g) return '撤回：缺少群';
  if (!mid && !nid) return '撤回：未能识别被撤消息ID';
  let whereFrag;
  const params = [g];
  if (nid && mid) {
    whereFrag = '(wx_new_msg_id = ? OR wx_msg_id = ?)';
    params.push(nid, mid);
  } else if (nid) {
    whereFrag = 'wx_new_msg_id = ?';
    params.push(nid);
  } else {
    whereFrag = 'wx_msg_id = ?';
    params.push(mid);
  }
  const grouped = db
    .prepare(
      `SELECT guide_word, category_word, SUM(order_amount) AS s
       FROM cmd_orders
       WHERE wx_group_id = ? AND ${whereFrag}
       GROUP BY guide_word, category_word
       ORDER BY MIN(id) ASC`
    )
    .all(...params);
  if (!grouped.length) {
    // 系统通知、误触发的 10002 等常带无关 msgId，群发提示会干扰正常指令（如报表后紧跟一条）。
    // 需要调试时：BOT_REVOKE_REPLY_NO_MATCH=1
    if (String(process.env.BOT_REVOKE_REPLY_NO_MATCH || '') === '1') {
      return '撤回：未找到该消息对应下单（无记录或历史订单未带消息ID）';
    }
    return null;
  }
  db.prepare(`DELETE FROM cmd_orders WHERE wx_group_id = ? AND ${whereFrag}`).run(...params);
  const totals = grouped.map((r) => Number(r.s) || 0);
  return formatMinusTermsFromTotals(totals);
}

function getBeijingTimeFields(now = new Date()) {
  const bj = new Date(now.getTime() + 8 * 60 * 60 * 1000);
  return {
    ymd: `${bj.getUTCFullYear()}-${String(bj.getUTCMonth() + 1).padStart(2, '0')}-${String(bj.getUTCDate()).padStart(
      2,
      '0'
    )}`,
    weekdayJs: bj.getUTCDay(),
    minutes: bj.getUTCHours() * 60 + bj.getUTCMinutes(),
  };
}

function addCalendarDaysYmd(ymd, delta) {
  const [y, m, d] = String(ymd || '')
    .trim()
    .split('-')
    .map((x) => Number(x));
  const t = Date.UTC(y, m - 1, d) + delta * 86400000;
  const x = new Date(t);
  return `${x.getUTCFullYear()}-${String(x.getUTCMonth() + 1).padStart(2, '0')}-${String(x.getUTCDate()).padStart(2, '0')}`;
}

function normalizeClockToHHMM(s) {
  const m = String(s || '')
    .trim()
    .match(/^(\d{1,2}):(\d{2})$/);
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  if (!Number.isInteger(h) || !Number.isInteger(min) || h > 23 || min > 59) return null;
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
}

function clockToMinutes(s) {
  const hm = normalizeClockToHHMM(s);
  if (!hm) return null;
  const [h, min] = hm.split(':').map((x) => Number(x));
  return h * 60 + min;
}

function isGroupOrderTakingEnabled(db, wxGroupId) {
  if (!wxGroupId) return true;
  const g = db.prepare(`SELECT owner_orders_enabled FROM wx_groups WHERE wx_group_id = ?`).get(wxGroupId);
  if (!g) return true;
  return Number(g.owner_orders_enabled ?? 1) !== 0;
}

function isGroupDebugOrderReplyEnabled(db, wxGroupId) {
  if (!wxGroupId) return false;
  const g = db.prepare(`SELECT debug_order_reply FROM wx_groups WHERE wx_group_id = ?`).get(wxGroupId);
  if (!g) return false;
  return Number(g.debug_order_reply ?? 0) !== 0;
}

/** 规则调试：仅当全局规则本次均未命中时发 [调试·未命中规则]；任一规则命中则不附加该说明（网关侧） */
export function isGroupDebugRuleMissReplyEnabled(db, wxGroupId) {
  if (!wxGroupId) return false;
  const g = db.prepare(`SELECT debug_rule_miss_reply FROM wx_groups WHERE wx_group_id = ?`).get(wxGroupId);
  if (!g) return false;
  return Number(g.debug_rule_miss_reply ?? 0) !== 0;
}

/**
 * 群内消息未命中下单/指令且未命中自定义规则时的标准回执（不计入注单）。
 * @param {string} senderNick 发送者昵称，用于首行 @
 * @param {string} rawContent 入站原文（中间原样回填，便于对照）
 * @param {import('better-sqlite3').Database | null} db 可选，用于剥掉句首 @机器人 等噪声
 */
/** 与 executeConfiguredCommandImpl 下单分支相同的正文预处理（渠道独占行 glue、连肖补各等） */
export function preprocessInboundOrderContent(db, rawContent, wxGroupId = null) {
  let content = prepareInboundInstructionText(rawContent, db);
  if (!content) return '';
  if (db) {
    content = String(content || '')
      .split(/\r?\n/)
      .map((ln) => peelDeclaredSegmentTotalFromLine(ln, db).line)
      .filter((ln) => !isOrderDeclaredTotalNoiseLine(ln))
      .join('\n');
  }
  content = splitWeiOrTouDigitSeparators(content);
  content = splitSeparatedDigitsBeforeWeiShuCollectionName(content);
  content = stripBatchForwardMessageLinePrefix(content);
  content = expandLooseMacauChannelLines(db, content, wxGroupId).trim();
  if (typeof content.normalize === 'function') content = content.normalize('NFKC');
  content = stripLeadingOrderNoise(content);
  content = normalizeEmbeddedMaZhongToTe(db, content);
  content = expandChaInstructionAliases(content, db);
  content = glueStandaloneGuideLineWithFollowing(db, content, wxGroupId);
  content = glueStandaloneCategoryAliasLineWithFollowing(db, content, wxGroupId);
  content = normalizeZodiacPingTeOrLianXiaoTrailingAAmount(content);
  content = normalizeOrderStreamText(content, db);
  content = String(content || '')
    .split('\n')
    .filter((ln) => !isOrderDeclaredTotalNoiseLine(ln))
    .join('\n');
  content = glueOrphanContinuationLinesToPreviousRoute(db, content, wxGroupId);
  content = applyGuideSynonymsToEachLine(db, content);
  try {
    content = String(content || '')
      .split('\n')
      .map((ln) => expandFushiLianMaZhongPlayOneLine(hoistInlineLianMaZhongPlayPrefix(String(ln || ''))))
      .join('\n');
  } catch {
    /* empty */
  }
  content = splitZodiacGeClauseAfterAmountLine(content);
  let unitSynonyms = [];
  try {
    unitSynonyms = db ? getOrderAmountUnitSynonyms(db) : [];
  } catch {
    unitSynonyms = [];
  }
  content = normalizeZodiacPingTeOrLianXiaoTrailingAAmount(content);
  content = normalizePerLineBallDotGeAmount(content, unitSynonyms);
  return String(content || '').trim();
}

/**
 * 引擎已走下单管线但未落单：优先提示 strict 群未开启的玩法，否则回退标准「无法识别」。
 */
export function buildInboundOrderParseFailureReply(db, wxGroupId, rawContent) {
  const body = String(prepareInboundInstructionText(rawContent, db) || rawContent || '').trim() || '（无正文）';
  const pre = preprocessInboundOrderContent(db, rawContent, wxGroupId);
  if (!pre) return '';
  const disabled = [];
  const seen = new Set();
  for (const ln of pre.split(/\r?\n+/)) {
    const line = String(ln || '').trim();
    if (!line) continue;
    if (!contentMatchesAnyRoute(db, line, null)) continue;
    if (!wxGroupId || contentMatchesAnyRoute(db, line, wxGroupId)) continue;
    const routePrefixes = buildSortedRoutePrefixes(db);
    const det = detectLineRoutePrefix(line, routePrefixes);
    if (!det) continue;
    const tag = `${det.guide}·${String(det.category || '').trim()}`;
    if (!tag || seen.has(tag)) continue;
    seen.add(tag);
    disabled.push(tag);
  }
  if (disabled.length > 0) {
    return `■【此消息有问题，不计入】■\n\n${body}\n\n本群未开启玩法：${disabled.join('、')}。请群主发送「开启${disabled[0]}」或在管理台勾选该玩法。`;
  }
  return '';
}

export function buildUnrecognizedInboundMessageReply(senderNick, rawContent, db = null) {
  let body = String(rawContent || '').trim();
  if (db) {
    try {
      body = stripWeChatAtPrefix(body, db).trim();
    } catch {
      /* empty */
    }
  }
  if (!body) body = '（无正文）';
  return `■【此消息有问题，不计入】■\n\n${body}\n\n【无法识别内容】`;
}

/**
 * 网关「调试未命中」：引擎未识别为指令且无全局规则列表时仍给出下单排查说明。
 * @returns {string}
 */
export function buildInboundOrderMissDebugText(db, rawContent) {
  let s = stripWeChatAtPrefix(String(rawContent || '').trim(), db);
  if (typeof s.normalize === 'function') s = s.normalize('NFKC');
  s = normalizeOrderStreamText(s, db);
  s = stripLeadingOrderNoise(s);
  if (!looksLikeInboundOrderAttempt(s, db)) return '';
  return '[调试·未命中下单]\n本句未解析为有效下单（引擎未返回金额回执）。可试：多条分行；生肖组之间用中文「。」或换行；英文句号「.」写在数字与下一组生肖之间会自动拆条。需要逐行解析时可「调试开」。';
}

function getOrderCycleDenyReason(db, guideWord) {
  const gw = String(guideWord || '').trim();
  const row = db.prepare(`SELECT * FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
  if (!row || !Number(row.is_active ?? 1)) return null;
  const ctype = String(row.cycle_type || 'daily').trim();
  const { ymd, weekdayJs } = getBeijingTimeFields();
  let list = [];
  try {
    const raw = JSON.parse(String(row.date_list_json || '[]'));
    list = Array.isArray(raw) ? raw : [];
  } catch {
    list = [];
  }
  if (ctype === 'weekly' && list.length > 0) {
    const ok = list.some((x) => Number(x) === weekdayJs);
    if (!ok) return `渠道「${gw}」今日不开放收单（按周期设置）。`;
  }
  if (ctype === 'date_list' && list.length > 0) {
    const ok = list.some((x) => String(x) === ymd);
    if (!ok) return `渠道「${gw}」今日不开放收单（仅指定日期开放）。`;
  }
  return null;
}

function computeSettlementDateYmdForGuide(db, guideWord, now = new Date()) {
  const gw = String(guideWord || '').trim();
  const row = db.prepare(`SELECT cutoff_time, is_active FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
  const { ymd, minutes } = getBeijingTimeFields(now);
  if (!row || !Number(row.is_active ?? 1)) return ymd;
  const cut = clockToMinutes(row.cutoff_time || '20:59');
  if (cut == null) return ymd;
  if (minutes < cut) return ymd;
  return addCalendarDaysYmd(ymd, 1);
}

function listActiveChannelWordsByLength(db) {
  return db
    .prepare(`SELECT guide_word FROM cmd_channels WHERE is_active = 1 ORDER BY length(guide_word) DESC`)
    .all()
    .map((r) => String(r.guide_word || '').trim())
    .filter(Boolean);
}

function splitLeadingChannelWord(db, text) {
  const c = String(text || '').trim();
  for (const gw of listActiveChannelWordsByLength(db)) {
    if (c.startsWith(gw)) return { channel: gw, rest: c.slice(gw.length).trim() };
  }
  return { channel: '', rest: c };
}

/** 「新澳门码中」→「新澳门特」等口语，须在路由匹配前替换 */
function normalizeEmbeddedMaZhongToTe(db, s) {
  let t = String(s || '');
  for (const gw of listActiveChannelWordsByLength(db)) {
    if (!gw || gw.length < 2) continue;
    const re = new RegExp(`${escapeRegExp(gw)}码中`, 'gu');
    t = t.replace(re, `${gw}特`);
  }
  return t;
}

/** 两位球号连写「04.35」勿当小数；反复剥直至稳定 */
function preNormalizeLottoTwoDigitDotChains(s) {
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
  /* 下单无小数：「05 .25元」视为球号与整数金额，勿解析为 0.25 */
  t = t.replace(/(\d{1,2})\s+\.(\d{2,})/g, '$1 $2');
  return t;
}

function isNumericBallTargetListOnly(headRaw) {
  const t = normalizeOrderTargetSeparators(String(headRaw || '').trim());
  if (!t) return false;
  const parts = t.split(/\s+/).filter(Boolean);
  for (const p of parts) {
    if (!/^\d{1,2}$/.test(p)) return false;
    const n = Number(p);
    if (!Number.isInteger(n) || n < 1 || n > 49) return false;
  }
  return parts.length >= 1;
}

/** 球号串末尾的渠道简称（如 …48澳门各30、…41香港各20），在路由已带渠道时多为冗余口癖，剥除后再按纯号码表解析 */
const STATIC_TRAILING_CHANNEL_LITTER = [
  '新澳门',
  '老澳门',
  '香港',
  '越南',
  '澳门',
  '新澳',
  '老澳',
  '港',
  '越',
  '奥',
  '噢',
  '澳',
];

function buildGuideChannelTrailingSuffixes(db) {
  const acc = [];
  const seen = new Set();
  const push = (w) => {
    const x = String(w || '').trim();
    if (!x) return;
    const k = x.toLowerCase();
    if (seen.has(k)) return;
    seen.add(k);
    acc.push(x);
  };
  for (const x of STATIC_TRAILING_CHANNEL_LITTER) push(x);
  try {
    for (const r of listDistinctActiveRoutePairs(db)) push(r.guide_word);
  } catch {
    /* empty */
  }
  try {
    for (const gw of listActiveChannelWordsByLength(db)) push(gw);
  } catch {
    /* empty */
  }
  try {
    const syns = listSynonymPairs(db, 'guide_word');
    for (const row of syns) push(row.alias_word);
  } catch {
    /* empty */
  }
  acc.sort((a, b) => b.length - a.length);
  return acc;
}

/** 解析阶段：球号目标末尾剥「特码」等冗余玩法口癖（与预处理 stripRedundantTeCategory… 一致） */
function stripTrailingTeCategoryLitterAfterNumericBalls(db, headRaw) {
  let t = trimTrailingOrderNoise(String(headRaw || '').trim());
  if (!t || isNumericBallTargetListOnly(t)) return t;
  const suffixes = new Set(['特码']);
  try {
    for (const { suf, canon } of listCategorySuffixesToCanonical(db)) {
      if (String(canon || '').trim() === '特' && suf) suffixes.add(String(suf).trim());
    }
  } catch {
    /* empty */
  }
  const ordered = [...suffixes].filter(Boolean).sort((a, b) => b.length - a.length);
  for (let guard = 0; guard < 24; guard += 1) {
    let stripped = false;
    for (const suf of ordered) {
      if (!suf || suf === '平特' || t.length <= suf.length || !t.endsWith(suf)) continue;
      const next = trimTrailingOrderNoise(t.slice(0, t.length - suf.length));
      if (next && isNumericBallTargetListOnly(next)) {
        t = next;
        stripped = true;
        break;
      }
    }
    if (!stripped) break;
  }
  return t;
}

function stripTrailingChannelNoiseAfterNumericBalls(db, headRaw, routedGuideNorm = '') {
  let t = trimTrailingOrderNoise(String(headRaw || '').trim());
  if (!t) return t;
  t = stripTrailingTeCategoryLitterAfterNumericBalls(db, t);
  const g0 = normalizeGuideWord(String(routedGuideNorm || '').trim());
  if (!g0) return t;
  const suffixes = buildGuideChannelTrailingSuffixes(db);
  for (let guard = 0; guard < 24; guard += 1) {
    let stripped = false;
    for (const suf of suffixes) {
      if (!suf || t.length <= suf.length || !t.endsWith(suf)) continue;
      const next = trimTrailingOrderNoise(t.slice(0, t.length - suf.length));
      if (next && isNumericBallTargetListOnly(next)) {
        t = next;
        stripped = true;
        break;
      }
    }
    if (!stripped) break;
  }
  return t;
}

function chineseWeekdayTokenToJs(tok) {
  const t = String(tok || '')
    .trim()
    .replace(/^(?:星期|礼拜|周)/u, '');
  if (/^\d$/.test(t)) {
    const n = Number(t);
    if (n === 0 || n === 7) return 0;
    if (n >= 1 && n <= 6) return n;
    return null;
  }
  const map = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 日: 0, 天: 0 };
  if (map[t] !== undefined) return map[t];
  return null;
}

function parseCyclePhrase(phraseRaw) {
  let p = String(phraseRaw || '')
    .trim()
    .replace(/\s+/g, '');
  p = p.replace(/^周期/u, '');
  if (!p) return { error: '周期说明为空' };
  if (/^(每天|每日|天天)$/u.test(p)) {
    return { cycle_type: 'daily', payload: [] };
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(p)) {
    const dates = p
      .split(/[，,、\s]+/)
      .map((x) => x.trim())
      .filter((x) => /^\d{4}-\d{2}-\d{2}$/.test(x));
    if (dates.length) return { cycle_type: 'date_list', payload: [...new Set(dates)].sort() };
  }
  p = p.replace(/^(?:每星期|每周|礼拜)/u, '');
  const parts = p.split(/[，,、]/).map((x) => x.trim()).filter(Boolean);
  if (parts.length === 0) return { error: '未能识别周期，可发：每天、每周1,3,5、每周二、四、六' };
  const days = new Set();
  for (const part of parts) {
    const js = chineseWeekdayTokenToJs(part);
    if (js == null) return { error: `未能识别「${part}」，周几请用 1–6 或 日/一…六` };
    days.add(js);
  }
  return { cycle_type: 'weekly', payload: [...days].sort((a, b) => a - b) };
}

function normalizeOwnerToggleInstructionText(content, db) {
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  let t = raw.replace(/\s+/g, '');
  if (t.startsWith('开启')) t = `开${t.slice(2)}`;
  else if (t.startsWith('关闭')) t = `关${t.slice(2)}`;
  return t;
}

/** 入站 pipeline：识别「调试开/关」等群主开关，避免被当闲聊丢弃 */
export function matchesDebugOrderReplyToggleLine(content, db) {
  let t = normalizeOwnerToggleInstructionText(content, db);
  if (t === '开调试') t = '调试开';
  if (t === '关调试') t = '调试关';
  return /^调试(开|启|关|闭)$/u.test(t);
}

export function matchesDebugRuleMissReplyToggleLine(content, db) {
  let t = normalizeOwnerToggleInstructionText(content, db);
  if (t === '开调试未命中') t = '调试未命中开';
  if (t === '关调试未命中') t = '调试未命中关';
  return /^调试未命中(开|启|关|闭)$/u.test(t);
}

export function matchesOwnerOrderToggleLine(content, db) {
  const t = normalizeOwnerToggleInstructionText(content, db);
  const isSingleKeyword = /^(开|启|关|闭)$/u.test(t);
  const isCompound =
    /^(?:收单|接单)(?:开|启|关|闭)$/u.test(t) || /^(?:开|启|关|闭)(?:收单|接单)$/u.test(t);
  return isSingleKeyword || isCompound;
}

function maybeHandleOwnerOrderToggle(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  if (!matchesOwnerOrderToggleLine(content, db)) return null;
  const t = normalizeOwnerToggleInstructionText(content, db);
  if (!wxGroupId) {
    return { ok: true, replyText: '请在群内发送「收单开」或「收单关」。' };
  }
  if (!senderWxid) {
    return { ok: true, replyText: '未能识别发送者，无法变更本群收单开关。' };
  }
  const on =
    /开|启/u.test(t) && !/关|闭/u.test(t) ? true : /关|闭/u.test(t) && !/开|启/u.test(t) ? false : null;
  if (on === null) return null;
  if (mutate) {
    db.prepare(`UPDATE wx_groups SET owner_orders_enabled = ? WHERE wx_group_id = ?`).run(on ? 1 : 0, wxGroupId);
  }
  return {
    ok: true,
    replyText: on ? '已开启本群收单。' : '已关闭本群收单（仍可查单、报表与群主改价）。',
  };
}

function maybeHandleDebugOrderReplyToggle(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  if (!matchesDebugOrderReplyToggleLine(content, db)) return null;
  let t = normalizeOwnerToggleInstructionText(content, db);
  if (t === '开调试') t = '调试开';
  if (t === '关调试') t = '调试关';
  if (!wxGroupId) {
    return { ok: true, replyText: '请在群内发送「调试开」或「调试关」。' };
  }
  if (!senderWxid) {
    return { ok: true, replyText: '未能识别发送者，无法变更本群调试回执开关。' };
  }
  const on =
    /开|启/u.test(t) && !/关|闭/u.test(t) ? true : /关|闭/u.test(t) && !/开|启/u.test(t) ? false : null;
  if (on === null) return null;
  if (mutate) {
    db.prepare(`UPDATE wx_groups SET debug_order_reply = ? WHERE wx_group_id = ?`).run(on ? 1 : 0, wxGroupId);
  }
  return {
    ok: true,
    replyText: on
      ? '已开启本群下单调试回执：原文（含换行）后输出各行个数、单注金额、小计，末行合计。'
      : '已关闭本群下单调试回执。',
  };
}

function maybeHandleDebugRuleMissReplyToggle(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  if (!matchesDebugRuleMissReplyToggleLine(content, db)) return null;
  let t = normalizeOwnerToggleInstructionText(content, db);
  if (t === '开调试未命中') t = '调试未命中开';
  if (t === '关调试未命中') t = '调试未命中关';
  if (!wxGroupId) {
    return { ok: true, replyText: '请在群内发送「调试未命中开」或「调试未命中关」。' };
  }
  if (!senderWxid) {
    return { ok: true, replyText: '未能识别发送者，无法变更本群调试未命中开关。' };
  }
  const on =
    /开|启/u.test(t) && !/关|闭/u.test(t) ? true : /关|闭/u.test(t) && !/开|启/u.test(t) ? false : null;
  if (on === null) return null;
  if (mutate) {
    db.prepare(`UPDATE wx_groups SET debug_rule_miss_reply = ? WHERE wx_group_id = ?`).run(on ? 1 : 0, wxGroupId);
  }
  return {
    ok: true,
    replyText: on
      ? '已开启「调试·未命中」：全局规则均未命中时附 [调试·未命中规则]（若有配置）；另附 [调试·未命中下单]（疑似下单句却未解析时）；有任一规则命中则不附调试。'
      : '已关闭「调试·仅未命中规则」。',
  };
}

function upsertGroupRouteEnable(db, wxGroupId, guideWord, categoryWord, on) {
  const g = String(guideWord || '').trim();
  const c = String(categoryWord || '').trim();
  if (!wxGroupId || !g || !c) return;
  db.prepare(
    `INSERT INTO wx_group_route_enables (wx_group_id, guide_word, category_word, is_enabled, updated_at)
     VALUES (?, ?, ?, ?, datetime('now'))
     ON CONFLICT(wx_group_id, guide_word, category_word) DO UPDATE SET
       is_enabled = excluded.is_enabled,
       updated_at = datetime('now')`
  ).run(wxGroupId, g, c, on ? 1 : 0);
}

/** strict 群：入站行在全局路由存在但未开启时，自动写入 wx_group_route_enables */
function ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, lineText) {
  if (!wxGroupId || !groupUsesStrictPlayRoutes(db, wxGroupId)) return;
  const line = String(lineText || '').trim();
  if (!line || contentMatchesAnyRoute(db, line, wxGroupId)) return;
  const det = detectLineRoutePrefix(line, buildSortedRoutePrefixes(db));
  if (!det?.guide || !det?.category) return;
  const candidate = `${det.guide}${det.category}`;
  if (!contentMatchesAnyRoute(db, candidate, null)) return;
  upsertGroupRouteEnable(db, wxGroupId, det.guide, det.category, true);
}

/** 查+渠道+结单时间/周期/玩法 */
function maybeHandleChaChannelFacetCommand(db, wxGroupId, senderWxid, content) {
  void senderWxid;
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  const t = raw.replace(/\s+/g, '').trim();
  if (!t.startsWith('查') || t.length < 3) return null;
  const rest = t.slice(1);
  if (!rest) return null;
  if (!wxGroupId) return { ok: true, replyText: '请在群内使用该查询。' };
  if (rest === '渠道到期') return null;

  if (rest.endsWith('结单时间')) {
    const chHint = rest.slice(0, -4);
    if (!chHint) return null;
    const gw = resolveGuideHintWithSynonyms(db, chHint);
    if (!gw) return { ok: true, replyText: `未识别渠道「${chHint}」。` };
    const row = db.prepare(`SELECT cutoff_time FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
    if (!row)
      return { ok: true, replyText: `渠道「${gw}」未配置结单时间（群主可发 ${gw}结单时间：HH:mm）。` };
    return {
      ok: true,
      replyText: `【${gw}】结单时间（截稿）：${String(row.cutoff_time || '—')}（北京时间）`,
    };
  }
  if (rest.endsWith('周期')) {
    const chHint = rest.slice(0, -2);
    if (!chHint) return null;
    const gw = resolveGuideHintWithSynonyms(db, chHint);
    if (!gw) return { ok: true, replyText: `未识别渠道「${chHint}」。` };
    const row = db.prepare(`SELECT cycle_type, date_list_json, is_active FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
    if (!row || !Number(row.is_active ?? 1))
      return { ok: true, replyText: `渠道「${gw}」无周期记录或未启用。` };
    let list = [];
    try {
      list = JSON.parse(String(row.date_list_json || '[]'));
    } catch {
      list = [];
    }
    const kind =
      row.cycle_type === 'daily'
        ? '每天'
        : row.cycle_type === 'weekly'
          ? `每周 ${Array.isArray(list) ? list.join(',') : ''}`
          : `指定日 ${Array.isArray(list) ? list.length : 0} 天`;
    return { ok: true, replyText: `【${gw}】周期：${kind}` };
  }
  if (rest.endsWith('玩法')) {
    const chHint = rest.slice(0, -2);
    if (!chHint) return null;
    const gw = resolveGuideHintWithSynonyms(db, chHint);
    if (!gw) return { ok: true, replyText: `未识别渠道「${chHint}」。` };
    const globalCats = db
      .prepare(
        `SELECT DISTINCT category_word FROM cmd_routes
         WHERE is_active = 1 AND guide_word = ?
           AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')`
      )
      .all(gw)
      .map((r) => String(r.category_word || '').trim())
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b, 'zh-CN'));
    if (!globalCats.length) return { ok: true, replyText: `渠道「${gw}」无已登记玩法。` };
    let enabled = null;
    if (groupUsesStrictPlayRoutes(db, wxGroupId)) {
      enabled = new Set(
        db
          .prepare(
            `SELECT category_word FROM wx_group_route_enables
             WHERE wx_group_id = ? AND guide_word = ? AND is_enabled = 1`
          )
          .all(wxGroupId, gw)
          .map((r) => String(r.category_word || '').trim())
      );
    }
    const lines = globalCats.map((c) =>
      enabled ? `· ${c}${enabled.has(c) ? ' ✓' : '（未开启）'}` : `· ${c}`
    );
    return {
      ok: true,
      replyText: `【${gw}】玩法：\n${lines.join('\n')}`,
    };
  }
  return null;
}

/**
 * strict 群：开启+渠道+分类 | 开启+渠道（该渠道下全部）| 开启+分类（全局含该分类的组合全开）
 */
function maybeHandleEnablePlayRouteCommand(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  const t = raw.replace(/\s+/g, '').trim();
  if (!t.startsWith('开启')) return null;
  if (!wxGroupId || !senderWxid) return null;
  if (!groupUsesStrictPlayRoutes(db, wxGroupId)) {
    return {
      ok: true,
      replyText: '本群未启用分玩法限制（非卡密新绑群通常为全玩法）；无需「开启」指令。',
    };
  }
  const tail = t.slice(2).trim();
  const pre = mutate ? '' : '[试算] ';
  if (!tail) {
    return {
      ok: true,
      replyText: `${pre}用法：开启+渠道+分类、开启+渠道、开启+玩法（均为后台已存在的全局路由）。`,
    };
  }
  const suffs = listCategorySuffixesToCanonical(db);
  for (const { suf, canon } of suffs) {
    if (tail.length <= suf.length || !tail.endsWith(suf)) continue;
    const chHint = tail.slice(0, tail.length - suf.length).trim();
    if (!chHint) continue;
    const guide = resolveGuideHintWithSynonyms(db, chHint);
    if (!guide || !assertActiveGlobalOrderRoute(db, guide, canon)) continue;
    if (mutate) upsertGroupRouteEnable(db, wxGroupId, guide, canon, true);
    return { ok: true, replyText: `${pre}已开启玩法「${guide}·${canon}」。` };
  }
  const gw = resolveGuideHintWithSynonyms(db, tail);
  if (gw && guideWordHasActiveGlobalRoute(db, gw)) {
    const rows = listActiveCmdRoutes(db).filter((r) => String(r.guide_word || '').trim() === gw);
    if (mutate) {
      for (const r of rows) {
        upsertGroupRouteEnable(db, wxGroupId, gw, String(r.category_word || '').trim(), true);
      }
    }
    return { ok: true, replyText: `${pre}已开启渠道「${gw}」下全部玩法（${rows.length} 项）。` };
  }
  const catCanon = resolveCategoryHintWithSynonyms(db, tail);
  const catRows = listActiveCmdRoutes(db).filter((r) => String(r.category_word || '').trim() === catCanon);
  if (catCanon && catRows.length) {
    if (mutate) {
      for (const r of catRows) {
        upsertGroupRouteEnable(db, wxGroupId, String(r.guide_word || '').trim(), catCanon, true);
      }
    }
    return { ok: true, replyText: `${pre}已为各渠道开启玩法「${catCanon}」（${catRows.length} 项组合）。` };
  }
  return { ok: true, replyText: `${pre}未能识别，请核对渠道/玩法与后台路由。` };
}

/** 群主：默认/设置默认/查默认 — 配置全群省略下单前缀时的渠道与玩法 */
function parseDefaultOrderAdminCommand(text) {
  const t = String(text || '').replace(/\s+/g, '').trim();
  if (!t) return null;
  if (t === '查默认' || t === '查看默认' || t === '默认配置' || t === '默认设置') {
    return { mode: 'query', tail: '' };
  }
  if (t.startsWith('查默认') || t.startsWith('查看默认')) return { mode: 'query', tail: '' };
  if (t.startsWith('设置默认')) return { mode: 'set', tail: t.slice(4).trim() };
  if (t.startsWith('默认')) return { mode: 'set', tail: t.slice(2).trim() };
  return null;
}

function matchesDefaultOrderAdminLine(text, db) {
  const raw = stripWeChatAtPrefix(String(text || '').trim(), db);
  return parseDefaultOrderAdminCommand(raw.replace(/\s+/g, '')) != null;
}

function buildDefaultOrderStatusReply(db, { pre = '' } = {}) {
  const gw = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_guide_word'`).get();
  const cw = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_category_word'`).get();
  const guide = String(gw?.value || '').trim() || '（未配置）';
  const cat = String(cw?.value || '').trim() || '（未配置）';
  return [
    `${pre}【全局默认下单】`,
    `默认渠道：${guide}`,
    `默认玩法：${cat}`,
    '设置：默认+渠道+分类（例 默认新澳门特）、默认+渠道、默认+分类；同义 设置默认…',
    '查询：查默认 / 查看默认',
    '须与后台已启用的全局路由一致；管理台「下单默认」页可同步修改。',
  ].join('\n');
}

/**
 * 群主：默认渠道+分类 | 默认渠道 | 默认分类（写入 app_settings，全群省略下单前缀时生效）
 */
function maybeHandleDefaultOrderRouteCommand(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  const parsed = parseDefaultOrderAdminCommand(raw.replace(/\s+/g, ''));
  if (!parsed) return null;
  if (!wxGroupId || !senderWxid) {
    return { ok: true, replyText: '请在群内使用该指令。' };
  }
  const pre = mutate ? '' : '[试算] ';
  if (parsed.mode === 'query') {
    return { ok: true, replyText: buildDefaultOrderStatusReply(db, { pre }) };
  }
  const tail = parsed.tail;
  if (!tail) {
    return { ok: true, replyText: buildDefaultOrderStatusReply(db, { pre }) };
  }

  const suffs = listCategorySuffixesToCanonical(db);

  for (const { suf, canon } of suffs) {
    if (tail.length <= suf.length || !tail.endsWith(suf)) continue;
    const chHint = tail.slice(0, tail.length - suf.length).trim();
    if (!chHint) continue;
    const guide = resolveGuideHintWithSynonyms(db, chHint);
    if (!guide || !assertActiveGlobalOrderRoute(db, guide, canon)) continue;
    if (mutate) {
      upsertAppSettingValue(db, 'default_order_guide_word', guide);
      upsertAppSettingValue(db, 'default_order_category_word', canon);
    }
    return {
      ok: true,
      replyText: `${pre}已设置全局默认下单：渠道「${guide}」，分类「${canon}」。`,
    };
  }

  const guideOnly = resolveGuideHintWithSynonyms(db, tail);
  if (guideOnly && guideWordHasActiveGlobalRoute(db, guideOnly)) {
    const catRow = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_category_word'`).get();
    const curCat = String(catRow?.value || '').trim();
    if (!curCat) {
      return {
        ok: true,
        replyText: `${pre}当前未配置默认分类，请先发：默认${tail}特（示例：渠道+分类）或先设默认分类。`,
      };
    }
    if (!assertActiveGlobalOrderRoute(db, guideOnly, curCat)) {
      return {
        ok: true,
        replyText: `${pre}渠道「${guideOnly}」与当前默认分类「${curCat}」无已启用的全局路由，请发完整：默认+渠道+分类。`,
      };
    }
    if (mutate) {
      upsertAppSettingValue(db, 'default_order_guide_word', guideOnly);
    }
    return {
      ok: true,
      replyText: `${pre}已更新全局默认渠道为「${guideOnly}」（分类仍为「${curCat}」）。`,
    };
  }

  const catCanon = resolveCategoryHintWithSynonyms(db, tail);
  const catExists = db
    .prepare(
      `SELECT 1 FROM cmd_routes
       WHERE is_active = 1 AND category_word = ?
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id, '')) = '' OR wx_group_id = '__global__')
       LIMIT 1`
    )
    .get(catCanon);
  if (catCanon && catExists) {
    const gRow = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_guide_word'`).get();
    const curGuide = String(gRow?.value || '').trim();
    if (!curGuide) {
      return {
        ok: true,
        replyText: `${pre}当前未配置默认渠道，请先发：默认新澳门${tail}（示例）或先设默认渠道+分类。`,
      };
    }
    if (!assertActiveGlobalOrderRoute(db, curGuide, catCanon)) {
      return {
        ok: true,
        replyText: `${pre}当前默认渠道「${curGuide}」与分类「${catCanon}」无已启用的全局路由。`,
      };
    }
    if (mutate) {
      upsertAppSettingValue(db, 'default_order_category_word', catCanon);
    }
    return {
      ok: true,
      replyText: `${pre}已更新全局默认分类为「${catCanon}」（渠道仍为「${curGuide}」）。`,
    };
  }

  return {
    ok: true,
    replyText: `${pre}未能识别：请检查渠道/分类是否与后台路由一致，或拆成 默认+渠道+分类 / 默认+渠道 / 默认+分类。`,
  };
}

function maybeHandleChannelCycleAdminCommand(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  const text = stripWeChatAtPrefix(String(content || '').trim(), db).replace(/\r\n/g, '\n').trim();
  const { channel: leadCh, rest } = splitLeadingChannelWord(db, text);
  const work = (rest || text).trim();
  if (!work) return null;

  let m = work.match(/^结单时间\s*[：:]\s*(\d{1,2}:\d{2})\s*$/u);
  if (m) {
    const hm = normalizeClockToHHMM(m[1]);
    if (!hm)
      return {
        ok: true,
        replyText: '结单时间格式须为 HH:mm（如 20:59）。',
      };
    let gw = leadCh;
    if (!gw) {
      gw = String(db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_guide_word'`).get()?.value || '').trim();
    }
    if (!gw) {
      return {
        ok: true,
        replyText: '请先配置默认渠道或在指令前加渠道名（例：新澳门结单时间：20:59）。',
      };
    }
    if (mutate) {
      const ex = db.prepare(`SELECT 1 FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
      if (ex) {
        db.prepare(
          `UPDATE cmd_order_cycles SET cutoff_time = ?, start_time = '00:00', updated_at = datetime('now') WHERE guide_word = ?`
        ).run(hm, gw);
      } else {
        db.prepare(
          `INSERT INTO cmd_order_cycles
          (guide_word, cycle_type, start_time, cutoff_time, date_list_json, is_active, updated_at)
          VALUES (?, 'daily', '00:00', ?, '[]', 1, datetime('now'))`
        ).run(gw, hm);
      }
      db.prepare(`INSERT OR IGNORE INTO cmd_channels (guide_word, is_active, updated_at) VALUES (?, 1, datetime('now'))`).run(
        gw
      );
    }
    return {
      ok: true,
      replyText: `${mutate ? '已设置' : '[试算] 将设置'}渠道「${gw}」结单时间 ${hm}（北京时间）。`,
    };
  }

  m = work.match(/^周期\s*[：:]?\s*(.+)$/u);
  if (m) {
    const parsed = parseCyclePhrase(m[1]);
    if (parsed.error) return { ok: true, replyText: parsed.error };
    let gw = leadCh;
    if (!gw) {
      gw = String(db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_guide_word'`).get()?.value || '').trim();
    }
    if (!gw) {
      return {
        ok: true,
        replyText: '请先配置默认渠道或在指令前加渠道名（例：香港周期 每周1、3、5）。',
      };
    }
    const jsonPayload = JSON.stringify(parsed.payload);
    const prev = db.prepare(`SELECT cutoff_time FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
    const cutoff = String(prev?.cutoff_time || '20:59');
    if (mutate) {
      db.prepare(
        `INSERT INTO cmd_order_cycles
        (guide_word, cycle_type, start_time, cutoff_time, date_list_json, is_active, updated_at)
        VALUES (?, ?, '00:00', ?, ?, 1, datetime('now'))
        ON CONFLICT(guide_word) DO UPDATE SET
          cycle_type = excluded.cycle_type,
          start_time = '00:00',
          date_list_json = excluded.date_list_json,
          updated_at = datetime('now')`
      ).run(gw, parsed.cycle_type, cutoff, jsonPayload);
      db.prepare(`INSERT OR IGNORE INTO cmd_channels (guide_word, is_active, updated_at) VALUES (?, 1, datetime('now'))`).run(
        gw
      );
    }
    const kind =
      parsed.cycle_type === 'daily' ? '每天' : parsed.cycle_type === 'weekly' ? `每周 ${parsed.payload.join(',')}` : `指定日 ${parsed.payload.length} 天`;
    return {
      ok: true,
      replyText: `${mutate ? '已设置' : '[试算] 将设置'}渠道「${gw}」周期：${kind}。`,
    };
  }

  return null;
}

function resolveMemberDisplayName(db, wxGroupId, wxid) {
  const who = String(wxid || '').trim();
  if (!who) return '';
  const room = String(wxGroupId || '').trim();
  if (room) {
    const member = db
      .prepare(
        `SELECT display_name, nick_name
         FROM wx_chatroom_members
         WHERE room_id = ? AND wxid = ?
         LIMIT 1`
      )
      .get(room, who);
    const roomName = String(member?.display_name || '').trim() || String(member?.nick_name || '').trim();
    if (roomName) return roomName;
  }
  const profile = db
    .prepare(
      `SELECT display_name, nick_name
       FROM wx_contact_profiles
       WHERE wxid = ?
       LIMIT 1`
    )
    .get(who);
  return String(profile?.display_name || '').trim() || String(profile?.nick_name || '').trim() || '未知成员';
}

/** 本群共用订单表（不按下单人过滤） */
function queryOrderRows(db, { wxGroupId }) {
  if (!wxGroupId) return [];
  return db
    .prepare(
      `SELECT * FROM cmd_orders
       WHERE wx_group_id = ?
       ORDER BY id ASC
       LIMIT 500`
    )
    .all(wxGroupId);
}

function formatAmount(n) {
  const v = Number(n || 0);
  if (!Number.isFinite(v)) return '0';
  if (Number.isInteger(v)) return String(v);
  return String(Number(v.toFixed(4)));
}

/** 当前「北京时间」墙上日对应的公历年（用于特码 01–49 转盘肖展示，与农历春节无关） */
function beijingWallCalendarYear(now = new Date()) {
  const { ymd } = getBeijingTimeFields(now);
  const m = String(ymd || '').match(/^(\d{4})-/);
  return m ? Number(m[1]) : now.getFullYear();
}

function zodiacToEmoji(zodiac) {
  const m = {
    鼠: '🐭',
    牛: '🐮',
    虎: '🐯',
    兔: '🐰',
    龙: '🐲',
    蛇: '🐍',
    马: '🐎',
    羊: '🐐',
    猴: '🐵',
    鸡: '🐔',
    狗: '🐶',
    猪: '🐷',
  };
  return m[String(zodiac || '').trim()] || '';
}

/**
 * 特码球号 01–49 旁显示生肖：按「特码转盘」规则 zodiacOfBallForSettlementYear（与岁数生肖 zodiacByAge 不同，不可混用）。
 * @param {unknown} itemValue
 * @param {number|Date|string|undefined} zodiacRef 四位年 | Date | YYYY-MM-DD 结单日；未传则用当前北京时间公历年（调试/即时回执）
 */
function formatTicketItemLabel(itemValue, zodiacRef) {
  const n = Number(itemValue);
  if (!Number.isFinite(n)) return String(itemValue ?? '');
  const int = Math.floor(n);
  const two = String(int).padStart(2, '0');
  if (int >= TE_XIAO_ZODIAC_ITEM_MIN && int <= TE_XIAO_ZODIAC_ITEM_MAX) {
    const z = zodiacFromTeXiaoItemSlot(int);
    return z || two;
  }
  if (int >= 1 && int <= 49) {
    let year;
    if (typeof zodiacRef === 'number' && Number.isFinite(zodiacRef) && zodiacRef >= 1900 && zodiacRef <= 3000) {
      year = Math.floor(zodiacRef);
    } else if (zodiacRef instanceof Date && !Number.isNaN(zodiacRef.getTime())) {
      year = beijingWallCalendarYear(zodiacRef);
    } else if (typeof zodiacRef === 'string' && /^\d{4}-\d{2}-\d{2}/.test(zodiacRef)) {
      year = settlementYearFromDateYmd(zodiacRef);
    } else {
      year = beijingWallCalendarYear();
    }
    const zodiac = zodiacOfBallForSettlementYear(int, year);
    const emoji = zodiacToEmoji(zodiac);
    return emoji ? `${two}${emoji}` : two;
  }
  return two;
}

const DEBUG_UNITS_MAX_DISPLAY = 18;
const DEBUG_UNITS_STR_MAX = 360;

function formatDebugCollapsedUnits(rows, zodiacRef, opts = {}) {
  const r = Array.isArray(rows) ? rows : [];
  if (r.length === 0) return '（无）';
  const categoryWord = String(opts.categoryWord || '').trim();
  const targetLabel = String(opts.targetLabel || '').trim();
  if (
    isLianXiaoCategory(categoryWord) &&
    r.length > 0 &&
    r.every((row) => Number(row?.item) === 0)
  ) {
    const per = r.map((row) => String(row.targetLabel || '').trim()).filter(Boolean);
    if (per.length === r.length) return `组合${per.map((lb) => `「${lb}」`).join('')}`;
    if (targetLabel) return `组合「${targetLabel}」`;
  }
  const labels = r.map((row) => formatTicketItemLabel(row.item, zodiacRef));
  let s = labels.join(' ');
  if (s.length > DEBUG_UNITS_STR_MAX || labels.length > DEBUG_UNITS_MAX_DISPLAY) {
    const k = Math.min(8, labels.length);
    return `${labels.slice(0, k).join(' ')} …共${r.length}项`;
  }
  return s;
}

function formatDebugPerBet(rows) {
  const r = Array.isArray(rows) ? rows : [];
  if (r.length === 0) return '-';
  const vals = r.map((x) => Number(x.value));
  if (!vals.every((v) => Number.isFinite(v))) return '-';
  const u0 = vals[0];
  if (vals.every((v) => v === u0)) return formatAmount(u0);
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  return mn === mx ? formatAmount(mn) : `不一(${formatAmount(mn)}~${formatAmount(mx)})`;
}

/** 收集单行调试结果（不含原文块；原文在消息级统一输出） */
function collectOrderDebugEntry(lineText, result, ast = null) {
  const ruleText = String(lineText || '').trim();
  const unitLines = ast ? formatOrderLineAstDebugOneLine(ast).split('\n').filter(Boolean) : [];
  if (!result) {
    return { miss: true, ruleText, unitLines };
  }
  if (result.blocked) {
    return { miss: true, ruleText, note: String(result.replyText || '已拦截').trim(), unitLines };
  }
  const rows = result.payload?.results;
  if (!Array.isArray(rows) || rows.length === 0) {
    return { miss: true, ruleText, unitLines };
  }
  const c = String(result.route?.category_word || '').trim();
  const sum = rows.reduce((a, x) => a + Number(x?.value || 0), 0);
  return {
    miss: false,
    ruleText,
    count: rows.length,
    perBet: formatDebugPerBet(rows),
    lineSum: sum,
    categoryWord: c,
    unitLines,
  };
}

/**
 * 调试回执块：原始消息（含换行）→ 空行 → 各行「个数 / 单注 / 小计」→ 末行合计。
 */
function buildOrderDebugReplyBlock(originalMessage, entries, messageSubtotal) {
  const raw = String(originalMessage ?? '');
  const parts = [raw, ''];
  let anyHit = false;
  for (const e of entries) {
    for (const u of e.unitLines || []) {
      if (String(u || '').trim()) parts.push(String(u).trim());
    }
    if (e.miss) {
      const note = String(e.note || '未命中').trim();
      parts.push(note);
      continue;
    }
    anyHit = true;
    const perBet = String(e.perBet || '-').trim();
    parts.push(`个数 ${e.count}  单注 ${perBet}  小计 ${formatAmount(e.lineSum)}`);
  }
  if (!anyHit && entries.length === 0) {
    parts.push('未命中');
  }
  parts.push(`合计：${formatAmount(messageSubtotal)}`);
  return parts.join('\n');
}

function appendOrderDebugToReply(db, wxGroupId, baseReply, debugBlock) {
  if (!isGroupDebugOrderReplyEnabled(db, wxGroupId) || !debugBlock) {
    return baseReply;
  }
  const head = String(baseReply ?? '').trimEnd();
  return head ? `${head}\n${debugBlock}` : debugBlock;
}

function formatRightSummaryLine(label, amount, width = 30) {
  const text = `${label} => ${formatAmount(amount)}`;
  if (text.length >= width) return text;
  return `${' '.repeat(width - text.length)}${text}`;
}

function formatBeijingDateTime(raw) {
  const text = String(raw || '').trim();
  if (!text) return '-';
  let d = null;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(text)) {
    // sqlite datetime('now') 是 UTC，无时区标记时按 UTC 解析后转北京时间
    d = new Date(`${text.replace(' ', 'T')}Z`);
  } else {
    const t = new Date(text);
    if (!Number.isNaN(t.getTime())) d = t;
  }
  if (!d || Number.isNaN(d.getTime())) return text;
  const bj = new Date(d.getTime() + 8 * 60 * 60 * 1000);
  const y = bj.getUTCFullYear();
  const m = String(bj.getUTCMonth() + 1).padStart(2, '0');
  const day = String(bj.getUTCDate()).padStart(2, '0');
  const hh = String(bj.getUTCHours()).padStart(2, '0');
  const mm = String(bj.getUTCMinutes()).padStart(2, '0');
  const ss = String(bj.getUTCSeconds()).padStart(2, '0');
  return `${y}-${m}-${day} ${hh}:${mm}:${ss}`;
}

function buildAggregateSections(rows, includeSender = false) {
  const map = new Map();
  for (const r of rows) {
    const settlementDate = String(r.settlement_date || '').trim() || 'unknown';
    const guideWord = String(r.guide_word || '').trim();
    const categoryWord = String(r.category_word || '').trim();
    const sender = String(r.sender_wxid || '').trim();
    const key = includeSender
      ? `${settlementDate}__${guideWord}__${categoryWord}__${sender}`
      : `${settlementDate}__${guideWord}__${categoryWord}`;
    if (!map.has(key)) {
      map.set(key, {
        settlementDate,
        guideWord,
        categoryWord,
        sender,
        itemTotals: new Map(),
      });
    }
    const section = map.get(key);
    const item = Number(r.item_value);
    if (!Number.isFinite(item)) continue;
    const prev = Number(section.itemTotals.get(item) || 0);
    section.itemTotals.set(item, prev + Number(r.order_amount || 0));
  }
  return Array.from(map.values());
}

function renderAggregateReply(db, wxGroupId, title, rows, includeSender = false) {
  if (rows.length === 0) return `${title}：暂无记录`;
  const sections = buildAggregateSections(rows, includeSender);
  const lines = [title];
  let grandTotal = 0;
  for (const sec of sections) {
    const senderName = includeSender ? resolveMemberDisplayName(db, wxGroupId, sec.sender) : '';
    const head = includeSender
      ? `【日期:${sec.settlementDate} 渠道:${sec.guideWord} 类型:${sec.categoryWord} 用户:${senderName}】`
      : `【日期:${sec.settlementDate} 渠道:${sec.guideWord} 类型:${sec.categoryWord}】`;
    lines.push(head);
    const items = Array.from(sec.itemTotals.entries()).sort((a, b) => a[0] - b[0]);
    let subTotal = 0;
    for (const [item, amount] of items) {
      lines.push(`${formatTicketItemLabel(item, sec.settlementDate)} => ${formatAmount(amount)}`);
      subTotal += Number(amount || 0);
    }
    lines.push(formatRightSummaryLine('小计', subTotal));
    const water = getRebateWaterRateForCategory(db, sec.categoryWord);
    if (water > 0) {
      const rebate = Math.round(subTotal * water * 10000) / 10000;
      lines.push(formatRightSummaryLine('返点(水)', rebate));
    }
    grandTotal += subTotal;
  }
  lines.push(formatRightSummaryLine('合计', grandTotal));
  return lines.join('\n');
}

function buildDetailBatches(rows) {
  const map = new Map();
  for (const r of rows) {
    const batchId =
      String(r.order_batch_id || '').trim() ||
      `${r.created_at || ''}|${r.sender_wxid || ''}|${r.guide_word || ''}|${r.category_word || ''}|${r.content_preview || ''}`;
    if (!map.has(batchId)) {
      map.set(batchId, {
        batchId,
        settlementDate: String(r.settlement_date || '').trim() || 'unknown',
        createdAt: String(r.created_at || '').trim(),
        guideWord: String(r.guide_word || '').trim(),
        categoryWord: String(r.category_word || '').trim(),
        sender: String(r.sender_wxid || '').trim(),
        content: String(r.content_preview || '').trim(),
        rows: [],
      });
    }
    const batch = map.get(batchId);
    const rowCreatedAt = String(r.created_at || '').trim();
    if (!batch.createdAt || (rowCreatedAt && rowCreatedAt < batch.createdAt)) {
      batch.createdAt = rowCreatedAt;
    }
    batch.rows.push(r);
  }
  return Array.from(map.values());
}

function renderDetailReply(db, wxGroupId, title, rows, includeSender = false) {
  if (rows.length === 0) return `${title}：暂无记录`;
  const batches = buildDetailBatches(rows);
  const allSetNames = db
    .prepare(
      `SELECT DISTINCT set_name FROM cmd_collections
       WHERE is_active = 1 AND wx_group_id IS NULL`
    )
    .all()
    .map((x) => String(x.set_name || '').trim())
    .filter(Boolean);
  const lines = [title];
  let grandTotal = 0;
  batches.forEach((b, idx) => {
    const headLine1 = `#${idx + 1} 下单时间:${formatBeijingDateTime(b.createdAt)} 日期:${b.settlementDate}`;
    const senderName = includeSender ? resolveMemberDisplayName(db, wxGroupId, b.sender) : '';
    const headLine2 = includeSender
      ? `渠道:${b.guideWord} 类型:${b.categoryWord} 用户:${senderName}`
      : `渠道:${b.guideWord} 类型:${b.categoryWord}`;
    lines.push(headLine1);
    lines.push(headLine2);
    if (b.content) lines.push(`指令: ${b.content}`);
    const targetRaw = resolveBatchTargetRaw(b, db);
    const keywordMatchers = parseTargetKeywordMatchers(db, targetRaw, allSetNames);
    const parsedSeg = parseDataSegmentFromBatchContent(b, db);
    const itemLines = b.rows
      .map((r) => ({
        item: Number(r.item_value),
        amount: Number(r.order_amount || 0),
      }))
      .filter((x) => Number.isFinite(x.item))
      .sort((a, b) => a.item - b.item)
      .map((x) =>
        formatOrderItemLineWithKeywords(keywordMatchers, x.item, x.amount, {
          algo: parsedSeg?.algo,
          unitValue: parsedSeg?.value,
          zodiacRef: b.settlementDate,
        })
      );
    lines.push(...itemLines);
    const subTotal = b.rows.reduce((acc, r) => acc + Number(r.order_amount || 0), 0);
    lines.push(formatRightSummaryLine('小计', subTotal));
    const waterB = getRebateWaterRateForCategory(db, b.categoryWord);
    if (waterB > 0) {
      const rebateB = Math.round(subTotal * waterB * 10000) / 10000;
      lines.push(formatRightSummaryLine('返点(水)', rebateB));
    }
    lines.push('---');
    grandTotal += subTotal;
  });
  if (lines[lines.length - 1] === '---') lines.pop();
  lines.push(formatRightSummaryLine('合计', grandTotal));
  return lines.join('\n');
}

function filterRowsToCurrentPeriods(rows) {
  return Array.isArray(rows) ? rows : [];
}

function appendOrderQueryTips(replyText, isDetail) {
  const tips = isDetail
    ? '提示：本群共用订单表，查明细单 / 查单 均列出全群记录'
    : '提示：本群共用订单表，查单 / 查明细单 均列出全群记录';
  return `${replyText}\n\n${tips}`;
}

/** 群内：报表 / 报表渠道 / 报表渠道2026-04-28（与私聊「报表…按号」导出区分） */
function parseGroupStatisticsReportIntent(content, db, wxGroupId = null) {
  let raw = stripWeChatAtPrefix(String(content || ''), db).trim();
  raw = stripLeadingRoutePrefixForInstructionParse(raw, db, wxGroupId);
  if (!raw) return null;
  const compact = raw.replace(/\s+/g, '');
  if (!compact.startsWith('报表')) return null;
  if (/^报表(?:帮助|指令)$/.test(compact)) return null;
  const restCompact = compact.slice(2);
  if (/按号|按成员/.test(restCompact)) {
    return { mode: 'private_style' };
  }
  let date = '';
  let channelHint = restCompact.replace(/^[:：+]+/, '').trim();
  const dateM = channelHint.match(/(\d{4}-\d{2}-\d{2})$/);
  if (dateM) {
    date = dateM[1];
    channelHint = channelHint.slice(0,channelHint.length - dateM[0].length).replace(/[:：+\s]+$/g,'').trim();
  }
  return { mode: 'group', channelHint, date };
}

/** 群内/私聊：水报表|水表（仅关键字时列出全局各玩法「水」）；水报表+渠道[+日期] 为成员返点汇总 */
function parseWaterReportIntent(content, db, wxGroupId = null) {
  let raw = stripWeChatAtPrefix(String(content || ''), db).trim();
  raw = stripLeadingRoutePrefixForInstructionParse(raw, db, wxGroupId);
  if (!raw) return null;
  const compact = raw.replace(/\s+/g, '');
  let restCompact;
  if (compact.startsWith('水报表')) {
    if (/^水报表(?:帮助|指令)$/.test(compact)) return null;
    restCompact = compact.slice(3);
  } else if (compact.startsWith('水表')) {
    if (/^水表(?:帮助|指令)$/.test(compact)) return null;
    restCompact = compact.slice(2);
  } else {
    return null;
  }
  if (/按号|按成员/.test(restCompact)) {
    return { mode: 'private_style' };
  }
  let date = '';
  let channelHint = restCompact.replace(/^[:：+]+/, '').trim();
  const dateM = channelHint.match(/(\d{4}-\d{2}-\d{2})$/);
  if (dateM) {
    date = dateM[1];
    channelHint = channelHint.slice(0, channelHint.length - dateM[0].length).replace(/[:：+\s]+$/g, '').trim();
  }
  if (!channelHint && !date) return { mode: 'all_water' };
  return { mode: 'group', channelHint, date };
}

function resolveReportGuideWordForGroup(db, wxGroupId, hint) {
  const h0 = String(hint || '').trim();
  const byVolume = db
    .prepare(
      `SELECT guide_word, COALESCE(SUM(order_amount), 0) AS s
       FROM cmd_orders
       WHERE wx_group_id = ? AND ${CMD_ORDERS_BET_ONLY}
       GROUP BY guide_word
       ORDER BY s DESC, guide_word ASC`
    )
    .all(wxGroupId);
  const distinct = byVolume.map((r) => String(r.guide_word || '').trim()).filter(Boolean);
  if (h0) {
    const canonHint = resolveGuideHintWithSynonyms(db, h0);
    if (distinct.includes(canonHint)) return canonHint;
    const byCanon = distinct.find((g) => g.startsWith(canonHint) || canonHint.startsWith(g));
    if (byCanon) return byCanon;
    if (distinct.includes(h0)) return h0;
    const byPrefix = distinct.find((g) => g.startsWith(h0) || h0.startsWith(g));
    if (byPrefix) return byPrefix;
    return canonHint;
  }
  const row = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('default_order_guide_word');
  const d = String(row?.value || '').trim();
  /** 未写渠道时：勿强行用后台默认（多为新澳门），否则本群仅下香港等渠道时报表永远对不上 */
  if (d && distinct.includes(d)) return d;
  if (distinct.length > 0) return distinct[0];
  if (d) return d;
  return '';
}

function resolveGroupReportSettlementDate(db, wxGroupId, guideWord, dateHint) {
  if (dateHint && /^\d{4}-\d{2}-\d{2}$/.test(dateHint)) return dateHint;
  const g = String(guideWord || '').trim();
  if (!g) return '';
  const row = db
    .prepare(
      `SELECT MAX(settlement_date) AS d FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND ${CMD_ORDERS_BET_ONLY}`
    )
    .get(wxGroupId, g);
  return String(row?.d || '').trim();
}

/** 全渠道汇总用结单日期：有日期则用之，否则取本群全部注单中最近一期 */
function resolveGroupReportSettlementDateAllChannels(db, wxGroupId, dateHint) {
  if (dateHint && /^\d{4}-\d{2}-\d{2}$/.test(dateHint)) return dateHint;
  const row = db
    .prepare(
      `SELECT MAX(settlement_date) AS d FROM cmd_orders
       WHERE wx_group_id = ? AND ${CMD_ORDERS_BET_ONLY}`
    )
    .get(wxGroupId);
  return String(row?.d || '').trim();
}

function getCmdTypeVarNumberForCategory(db, categoryWord, varNames) {
  const cat = String(categoryWord || '').trim();
  if (!cat) return null;
  for (const vn of varNames) {
    const row = db
      .prepare(
        `SELECT var_type, default_value_number, default_value_text FROM cmd_type_vars
         WHERE category_word = ? AND var_name = ?`
      )
      .get(cat, String(vn || '').trim());
    if (!row) continue;
    if (String(row.var_type || 'number') === 'text') {
      const n = Number(row.default_value_text ?? 0);
      if (Number.isFinite(n)) return n;
    } else {
      const n = Number(row.default_value_number ?? 0);
      if (Number.isFinite(n)) return n;
    }
  }
  return null;
}

/** 下单返点比例（水），用于查单展示 */
function getRebateWaterRateForCategory(db, categoryWord) {
  const w = getCmdTypeVarNumberForCategory(db, categoryWord, ['水', '返点']);
  return Number.isFinite(Number(w)) && Number(w) > 0 ? Number(w) : 0;
}

function buildAllWaterRatesReply(db) {
  const rows = db
    .prepare(
      `SELECT DISTINCT category_word FROM cmd_type_vars
       WHERE var_name IN ('水', '返点') AND TRIM(IFNULL(category_word, '')) <> ''`
    )
    .all();
  const cats = sortOddsCategoriesForDisplay(
    rows.map((r) => String(r.category_word || '').trim()).filter(Boolean)
  );
  if (cats.length === 0) {
    return '【水表】\n（暂无「水/返点」类型变量，请在后台「类型变量」配置）';
  }
  const lines = ['【水表】各玩法「水」（返点比例，全局类型变量）', '━━━━━━━━'];
  for (const cat of cats) {
    const v = getCmdTypeVarNumberForCategory(db, cat, ['水', '返点']);
    const display =
      v != null && Number.isFinite(Number(v)) ? formatAmount(Number(v)) : '（未配置）';
    lines.push(`【${cat}】`);
    lines.push(`  · 水：${display}`);
    lines.push('');
  }
  if (lines[lines.length - 1] === '') lines.pop();
  lines.push('━━━━━━━━');
  lines.push('成员返点汇总（按订单×上表比例）：群内群主发 水报表+渠道 或 水报表+渠道+日期。');
  return lines.join('\n');
}

function formatPnlAmount(n) {
  const x = Math.round(Number(n));
  if (!Number.isFinite(x)) return '0';
  if (x >= 0) return `+${x}`;
  return String(x);
}

/**
 * 特码逐号开奖预测（庄家净额）：若该号开特，= 全期特本金 − 该号派彩(本金×赔率) − 全期特水。
 * @returns {number}
 */
function computeTeHousePnlIfBallDraws(stake, rate, totalTe, totalWaterTe) {
  const a = Number(stake || 0);
  const r = Number(rate ?? 1);
  const t = Number(totalTe || 0);
  const w = Number(totalWaterTe || 0);
  if (!Number.isFinite(a) || !Number.isFinite(r) || !Number.isFinite(t) || !Number.isFinite(w)) return 0;
  return Math.round(t - a * r - w);
}

function formatExpiresDisplayBj(exp) {
  const s = String(exp || '').trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split('-');
    return `${y}年${Number(m)}月${Number(d)}日`;
  }
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  const bjMs = d.getTime() + 8 * 60 * 60 * 1000;
  const bj = new Date(bjMs);
  const mon = bj.getUTCMonth() + 1;
  const day = bj.getUTCDate();
  const hh = bj.getUTCHours();
  const mm = String(bj.getUTCMinutes()).padStart(2, '0');
  return `${mon}月${day}日${hh}点${mm}分`;
}

const ORDER_GUIDE_EXPIRES_JSON_KEY = 'order_guide_expires_json';

function getOrderGuideExpiresMap(db) {
  const row = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get(ORDER_GUIDE_EXPIRES_JSON_KEY);
  try {
    const o = JSON.parse(String(row?.value || '{}'));
    return o && typeof o === 'object' && !Array.isArray(o) ? o : {};
  } catch {
    return {};
  }
}

function saveOrderGuideExpiresMap(db, map) {
  db.prepare(
    `INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
     ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')`
  ).run(ORDER_GUIDE_EXPIRES_JSON_KEY, JSON.stringify(map));
}

/** 水报表等文末一行：到期时间（与群内统计报表口径一致，不另起「渠道到期」多行说明） */
function formatReportGuideExpiresLines(db, guideWord) {
  const gw = String(guideWord || '').trim();
  const map = getOrderGuideExpiresMap(db);
  const raw = map[gw];
  if (!raw) return ['到期时间：未设置'];
  return [`到期时间：${formatExpiresDisplayBj(String(raw))}`];
}

/** 报表文案里渠道简称（仅展示用） */
function shortenGuideWordForReportLabel(gw) {
  const s = String(gw || '').trim();
  if (s === '新澳门') return '新澳';
  if (s === '老澳门') return '老澳';
  return s;
}

/** 报表「合计」行渠道简称（香港→香） */
function shortenGuideWordForChannelTotalLabel(gw) {
  const s = String(gw || '').trim();
  if (s === '香港') return '香';
  return shortenGuideWordForReportLabel(s);
}

const REPORT_CHANNEL_SEPARATOR = '~~~~~~~分割线~~~~~~~~';
const REPORT_STATS_BRAND_FOOTER = '灵境统计';
const LIAN_XIAO_BALL_REPORT_CATEGORIES = new Set(['三连肖', '连肖', '四连肖', '五连肖']);

/** 从连肖 target_label 提取 1–49 球号（空格/斜杠分隔） */
function parseBallNumbersFromTargetLabel(label) {
  const s = String(label || '').trim();
  if (!s) return [];
  const nums = [];
  for (const m of s.matchAll(/(?:^|[\s/、,，]+)(\d{1,2})(?=[\s/、,，]|$)/gu)) {
    const n = Math.floor(Number(m[1]));
    if (n >= 1 && n <= 49) nums.push(n);
  }
  if (nums.length === 0) {
    for (const m of s.matchAll(/\b(\d{1,2})\b/g)) {
      const n = Math.floor(Number(m[1]));
      if (n >= 1 && n <= 49) nums.push(n);
    }
  }
  return [...new Set(nums)];
}

/** 连肖目标仅为球号组合（无生肖汉字）时，报表按「特」逐号展示 */
function isBallOnlyLianXiaoTargetLabel(label) {
  const s = String(label || '').trim();
  if (!s) return false;
  for (const z of ZODIAC_ORDER) {
    if (s.includes(z)) return false;
  }
  return parseBallNumbersFromTargetLabel(s).length > 0;
}

function mergeTeBallStakeMap(into, from) {
  for (const [ball, amt] of from) {
    into.set(ball, (into.get(ball) || 0) + amt);
  }
}

/** @returns {Map<number, number>} */
function loadTeBallStakeMapForCategory(db, wxGroupId, gw, sd, categoryWord) {
  const map = new Map();
  const rows = db
    .prepare(
      `SELECT item_value, target_label, order_amount FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
         AND category_word = ? AND ${CMD_ORDERS_BET_ONLY}`
    )
    .all(wxGroupId, gw, sd, categoryWord);
  for (const r of rows) {
    const amt = Number(r.order_amount || 0);
    if (amt <= 0) continue;
    const item = Math.floor(Number(r.item_value));
    if (item >= 1 && item <= 49) {
      map.set(item, (map.get(item) || 0) + amt);
      continue;
    }
    const lab = String(r.target_label || '').trim();
    if (!isBallOnlyLianXiaoTargetLabel(lab)) continue;
    const balls = parseBallNumbersFromTargetLabel(lab);
    if (balls.length === 0) continue;
    const per = amt / balls.length;
    for (const b of balls) {
      map.set(b, (map.get(b) || 0) + per);
    }
  }
  return map;
}

function computeTeReportWaterTotal(db, wxGroupId, gw, sd, categoryWords) {
  const cats = [...new Set((categoryWords || []).map((c) => String(c || '').trim()).filter(Boolean))];
  if (cats.length === 0) return 0;
  const placeholders = cats.map(() => '?').join(',');
  const rows = db
    .prepare(
      `SELECT category_word, order_amount FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
         AND category_word IN (${placeholders}) AND ${CMD_ORDERS_BET_ONLY}`
    )
    .all(wxGroupId, gw, sd, ...cats);
  let totalWaterTe = 0;
  for (const sr of rows) {
    const st = Number(sr.order_amount || 0);
    if (st <= 0) continue;
    const cat = String(sr.category_word || '').trim();
    const w = getRebateWaterRateForCategory(db, cat);
    if (w > 0) totalWaterTe += Math.round(st * w * 10000) / 10000;
  }
  return Math.round(totalWaterTe * 100) / 100;
}

/** @param {Map<number, number>} ballMap @param {number} totalTeStake */
function formatTeBallReportLines(db, ballMap, totalTeStake, totalWaterTe) {
  const rate = getCmdTypeVarNumberForCategory(db, '特', ['特费率', '固定费率', '费率']) ?? 1;
  const rows = [...ballMap.entries()].map(([item, amt]) => {
    const stake = Number(amt || 0);
    const pnl = computeTeHousePnlIfBallDraws(stake, rate, totalTeStake, totalWaterTe);
    return { item, stake, pnl };
  });
  rows.sort((a, b) => a.pnl - b.pnl || a.item - b.item);
  return rows.map(({ item, stake, pnl }) => {
    const pad = String(item).padStart(2, '0');
    return `${pad}各${formatAmount(stake)}   ${formatPnlAmount(pnl)}`;
  });
}

function formatReportExpiryPlain(db, guideWord) {
  const gw = String(guideWord || '').trim();
  const map = getOrderGuideExpiresMap(db);
  const raw = map[gw];
  if (!raw) return '到期时间：未设置';
  return `到期时间：${formatExpiresDisplayBj(String(raw))}`;
}

function formatReportExpiryPlainMulti(db, guideWords) {
  const uniq = [
    ...new Set((guideWords || []).map((x) => String(x || '').trim()).filter(Boolean)),
  ].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  if (!uniq.length) return '到期时间：未设置';
  const map = getOrderGuideExpiresMap(db);
  const parts = uniq.map((gw) => {
    const raw = map[gw];
    const sg = shortenGuideWordForReportLabel(gw);
    const t = raw ? formatExpiresDisplayBj(String(raw)) : '未设置';
    return `${sg}${t}`;
  });
  return `到期时间：${parts.join('；')}`;
}

function resolveGroupServiceExpireRaw(db, wxGroupId) {
  const gid = String(wxGroupId || '').trim();
  if (!gid) return '';
  const g = db.prepare(`SELECT expires_at FROM wx_groups WHERE wx_group_id = ? LIMIT 1`).get(gid);
  if (g?.expires_at) return String(g.expires_at).trim();
  const w = db
    .prepare(`SELECT expire_datetime FROM group_whitelist WHERE group_id = ? LIMIT 1`)
    .get(gid);
  return String(w?.expire_datetime || '').trim();
}

function formatGroupStatisticsReportFooterLines(db, wxGroupId) {
  const raw = resolveGroupServiceExpireRaw(db, wxGroupId);
  const expiryText = raw ? formatExpiresDisplayBj(raw) : '未设置';
  return ['', '========', REPORT_STATS_BRAND_FOOTER, '到期时间：', expiryText];
}

function formatAllGuideExpiresForReply(db) {
  const map = getOrderGuideExpiresMap(db);
  const keys = Object.keys(map).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  if (keys.length === 0) {
    return '【渠道到期】暂无记录。群主可发：渠道到期 新澳门 2026-12-31；或渠道到期 2026-12-31（默认渠道）';
  }
  const lines = ['【渠道到期】'];
  for (const k of keys) {
    lines.push(`${k}：${formatExpiresDisplayBj(String(map[k]))}`);
  }
  return lines.join('\n');
}

function normalizeExpiresUserInput(raw) {
  const t = String(raw || '').trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return null;
  return dateToYmd(d);
}

/**
 * 群主：渠道到期 [渠道名] YYYY-MM-DD | 渠道到期 YYYY-MM-DD（默认渠道）| 渠道到期 渠道 清除 | 查渠道到期
 */
function maybeHandleOrderGuideExpiresCommand(db, wxGroupId, senderWxid, content) {
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  const norm = raw.replace(/\s+/g, ' ').trim();
  if (!norm) return null;
  const compactEx = norm.replace(/\s+/g, '');
  const isList = /^查渠道到期$/u.test(compactEx);
  const isCmd = /^渠道到期/u.test(compactEx);
  if (!isList && !isCmd) return null;
  if (!wxGroupId || !senderWxid) {
    return { ok: true, replyText: '请在群内使用该指令。' };
  }
  if (isList) {
    return { ok: true, replyText: formatAllGuideExpiresForReply(db) };
  }
  let rest = norm.replace(/^渠道到期\s*/u, '').trim();
  if (!rest) {
    return {
      ok: true,
      replyText:
        '用法：\n渠道到期 新澳门 2026-12-31（指定渠道）\n渠道到期 2026-12-31（默认下单渠道）\n渠道到期 新澳门 清除\n查渠道到期（列表）\n后台 app_settings 键：order_guide_expires_json',
    };
  }
  if (rest === '查看') {
    return { ok: true, replyText: formatAllGuideExpiresForReply(db) };
  }
  const parts = rest.split(/\s+/).filter(Boolean);
  const dateRe = /^\d{4}-\d{2}-\d{2}$/;
  let guide = '';
  let datePart = '';
  let clearMode = false;
  if (parts.length >= 2 && parts[parts.length - 1] === '清除') {
    guide = resolveGuideHintWithSynonyms(db, parts.slice(0, -1).join(''));
    if (!guide) guide = parts.slice(0, -1).join('');
    clearMode = true;
  } else if (parts.length === 1) {
    if (!dateRe.test(parts[0])) {
      return { ok: true, replyText: '请提供日期：YYYY-MM-DD，例如 渠道到期 2026-12-31' };
    }
    const row = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_guide_word'`).get();
    guide = String(row?.value || '').trim();
    if (!guide) return { ok: true, replyText: '未配置默认下单渠道，请用：渠道到期 新澳门 2026-12-31' };
    datePart = parts[0];
  } else if (parts.length === 2 && dateRe.test(parts[1])) {
    guide = resolveGuideHintWithSynonyms(db, parts[0]);
    if (!guide) guide = parts[0];
    datePart = parts[1];
  } else {
    return {
      ok: true,
      replyText: '格式示例：渠道到期 新澳门 2026-12-31；渠道到期 2026-12-31；渠道到期 新澳门 清除',
    };
  }
  const map = { ...getOrderGuideExpiresMap(db) };
  if (clearMode) {
    if (!guide) return { ok: true, replyText: '请指定要清除的渠道名。' };
    delete map[guide];
    saveOrderGuideExpiresMap(db, map);
    return { ok: true, replyText: `已清除渠道「${guide}」到期设置` };
  }
  const ymd = normalizeExpiresUserInput(datePart);
  if (!ymd) return { ok: true, replyText: '日期无效，请用 YYYY-MM-DD' };
  map[guide] = ymd;
  saveOrderGuideExpiresMap(db, map);
  return {
    ok: true,
    replyText: `已设置渠道「${guide}」到期：${formatExpiresDisplayBj(ymd)}`,
  };
}

/** 群内报表一行约 15 个中文字宽，过长则换行（不影响语义） */
const REPORT_LINE_MAX_UNITS = 15;

function splitReportGraphemes(s) {
  const t = String(s);
  if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
    const seg = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' });
    return [...seg.segment(t)].map((x) => x.segment);
  }
  return Array.from(t);
}

/** @param {string} line @param {number} maxUnits */
function wrapReportLine(line, maxUnits = REPORT_LINE_MAX_UNITS) {
  const s = String(line);
  if (!s) return [''];
  const parts = splitReportGraphemes(s);
  if (parts.length <= maxUnits) return [s];
  const out = [];
  let buf = '';
  let n = 0;
  for (const ch of parts) {
    const need = 1;
    if (n + need > maxUnits && buf) {
      out.push(buf);
      buf = ch;
      n = need;
    } else {
      buf += ch;
      n += need;
    }
  }
  if (buf) out.push(buf);
  return out;
}

/** @param {string[]} lines */
function wrapReportLines(lines, maxUnits = REPORT_LINE_MAX_UNITS) {
  const out = [];
  for (const ln of lines) {
    if (ln === '') {
      out.push('');
      continue;
    }
    out.push(...wrapReportLine(ln, maxUnits));
  }
  return out;
}

function sortCategoryWordsForReport(list) {
  const order = [
    '特',
    '特肖',
    '特肖马',
    '平特',
    '平特马',
    '平尾',
    '平尾0尾',
    '单双',
    '连肖',
    '三连肖',
    '四连肖',
    '五连肖',
    '连码',
  ];
  const rank = (c) => {
    const i = order.indexOf(c);
    return i >= 0 ? i : 100;
  };
  return [...list].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b, 'zh-CN'));
}

/** 单一渠道下：全部玩法分类明细 +「【渠道】合计」，不含文末公共说明与全渠道总计 */
function computeGroupStatisticsReportSection(db, wxGroupId, guideWord, settlementDate) {
  const gw = String(guideWord || '').trim();
  const sd = String(settlementDate || '').trim();
  const sgw = shortenGuideWordForReportLabel(gw);
  const channelTotalLabel = shortenGuideWordForChannelTotalLabel(gw);
  const teBallMap = new Map();
  const teReportCats = [];
  const midDetails = [];
  const subParts = [];
  const subTotals = new Map();

  const catRows = db
    .prepare(
      `SELECT DISTINCT category_word FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
         AND ${CMD_ORDERS_BET_ONLY}`
    )
    .all(wxGroupId, gw, sd);
  const categories = sortCategoryWordsForReport(
    catRows.map((r) => String(r.category_word || '').trim()).filter(Boolean)
  );
  if (categories.length === 0) return null;

  for (const cat of categories) {
    const sumRow = db
      .prepare(
        `SELECT COALESCE(SUM(order_amount), 0) AS t FROM cmd_orders
         WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
           AND category_word = ? AND ${CMD_ORDERS_BET_ONLY}`
      )
      .get(wxGroupId, gw, sd, cat);
    const catTotal = Number(sumRow?.t || 0);
    subTotals.set(cat, catTotal);

    if (cat === '特') {
      mergeTeBallStakeMap(teBallMap, loadTeBallStakeMapForCategory(db, wxGroupId, gw, sd, cat));
      teReportCats.push(cat);
      continue;
    }

    if (LIAN_XIAO_BALL_REPORT_CATEGORIES.has(cat)) {
      const lxRows = db
        .prepare(
          `SELECT target_label FROM cmd_orders
           WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
             AND category_word = ? AND ${CMD_ORDERS_BET_ONLY}`
        )
        .all(wxGroupId, gw, sd, cat);
      const allBallOnly = lxRows.every((r) =>
        isBallOnlyLianXiaoTargetLabel(String(r.target_label || ''))
      );
      if (allBallOnly && lxRows.length > 0) {
        mergeTeBallStakeMap(teBallMap, loadTeBallStakeMapForCategory(db, wxGroupId, gw, sd, cat));
        teReportCats.push(cat);
        continue;
      }
      const str = db
        .prepare(
          `SELECT target_label, SUM(order_amount) AS s FROM cmd_orders
           WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
             AND category_word = ? AND ${CMD_ORDERS_BET_ONLY}
           GROUP BY target_label
           ORDER BY s DESC`
        )
        .all(wxGroupId, gw, sd, cat);
      for (const r of str) {
        const lab = String(r.target_label || '').trim() || '目标';
        midDetails.push(`${lab}=${formatAmount(r.s)}`);
      }
      subParts.push(`【${sgw}${cat}】小计：${formatAmount(catTotal)}`);
      continue;
    }

    if (cat === '平特') {
      const ptr = db
        .prepare(
          `SELECT target_label, SUM(order_amount) AS s FROM cmd_orders
           WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
             AND category_word = ? AND ${CMD_ORDERS_BET_ONLY}
           GROUP BY target_label
           ORDER BY s DESC`
        )
        .all(wxGroupId, gw, sd, cat);
      for (const r of ptr) {
        const lab = String(r.target_label || '').trim() || '目标';
        midDetails.push(`平特${lab}${formatAmount(r.s)}`);
      }
      subParts.push(`【${sgw}${cat}】小计：${formatAmount(catTotal)}`);
      continue;
    }

    subParts.push(`【${sgw}${cat}】小计：${formatAmount(catTotal)}`);
  }

  const channelGrand = categories.reduce((acc, c) => acc + Number(subTotals.get(c) || 0), 0);
  const out = [];
  if (teBallMap.size > 0) {
    let teBlockStake = 0;
    for (const v of teBallMap.values()) teBlockStake += v;
    teBlockStake = Math.round(teBlockStake * 100) / 100;
    const totalWaterTe = computeTeReportWaterTotal(db, wxGroupId, gw, sd, teReportCats);
    out.push('当前统计：');
    out.push(...formatTeBallReportLines(db, teBallMap, teBlockStake, totalWaterTe));
    out.push(`【${sgw}特】小计：${formatAmount(teBlockStake)}`);
  }
  for (const ln of midDetails) out.push(ln);
  for (const sp of subParts) out.push(sp);
  out.push(`【${channelTotalLabel}】合计：${formatAmount(channelGrand)}`);
  return { lines: out, channelGrand };
}

/** 报表仅「报表」二字时：本群该结单日全部渠道、全部玩法 */
function buildAllChannelsGroupStatisticsReportText(db, wxGroupId, settlementDate) {
  const sd = String(settlementDate || '').trim();
  if (!sd) return '';
  const guideRows = db
    .prepare(
      `SELECT DISTINCT guide_word FROM cmd_orders
       WHERE wx_group_id = ? AND settlement_date = ? AND ${CMD_ORDERS_BET_ONLY}
       ORDER BY guide_word ASC`
    )
    .all(wxGroupId, sd);
  const guides = guideRows.map((r) => String(r.guide_word || '').trim()).filter(Boolean);
  if (guides.length === 0) return '';

  const channelBlocks = [];
  let grandAll = 0;
  for (const gw of guides) {
    const sec = computeGroupStatisticsReportSection(db, wxGroupId, gw, sd);
    if (!sec) continue;
    grandAll += sec.channelGrand;
    channelBlocks.push(sec.lines);
  }
  if (channelBlocks.length === 0) return '';

  const body = [];
  for (let i = 0; i < channelBlocks.length; i++) {
    if (i > 0) {
      body.push('');
      body.push(REPORT_CHANNEL_SEPARATOR);
      body.push('');
    }
    body.push(...channelBlocks[i]);
  }
  const out = [
    ...body,
    '',
    `=====总计：${formatAmount(grandAll)}=====`,
    ...formatGroupStatisticsReportFooterLines(db, wxGroupId),
  ];
  return out.join('\n');
}

function buildGroupStatisticsReportText(db, wxGroupId, guideWord, settlementDate) {
  const gw = String(guideWord || '').trim();
  const sd = String(settlementDate || '').trim();
  const sec = computeGroupStatisticsReportSection(db, wxGroupId, gw, sd);
  if (!sec) return '';

  const out = [
    ...sec.lines,
    '',
    `=====总计：${formatAmount(sec.channelGrand)}=====`,
    ...formatGroupStatisticsReportFooterLines(db, wxGroupId),
  ];
  return out.join('\n');
}

function buildWaterRebateReportText(db, wxGroupId, guideWord, settlementDate) {
  const gw = String(guideWord || '').trim();
  const sd = String(settlementDate || '').trim();
  const orderRows = db
    .prepare(
      `SELECT sender_wxid, category_word, order_amount
       FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
         AND ${CMD_ORDERS_BET_ONLY}`
    )
    .all(wxGroupId, gw, sd);
  if (orderRows.length === 0) return '';

  const rebateBySender = new Map();
  for (const r of orderRows) {
    const wxid = String(r.sender_wxid || '').trim();
    if (!wxid) continue;
    const cat = String(r.category_word || '').trim();
    const amt = Number(r.order_amount ?? 0);
    if (!Number.isFinite(amt)) continue;
    const water = getRebateWaterRateForCategory(db, cat);
    const rebate = Math.round(amt * water * 10000) / 10000;
    rebateBySender.set(wxid, (rebateBySender.get(wxid) || 0) + rebate);
  }

  const entries = [...rebateBySender.entries()].map(([wxid, rebate]) => ({
    wxid,
    rebate,
    name: String(resolveMemberDisplayName(db, wxGroupId, wxid) || '').trim(),
  }));
  entries.sort(
    (a, b) =>
      b.rebate - a.rebate || (a.name || a.wxid).localeCompare(b.name || b.wxid, 'zh-CN')
  );

  let grand = 0;
  for (const e of entries) grand += e.rebate;
  grand = Math.round(grand * 10000) / 10000;

  const lines = [
    '【水报表】按成员汇总返点（水）',
    `渠道：${gw} 期号：${sd}`,
    '返点＝金额×玩法水比例（不含发货/开奖行）。',
    '--------',
  ];
  for (const e of entries) {
    const label = e.name || e.wxid || '未知';
    lines.push(`${label}：${formatAmount(e.rebate)}`);
  }
  lines.push('--------');
  lines.push(`合计返点 ${formatAmount(grand)}`);
  lines.push('');
  lines.push(...formatReportGuideExpiresLines(db, gw));
  return wrapReportLines(lines).join('\n');
}

function maybeHandleGroupStatisticsReport(db, wxGroupId, senderWxid, content) {
  const intent = parseGroupStatisticsReportIntent(content, db, wxGroupId);
  if (!intent) return null;
  if (intent.mode === 'private_style') {
    return {
      ok: true,
      replyText:
        '群内「报表」为当前群、按最近有单汇总。若要导出 Excel，请私聊机器人：报表+渠道名+按号（或按成员）。',
    };
  }
  if (!wxGroupId) {
    return { ok: true, replyText: '请在群内发送「报表」查看汇总。' };
  }
  const channelHint = String(intent.channelHint || '').trim();
  if (!channelHint) {
    const settlementDate = resolveGroupReportSettlementDateAllChannels(db, wxGroupId, intent.date);
    if (!settlementDate) {
      return {
        ok: true,
        replyText: `当前群暂无可统计订单${intent.date ? `（${intent.date}）` : ''}。`,
      };
    }
    const body = buildAllChannelsGroupStatisticsReportText(db, wxGroupId, settlementDate);
    if (!body) {
      return {
        ok: true,
        replyText: `本群在 ${settlementDate} 暂无可统计订单。`,
      };
    }
    return { ok: true, replyText: body };
  }
  const guideWord = resolveReportGuideWordForGroup(db, wxGroupId, channelHint);
  if (!guideWord) {
    return {
      ok: true,
      replyText: '暂未找到渠道名，请先下单、或在后台配置默认订单渠道；也可发送：报表新澳门',
    };
  }
  const settlementDate = resolveGroupReportSettlementDate(db, wxGroupId, guideWord, intent.date);
  if (!settlementDate) {
    return {
      ok: true,
      replyText: `当前群暂无渠道「${guideWord}」的订单记录${intent.date ? `（${intent.date}）` : ''}。`,
    };
  }
  const body = buildGroupStatisticsReportText(db, wxGroupId, guideWord, settlementDate);
  if (!body) {
    return {
      ok: true,
      replyText: `渠道「${guideWord}」在 ${settlementDate} 暂无可统计订单。`,
    };
  }
  return { ok: true, replyText: body };
}

function maybeHandleWaterRebateReport(db, wxGroupId, senderWxid, content) {
  const intent = parseWaterReportIntent(content, db, wxGroupId);
  if (!intent) return null;
  if (intent.mode === 'all_water') {
    return { ok: true, replyText: buildAllWaterRatesReply(db) };
  }
  if (intent.mode === 'private_style') {
    return {
      ok: true,
      replyText:
        '「水报表」请在群内发送：水报表 / 水报表+渠道 / 水报表+日期。查各玩法水比例可发：水表 或 水报表（不带渠道）。私聊 Excel 请用「报表+渠道+按成员」。',
    };
  }
  if (!wxGroupId) {
    return { ok: true, replyText: '请在群内发送「水报表+渠道」查看各成员返点；查全局水比例可私聊发：水表' };
  }
  const guideWord = resolveReportGuideWordForGroup(db, wxGroupId, intent.channelHint);
  if (!guideWord) {
    return {
      ok: true,
      replyText:
        '暂未找到渠道名，请先下单、或在后台配置默认订单渠道；也可发送：水报表新澳门',
    };
  }
  const settlementDate = resolveGroupReportSettlementDate(db, wxGroupId, guideWord, intent.date);
  if (!settlementDate) {
    return {
      ok: true,
      replyText: `当前群暂无渠道「${guideWord}」的订单记录${intent.date ? `（${intent.date}）` : ''}。`,
    };
  }
  const body = buildWaterRebateReportText(db, wxGroupId, guideWord, settlementDate);
  if (!body) {
    return {
      ok: true,
      replyText: `渠道「${guideWord}」在 ${settlementDate} 暂无订单，无法汇总返点。`,
    };
  }
  return { ok: true, replyText: body };
}

function maybeHandleOrderQueryCommand(db, wxGroupId, senderWxid, content) {
  void senderWxid;
  const text = stripWeChatAtPrefix(String(content || '').trim(), db).trim();
  const altAgg = instructionAltPattern(db, 'order_query');
  const altDetail = instructionAltPattern(db, 'order_query_detail');
  if (!altAgg || !altDetail) return null;
  const mDetail = text.match(new RegExp(`^(?:${altDetail})(?:\\s+(.+))?$`, 'u'));
  const mAgg = text.match(new RegExp(`^(?:${altAgg})(?:\\s+(.+))?$`, 'u'));
  if (!mAgg && !mDetail) return null;
  const isDetail = Boolean(mDetail);
  const rows = filterRowsToCurrentPeriods(queryOrderRows(db, { wxGroupId }));
  const title = isDetail ? '本群明细单' : '本群订单';
  const replyText = isDetail
    ? renderDetailReply(db, wxGroupId, title, rows, false)
    : renderAggregateReply(db, wxGroupId, title, rows, false);
  return { ok: true, replyText: appendOrderQueryTips(replyText, isDetail) };
}

function numTypeVarRow(r) {
  if (String(r?.var_type || 'number') === 'text') return null;
  const n = Number(r?.default_value_number);
  return Number.isFinite(n) ? n : null;
}

/**
 * 倍率与费率同义：与通用「费率」同值的倍率/固定费率只保留一条「费率」。
 * 「特费率」为玩法「特」（特码）专用：与同值「费率」并存时，【特】保留「特费率」并去重「费率」；其它玩法下去重「特费率」。
 */
function filterRedundantOddsRows(rows, categoryWord = '') {
  const list = Array.isArray(rows) ? [...rows] : [];
  const cat = String(categoryWord || '').trim();
  const by = new Map();
  for (const r of list) {
    const nm = String(r.var_name || '').trim();
    if (nm) by.set(nm, r);
  }
  const omit = new Set();
  const v费率 = numTypeVarRow(by.get('费率'));
  const v特 = numTypeVarRow(by.get('特费率'));
  const v固 = numTypeVarRow(by.get('固定费率'));
  const v倍 = numTypeVarRow(by.get('倍率'));

  if (v倍 != null) {
    if (v费率 === v倍 || v特 === v倍 || v固 === v倍) omit.add('倍率');
  }
  if (v固 != null && v费率 != null && v固 === v费率) omit.add('固定费率');
  if (v特 != null && v费率 != null && v特 === v费率) {
    if (cat === '特') omit.add('费率');
    else omit.add('特费率');
  }
  if (v固 != null && v费率 == null && v特 != null && v固 === v特) omit.add('固定费率');

  const out = list.filter((r) => !omit.has(String(r.var_name || '').trim()));
  const has费率 = out.some((x) => String(x.var_name || '').trim() === '费率');
  return out.map((r) => {
    const nm = String(r.var_name || '').trim();
    if (nm === '倍率' && !has费率) {
      return { ...r, _displayName: '费率' };
    }
    return { ...r };
  });
}

/** 赔率表玩法块顺序（与群配置示例一致）；未列出的分类排在末尾并按拼音排序 */
const ODDS_TABLE_CATEGORY_ORDER = [
  '特',
  '平特',
  '平特马',
  '平尾',
  '平尾0尾',
  '单双',
  '特肖',
  '特肖马',
  '连肖',
  '三连肖',
  '四连肖',
  '五连肖',
  '连码',
];

const ODDS_TABLE_LIANMA_KEYS = ['二中二', '三中三', '三中二', '中三'];

const ODDS_TABLE_LIANXIAO_GROUPS = ['二联', '三联', '四联', '五联'];

const ODDS_TABLE_LIANXIAO_INNER = ['带马', '不带'];

function sortOddsKeysByPreferred(keys, preferred) {
  const pref = new Map(preferred.map((k, i) => [k, i]));
  return [...keys].sort((a, b) => {
    const ia = pref.has(a) ? pref.get(a) : 10000;
    const ib = pref.has(b) ? pref.get(b) : 10000;
    if (ia !== ib) return ia - ib;
    return String(a).localeCompare(String(b), 'zh-CN');
  });
}

function sortOddsCategoriesForDisplay(cats) {
  const orderMap = new Map(ODDS_TABLE_CATEGORY_ORDER.map((c, i) => [c, i]));
  return [...cats].sort((a, b) => {
    const ia = orderMap.has(a) ? orderMap.get(a) : 100000;
    const ib = orderMap.has(b) ? orderMap.get(b) : 100000;
    if (ia !== ib) return ia - ib;
    return a.localeCompare(b, 'zh-CN');
  });
}

function formatJsonOddsForRead(name, raw) {
  const label = String(name || '').trim();
  try {
    const o = JSON.parse(String(raw || 'null'));
    if (!o || typeof o !== 'object' || Array.isArray(o)) return String(raw || '').slice(0, 200);
    const keys = Object.keys(o);
    if (keys.length === 0) return '（空）';
    const flatLike = label.includes('连码') || keys.every((k) => !o[k] || typeof o[k] !== 'object');
    if (flatLike) {
      if (label.includes('连码')) {
        const ordered = sortOddsKeysByPreferred(keys, ODDS_TABLE_LIANMA_KEYS);
        const hasStdFour =
          ODDS_TABLE_LIANMA_KEYS.every((k) => Object.prototype.hasOwnProperty.call(o, k)) &&
          keys.length === ODDS_TABLE_LIANMA_KEYS.length;
        if (hasStdFour) {
          return `二中二${o['二中二']}；三中三${o['三中三']}\n三中二${o['三中二']}；中三${o['中三']}`;
        }
        return ordered.map((k) => `${k}${o[k]}`).join('；');
      }
      const parts = keys.map((k) => `${k}${o[k]}`);
      return parts.join('；');
    }
    const lines = [];
    const outerKeys = label.includes('连肖')
      ? sortOddsKeysByPreferred(keys, ODDS_TABLE_LIANXIAO_GROUPS)
      : sortOddsKeysByPreferred(keys, []);
    for (const k of outerKeys) {
      const v = o[k];
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        const innerKeys = label.includes('连肖')
          ? sortOddsKeysByPreferred(Object.keys(v), ODDS_TABLE_LIANXIAO_INNER)
          : sortOddsKeysByPreferred(Object.keys(v), []);
        const seg = innerKeys.map((k2) => `${k2}${v[k2]}`).join(' ');
        lines.push(`  ${k}：${seg}`);
      } else {
        lines.push(`  ${k}=${v}`);
      }
    }
    return lines.join('\n');
  } catch {
    const s = String(raw || '').trim();
    return s.length > 180 ? `${s.slice(0, 178)}…` : s;
  }
}

function formatTypeVarDisplayForOddsTable(row) {
  if (String(row?.var_type || 'number') === 'text') {
    const raw = String(row?.default_value_text ?? '').trim();
    if (!raw) return '（空）';
    const vn = String(row?.var_name || '').trim();
    if (/赔率$/u.test(vn) || vn === '连肖赔率' || vn === '连码赔率') {
      return formatJsonOddsForRead(vn, raw);
    }
    try {
      const o = JSON.parse(raw);
      const s = JSON.stringify(o);
      return s.length > 200 ? `${s.slice(0, 198)}…` : s;
    } catch {
      return raw.length > 200 ? `${raw.slice(0, 198)}…` : raw;
    }
  }
  const n = Number(row?.default_value_number);
  return Number.isFinite(n) ? String(n) : '';
}

function sortOddsRowsForDisplay(vars) {
  const rank = (r) => {
    const n = String(r.var_name || '').trim();
    const d = String(r._displayName || '').trim();
    if (n === '水') return 2;
    if (/赔率$/u.test(n) && String(r.var_type || '') === 'text') return 40;
    if (d === '费率' || n === '费率' || n === '特费率' || n === '固定费率' || n === '倍率') return 0;
    return 20;
  };
  return [...vars].sort(
    (a, b) => rank(a) - rank(b) || String(a.var_name || '').localeCompare(String(b.var_name || ''), 'zh-CN')
  );
}

function buildOddsTableReply(db) {
  const rows = db
    .prepare(
      `SELECT category_word, var_name, var_type, default_value_number, default_value_text
       FROM cmd_type_vars
       ORDER BY category_word ASC, var_name ASC`
    )
    .all();
  if (rows.length === 0) {
    return '【赔率表】\n（暂无类型变量，请在后台「类型变量」添加费率/水等）';
  }
  const byCat = new Map();
  for (const r of rows) {
    const c = String(r.category_word || '').trim();
    if (!c) continue;
    if (!byCat.has(c)) byCat.set(c, []);
    byCat.get(c).push(r);
  }
  const cats = sortOddsCategoriesForDisplay([...byCat.keys()]);
  const lines = ['【赔率表】各玩法费率与水（后台「类型变量」）', '━━━━━━━━'];
  const maxCatLines = 40;
  for (let i = 0; i < cats.length; i++) {
    if (i >= maxCatLines) {
      lines.push(`… 另有 ${cats.length - maxCatLines} 个玩法，请到后台查看`);
      break;
    }
    const cat = cats[i];
    const rawVars = byCat.get(cat) || [];
    const vars = sortOddsRowsForDisplay(filterRedundantOddsRows(rawVars, cat));
    lines.push(`【${cat}】`);
    for (const r of vars) {
      const vn0 = String(r.var_name || '').trim();
      let disp = String(r._displayName || vn0).trim() || vn0;
      if (/赔率$/u.test(vn0) && String(r.var_type || '') === 'text') disp = '组合';
      const val = formatTypeVarDisplayForOddsTable(r);
      if (String(r.var_type || '') === 'text' && /赔率$/u.test(vn0) && val.includes('\n')) {
        lines.push(`  · ${disp}：`);
        for (const ln of String(val).split('\n')) {
          const t = ln.replace(/^\s+/, '');
          if (t) lines.push(`    ${t}`);
        }
      } else {
        lines.push(`  · ${disp}：${val}`);
      }
    }
    lines.push('');
  }
  if (lines[lines.length - 1] === '') lines.pop();
  lines.push('━━━━━━━━');
  lines.push(`共 ${rows.length} 条变量 · 修改请后台或群主「群配置/设置/配置」等`);
  return lines.join('\n');
}

function buildQueryGroupConfigReply(db, wxGroupId) {
  const lines = ['【查询群配置】', '--------'];
  const g = db.prepare(`SELECT * FROM wx_groups WHERE wx_group_id = ? LIMIT 1`).get(wxGroupId);
  if (!g) {
    lines.push('后台尚未登记本群资料（后台「群管理」绑定后可显示名称、到期时间等）。');
  } else {
    lines.push(`群ID：${g.wx_group_id || ''}`);
    lines.push(`登记名称：${g.name || '（未填）'}`);
    lines.push(`后台标签：${g.admin_label || '（未填）'}`);
    lines.push(`手动备注群主：${g.manual_owner || '（未填）'}`);
    lines.push(`运维备注：${g.admin_remark || '（未填）'}`);
    const exp = g.expires_at;
    if (!exp) {
      lines.push('群授权到期（后台「群管理」）：（未配置）');
    } else {
      const d = new Date(exp);
      if (Number.isNaN(d.getTime())) {
        lines.push(`群授权到期（后台「群管理」）：${exp}`);
      } else {
        const bjMs = d.getTime() + 8 * 60 * 60 * 1000;
        const bj = new Date(bjMs);
        lines.push(
          `群授权到期（后台「群管理」）：${bj.getUTCMonth() + 1}月${bj.getUTCDate()}日${bj.getUTCHours()}点${String(bj.getUTCMinutes()).padStart(2, '0')}分`
        );
      }
    }
    lines.push(`启用状态：${Number(g.is_active ?? 1) === 1 ? '是' : '否'}`);
    lines.push(`收单开关（群主指令 开/关/启/闭 或 收单开/收单关）：${Number(g.owner_orders_enabled ?? 1) !== 0 ? '开' : '关'}`);
    lines.push(
      `下单调试回执（群主指令 调试开/关/启/闭；开则附原文+各行个数/单注/小计+合计）：${
        Number(g.debug_order_reply ?? 0) !== 0 ? '开' : '关'
      }`
    );
    lines.push(
      `规则/下单未命中调试（群主指令 调试未命中开/关；未命中全局规则时附规则列表与疑似下单排查；有规则命中时不附）：${
        Number(g.debug_rule_miss_reply ?? 0) !== 0 ? '开' : '关'
      }`
    );
    lines.push(
      `玩法权限：${
        Number(g.strict_play_routes ?? 0) === 1
          ? '卡密限流（仅已「开启」的玩法可下单；发「玩法」查看）'
          : '全玩法（与后台全部全局路由一致）'
      }`
    );
  }
  lines.push('--------');
  lines.push('全局默认下单（app_settings，全群共用）：');
  const gw = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_guide_word'`).get();
  const cw = db.prepare(`SELECT value FROM app_settings WHERE key = 'default_order_category_word'`).get();
  lines.push(`默认渠道词：${String(gw?.value || '').trim() || '（未配置）'}`);
  lines.push(`默认玩法：${String(cw?.value || '').trim() || '（未配置）'}`);
  lines.push(
    '（未写渠道/玩法时用上述默认；群主可发：默认新澳门特、设置默认新澳门、默认特、查默认；管理台侧栏「下单默认」可改。）'
  );
  lines.push('--------');
  lines.push(
    '渠道下单到期（与报表底栏同源）：群主可发「查渠道到期」「渠道到期 渠道 YYYY-MM-DD」；后台可维护 app_settings.order_guide_expires_json'
  );
  lines.push('--------');
  lines.push('玩法费率/水/连肖连码 JSON 等见「赔率表」。');
  return lines.join('\n');
}

function buildListPlayModesReply(db, wxGroupId) {
  if (!groupUsesStrictPlayRoutes(db, wxGroupId)) {
    const rows = listActiveCmdRoutes(db);
    const byG = new Map();
    for (const r of rows) {
      const g = String(r.guide_word || '').trim();
      const c = String(r.category_word || '').trim();
      if (!g || !c) continue;
      if (!byG.has(g)) byG.set(g, []);
      byG.get(g).push(c);
    }
    const lines = ['【玩法一览】本群为全玩法模式（非卡密限流绑群）。'];
    for (const [g, cats] of [...byG.entries()].sort((a, b) => a[0].localeCompare(b[0], 'zh-CN'))) {
      const u = [...new Set(cats)].sort((a, b) => a.localeCompare(b, 'zh-CN'));
      lines.push(`${g}：${u.join('、')}`);
    }
    return lines.join('\n');
  }
  let en;
  try {
    en = db
      .prepare(
        `SELECT guide_word, category_word FROM wx_group_route_enables WHERE wx_group_id = ? AND is_enabled = 1`
      )
      .all(wxGroupId);
  } catch {
    en = [];
  }
  if (!en.length) return '【本群已开玩法】暂无。群主可用「开启+渠道+玩法」逐项打开（卡密新绑群默认仅新澳门·特）。';
  const lines = ['【本群已开玩法】卡密绑群为限流模式：'];
  const byG = new Map();
  for (const r of en) {
    const g = String(r.guide_word || '').trim();
    const c = String(r.category_word || '').trim();
    if (!byG.has(g)) byG.set(g, []);
    byG.get(g).push(c);
  }
  for (const [g, cats] of [...byG.entries()].sort((a, b) => a[0].localeCompare(b[0], 'zh-CN'))) {
    lines.push(`${g}：${cats.sort((a, b) => a.localeCompare(b, 'zh-CN')).join('、')}`);
  }
  lines.push('查询单渠道：查+渠道名+玩法。');
  return lines.join('\n');
}

/**
 * 群内：查询群配置；群内/私聊：赔率表（全局类型变量）。
 */
function maybeHandleGroupInfoReadCommands(db, wxGroupId, senderWxid, content) {
  void senderWxid;
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  const compact = raw.replace(/\s+/g, '');
  if (!compact) return null;
  const altOdds = instructionAltPattern(db, 'odds_table');
  const altPlay = instructionAltPattern(db, 'list_play_modes');
  const altQgc = instructionAltPattern(db, 'query_group_config');
  if (altOdds && new RegExp(`^(?:${altOdds})$`, 'u').test(compact)) {
    return { guideTag: '赔率表', replyText: buildOddsTableReply(db) };
  }
  if (altPlay && new RegExp(`^(?:${altPlay})$`, 'u').test(compact)) {
    if (!wxGroupId) {
      return { guideTag: '查玩法', replyText: '请在群内发送「玩法」查看本群可用玩法。' };
    }
    return { guideTag: '查玩法', replyText: buildListPlayModesReply(db, wxGroupId) };
  }
  if (altQgc && new RegExp(`^(?:${altQgc})$`, 'u').test(compact)) {
    if (!wxGroupId) {
      return { guideTag: '查询群配置', replyText: '请在群内发送「查询群配置」查看本群资料。' };
    }
    return { guideTag: '查询群配置', replyText: buildQueryGroupConfigReply(db, wxGroupId) };
  }
  return null;
}

function safeJsonParseObjectForVars(s) {
  try {
    const o = JSON.parse(String(s || 'null'));
    return o && typeof o === 'object' && !Array.isArray(o) ? o : {};
  } catch {
    return {};
  }
}

function deepMergeObjects(a, b) {
  const out = { ...a };
  for (const k of Object.keys(b || {})) {
    const bv = b[k];
    const av = out[k];
    if (
      bv != null &&
      typeof bv === 'object' &&
      !Array.isArray(bv) &&
      av != null &&
      typeof av === 'object' &&
      !Array.isArray(av)
    ) {
      out[k] = deepMergeObjects(av, bv);
    } else {
      out[k] = bv;
    }
  }
  return out;
}

function getCmdTypeVarRowForUpsert(db, categoryWord, varName) {
  return db
    .prepare(`SELECT * FROM cmd_type_vars WHERE category_word = ? AND var_name = ?`)
    .get(String(categoryWord || '').trim(), String(varName || '').trim());
}

function upsertCmdTypeVarNumber(db, categoryWord, varName, value) {
  const cat = String(categoryWord || '').trim();
  const vn = String(varName || '').trim();
  const v = Number(value);
  if (!cat || !vn || !Number.isFinite(v)) return;
  const row = getCmdTypeVarRowForUpsert(db, cat, vn);
  if (row) {
    db.prepare(
      `UPDATE cmd_type_vars SET default_value_number = ?, var_type = 'number', default_value_text = NULL, updated_at = datetime('now')
       WHERE category_word = ? AND var_name = ?`
    ).run(v, cat, vn);
  } else {
    db.prepare(
      `INSERT INTO cmd_type_vars (category_word, var_name, var_type, default_value_number, default_value_text, updated_at)
       VALUES (?, ?, 'number', ?, NULL, datetime('now'))`
    ).run(cat, vn, v);
  }
}

function upsertCmdTypeVarText(db, categoryWord, varName, textVal) {
  const cat = String(categoryWord || '').trim();
  const vn = String(varName || '').trim();
  const t = String(textVal ?? '');
  if (!cat || !vn) return;
  const row = getCmdTypeVarRowForUpsert(db, cat, vn);
  if (row) {
    db.prepare(
      `UPDATE cmd_type_vars SET default_value_text = ?, var_type = 'text', updated_at = datetime('now')
       WHERE category_word = ? AND var_name = ?`
    ).run(t, cat, vn);
  } else {
    db.prepare(
      `INSERT INTO cmd_type_vars (category_word, var_name, var_type, default_value_number, default_value_text, updated_at)
       VALUES (?, ?, 'text', NULL, ?, datetime('now'))`
    ).run(cat, vn, t);
  }
}

function buildGroupAdminLinePrefixRe(db) {
  const marks = listInstructionAliasPhrases(db, 'group_config_mark');
  const setVars = listInstructionAliasPhrases(db, 'set_var');
  const parts = [...marks, ...setVars];
  const alt = parts.map(escapeRegExp).join('|');
  if (!alt) return /$^/u;
  return new RegExp(
    `^(?:${alt})\\s+(.+?)\\s+(费率|水|特费率)\\s+([\\d.]+)\\s*$`,
    'u'
  );
}

/** 群配置多行模板：玩法费率/水/连肖连码（与 tryApplyGroupConfigBulk 解析一致） */
const GROUP_CONFIG_BULK_CAT_RATE_WATER_RE =
  /^(平尾0尾|平特马|平特|平尾|单双|特肖马|特肖)费率([\d.]+)水([\d.]+)$/u;

function isGroupConfigBulkTemplateLine(line) {
  const l = String(line || '').trim();
  if (!l) return false;
  if (/^特费率[\d.]+\s*水[\d.]+$/u.test(l)) return true;
  if (GROUP_CONFIG_BULK_CAT_RATE_WATER_RE.test(l)) return true;
  if (/^连肖水([\d.]+)$/u.test(l)) return true;
  if (/^连码水([\d.]+)$/u.test(l)) return true;
  if (/^半波费率\s*([\d.]+)$/u.test(l)) return true;
  if (/^波段费率\s*([\d.]+)$/u.test(l)) return true;
  if (/^二连带马([\d.]+)不带([\d.]+)$/u.test(l)) return true;
  if (/^三连带马([\d.]+)不带([\d.]+)$/u.test(l)) return true;
  if (/^四连带马([\d.]+)不带([\d.]+)$/u.test(l)) return true;
  if (/^五连带马([\d.]+)不带([\d.]+)$/u.test(l)) return true;
  if (/^二中二(\d+)三中三(\d+)$/u.test(l)) return true;
  if (/^三中二(\d+)中三(\d+)$/u.test(l)) return true;
  return false;
}

/** 从任意文本中截取：自第一行「特费率…水…」起连续配置行（空行跳过，遇非配置行终止；前面可有大段无关内容） */
function extractContiguousGroupConfigBlockFromText(raw) {
  const t0 = String(raw || '').replace(/\r\n/g, '\n').trim();
  if (!t0) return null;
  const allLines = t0.split('\n').map((l) => l.trim());
  const anchorRe = /^特费率[\d.]+\s*水[\d.]+$/u;
  const anchorIdx = allLines.findIndex((l) => anchorRe.test(l));
  if (anchorIdx < 0) return null;
  const out = [];
  for (let i = anchorIdx; i < allLines.length; i++) {
    const l = allLines[i];
    if (!l) continue;
    if (isGroupConfigBulkTemplateLine(l)) out.push(l);
    else break;
  }
  return out.length > 0 ? out.join('\n') : null;
}

/** 群配置可在开头（可无空格直接接内容）或整段末尾；设变量仍仅前置单行。 */
function extractGroupConfigBulkBody(db, rawText) {
  const text = String(rawText || '').replace(/\r\n/g, '\n').trim();
  for (const mark of listInstructionAliasPhrases(db, 'group_config_mark')) {
    if (text.startsWith(mark)) {
      return text.slice(mark.length).replace(/^\s+/u, '').trim();
    }
    if (text.endsWith(mark)) {
      return text.slice(0, -mark.length).replace(/\s+$/u, '').trim();
    }
  }
  return null;
}

/** 去掉「群配置」等标记后的正文；或从全文截取「特费率…」起的连续配置块（允许前后噪音） */
function resolveGroupConfigBulkBody(db, rawText) {
  const textNorm = String(rawText || '').replace(/\r\n/g, '\n').trim();
  const fromMark = extractGroupConfigBulkBody(db, rawText);
  if (fromMark != null) {
    if (!String(fromMark).trim()) return '';
    const cut = extractContiguousGroupConfigBlockFromText(fromMark);
    if (cut) return cut;
  }
  return extractContiguousGroupConfigBlockFromText(textNorm);
}

/** 群配置关键词触发的可复制模板：数字来自全局类型变量（与赔率表一致） */
function buildGroupConfigKeywordTemplateReply(db) {
  const numOr = (v, fb = '?') => {
    if (v == null || v === '') return fb;
    const x = Number(v);
    return Number.isFinite(x) ? String(x) : fb;
  };
  const teR = getCmdTypeVarNumberForCategory(db, '特', ['特费率', '固定费率']);
  const teW = getCmdTypeVarNumberForCategory(db, '特', ['水']);
  const rwFull = (cat) => {
    const r = getCmdTypeVarNumberForCategory(db, cat, ['费率']);
    const w = getCmdTypeVarNumberForCategory(db, cat, ['水']);
    return `${cat}费率${numOr(r)}水${numOr(w)}`;
  };
  const rwRateOnly = (cat) => {
    const r = getCmdTypeVarNumberForCategory(db, cat, ['费率']);
    return `${cat}费率${numOr(r)}`;
  };

  const lxRow = db
    .prepare(`SELECT default_value_text FROM cmd_type_vars WHERE category_word = '连肖' AND var_name = '连肖赔率' LIMIT 1`)
    .get();
  const lxO = safeJsonParseObjectForVars(lxRow?.default_value_text || '{}');
  const lxWater = getCmdTypeVarNumberForCategory(db, '连肖', ['水']);
  const lxPairLine = (jsonKey, digitHan) => {
    const inner = lxO[jsonKey] || {};
    const dm = inner['带马'];
    const bd = inner['不带'];
    return `${digitHan}连带马${numOr(dm)}不带${numOr(bd)}`;
  };

  const lmRow = db
    .prepare(`SELECT default_value_text FROM cmd_type_vars WHERE category_word = '连码' AND var_name = '连码赔率' LIMIT 1`)
    .get();
  const lmO = safeJsonParseObjectForVars(lmRow?.default_value_text || '{}');
  const lmWater = getCmdTypeVarNumberForCategory(db, '连码', ['水']);

  const lines = [
    '复制下方内容修改后发送',
    '',
    `特费率${numOr(teR)}水${numOr(teW)}`,
    rwFull('平特'),
    rwFull('平特马'),
    rwFull('平尾'),
    rwFull('平尾0尾'),
    rwFull('单双'),
    rwFull('特肖'),
    rwFull('特肖马'),
    rwRateOnly('半波'),
    rwRateOnly('波段'),
    `连肖水${numOr(lxWater)}`,
    lxPairLine('二联', '二'),
    lxPairLine('三联', '三'),
    lxPairLine('四联', '四'),
    lxPairLine('五联', '五'),
    `连码水${numOr(lmWater)}`,
    `二中二${numOr(lmO['二中二'])}三中三${numOr(lmO['三中三'])}`,
    `三中二${numOr(lmO['三中二'])}中三${numOr(lmO['中三'])}`,
  ];
  return lines.join('\n');
}


/**
 * 多行块：群配置 + 各行参数；可接在「群配置」后不换行，也可把「群配置」放在整段末尾。
 */
function tryApplyGroupConfigBulk(db, wxGroupId, senderWxid, rawText, { mutate = true } = {}) {
  const text = String(rawText || '').replace(/\r\n/g, '\n').trim();
  const body = resolveGroupConfigBulkBody(db, text);
  if (body == null) return null;

  const singleLineAdmin = buildGroupAdminLinePrefixRe(db).test(text);
  if (singleLineAdmin) return null;

  if (!wxGroupId || !senderWxid) return null;

  if (!body) {
    return {
      ok: true,
      replyText: buildGroupConfigKeywordTemplateReply(db),
    };
  }

  const lines = body
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
  const applied = [];
  const errors = [];
  let 连肖JsonMerge = {};
  let 连码JsonMerge = {};

  const catRateWaterRe = GROUP_CONFIG_BULK_CAT_RATE_WATER_RE;

  for (const line of lines) {
    let m;
    if ((m = line.match(/^特费率([\d.]+)水([\d.]+)$/u))) {
      applied.push(`特 特费率=${m[1]} 水=${m[2]}`);
      if (mutate) {
        upsertCmdTypeVarNumber(db, '特', '特费率', m[1]);
        upsertCmdTypeVarNumber(db, '特', '固定费率', m[1]);
        upsertCmdTypeVarNumber(db, '特', '水', m[2]);
      }
      continue;
    }
    if ((m = line.match(catRateWaterRe))) {
      const cat = m[1];
      applied.push(`${cat} 费率=${m[2]} 水=${m[3]}`);
      if (mutate) {
        upsertCmdTypeVarNumber(db, cat, '费率', m[2]);
        upsertCmdTypeVarNumber(db, cat, '水', m[3]);
      }
      continue;
    }
    if ((m = line.match(/^连肖水([\d.]+)$/u))) {
      applied.push(`连肖 水=${m[1]}`);
      if (mutate) upsertCmdTypeVarNumber(db, '连肖', '水', m[1]);
      continue;
    }
    if ((m = line.match(/^连码水([\d.]+)$/u))) {
      applied.push(`连码 水=${m[1]}`);
      if (mutate) upsertCmdTypeVarNumber(db, '连码', '水', m[1]);
      continue;
    }
    if ((m = line.match(/^半波费率\s*([\d.]+)$/u))) {
      applied.push(`半波 费率=${m[1]}`);
      if (mutate) upsertCmdTypeVarNumber(db, '半波', '费率', m[1]);
      continue;
    }
    if ((m = line.match(/^波段费率\s*([\d.]+)$/u))) {
      applied.push(`波段 费率=${m[1]}`);
      if (mutate) upsertCmdTypeVarNumber(db, '波段', '费率', m[1]);
      continue;
    }
    if ((m = line.match(/^二连带马([\d.]+)不带([\d.]+)$/u))) {
      连肖JsonMerge = deepMergeObjects(连肖JsonMerge, {
        二联: { 带马: Number(m[1]), 不带: Number(m[2]) },
      });
      applied.push(`连肖 二联 带马(当年肖)${m[1]} 不带${m[2]}`);
      continue;
    }
    if ((m = line.match(/^三连带马([\d.]+)不带([\d.]+)$/u))) {
      连肖JsonMerge = deepMergeObjects(连肖JsonMerge, {
        三联: { 带马: Number(m[1]), 不带: Number(m[2]) },
      });
      applied.push(`连肖 三联 带马(当年肖)${m[1]} 不带${m[2]}`);
      continue;
    }
    if ((m = line.match(/^四连带马([\d.]+)不带([\d.]+)$/u))) {
      连肖JsonMerge = deepMergeObjects(连肖JsonMerge, {
        四联: { 带马: Number(m[1]), 不带: Number(m[2]) },
      });
      applied.push(`连肖 四联 带马(当年肖)${m[1]} 不带${m[2]}`);
      continue;
    }
    if ((m = line.match(/^五连带马([\d.]+)不带([\d.]+)$/u))) {
      连肖JsonMerge = deepMergeObjects(连肖JsonMerge, {
        五联: { 带马: Number(m[1]), 不带: Number(m[2]) },
      });
      applied.push(`连肖 五联 带马(当年肖)${m[1]} 不带${m[2]}`);
      continue;
    }
    if ((m = line.match(/^二中二(\d+)三中三(\d+)$/u))) {
      连码JsonMerge = deepMergeObjects(连码JsonMerge, { 二中二: Number(m[1]), 三中三: Number(m[2]) });
      applied.push(`连码 二中二=${m[1]} 三中三=${m[2]}`);
      continue;
    }
    if ((m = line.match(/^三中二(\d+)中三(\d+)$/u))) {
      连码JsonMerge = deepMergeObjects(连码JsonMerge, { 三中二: Number(m[1]), 中三: Number(m[2]) });
      applied.push(`连码 三中二=${m[1]} 中三=${m[2]}`);
      continue;
    }
    errors.push(line);
  }

  if (Object.keys(连肖JsonMerge).length > 0) {
    if (mutate) {
      const row = getCmdTypeVarRowForUpsert(db, '连肖', '连肖赔率');
      const base = row?.default_value_text ? safeJsonParseObjectForVars(row.default_value_text) : {};
      const next = deepMergeObjects(base, 连肖JsonMerge);
      upsertCmdTypeVarText(db, '连肖', '连肖赔率', JSON.stringify(next));
    }
  }
  if (Object.keys(连码JsonMerge).length > 0) {
    if (mutate) {
      const row = getCmdTypeVarRowForUpsert(db, '连码', '连码赔率');
      const base = row?.default_value_text ? safeJsonParseObjectForVars(row.default_value_text) : {};
      const next = deepMergeObjects(base, 连码JsonMerge);
      upsertCmdTypeVarText(db, '连码', '连码赔率', JSON.stringify(next));
    }
  }

  if (errors.length > 0 && applied.length === 0 && Object.keys(连肖JsonMerge).length === 0 && Object.keys(连码JsonMerge).length === 0) {
    return {
      ok: true,
      replyText: `未能识别配置行：\n${errors.slice(0, 6).join('\n')}${errors.length > 6 ? '\n…' : ''}`,
    };
  }

  if (!mutate && applied.length > 0) {
    const head = '[试算] 将更新';
    const parts = [head, applied.length ? applied.join('；') : '', errors.length ? `未识别行（将跳过）：${errors.join(' | ')}` : '']
      .filter(Boolean)
      .join('\n');
    return { ok: true, replyText: parts };
  }

  if (mutate && applied.length > 0) {
    const tpl = buildGroupConfigKeywordTemplateReply(db);
    if (errors.length === 0) {
      return { ok: true, replyText: `已更新。\n\n${tpl}` };
    }
    return {
      ok: true,
      replyText: `已部分更新（未识别行已跳过）。\n\n${tpl}\n\n未识别行：${errors.join(' | ')}`,
    };
  }

  return { ok: true, replyText: buildGroupConfigKeywordTemplateReply(db) };
}

/**
 * 群主（群管理 is_owner）：群内修改玩法类型变量。
 * 支持单行：群配置/设变量 分类 费率|水|特费率 数字
 * 支持多行块：群配置 + 各行（可无换行；群配置可置顶或置底）。无权限时静默不回复。
 */
function maybeHandleGroupAdminTypeVarSet(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  const text = stripWeChatAtPrefix(String(content || '').trim(), db).replace(/\r\n/g, '\n').trim();

  const m = text.match(buildGroupAdminLinePrefixRe(db));
  if (m) {
    if (!wxGroupId || !senderWxid) return null;
    const cat = String(m[1] || '').trim();
    let varName = String(m[2] || '').trim();
    if (varName === '费率' && cat === '特') varName = '特费率';
    const val = Number(m[3]);
    if (!Number.isFinite(val)) {
      return { ok: true, replyText: '数值无效。' };
    }
    const row = db.prepare(`SELECT id FROM cmd_type_vars WHERE category_word = ? AND var_name = ?`).get(cat, varName);
    if (!row) {
      if (mutate) {
        upsertCmdTypeVarNumber(db, cat, varName, val);
        return { ok: true, replyText: `已新增并更新：${cat} ${varName}=${val}` };
      }
      return { ok: true, replyText: `[试算] 将新增 ${cat} ${varName}=${val}` };
    }
    if (!mutate) {
      return { ok: true, replyText: `[试算] 将更新 ${cat} ${varName}=${val}` };
    }
    db.prepare(
      `UPDATE cmd_type_vars SET default_value_number = ?, var_type = 'number', default_value_text = NULL, updated_at = datetime('now')
       WHERE category_word = ? AND var_name = ?`
    ).run(val, cat, varName);
    return { ok: true, replyText: `已更新：${cat} ${varName}=${val}` };
  }

  const bulk = tryApplyGroupConfigBulk(db, wxGroupId, senderWxid, text, { mutate });
  if (bulk && bulk.replyText) return bulk;

  return null;
}

/** 清空/清零：清空本群共用订单表（不按下单人区分）。 */
function maybeHandleClearOrderCommand(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  const text = stripWeChatAtPrefix(String(content || '').trim(), db).trim();
  const alt = instructionAltPattern(db, 'clear_order');
  if (!alt || !new RegExp(`^(?:${alt})$`, 'u').test(text)) return null;
  if (!wxGroupId || !senderWxid) {
    return { ok: true, replyText: '当前上下文缺少群或用户信息，无法清空订单' };
  }
  const countRow = db.prepare(`SELECT COUNT(*) AS c FROM cmd_orders WHERE wx_group_id = ?`).get(wxGroupId);
  const c = Number(countRow?.c || 0);
  if (!mutate) {
    return { ok: true, replyText: `试算模式：将清空本群全部订单（共 ${c} 条）` };
  }
  if (c > 0) db.prepare(`DELETE FROM cmd_orders WHERE wx_group_id = ?`).run(wxGroupId);
  return {
    ok: true,
    replyText: c > 0 ? '[强]重置成功,当前记录为空' : '当前本群暂无订单',
  };
}

function parseShipmentNumbers(content) {
  const text = String(content || '').trim();
  if (!/^发货/.test(text)) return null;
  const nums = (text.match(/\d+/g) || []).map((x) => Number(x)).filter((x) => Number.isInteger(x));
  if (nums.length !== 7) {
    return { error: '发货指令需提供7个数字（前6平，最后1特）' };
  }
  if (nums.some((x) => x < 1 || x > 49)) {
    return { error: '发货数字范围应为 1-49' };
  }
  return {
    normal: nums.slice(0, 6),
    special: nums[6],
    raw: nums,
  };
}

function getCurrentSettlementScopes(db, wxGroupId) {
  if (!wxGroupId) return [];
  return db
    .prepare(
      `SELECT guide_word, category_word, MAX(settlement_date) AS settlement_date
       FROM cmd_orders
       WHERE wx_group_id = ?
         AND ${CMD_ORDERS_BET_ONLY}
       GROUP BY guide_word, category_word`
    )
    .all(wxGroupId);
}

function getCategoryPayoutMultiplier(db, categoryWord, useTeMaBall) {
  const cat = String(categoryWord || '').trim();
  if (useTeMaBall || cat === '特') {
    let row = db
      .prepare(`SELECT default_value_number FROM cmd_type_vars WHERE category_word = '特' AND var_name = '特费率' LIMIT 1`)
      .get();
    if (!row) {
      row = db
        .prepare(`SELECT default_value_number FROM cmd_type_vars WHERE category_word = '特' AND var_name = '固定费率' LIMIT 1`)
        .get();
    }
    const n = Number(row?.default_value_number ?? 47);
    return Number.isFinite(n) && n > 0 ? n : 47;
  }
  const row = db
    .prepare(`SELECT default_value_number FROM cmd_type_vars WHERE category_word = ? AND var_name = '费率' LIMIT 1`)
    .get(cat);
  const n = Number(row?.default_value_number ?? 1);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

/** 结单日期 YYYY-MM-DD → 农历生肖映射用公历年 */
function settlementYearFromDateYmd(ymd) {
  const m = String(ymd || '').match(/^(\d{4})-/);
  return m ? Number(m[1]) : new Date().getFullYear();
}

function buildDrawBallSet(parsed) {
  return new Set([...parsed.normal, parsed.special]);
}

function zodiacAppearsInDraw(drawSet, zodiac, year) {
  const z = normalizeZodiacHanChar(String(zodiac || '').trim());
  if (!z || !ZODIAC_ORDER.includes(z)) return false;
  for (const b of drawSet) {
    if (zodiacOfBallForSettlementYear(b, year) === z) return true;
  }
  return false;
}

function parseAllZodiacsFromTargetLabel(targetLabel) {
  const s = String(targetLabel || '').trim();
  if (!s) return [];
  const chunks = s.split(/[；;]+/).map((x) => x.trim()).filter(Boolean);
  const parts = chunks.length > 0 ? chunks : [s];
  const out = [];
  for (const p of parts) out.push(...parseZodiacTokens(p));
  return out;
}

/**
 * 连肖赔率 JSON（cmd_type_vars「连肖赔率」）：二联～五联，每联下「带马」「不带」两档。
 * 「带马」= 所选生肖中含结单公历年生肖（当年肖）；「不带」= 不含当年肖。键名沿用历史写法。
 */
function getLianXiaoJsonRate(db, zodiacCount, includesSettlementYearZodiac) {
  const mapN = { 2: '二联', 3: '三联', 4: '四联', 5: '五联' };
  const gk = mapN[zodiacCount];
  if (!gk) return getCategoryPayoutMultiplier(db, '连肖', false);
  const row = db
    .prepare(`SELECT default_value_text FROM cmd_type_vars WHERE category_word = '连肖' AND var_name = '连肖赔率' LIMIT 1`)
    .get();
  const o = safeJsonParseObjectForVars(row?.default_value_text || '{}');
  const inner = o[gk];
  if (!inner || typeof inner !== 'object') return getCategoryPayoutMultiplier(db, '连肖', false);
  const sub = includesSettlementYearZodiac ? '带马' : '不带';
  const r = Number(inner[sub]);
  return Number.isFinite(r) && r > 0 ? r : getCategoryPayoutMultiplier(db, '连肖', false);
}

function getLianMaJsonRates(db) {
  const row = db
    .prepare(`SELECT default_value_text FROM cmd_type_vars WHERE category_word = '连码' AND var_name = '连码赔率' LIMIT 1`)
    .get();
  const o = safeJsonParseObjectForVars(row?.default_value_text || '{}');
  return {
    er: Number(o.二中二),
    sanSan: Number(o.三中三),
    sanEr: Number(o.三中二),
    zhongSan: Number(o.中三),
  };
}

function resolveLianMaHitRate(rates, pickN, hitN) {
  if (pickN === 2 && hitN === 2 && Number.isFinite(rates.er) && rates.er > 0) return rates.er;
  if (pickN === 3) {
    if (hitN === 3) {
      if (Number.isFinite(rates.sanSan) && rates.sanSan > 0) return rates.sanSan;
      if (Number.isFinite(rates.zhongSan) && rates.zhongSan > 0) return rates.zhongSan;
    }
    if (hitN === 2 && Number.isFinite(rates.sanEr) && rates.sanEr > 0) return rates.sanEr;
  }
  return 0;
}

/** 发货/开奖：单条注单是否命中（前 6 + 特码共 7 个开奖号） */
function orderRowMatchesDrawHit(row, categoryWord, year, drawSet, parsed) {
  const cat = String(categoryWord || '').trim();
  const item = Number(row.item_value);
  const sp = Number(parsed.special);
  if (!Number.isFinite(sp)) return false;
  if (cat === '特肖' || cat === '特肖马') {
    const betZ = zodiacFromTeXiaoItemSlot(item);
    if (betZ) {
      return zodiacOfBallForSettlementYear(sp, year) === betZ;
    }
    return Number.isFinite(item) && item === sp;
  }
  if (cat === '特' || cat === '半波' || cat === '波段' || cat === '合单双') {
    return Number.isFinite(item) && item === sp;
  }
  if (cat === '平特' || cat === '平特马' || cat === '平尾' || cat === '平尾0尾') {
    return Number.isFinite(item) && drawSet.has(item);
  }
  if (cat === '单双') {
    if (!Number.isFinite(item)) return false;
    return Math.abs(item) % 2 === Math.abs(sp) % 2;
  }
  return Number.isFinite(item) && drawSet.has(item);
}

/** 命中后应用的赔率倍率（平特：马年「马」球号用平特马费率，否则平特费率） */
function getPayoutMultiplierForOrderRow(db, row, settlementYear) {
  const cat = String(row.category_word || '').trim();
  const item = Number(row.item_value);
  if (cat === '特') {
    return getCategoryPayoutMultiplier(db, '特', true);
  }
  if (cat === '平特') {
    if (!Number.isFinite(item)) return getCategoryPayoutMultiplier(db, '平特', false);
    const z = zodiacOfBallForSettlementYear(item, settlementYear);
    if (z === '马') {
      const r = getCmdTypeVarNumberForCategory(db, '平特马', ['费率']);
      if (r != null && Number(r) > 0) return Number(r);
      return 1.75;
    }
    return getCategoryPayoutMultiplier(db, '平特', false);
  }
  if (cat === '平特马') {
    return getCategoryPayoutMultiplier(db, '平特马', false);
  }
  if (cat === '合单双') {
    const r = getCmdTypeVarNumberForCategory(db, '合单双', ['费率']);
    if (r != null && Number(r) > 0) return Number(r);
    return getCategoryPayoutMultiplier(db, '单双', false);
  }
  return getCategoryPayoutMultiplier(db, cat, cat === '特');
}

/**
 * 开奖报表：同一条微信消息（或同一次 persist 批次）视为**一条下单**，与展单后的多行库表记录区分。
 */
function messageSubmitGroupKeyForDrawReport(r) {
  const wxid = String(r.sender_wxid || '').trim();
  const mid = String(r.wx_msg_id ?? '').trim();
  const nid = String(r.wx_new_msg_id ?? '').trim();
  const bid = String(r.order_batch_id ?? '').trim();
  if (nid || mid) return `msg\t${wxid}\t${nid}\t${mid}`;
  if (bid) return `batch\t${wxid}\t${bid}`;
  return `row\t${Number(r.id)}`;
}

/**
 * @returns {{ key: string, minId: number, sum: number, rowIds: number[] }[]}
 */
function groupRowsByMessageOrderForDrawReport(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  /** @type {Map<string, { key: string, minId: number, sum: number, rowIds: number[] }>} */
  const m = new Map();
  for (const r of rows) {
    const k = messageSubmitGroupKeyForDrawReport(r);
    const id = Number(r.id);
    const amt = Number(r.order_amount || 0);
    if (!m.has(k)) {
      m.set(k, { key: k, minId: id, sum: 0, rowIds: [] });
    }
    const g = m.get(k);
    g.rowIds.push(id);
    if (id < g.minId) g.minId = id;
    g.sum += amt;
  }
  for (const g of m.values()) {
    g.sum = Math.round(g.sum * 100) / 100;
  }
  return [...m.values()].sort((a, b) => a.minId - b.minId);
}

function buildRowIdToMessageSeqMapFromRows(rows) {
  const groups = groupRowsByMessageOrderForDrawReport(rows);
  /** @type {Map<number, number>} */
  const map = new Map();
  groups.forEach((g, idx) => {
    const seq = idx + 1;
    for (const id of g.rowIds) map.set(id, seq);
  });
  return map;
}

/** 指定渠道+结单日期内：每条「消息」一个序号 1…M（见 messageSubmitGroupKeyForDrawReport），每笔库表 id 映射到所属消息序号 */
function buildGuideSettlementMessageSeqByRowId(db, wxGroupId, guideWord, settlementDate) {
  const gw = String(guideWord || '').trim();
  const sd = String(settlementDate || '').trim();
  if (!wxGroupId || !gw || !sd) return new Map();
  const rows = db
    .prepare(
      `SELECT id, order_amount, sender_wxid, wx_msg_id, wx_new_msg_id, order_batch_id FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND settlement_date = ?
         AND ${CMD_ORDERS_BET_ONLY}
       ORDER BY id ASC`
    )
    .all(wxGroupId, gw, sd);
  return buildRowIdToMessageSeqMapFromRows(rows);
}

/**
 * 按 7 个开奖号码结算注单：奖金＝本金×玩法费率，返点＝本金×水（写入回执文案；落库 order_amount 仍为奖金）。
 * @returns {{ memberAgg: Map, hitRows: number, hitDetails: { sourceId: number, sourceRowId?: number, wxid: string, cat: string, stake: number, rate: number, bonus: number, rebate: number }[] }}
 * hitDetails[].sourceId 为该笔在渠道+结单日内的**消息**序号（1 起），与本金链「按消息」汇总一致。
 */
function applySettlementsForDrawNumbers(db, wxGroupId, scopes, parsed, batchId, hitAlgoTag, { mutate, onlyGuideWord }) {
  const drawSet = buildDrawBallSet(parsed);
  const memberAgg = new Map();
  let hitRows = 0;
  /** @type {{ sourceId: number, sourceRowId?: number, wxid: string, cat: string, stake: number, rate: number, bonus: number, rebate: number }[]} */
  const hitDetails = [];
  /** @type {Map<string, Map<number, number>>} */
  const seqMapCache = new Map();
  const displaySeqForOrderRow = (rid, gw, sd) => {
    const g = String(gw || '').trim();
    const d = String(sd || '').trim();
    const key = `${g}\t${d}`;
    let m = seqMapCache.get(key);
    if (!m) {
      m = buildGuideSettlementMessageSeqByRowId(db, wxGroupId, g, d);
      seqMapCache.set(key, m);
    }
    return m.get(Number(rid)) ?? Number(rid);
  };

  const bumpMember = (wxid, cat, stake, rate) => {
    const bonus = stake * rate;
    const water = getRebateWaterRateForCategory(db, cat);
    const rebate =
      water > 0 && Number.isFinite(stake) ? Math.round(stake * water * 10000) / 10000 : 0;
    const cur = memberAgg.get(wxid) || { bonus: 0, rebate: 0 };
    cur.bonus += bonus;
    cur.rebate += rebate;
    memberAgg.set(wxid, cur);
  };

  const insertStmt = mutate
    ? db.prepare(
        `INSERT INTO cmd_orders
        (order_batch_id, wx_group_id, sender_wxid, guide_word, category_word, target_label, algo, cmd_value, item_value, order_amount, settlement_date, content_preview, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))`
      )
    : null;

  const pushInsert = (wxid, gw, cat, sd, rate, itemVal, payout, preview) => {
    if (!insertStmt) return;
    const teLabel = cat === '特' ? '特' : '平';
    insertStmt.run(
      batchId,
      wxGroupId,
      wxid,
      gw,
      cat,
      teLabel,
      hitAlgoTag,
      rate,
      itemVal,
      payout,
      sd,
      preview
    );
  };

  for (const scope of scopes) {
    const gw = String(scope.guide_word || '').trim();
    const cat = String(scope.category_word || '').trim();
    const sd = String(scope.settlement_date || '').trim();
    if (onlyGuideWord && gw !== onlyGuideWord) continue;
    if (parsed.teMaOnly && cat !== '特' && cat !== '特肖' && cat !== '特肖马') continue;
    const year = settlementYearFromDateYmd(sd);

    const sourceRows = db
      .prepare(
        `SELECT * FROM cmd_orders
         WHERE wx_group_id = ?
           AND guide_word = ?
           AND category_word = ?
           AND settlement_date = ?
           AND ${CMD_ORDERS_BET_ONLY}`
      )
      .all(wxGroupId, gw, cat, sd);

    if (!sourceRows?.length) continue;

    if (isLianXiaoCategory(cat)) {
      const batchMap = new Map();
      for (const r of sourceRows) {
        const k = `${String(r.order_batch_id || '')}\t${String(r.sender_wxid || '').trim()}`;
        if (!batchMap.has(k)) batchMap.set(k, []);
        batchMap.get(k).push(r);
      }
      for (const [, batchRows] of batchMap) {
        const label = String(batchRows[0]?.target_label || '');
        const zs = parseAllZodiacsFromTargetLabel(label);
        if (zs.length < 2) continue;
        if (!zs.every((z) => zodiacAppearsInDraw(drawSet, z, year))) continue;
        const yearZodiac = zodiacOfYear(year);
        const includesYearZodiac = zs.some((z) => normalizeZodiacHanChar(z) === yearZodiac);
        const rate =
          cat === '平特三连'
            ? getCategoryPayoutMultiplier(db, '平特三连', false)
            : getLianXiaoJsonRate(db, zs.length, includesYearZodiac);
        const stake = batchRows.reduce((a, r) => a + Number(r.order_amount || 0), 0);
        if (!(stake > 0) || !(rate > 0)) continue;
        const wxid = String(batchRows[0].sender_wxid || '').trim();
        bumpMember(wxid, cat, stake, rate);
        hitRows += batchRows.length;
        const bonus = stake * rate;
        const water = getRebateWaterRateForCategory(db, cat);
        const rebate = water > 0 ? Math.round(stake * water * 10000) / 10000 : 0;
        const bandLabel = includesYearZodiac ? `含${yearZodiac}年肖·带马档` : `不含${yearZodiac}年肖·不带档`;
        const preview = `${hitAlgoTag} ${parsed.raw.join(',')} 连肖[${zs.join('')}] ${bandLabel} 赔率${rate} 奖金${formatAmount(bonus)} 返点${formatAmount(rebate)}`;
        hitDetails.push({
          sourceId: displaySeqForOrderRow(batchRows[0].id, gw, sd),
          sourceRowId: Number(batchRows[0].id),
          wxid,
          cat,
          stake,
          rate,
          bonus,
          rebate,
        });
      }
      continue;
    }

    if (cat === '连码') {
      const batchMap = new Map();
      for (const r of sourceRows) {
        const k = `${String(r.order_batch_id || '')}\t${String(r.sender_wxid || '').trim()}`;
        if (!batchMap.has(k)) batchMap.set(k, []);
        batchMap.get(k).push(r);
      }
      const lianMaRates = getLianMaJsonRates(db);
      for (const [, batchRows] of batchMap) {
        const items = [
          ...new Set(
            batchRows.map((r) => Number(r.item_value)).filter((n) => Number.isFinite(n) && n >= 1 && n <= 49)
          ),
        ].sort((a, b) => a - b);
        if (items.length < 2 || items.length > 3) continue;
        const hitCount = items.filter((i) => drawSet.has(i)).length;
        const rate = resolveLianMaHitRate(lianMaRates, items.length, hitCount);
        if (!(rate > 0)) continue;
        const stake = batchRows.reduce((a, r) => a + Number(r.order_amount || 0), 0);
        if (!(stake > 0)) continue;
        const wxid = String(batchRows[0].sender_wxid || '').trim();
        bumpMember(wxid, cat, stake, rate);
        hitRows += batchRows.length;
        const bonus = stake * rate;
        const water = getRebateWaterRateForCategory(db, cat);
        const rebate = water > 0 ? Math.round(stake * water * 10000) / 10000 : 0;
        const preview = `${hitAlgoTag} ${parsed.raw.join(',')} 连码 中${hitCount}/${items.length} 赔率${rate} 奖金${formatAmount(bonus)} 返点${formatAmount(rebate)}`;
        hitDetails.push({
          sourceId: displaySeqForOrderRow(batchRows[0].id, gw, sd),
          sourceRowId: Number(batchRows[0].id),
          wxid,
          cat,
          stake,
          rate,
          bonus,
          rebate,
        });
      }
      continue;
    }

    for (const r of sourceRows) {
      if (!orderRowMatchesDrawHit(r, cat, year, drawSet, parsed)) continue;
      const rate = getPayoutMultiplierForOrderRow(db, r, year);
      const stake = Number(r.order_amount || 0);
      if (!(stake > 0)) continue;
      const wxid = String(r.sender_wxid || '').trim();
      bumpMember(wxid, cat, stake, rate);
      hitRows += 1;
      const bonus = stake * rate;
      const water = getRebateWaterRateForCategory(db, cat);
      const rebate = water > 0 ? Math.round(stake * water * 10000) / 10000 : 0;
      const preview = `${hitAlgoTag} ${parsed.raw.join(',')} 赔率${rate} 奖金${formatAmount(bonus)} 返点${formatAmount(rebate)}`;
      pushInsert(wxid, gw, cat, sd, rate, Number(r.item_value || 0), bonus, preview);
      hitDetails.push({
        sourceId: displaySeqForOrderRow(r.id, gw, sd),
        sourceRowId: Number(r.id),
        wxid,
        cat,
        stake,
        rate,
        bonus,
        rebate,
      });
    }
  }

  return { memberAgg, hitRows, hitDetails };
}

/** 开奖句首渠道词 → 规范 guide_word（新澳/老澳/同义词/最长前缀） */
function resolveGuideWordFromDrawChannelPrefix(db, prefixRaw) {
  const p = String(prefixRaw || '').trim();
  if (!p) return '';
  for (const gw of listActiveChannelWordsByLength(db)) {
    if (p === gw) return gw;
    if (normalizeGuideWord(p) === normalizeGuideWord(gw)) return gw;
  }
  if (p === '新澳' || p === '新噢') return '新澳门';
  if (p === '老澳') return '老澳门';
  if (p === '港' || p === '香') return '香港';
  let g = applyLongestGuidePrefixReplacement(db, p);
  const hinted = resolveGuideHintWithSynonyms(db, g || p);
  const canon = normalizeGuideWord(String(hinted || g || '').trim());
  if (canon) {
    for (const gw of listActiveChannelWordsByLength(db)) {
      if (normalizeGuideWord(gw) === canon) return gw;
    }
    return canon;
  }
  const syns = listSynonymPairs(db, 'guide_word');
  for (const row of syns) {
    if (String(row.alias_word || '').trim() === p) {
      return String(row.canonical_word || '').trim();
    }
  }
  return '';
}

/** 渠道 +「开」+ 号码，如 新澳开13.10.42…特16 / 老澳门开1-2-4… */
function resolveDrawChannelPrefix(db, text) {
  const s = stripWeChatAtPrefix(String(text || '').trim(), db);
  if (!s || !s.includes('开')) return null;
  const m = s.match(/^(.+?)开([\s\S]+)$/u);
  if (m) {
    const guideWord = resolveGuideWordFromDrawChannelPrefix(db, m[1].trim());
    if (guideWord) return { guideWord, rest: m[2].trim() };
  }
  for (const gw of listActiveChannelWordsByLength(db)) {
    const head = `${gw}开`;
    if (s.startsWith(head)) return { guideWord: gw, rest: s.slice(head.length).trim() };
  }
  const syns = listSynonymPairs(db, 'guide_word').sort((a, b) => b.alias_word.length - a.alias_word.length);
  for (const row of syns) {
    const a = String(row.alias_word || '').trim();
    const canon = String(row.canonical_word || '').trim();
    if (!a || !canon) continue;
    const head = `${a}开`;
    if (s.startsWith(head)) return { guideWord: canon, rest: s.slice(head.length).trim() };
  }
  return null;
}

/** 是否形如开奖指令（供入站 pipeline 识别为 instruction，避免无「各」被当闲聊丢弃） */
export function matchesDrawCommandLine(text, db) {
  const s = stripWeChatAtPrefix(String(text || '').trim(), db);
  if (!s || !s.includes('开')) return false;
  if (resolveDrawChannelPrefix(db, s)) return true;
  return /^开\s*(?:0?[1-9]|[1-4][0-9])\s*号?\s*$/u.test(s);
}

/** 本群该渠道「特」当期注单的最大结单日期（仅下注行） */
function maxSettlementDateForTeBets(db, wxGroupId, guideWord) {
  const row = db
    .prepare(
      `SELECT MAX(settlement_date) AS d FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND category_word = '特' AND ${CMD_ORDERS_BET_ONLY}`
    )
    .get(wxGroupId, String(guideWord || '').trim());
  return String(row?.d || '').trim();
}

/** 群主：风控 + 金额 — 按各特码号汇总本金；若该号开出特码则庄家预测亏损（全期特收−该号派彩−全期特水）≥阈值者列出 */
function maybeHandleRiskFengkongCommand(db, wxGroupId, senderWxid, content) {
  if (!wxGroupId || !senderWxid) return null;
  const raw0 = String(content || '').trim().split(/\r?\n/)[0]?.trim();
  if (!raw0) return null;
  const idx = raw0.indexOf('风控');
  if (idx < 0) return null;
  const tail = raw0.slice(idx).trim();
  const m = tail.match(/^风控\s*(\d{1,9})\s*$/u);
  if (!m) return null;
  const threshold = Number(m[1]);
  if (!Number.isFinite(threshold) || threshold < 1) return null;
  const head = raw0.slice(0, idx).trim();
  let guideWord = '';
  if (head) {
    let g = applyLongestGuidePrefixReplacement(db, head);
    const hinted = resolveGuideHintWithSynonyms(db, g);
    if (hinted) g = hinted;
    guideWord = normalizeGuideWord(g);
  } else {
    const { guide } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
    guideWord = normalizeGuideWord(String(guide || '').trim());
  }
  if (!guideWord) {
    return { ok: true, replyText: '未指定渠道且后台未配置默认下单渠道，无法风控。可发：新澳门风控2000' };
  }
  const routesForParse = listActiveCmdRoutesForOrderParse(db, wxGroupId);
  const teOk = routesForParse.some(
    (r) => normalizeGuideWord(r.guide_word) === guideWord && String(r.category_word || '').trim() === '特'
  );
  if (!teOk) {
    return { ok: true, replyText: `渠道「${guideWord}」当前未开「特」玩法，无法特码风控。` };
  }
  if (!assertActiveGlobalOrderRoute(db, guideWord, '特')) {
    return { ok: true, replyText: `渠道「${guideWord}」无全局「特」路由，无法风控。` };
  }
  const sd = maxSettlementDateForTeBets(db, wxGroupId, guideWord);
  if (!sd) {
    return { ok: true, replyText: `渠道「${guideWord}」暂无「特」类下注记录。` };
  }
  const rows = db
    .prepare(
      `SELECT item_value AS ball, SUM(order_amount) AS stake
       FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND category_word = '特' AND settlement_date = ?
         AND ${CMD_ORDERS_BET_ONLY}
       GROUP BY item_value
       HAVING SUM(order_amount) > 0`
    )
    .all(wxGroupId, guideWord, sd);
  if (!rows?.length) {
    return { ok: true, replyText: `渠道「${guideWord}」结单 ${sd} 无特码注单。` };
  }
  const totalRow = db
    .prepare(
      `SELECT COALESCE(SUM(order_amount), 0) AS t FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND category_word = '特' AND settlement_date = ?
         AND ${CMD_ORDERS_BET_ONLY}`
    )
    .get(wxGroupId, guideWord, sd);
  const totalTe = Number(totalRow?.t || 0);
  if (!(totalTe > 0)) {
    return { ok: true, replyText: `渠道「${guideWord}」结单 ${sd} 无特码注单。` };
  }
  const teStakeRows = db
    .prepare(
      `SELECT order_amount FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND category_word = '特' AND settlement_date = ?
         AND ${CMD_ORDERS_BET_ONLY}`
    )
    .all(wxGroupId, guideWord, sd);
  let totalWaterTe = 0;
  for (const sr of teStakeRows) {
    const st = Number(sr.order_amount || 0);
    if (st <= 0) continue;
    const w = getRebateWaterRateForCategory(db, '特');
    if (w > 0) totalWaterTe += Math.round(st * w * 10000) / 10000;
  }
  totalWaterTe = Math.round(totalWaterTe * 100) / 100;
  const rate =
    getCmdTypeVarNumberForCategory(db, '特', ['特费率', '固定费率', '费率']) ?? 1;
  const items = [];
  for (const r of rows) {
    const ball = Number(r.ball);
    const stake = Number(r.stake || 0);
    if (!Number.isFinite(ball) || ball < 1 || ball > 49 || !(stake > 0)) continue;
    const pnl = computeTeHousePnlIfBallDraws(stake, rate, totalTe, totalWaterTe);
    const houseLoss = Math.round(-pnl);
    if (houseLoss >= threshold) {
      items.push({ ball, stake, lossInt: houseLoss });
    }
  }
  items.sort((a, b) => b.lossInt - a.lossInt);
  const lines = [`【特码敞口】${guideWord} · 结单 ${sd} · 阈值≥${threshold}`];
  if (items.length === 0) {
    lines.push(`无单号敞口≥${threshold}（可略调阈值或确认仍有注单）。`);
  } else {
    for (const { ball, stake, lossInt } of items) {
      const bTxt = String(Math.trunc(ball)).padStart(2, '0');
      lines.push(`${bTxt}各${Math.round(stake)} -${lossInt}`);
    }
  }
  return { ok: true, replyText: lines.join('\n') };
}

/** 特码单独开奖：开07 / 开7号（须 1–49）；与完整 7 球开奖互斥由 tryParseDrawCommand 先后尝试。 */
function extractTeMaOnlyDrawNumber(rest) {
  const s = String(rest || '')
    .trim()
    .replace(/号$/u, '')
    .trim();
  const m = s.match(/^(0?[1-9]|[1-4][0-9])$/);
  if (!m) {
    return {
      error:
        '请发齐 7 个开奖号（前 6 平码 + 1 特码，须有分隔），或仅发一个特码（例：新澳门开07 或 开07）。',
    };
  }
  const n = parseInt(m[1], 10);
  if (!(n >= 1 && n <= 49)) {
    return { error: '特码须在 1–49 之间。' };
  }
  return { normal: [], special: n, raw: [n] };
}

function extractSevenDrawNumbers(rest) {
  let s = String(rest || '').trim();
  const teTail = s.match(/^([\s\S]*?)特\s*(0?[1-9]|[1-4][0-9])\s*$/u);
  if (teTail) {
    s = `${teTail[1].trim()} ${teTail[2].trim()}`.trim();
  }
  const matches = [...s.matchAll(/\d+/g)];
  if (matches.length !== 7) {
    return { error: `开奖须 7 个号码（1–49），当前解析到 ${matches.length} 段数字。` };
  }
  for (let i = 0; i < 6; i++) {
    const end = matches[i].index + matches[i][0].length;
    const nextStart = matches[i + 1].index;
    const gap = s.slice(end, nextStart);
    if (!gap.length) return { error: '相邻号码之间须有分隔，不能连写数字。' };
    if (/^\d+$/.test(gap)) return { error: '相邻两号码之间须有非数字分隔。' };
  }
  const nums = matches.map((m) => Number(m[0]));
  if (nums.some((n) => !Number.isInteger(n) || n < 1 || n > 49)) {
    return { error: '号码须在 1–49 之间。' };
  }
  return { normal: nums.slice(0, 6), special: nums[6], raw: nums };
}

function getSettlementScopesForGuide(db, wxGroupId, guideWord) {
  const gw = String(guideWord || '').trim();
  if (!wxGroupId || !gw) return [];
  return db
    .prepare(
      `SELECT guide_word, category_word, MAX(settlement_date) AS settlement_date
       FROM cmd_orders
       WHERE wx_group_id = ? AND guide_word = ? AND ${CMD_ORDERS_BET_ONLY}
       GROUP BY guide_word, category_word`
    )
    .all(wxGroupId, gw);
}

/** 开奖：触发渠道当期结单日下，合并同群其它渠道 scope（PRD 多渠道总结「新奥+香港」） */
function getSettlementScopesForDrawCommand(db, wxGroupId, triggerGuideWord) {
  const primary = getSettlementScopesForGuide(db, wxGroupId, triggerGuideWord);
  if (!primary.length || !wxGroupId) return primary;
  const dates = primary
    .map((s) => String(s.settlement_date || '').trim())
    .filter(Boolean)
    .sort();
  const sd = dates[dates.length - 1];
  if (!sd) return primary;
  return db
    .prepare(
      `SELECT guide_word, category_word, MAX(settlement_date) AS settlement_date
       FROM cmd_orders
       WHERE wx_group_id = ? AND settlement_date = ? AND ${CMD_ORDERS_BET_ONLY}
       GROUP BY guide_word, category_word`
    )
    .all(wxGroupId, sd);
}

function reportGuideWordsFromScopes(scopes, triggerGuideWord) {
  const trigger = String(triggerGuideWord || '').trim();
  const guides = [
    ...new Set(
      (scopes || []).map((s) => String(s.guide_word || '').trim()).filter(Boolean)
    ),
  ];
  guides.sort((a, b) => {
    if (a === trigger) return -1;
    if (b === trigger) return 1;
    return a.localeCompare(b, 'zh');
  });
  return guides.length ? guides : trigger ? [trigger] : [];
}

/** 开奖回执「报表体」：特 / 特肖 / 特肖马 本金链、命中条、中特、特水、赢（可与示例版式对齐） */
const TE_DRAW_REPORT_CATS = new Set(['特', '特肖', '特肖马']);

function abbrevGuideWordForDrawReport(gw) {
  const g = String(gw || '').trim();
  if (g === '新澳门') return '新奥';
  if (g === '老澳门') return '老澳';
  return g.length > 6 ? g.slice(0, 4) : g;
}

/**
 * 开奖报表「本次下单一共N条」：按**微信消息**计（逻辑同 groupRowsByMessageOrderForDrawReport）。
 */
function countDistinctOrderSubmitMessagesForDrawReport(rows) {
  return groupRowsByMessageOrderForDrawReport(rows).length;
}

function collectTeCategoryBetRowsForDrawReport(db, wxGroupId, guideWord, scopes) {
  const gw = String(guideWord || '').trim();
  /** @type {{ id: number, order_amount: number, category_word: string, sender_wxid: string, wx_msg_id?: string, wx_new_msg_id?: string, order_batch_id?: string }[]} */
  const out = [];
  for (const scope of scopes) {
    if (String(scope.guide_word || '').trim() !== gw) continue;
    const cat = String(scope.category_word || '').trim();
    if (!TE_DRAW_REPORT_CATS.has(cat)) continue;
    const sd = String(scope.settlement_date || '').trim();
    const rows = db
      .prepare(
        `SELECT id, order_amount, category_word, sender_wxid, wx_msg_id, wx_new_msg_id, order_batch_id FROM cmd_orders
         WHERE wx_group_id = ? AND guide_word = ? AND category_word = ? AND settlement_date = ?
           AND ${CMD_ORDERS_BET_ONLY}
         ORDER BY id ASC`
      )
      .all(wxGroupId, gw, cat, sd);
    out.push(...rows);
  }
  out.sort((a, b) => Number(a.id) - Number(b.id));
  return out;
}

/** 本渠道当期全部玩法下注行（完整开奖报表本金链用） */
function collectAllCategoryBetRowsForDrawReport(db, wxGroupId, guideWord, scopes) {
  const gw = String(guideWord || '').trim();
  /** @type {{ id: number, order_amount: number, category_word: string, sender_wxid: string, wx_msg_id?: string, wx_new_msg_id?: string, order_batch_id?: string }[]} */
  const out = [];
  for (const scope of scopes) {
    if (String(scope.guide_word || '').trim() !== gw) continue;
    const cat = String(scope.category_word || '').trim();
    const sd = String(scope.settlement_date || '').trim();
    const rows = db
      .prepare(
        `SELECT id, order_amount, category_word, sender_wxid, wx_msg_id, wx_new_msg_id, order_batch_id FROM cmd_orders
         WHERE wx_group_id = ? AND guide_word = ? AND category_word = ? AND settlement_date = ?
           AND ${CMD_ORDERS_BET_ONLY}
         ORDER BY id ASC`
      )
      .all(wxGroupId, gw, cat, sd);
    out.push(...rows);
  }
  out.sort((a, b) => Number(a.id) - Number(b.id));
  return out;
}

/**
 * @param {string} drawBatchId
 * @param { { sourceId: number, sourceRowId?: number, wxid: string, cat: string, stake: number, rate: number, bonus: number, rebate: number }[] } hitDetails
 * @param {{ teMaOnly: boolean }} opts
 */
function buildDrawSettlementReportReply(
  db,
  wxGroupId,
  guideWord,
  scopes,
  drawBatchId,
  hitDetails,
  ballTxtLine,
  opts
) {
  const teMaOnly = Boolean(opts?.teMaOnly);
  const gw = String(guideWord || '').trim();
  const reportGuides =
    Array.isArray(opts?.reportGuideWords) && opts.reportGuideWords.length > 0
      ? opts.reportGuideWords.map((g) => String(g || '').trim()).filter(Boolean)
      : [gw];
  const collectForGuides = (collector) => {
    /** @type {ReturnType<typeof collectAllCategoryBetRowsForDrawReport>} */
    const merged = [];
    for (const g of reportGuides) {
      const gScopes = (scopes || []).filter((s) => String(s.guide_word || '').trim() === g);
      merged.push(...collector(db, wxGroupId, g, gScopes));
    }
    merged.sort((a, b) => Number(a.id) - Number(b.id));
    return merged;
  };
  const allRows = collectForGuides(collectAllCategoryBetRowsForDrawReport);
  const teRows = collectForGuides(collectTeCategoryBetRowsForDrawReport);
  const stakeRows = teMaOnly ? teRows : allRows;

  const stakeMsgGroups = groupRowsByMessageOrderForDrawReport(stakeRows);
  const stakes = stakeMsgGroups.map((g) => Math.round(Number(g.sum || 0) * 100) / 100);
  const rawSum = stakes.reduce((a, s) => a + s, 0);
  const deductRow = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('draw_report_stake_deduct');
  const manualDeduct = Math.max(0, Number(deductRow?.value || 0) || 0);
  const reportTotal = Math.round((rawSum - manualDeduct) * 100) / 100;

  const payoutAllRow = db
    .prepare(
      `SELECT COALESCE(SUM(order_amount), 0) AS s FROM cmd_orders WHERE order_batch_id = ? AND algo = ?`
    )
    .get(drawBatchId, '开奖命中');
  const totalPayoutAll = Math.round(Number(payoutAllRow?.s || 0) * 100) / 100;

  const hitTe = (hitDetails || []).filter((h) => TE_DRAW_REPORT_CATS.has(String(h.cat || '')));
  hitTe.sort((a, b) => Number(a.sourceRowId ?? a.sourceId) - Number(b.sourceRowId ?? b.sourceId));
  const bonuses = hitTe.map((h) => Math.round(Number(h.bonus) * 100) / 100);
  const totalPayoutTe = Math.round(bonuses.reduce((a, b) => a + b, 0) * 100) / 100;
  const hitStakeSum = Math.round(hitTe.reduce((a, h) => a + Number(h.stake || 0), 0) * 100) / 100;
  const equivRate = hitStakeSum > 0 ? totalPayoutTe / hitStakeSum : 0;
  const hitStakeDetail = hitTe.map((h) => Math.round(Number(h.stake || 0) * 100) / 100);
  const hitStakeStr = hitStakeDetail.map((x) => formatAmount(x)).join('+');

  const waterSourceRows = teMaOnly ? teRows : allRows;
  const byCat = new Map();
  for (const r of waterSourceRows) {
    const c = String(r.category_word || '').trim();
    if (!byCat.has(c)) byCat.set(c, []);
    byCat.get(c).push(r);
  }
  /** @type {{ tag: string, base: number | null, rate: number | null, rebate: number }[]} */
  const waterLines = [];
  let teStake = 0;
  let teRebate = 0;
  const teRates = new Set();
  for (const cat of TE_DRAW_REPORT_CATS) {
    const rs = byCat.get(cat);
    if (!rs) continue;
    for (const r of rs) {
      const stake = Number(r.order_amount || 0);
      const w = getRebateWaterRateForCategory(db, cat);
      teStake += stake;
      if (w > 0 && stake > 0) {
        teRebate += Math.round(stake * w * 10000) / 10000;
        teRates.add(w);
      }
    }
  }
  const teRebateR = Math.round(teRebate * 100) / 100;
  if (teStake > 0) {
    if (teRates.size === 1 && teRebateR > 0) {
      const wr = [...teRates][0];
      waterLines.push({ tag: '特水', base: Math.round(teStake * 100) / 100, rate: wr, rebate: teRebateR });
    } else if (teRebateR > 0) {
      waterLines.push({ tag: '特水', base: null, rate: null, rebate: teRebateR });
    } else {
      waterLines.push({ tag: '特水', base: teStake, rate: 0, rebate: 0 });
    }
  }
  const catSort = (a, b) => {
    const rank = (c) => {
      if (c === '连码') return 1;
      if (isLianXiaoCategoryWord(c)) return 2;
      return 50;
    };
    const d = rank(a) - rank(b);
    if (d !== 0) return d;
    return a.localeCompare(b, 'zh');
  };
  for (const cat of [...byCat.keys()].filter((c) => !TE_DRAW_REPORT_CATS.has(c)).sort(catSort)) {
    const rs = byCat.get(cat) || [];
    let stake = 0;
    let rebate = 0;
    const rates = new Set();
    for (const r of rs) {
      const s = Number(r.order_amount || 0);
      const w = getRebateWaterRateForCategory(db, cat);
      stake += s;
      if (w > 0 && s > 0) {
        rebate += Math.round(s * w * 10000) / 10000;
        rates.add(w);
      }
    }
    const rebR = Math.round(rebate * 100) / 100;
    if (stake <= 0 && rebR <= 0) continue;
    const tag = `${cat}水`;
    if (rates.size === 1 && rebR > 0) {
      waterLines.push({
        tag,
        base: Math.round(stake * 100) / 100,
        rate: [...rates][0],
        rebate: rebR,
      });
    } else if (rebR > 0) {
      waterLines.push({ tag, base: null, rate: null, rebate: rebR });
    } else {
      waterLines.push({ tag, base: Math.round(stake * 100) / 100, rate: 0, rebate: 0 });
    }
  }
  const totalWaterAll = Math.round(waterLines.reduce((a, x) => a + Number(x.rebate || 0), 0) * 100) / 100;
  const net = Math.round((reportTotal - totalPayoutAll - totalWaterAll) * 100) / 100;

  const sep = '--------------------';
  const abbr =
    reportGuides.length > 1
      ? reportGuides.map((g) => abbrevGuideWordForDrawReport(g)).join('+')
      : abbrevGuideWordForDrawReport(gw);
  /** @type {string[]} */
  const lines = [sep, abbr, sep];

  const stakeStr = stakes.map((x) => formatAmount(x)).join('+');
  const bracket1 =
    stakes.length > 0
      ? manualDeduct > 0
        ? `【${stakeStr}=总${formatAmount(rawSum)}-已减${formatAmount(manualDeduct)}=报表总${formatAmount(reportTotal)}】`
        : `【${stakeStr}=总${formatAmount(reportTotal)}】`
      : teMaOnly
        ? `【本期无特码类注单本金】`
        : `【本期无下注本金】`;
  lines.push(bracket1, sep);

  if (hitTe.length === 0) {
    lines.push('【中：无人中】', sep, '中：', sep, '水：');
  } else {
    lines.push(`【中：${hitStakeStr}=${formatAmount(hitStakeSum)}】`);
    for (const h of hitTe) {
      lines.push(`第${h.sourceId}条中${formatAmount(Math.round(Number(h.stake || 0) * 100) / 100)}`);
    }
    lines.push(sep, '中：');
    if (hitStakeSum > 0 && equivRate > 0) {
      const erDisp =
        Number.isInteger(equivRate) || Math.abs(equivRate - Math.round(equivRate)) < 1e-9
          ? formatAmount(equivRate)
          : Number(equivRate.toFixed(6)).toString();
      lines.push(`【中特：${formatAmount(hitStakeSum)}*${erDisp}=${formatAmount(totalPayoutTe)}】`);
    } else {
      lines.push(`【中特：${formatAmount(totalPayoutTe)}】`);
    }
    lines.push(sep, '水：');
  }

  for (const w of waterLines) {
    if (w.base != null && w.rate != null && Number(w.rate) > 0 && w.rebate >= 0) {
      const sp = w.tag === '连码水' ? '' : ' ';
      lines.push(`【${w.tag}${sp}${formatAmount(w.base)}*${formatAmount(w.rate)}=${formatAmount(w.rebate)}】`);
    } else if (w.rebate > 0) {
      lines.push(`【${w.tag} 合计${formatAmount(w.rebate)}】`);
    } else {
      lines.push(`【${w.tag} 0】`);
    }
  }

  lines.push(sep);
  const deductParts = [];
  if (totalPayoutAll > 0) deductParts.push(formatAmount(totalPayoutAll));
  for (const w of waterLines) {
    if (Number(w.rebate || 0) > 0) deductParts.push(formatAmount(w.rebate));
  }
  let finalBracket = `【总${formatAmount(reportTotal)}`;
  if (deductParts.length) finalBracket += `-${deductParts.join('-')}`;
  finalBracket += `=赢${formatAmount(net)}】`;
  lines.push(finalBracket, sep);
  lines.push(`开奖完成（${gw}）${ballTxtLine}`);
  lines.push('');
  lines.push(`本次下单一共${countDistinctOrderSubmitMessagesForDrawReport(stakeRows)}条`);
  return lines.join('\n');
}

function tryParseDrawCommand(db, content, wxGroupId = null) {
  const s0 = stripWeChatAtPrefix(String(content || '').trim(), db);
  if (!s0 || !s0.includes('开')) return null;

  const bareTe = s0.match(/^开\s*(0?[1-9]|[1-4][0-9])\s*号?\s*$/u);
  if (bareTe && wxGroupId) {
    const { guide } = getEffectiveDefaultOrderGuideCategory(db, wxGroupId);
    const guideWord = normalizeGuideWord(String(guide || '').trim());
    if (guideWord) {
      const n = parseInt(bareTe[1], 10);
      if (n >= 1 && n <= 49) {
        return { guideWord, normal: [], special: n, raw: [n], teMaOnly: true };
      }
    }
  }

  const ch = resolveDrawChannelPrefix(db, s0);
  if (!ch) return null;
  const seven = extractSevenDrawNumbers(ch.rest);
  if (!seven.error) {
    return { guideWord: ch.guideWord, ...seven, teMaOnly: false };
  }
  const te = extractTeMaOnlyDrawNumber(ch.rest);
  if (!te.error) {
    return { guideWord: ch.guideWord, ...te, teMaOnly: true };
  }
  return { error: te.error, guideWord: ch.guideWord };
}

function parseSettlementSummaryIntent(content, db) {
  const raw = stripWeChatAtPrefix(String(content || '').trim(), db);
  const compact = raw.replace(/\s+/g, '');
  const alt = instructionAltPattern(db, 'settlement_summary');
  if (alt && new RegExp(`^(?:${alt})$`, 'u').test(compact)) return true;
  return compact === '总结';
}

function maybeHandleSettlementSummaryCommand(db, wxGroupId, senderWxid, content) {
  if (!parseSettlementSummaryIntent(content, db)) return null;
  if (!wxGroupId) {
    return { ok: true, replyText: '请在群内发送「总结」查看开奖账务。' };
  }
  const cache = loadGroupDrawCache(db, wxGroupId);
  if (!cache) {
    return { ok: true, replyText: '暂无开奖记录，请先发送开奖指令。' };
  }
  return {
    ok: true,
    replyText: buildDrawSettlementReportReply(
      db,
      wxGroupId,
      cache.guideWord,
      cache.scopes,
      cache.drawBatchId,
      cache.hitDetails,
      cache.ballTxt,
      {
        teMaOnly: cache.teMaOnly,
        reportGuideWords:
          cache.reportGuideWords?.length > 1
            ? cache.reportGuideWords
            : reportGuideWordsFromScopes(cache.scopes, cache.guideWord),
      }
    ),
  };
}

export function maybeHandleDrawCommand(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  if (!wxGroupId) return null;
  const parsed = tryParseDrawCommand(db, content, wxGroupId);
  if (!parsed) {
    if (matchesDrawCommandLine(content, db)) {
      return {
        ok: true,
        replyText:
          '开奖格式有误。示例：新澳开13.10.42.04.46.34特16（前6平码+特码，点号/空格分隔；或 新澳开07 仅开特码）。',
      };
    }
    return null;
  }
  if (parsed.error) {
    return { ok: true, replyText: parsed.error };
  }
  const guideWord = String(parsed.guideWord || '').trim();
  const scopes = getSettlementScopesForDrawCommand(db, wxGroupId, guideWord);
  const reportGuideWords = reportGuideWordsFromScopes(scopes, guideWord);
  if (scopes.length === 0) {
    return {
      ok: true,
      replyText: `渠道「${guideWord}」当前无可开奖订单（请确认本群该渠道已有下注且未清空）。`,
    };
  }
  const drawBatchId = `draw_${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
  const { memberAgg, hitRows, hitDetails } = applySettlementsForDrawNumbers(
    db,
    wxGroupId,
    scopes,
    parsed,
    drawBatchId,
    '开奖命中',
    {
      mutate,
      onlyGuideWord: reportGuideWords.length > 1 ? null : guideWord,
    }
  );
  const ballTxt = parsed.teMaOnly
    ? `特码 ${String(parsed.special).padStart(2, '0')}（仅结算特码·特肖·特肖马）`
    : `${parsed.raw.slice(0, 6).join(',')}+特${parsed.raw[6]}`;
  const reportOpts = { reportGuideWords };
  const teRowsForReport =
    reportGuideWords.length > 1
      ? reportGuideWords.flatMap((g) => {
          const gScopes = scopes.filter((s) => String(s.guide_word || '').trim() === g);
          return collectTeCategoryBetRowsForDrawReport(db, wxGroupId, g, gScopes);
        })
      : collectTeCategoryBetRowsForDrawReport(db, wxGroupId, guideWord, scopes);
  const allRowsForReport =
    reportGuideWords.length > 1
      ? reportGuideWords.flatMap((g) => {
          const gScopes = scopes.filter((s) => String(s.guide_word || '').trim() === g);
          return collectAllCategoryBetRowsForDrawReport(db, wxGroupId, g, gScopes);
        })
      : collectAllCategoryBetRowsForDrawReport(db, wxGroupId, guideWord, scopes);
  if (parsed.teMaOnly) {
    if (hitRows === 0 && teRowsForReport.length === 0) {
      return {
        ok: true,
        replyText: `开奖完成（${guideWord}）${ballTxt}\n未命中任何订单（本期无特码类注单可展示报表）。`,
      };
    }
  } else if (hitRows === 0 && allRowsForReport.length === 0) {
    return {
      ok: true,
      replyText: `开奖完成（${guideWord}）${ballTxt}\n未命中任何订单（本期无可展示报表）。`,
    };
  }
  const canDrawReport = parsed.teMaOnly
    ? teRowsForReport.length > 0
    : allRowsForReport.length > 0;
  if (canDrawReport) {
    if (isDrawDeferSummaryEnabled(db) && mutate) {
      saveGroupDrawCache(db, wxGroupId, {
        drawBatchId,
        guideWord,
        ballTxt,
        teMaOnly: parsed.teMaOnly,
        scopes,
        hitDetails,
        reportGuideWords,
      });
      return { ok: true, replyText: '[OK]已录入，查看指令为：总结' };
    }
    return {
      ok: true,
      replyText: buildDrawSettlementReportReply(
        db,
        wxGroupId,
        guideWord,
        scopes,
        drawBatchId,
        hitDetails,
        ballTxt,
        { teMaOnly: parsed.teMaOnly, reportGuideWords }
      ),
    };
  }
  if (hitRows === 0) {
    return {
      ok: true,
      replyText: `开奖完成（${guideWord}）${ballTxt}\n未命中任何订单。`,
    };
  }
  const linesFallback = [
    `开奖完成（${guideWord}）${ballTxt}`,
    `奖金＝本金×玩法费率，返点＝本金×水；命中 ${hitRows} 条下注`,
  ];
  const sorted = Array.from(memberAgg.entries()).sort((a, b) => b[1].bonus - a[1].bonus);
  for (const [wxid, agg] of sorted) {
    const name = resolveMemberDisplayName(db, wxGroupId, wxid);
    linesFallback.push(`${name} 奖金 ${formatAmount(agg.bonus)} 返点 ${formatAmount(agg.rebate)}`);
  }
  return { ok: true, replyText: linesFallback.join('\n') };
}

function maybeHandleShipmentCommand(db, wxGroupId, senderWxid, content, { mutate = true } = {}) {
  const parsed = parseShipmentNumbers(content);
  if (!parsed) return null;
  if (parsed.error) return { ok: true, replyText: parsed.error };
  const scopes = getCurrentSettlementScopes(db, wxGroupId);
  if (scopes.length === 0) {
    return { ok: true, replyText: '当前无可发货订单' };
  }
  const shipmentBatchId = `shipment_${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
  const { memberAgg, hitRows } = applySettlementsForDrawNumbers(db, wxGroupId, scopes, parsed, shipmentBatchId, '发货命中', {
    mutate,
    onlyGuideWord: null,
  });
  if (hitRows === 0) {
    return { ok: true, replyText: `发货完成：未命中任何订单（号码 ${parsed.raw.join(',')}）` };
  }
  const lines = [
    `发货完成：${parsed.raw.join(',')}（前6平，末位特）`,
    `奖金＝本金×玩法费率，返点＝本金×水；命中 ${hitRows} 条下注`,
  ];
  const sorted = Array.from(memberAgg.entries()).sort((a, b) => b[1].bonus - a[1].bonus);
  for (const [wxid, agg] of sorted) {
    const name = resolveMemberDisplayName(db, wxGroupId, wxid);
    lines.push(`${name} 奖金 ${formatAmount(agg.bonus)} 返点 ${formatAmount(agg.rebate)}`);
  }
  return { ok: true, replyText: lines.join('\n') };
}

/**
 * 去掉微信「@ 昵称」前缀（含 \u2005 等分隔符），使「@机器人 帮助」能命中帮助类指令。
 */
export function stripWeChatAtPrefix(raw, db) {
  let s = String(raw || '')
    .replace(/^\uFEFF/g, '')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .trim();
  if (!s) return s;
  if (!s.startsWith('@')) return s;
  const helpAlt = instructionAltPattern(db, 'help');
  let guard = 0;
  while (s.startsWith('@') && guard < 8) {
    guard += 1;
    const helpMatch = helpAlt ? s.match(new RegExp(`(${helpAlt})`, 'u')) : null;
    if (helpMatch) {
      const atPos = s.indexOf('@');
      const helpPos = s.indexOf(helpMatch[0], atPos >= 0 ? atPos : 0);
      if (helpPos > atPos) {
        s = s.slice(helpPos).trim();
        break;
      }
    }
    const next = s
      .replace(
        /^@[^\n\r]+?[\s\u00a0\u2000-\u200B\u2005:：;；,，\uff1a]+/u,
        ''
      )
      .trim();
    if (next === s) break;
    s = next;
  }
  return s;
}

/** 前置逗号/句号等口语标点，避免「，蛇鼠各5」在补上默认渠道后数据段解析失败 */
function stripLeadingOrderNoise(raw) {
  let s = String(raw || '').trim();
  let prev;
  do {
    prev = s;
    s = s.replace(/^(?:买|要|下单)\s*/u, '').trim();
    s = s.replace(ORDER_NOISE_HEAD_RE, '').trim();
  } while (s !== prev);
  return s;
}

/**
 * 数据段开头「奥，」「澳，」等：整句已带渠道+类型时，口语再喊渠道会导致目标串混入「奥」无法识别生肖。
 * 长词优先（新澳门、老澳门等），循环剥多层。
 */
function stripLeadingRedundantChannelInterjection(raw) {
  let s = String(raw || '').trim();
  let prev;
  do {
    prev = s;
    s = s.replace(/^(?:新澳门|澳门|老澳门|香港|越南|奥|噢|澳)[，,。.、:：;；\s]+/u, '').trim();
  } while (s !== prev);
  return s;
}

function buildHelpReplyText({ isOwner }) {
  const lines = [
    '【帮助】',
    '下单：渠道+玩法+内容+金额，如 新澳门特牛羊各100（省略渠道/分类用默认）',
    '查单 / 查明细单（本群共用）；报表（本群汇总）；清空、清零（群管理，清全群）',
    '赔率表；查询群配置（群内）',
  ];
  if (isOwner) {
    lines.push(
      '',
      '【管理指令】',
      '水报表；清空/清零（清本群全部订单）',
      '发货+7码；开奖：渠道+开+7码 或 开+特码',
      '风控+金额；默认/设置默认+渠道(+玩法)；查默认',
      '开/关收单；调试开/关、调试未命中开/关',
      '群设置/改价；开启+渠道+玩法、查玩法',
      '续费/续期+卡密；渠道到期、结单时间、周期'
    );
  }
  return lines.join('\n');
}

function maybeHandleHelpCommand(content, { db, wxGroupId, senderWxid } = {}) {
  const text = stripWeChatAtPrefix(String(content || ''), db).trim();
  if (!matchesHelpInstruction(text, db)) return null;
  return {
    ok: true,
    replyText: buildHelpReplyText({ isOwner: Boolean(wxGroupId && senderWxid) }),
  };
}

function executeSingleConfiguredCommand(
  db,
  wxGroupId,
  content,
  {
    senderWxid = '',
    persistEnabled = true,
    wxMsgId = '',
    wxNewMsgId = '',
    declaredSegmentTotal = null,
  } = {}
) {
  let resolvedContent = String(content || '').trim();
  resolvedContent = applyLongestGuidePrefixReplacement(db, resolvedContent);
  resolvedContent = hoistTrailingCategoryAfterZodiacs(db, resolvedContent);
  resolvedContent = hoistEmbeddedGuideChannelBeforeBallsEach(db, resolvedContent, wxGroupId);
  resolvedContent = resolveOrderContentWithDefaultPrefix(db, resolvedContent, wxGroupId);
  resolvedContent = normalizeRoutePrefixWithSynonyms(db, resolvedContent);
  const routesAll = db
    .prepare(
      `SELECT * FROM cmd_routes
       WHERE is_active = 1
         AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
       ORDER BY priority DESC, id DESC`
    )
    .all();
  const allow = new Set(
    listActiveCmdRoutesForOrderParse(db, wxGroupId).map(
      (r) => `${String(r.guide_word || '').trim()}\0${String(r.category_word || '').trim()}`
    )
  );
  const routes =
    !wxGroupId || !groupUsesStrictPlayRoutes(db, wxGroupId)
      ? routesAll
      : routesAll.filter((r) =>
          allow.has(`${String(r.guide_word || '').trim()}\0${String(r.category_word || '').trim()}`)
        );
  /** 同渠道下长分类优先（先「特肖马」再「特肖」），避免「特肖马100」被当成「特肖」+「马100」 */
  const routesSorted = [...routes].sort((a, b) => {
    const pa = Number(a.priority ?? 0);
    const pb = Number(b.priority ?? 0);
    if (pb !== pa) return pb - pa;
    const ga = normalizeGuideWord(a.guide_word);
    const gb = normalizeGuideWord(b.guide_word);
    if (ga !== gb) return String(ga).localeCompare(String(gb));
    const ca = String(a.category_word || '').trim().length;
    const cb = String(b.category_word || '').trim().length;
    if (cb !== ca) return cb - ca;
    return Number(b.id ?? 0) - Number(a.id ?? 0);
  });
  for (const route of routesSorted) {
    const guide = normalizeGuideWord(route.guide_word);
    const category = String(route.category_word || '').trim();
    if (!guide || !category) continue;
    if (!resolvedContent.startsWith(guide)) continue;
    const remainAfterGuide = resolvedContent.slice(guide.length).trim();
    if (!remainAfterGuide.startsWith(category)) continue;
    if (category === '特' && /^肖/u.test(remainAfterGuide.slice(category.length))) continue;
    let dataSegment = remainAfterGuide.slice(category.length).trim();
    if (category === '特') dataSegment = stripLeadingOralMenAfterTeDataSegment(dataSegment);
    dataSegment = String(dataSegment || '').trim();
    let clauses = parseAllDataSegmentClauses(dataSegment, db, { routedGuideNorm: guide, categoryWord: category });
    if (clauses.length === 0) {
      const retry = tryParseClausesWithTrailingCategoryZodiac(db, category, dataSegment);
      if (retry && retry.length > 0) clauses = retry;
    }
    if (clauses.length === 0) continue;

    const allSetNames = db
      .prepare(
        `SELECT DISTINCT set_name FROM cmd_collections
         WHERE is_active = 1 AND wx_group_id IS NULL`
      )
      .all()
      .map((x) => x.set_name)
      .filter(Boolean);

    const formula = route.formula_name
      ? db
          .prepare('SELECT * FROM cmd_formulas WHERE formula_name = ? AND is_active = 1')
          .get(route.formula_name)
      : null;

    let mergedResultRows = [];
    const targetLabels = [];
    const itemsAcc = [];

    for (const parsed of clauses) {
      const items = resolveCommandTargetItems(db, parsed.targetRaw, allSetNames, route.category_word);
      if (items.length === 0) {
        mergedResultRows = null;
        break;
      }
      const resultsRaw = applyFormulaPipeline(formula?.pipeline_expr || 'identity|algo', {
        items,
        algo: parsed.algo,
        value: parsed.value,
        categoryWord: category,
        resolveSet: (setName) => resolveSetItems(db, setName),
        resolveVar: (varName) => {
          const row = db
            .prepare(
              `SELECT var_type, default_value_number, default_value_text
               FROM cmd_type_vars
               WHERE category_word = ? AND var_name = ?`
            )
            .get(String(route.category_word || '').trim(), String(varName || '').trim());
          if (!row) return 0;
          if (String(row.var_type || 'number') === 'text') {
            const n = Number(row.default_value_text ?? 0);
            return Number.isFinite(n) ? n : 0;
          }
          return Number(row.default_value_number ?? 0);
        },
      });
      const collapsedClause = collapseResultRows(resultsRaw);
      const tlr = String(parsed.targetRaw || '').trim();
      mergedResultRows.push(
        ...collapsedClause.map((row) => (tlr ? { ...row, targetLabel: tlr } : row))
      );
      targetLabels.push(parsed.targetRaw);
      itemsAcc.push(...items);
    }
    if (mergedResultRows == null || mergedResultRows.length === 0) continue;

    const results =
      isLianXiaoCategoryWord(category) || category === '连码'
        ? mergedResultRows
        : collapseResultRows(mergedResultRows);
    const last = clauses[clauses.length - 1];
    const payload = {
      targetLabel: targetLabels.join('；'),
      algo: last.algo,
      value: last.value,
      items: uniqueNumbers(itemsAcc),
      results,
    };
    if (!isGroupOrderTakingEnabled(db, wxGroupId)) {
      return {
        blocked: true,
        route,
        payload: { results: [] },
        replyText: '本群收单已关闭，请联系群主开启。',
      };
    }
    const cycleDeny = getOrderCycleDenyReason(db, route.guide_word);
    if (cycleDeny) {
      return {
        blocked: true,
        route,
        payload: { results: [] },
        replyText: cycleDeny,
      };
    }
    const segmentTotalErr = validateDeclaredSegmentTotalAgainstPayload(declaredSegmentTotal, {
      payload,
    });
    if (segmentTotalErr) {
      return {
        blocked: true,
        route,
        payload: { results: [] },
        replyText: segmentTotalErr,
      };
    }
    if (persistEnabled) {
      const settlementDate = computeSettlementDateYmdForGuide(db, route.guide_word);
      const orderBatchId = `${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
      persistOrderRows(db, {
        wxGroupId,
        senderWxid,
        route,
        content: resolvedContent,
        payload,
        settlementDate,
        orderBatchId,
        wxMsgId,
        wxNewMsgId,
      });
    }
    const receiptLine =
      isLianXiaoCategoryWord(category) || category === '连码'
        ? formatPlusTermsFromTotals(results.map((x) => Number(x?.value)))
        : formatPlusTermsFromTotals([sumPayloadResults(payload)]);
    return {
      route,
      payload,
      replyText: appendOrderDebugToReply(db, wxGroupId, receiptLine, null),
    };
  }
  return null;
}

/** 探测单行（经 ensureRoutedOrderLine）是否能解析出至少一条下注 */
function probeOrderLineYieldsBets(db, wxGroupId, rawLine, blockPrepend, probeOpts = {}) {
  const ln = String(rawLine || '').trim();
  if (!ln) return false;
  const routed = ensureRoutedOrderLine(db, ln, String(blockPrepend || ''), wxGroupId);
  const toRun = applyStructuralCanonicalLine(db, wxGroupId, routed);
  const r = executeSingleConfiguredCommand(db, wxGroupId, toRun, {
    senderWxid: String(probeOpts.senderWxid || ''),
    persistEnabled: false,
    wxMsgId: String(probeOpts.wxMsgId || ''),
    wxNewMsgId: String(probeOpts.wxNewMsgId || ''),
  });
  return Boolean(r?.payload?.results?.length);
}

/** 合并探测时去掉重复的「渠道+分类」前缀，避免「新澳门特…新澳门特…」粘连 */
function stitchUnparsedOrderLinesForProbe(db, wxGroupId, a, b, blockPrepend) {
  const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
  const peelOne = (line) => {
    const routed = ensureRoutedOrderLine(db, String(line || '').trim(), String(blockPrepend || ''), wxGroupId);
    const p = peelRoutePrefixFromLine(routed, routePrefixes);
    if (p) return { prefix: p.prefix, rest: String(p.rest || '').trim() };
    return { prefix: '', rest: routed.trim() };
  };
  const pa = peelOne(a);
  const pb = peelOne(b);
  if (pa.prefix && pa.prefix === pb.prefix) {
    return `${pa.prefix}${pa.rest} ${pb.rest}`.replace(/\s+/g, ' ').trim();
  }
  if (pa.prefix && !pb.prefix) {
    return `${pa.prefix}${pa.rest} ${pb.rest}`.replace(/\s+/g, ' ').trim();
  }
  if (!pa.prefix && pb.prefix) {
    return `${pb.prefix}${pa.rest} ${pa.rest}`.replace(/\s+/g, ' ').trim();
  }
  return `${a} ${b}`.trim();
}

/**
 * 分块内：若某行单独解析失败，与下一行合并后再试，直至命中或合并完（处理用户随意断行）。
 */
function mergeAdjacentUnparsedOrderLines(db, wxGroupId, rawLines, blockPrepend, probeOpts) {
  const rows = Array.isArray(rawLines) ? rawLines.map((x) => String(x || '').trim()).filter(Boolean) : [];
  if (rows.length <= 1) return rows;
  const out = [];
  let buf = '';
  for (const s of rows) {
    if (
      buf &&
      lineLooksLikeStandaloneBallEachAmountLine(s) &&
      probeOrderLineYieldsBets(db, wxGroupId, s, blockPrepend, probeOpts)
    ) {
      out.push(buf);
      out.push(s);
      buf = '';
      continue;
    }
    const cand = buf ? stitchUnparsedOrderLinesForProbe(db, wxGroupId, buf, s, blockPrepend) : s;
    if (probeOrderLineYieldsBets(db, wxGroupId, cand, blockPrepend, probeOpts)) {
      out.push(cand);
      buf = '';
    } else {
      buf = cand;
    }
  }
  if (buf) out.push(buf);
  return out.length ? out : rows;
}

export function executeConfiguredCommandImpl(db, wxGroupId, text, options = {}) {
  const senderWxid = String(options.senderWxid || '').trim();
  const persistEnabled = options.persist !== false;
  const wxMsgId = String(options.wxMsgId || '').trim();
  const wxNewMsgId = String(options.wxNewMsgId || '').trim();
  if (isWeChatInboundFileXmlQuick(text)) return null;
  const instructionText = prepareInboundInstructionText(text, db);
  const debugOriginalMessage = prepareDebugOriginalMessageText(text, db);
  if (!instructionText) return null;

  const orderQueryEarly = maybeHandleOrderQueryCommand(db, wxGroupId, senderWxid, instructionText);
  if (orderQueryEarly) {
    return {
      route: { guide_word: '查单', category_word: '' },
      payload: { results: [] },
      replyText: orderQueryEarly.replyText,
    };
  }

  const groupReportEarly = maybeHandleGroupStatisticsReport(db, wxGroupId, senderWxid, instructionText);
  if (groupReportEarly) {
    return {
      route: { guide_word: '报表', category_word: '' },
      payload: { results: [] },
      replyText: groupReportEarly.replyText,
    };
  }
  const waterReportEarly = maybeHandleWaterRebateReport(db, wxGroupId, senderWxid, instructionText);
  if (waterReportEarly) {
    return {
      route: { guide_word: '水报表', category_word: '' },
      payload: { results: [] },
      replyText: waterReportEarly.replyText,
    };
  }
  const summaryEarly = maybeHandleSettlementSummaryCommand(db, wxGroupId, senderWxid, instructionText);
  if (summaryEarly) {
    return {
      route: { guide_word: '总结', category_word: '' },
      payload: { results: [] },
      replyText: summaryEarly.replyText,
    };
  }

  const drawEarly = maybeHandleDrawCommand(db, wxGroupId, senderWxid, instructionText, {
    mutate: persistEnabled,
  });
  if (drawEarly) {
    return {
      route: { guide_word: '开奖', category_word: '' },
      payload: { results: [] },
      replyText: drawEarly.replyText,
    };
  }

  const shipmentEarly = maybeHandleShipmentCommand(db, wxGroupId, senderWxid, instructionText, {
    mutate: persistEnabled,
  });
  if (shipmentEarly) {
    return {
      route: { guide_word: '发货', category_word: '' },
      payload: { results: [] },
      replyText: shipmentEarly.replyText,
    };
  }

  let content = preprocessInboundOrderContent(db, instructionText, wxGroupId);
  if (!content && !matchesInstructionOnlyLine(instructionText, db)) return null;

  const riskFkResult = maybeHandleRiskFengkongCommand(db, wxGroupId, senderWxid, content);
  if (riskFkResult) {
    return {
      route: { guide_word: '特码敞口', category_word: '' },
      payload: { results: [] },
      replyText: riskFkResult.replyText,
    };
  }

  const ownerToggleResult = maybeHandleOwnerOrderToggle(db, wxGroupId, senderWxid, content, {
    mutate: persistEnabled,
  });
  if (ownerToggleResult) {
    return {
      route: { guide_word: '收单开关', category_word: '' },
      payload: { results: [] },
      replyText: ownerToggleResult.replyText,
    };
  }

  const debugReplyToggleResult = maybeHandleDebugOrderReplyToggle(db, wxGroupId, senderWxid, content, {
    mutate: persistEnabled,
  });
  if (debugReplyToggleResult) {
    return {
      route: { guide_word: '调试回执', category_word: '' },
      payload: { results: [] },
      replyText: debugReplyToggleResult.replyText,
    };
  }

  const debugRuleMissToggleResult = maybeHandleDebugRuleMissReplyToggle(db, wxGroupId, senderWxid, content, {
    mutate: persistEnabled,
  });
  if (debugRuleMissToggleResult) {
    return {
      route: { guide_word: '调试未命中规则', category_word: '' },
      payload: { results: [] },
      replyText: debugRuleMissToggleResult.replyText,
    };
  }

  const chaFacetResult = maybeHandleChaChannelFacetCommand(db, wxGroupId, senderWxid, content);
  if (chaFacetResult) {
    return {
      route: { guide_word: '查询渠道', category_word: '' },
      payload: { results: [] },
      replyText: chaFacetResult.replyText,
    };
  }

  const defaultOrderResult = maybeHandleDefaultOrderRouteCommand(db, wxGroupId, senderWxid, content, {
    mutate: persistEnabled,
  });
  if (defaultOrderResult) {
    return {
      route: { guide_word: '默认下单', category_word: '' },
      payload: { results: [] },
      replyText: defaultOrderResult.replyText,
    };
  }

  const channelCycleAdminResult = maybeHandleChannelCycleAdminCommand(db, wxGroupId, senderWxid, content, {
    mutate: persistEnabled,
  });
  if (channelCycleAdminResult) {
    return {
      route: { guide_word: '渠道周期', category_word: '' },
      payload: { results: [] },
      replyText: channelCycleAdminResult.replyText,
    };
  }

  const enablePlayResult = maybeHandleEnablePlayRouteCommand(db, wxGroupId, senderWxid, content, {
    mutate: persistEnabled,
  });
  if (enablePlayResult) {
    return {
      route: { guide_word: '开启玩法', category_word: '' },
      payload: { results: [] },
      replyText: enablePlayResult.replyText,
    };
  }

  const groupVarResult = maybeHandleGroupAdminTypeVarSet(db, wxGroupId, senderWxid, instructionText, {
    mutate: persistEnabled,
  });
  if (groupVarResult) {
    return {
      route: {
        guide_word: '群配置',
        category_word: '',
      },
      payload: { results: [] },
      replyText: groupVarResult.replyText,
    };
  }

  const clearResult = maybeHandleClearOrderCommand(db, wxGroupId, senderWxid, instructionText, {
    mutate: persistEnabled,
  });
  if (clearResult) {
    return {
      route: {
        guide_word: '清空订单',
        category_word: '',
      },
      payload: { results: [] },
      replyText: clearResult.replyText,
    };
  }

  const groupReadResult = maybeHandleGroupInfoReadCommands(db, wxGroupId, senderWxid, instructionText);
  if (groupReadResult) {
    return {
      route: {
        guide_word: groupReadResult.guideTag,
        category_word: '',
      },
      payload: { results: [] },
      replyText: groupReadResult.replyText,
    };
  }

  const guideExpiresResult = maybeHandleOrderGuideExpiresCommand(db, wxGroupId, senderWxid, content);
  if (guideExpiresResult) {
    return {
      route: {
        guide_word: '渠道到期',
        category_word: '',
      },
      payload: { results: [] },
      replyText: guideExpiresResult.replyText,
    };
  }

  const helpResult = maybeHandleHelpCommand(instructionText, { db, wxGroupId, senderWxid });
  if (helpResult) {
    return {
      route: {
        guide_word: '帮助',
        category_word: '',
      },
      payload: { results: [] },
      replyText: helpResult.replyText,
    };
  }

  if (!inboundTextHasOrderDigits(instructionText, db)) {
    return null;
  }

  if (inboundOrderContentLooksMalformed(instructionText)) {
    const body = String(instructionText || '').trim() || '（无正文）';
    return {
      blocked: true,
      route: { guide_word: '', category_word: '' },
      payload: { results: [] },
      replyText: `■【此消息有问题，不计入】■\n\n${body}\n\n【无法识别内容】`,
    };
  }

  const blocks = splitInstructionBlocks(content);
  if (blocks.length === 0) return null;

  const instructionLinesForDeclaredTotal = String(instructionText || '')
    .trim()
    .split(/\r?\n+/)
    .map((x) => String(x || '').trim())
    .filter(Boolean);
  let instructionLineDeclaredIdx = 0;

  const blockTotals = [];
  const lineTotals = [];
  const routeGroupSum = new Map();
  const routeGroupOrder = [];
  let mergedResults = [];
  const mergedDebugEntries = [];
  let primaryRoute = null;

  for (const blockRaw of blocks) {
    const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
    const rawLines = blockRaw
      .split(/\r?\n+/)
      .map((x) => {
        let ln = stripLeadingOrderNoise(String(x || '').trim());
        ln = stripLineLeadingChatTimestamp(ln);
        ln = stripBatchForwardMessageLinePrefix(ln);
        ln = stripTrailingInlineOrderSummary(ln);
        return stripTrailingEmbeddedAtPlusReceipt(ln);
      })
      .filter(
        (x) =>
          x &&
          !looksLikePlusOnlyReceiptLine(x) &&
          !isOrderDeclaredTotalNoiseLine(x) &&
          !looksLikeAtPlusReceiptLine(x) &&
          !isOrderSummaryFooterLine(x, routePrefixes)
      );
    const { contentLines, blockPrepend } = peelTrailingRouteOnlyLinesFromBlock(db, rawLines);
    if (contentLines.length === 0) continue;
    const mergedContentLines = mergeAdjacentUnparsedOrderLines(db, wxGroupId, contentLines, blockPrepend, {
      senderWxid,
      wxMsgId,
      wxNewMsgId,
    });
    if (wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
      for (const ln of mergedContentLines) {
        ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, ln);
      }
    }
    const routePrefixesEnabled = buildSortedRoutePrefixesForGroup(db, wxGroupId);
    const routedLines = mergedContentLines.map((ln) => ensureRoutedOrderLine(db, ln, blockPrepend, wxGroupId));
    let lines = [...routedLines];
    let first = applyLongestGuidePrefixReplacement(db, String(lines[0] || '').trim());
    first = hoistTrailingCategoryAfterZodiacs(db, first);
    first = hoistEmbeddedGuideChannelBeforeBallsEach(db, first, wxGroupId);
    if (!contentMatchesAnyRoute(db, first, wxGroupId)) {
      const globalFirst = detectLineRoutePrefix(first, buildSortedRoutePrefixes(db));
      if (globalFirst?.guide && globalFirst?.category && wxGroupId && groupUsesStrictPlayRoutes(db, wxGroupId)) {
        ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, first);
      } else {
        first = resolveOrderContentWithDefaultPrefix(db, first, wxGroupId);
      }
    }
    first = normalizeRoutePrefixWithSynonyms(db, first);
    lines[0] = first;
    const normalizedLines = mergeZodiacHeadLinesWithEachAlgo(
      mergeBallGridLinesWithAlgo(
        normalizeMultilineCommandLines(db, lines, routePrefixesEnabled, wxGroupId).filter(Boolean),
        routePrefixesEnabled,
        db
      ),
      routePrefixesEnabled,
      db
    );
    let blockSum = 0;
    let anyOk = false;
    for (let lineIdx = 0; lineIdx < normalizedLines.length; lineIdx++) {
      const rawLineForExecute0 = normalizeTeRouteSpaceBallAmountTableSameLine(
        normalizedLines[lineIdx],
        routePrefixesEnabled
      );
      const expanded = fanOutEmbeddedLianXiaoOrderLines(db, wxGroupId, rawLineForExecute0);
      for (const rawLineForExecute of expanded) {
        const declaredFromRaw = peelDeclaredSegmentTotalFromLine(
          instructionLinesForDeclaredTotal[instructionLineDeclaredIdx] || '',
          db
        );
        instructionLineDeclaredIdx += 1;
        const lineAst = buildOrderLineStructuralAst(db, wxGroupId, rawLineForExecute);
        const lineText = lineAst
          ? emitCanonicalOrderLine(lineAst) || applyStructuralCanonicalLine(db, wxGroupId, rawLineForExecute)
          : applyStructuralCanonicalLine(db, wxGroupId, rawLineForExecute);
        const orderUnits = extractOrderUnitsFromAst(lineAst);
        if (orderUnits.length) {
          appendOrderUnitLog({
            source: 'inbound',
            wxGroupId,
            rawLine: rawLineForExecute,
            units: orderUnits,
          });
        }
        ensureGlobalRoutesEnabledForStrictGroupLine(db, wxGroupId, lineText);
        const result = executeSingleConfiguredCommand(db, wxGroupId, lineText, {
          senderWxid,
          persistEnabled,
          wxMsgId,
          wxNewMsgId,
          declaredSegmentTotal: declaredFromRaw.expectedTotal,
        });
        if (isGroupDebugOrderReplyEnabled(db, wxGroupId)) {
          mergedDebugEntries.push(collectOrderDebugEntry(rawLineForExecute, result, lineAst));
        }
        if (!result) continue;
        if (result.blocked) {
          const partialSubtotal = lineTotals.reduce((a, x) => a + Number(x || 0), 0);
          const debugBlock =
            isGroupDebugOrderReplyEnabled(db, wxGroupId) && mergedDebugEntries.length
              ? buildOrderDebugReplyBlock(debugOriginalMessage, mergedDebugEntries, partialSubtotal)
              : null;
          const replyWithDebug = appendOrderDebugToReply(db, wxGroupId, result.replyText, debugBlock);
          return {
            ...result,
            replyText: replyWithDebug,
            payload: {
              ...result.payload,
              ...(debugBlock ? { debug_detail: { block: debugBlock, entries: mergedDebugEntries } } : {}),
            },
          };
        }
        const lineSum = sumPayloadResults(result.payload);
        blockSum += lineSum;
        lineTotals.push(lineSum);
        const gk = routeGroupKey(result.route);
        if (!routeGroupSum.has(gk)) {
          routeGroupSum.set(gk, 0);
          routeGroupOrder.push(gk);
        }
        routeGroupSum.set(gk, routeGroupSum.get(gk) + lineSum);
        anyOk = true;
        mergedResults = mergedResults.concat(result.payload?.results || []);
        if (!primaryRoute) primaryRoute = result.route;
      }
    }
    if (anyOk) blockTotals.push(blockSum);
  }

  const messageDebugSubtotal = lineTotals.reduce((a, x) => a + Number(x || 0), 0);
  const debugBlock =
    isGroupDebugOrderReplyEnabled(db, wxGroupId) && mergedDebugEntries.length
      ? buildOrderDebugReplyBlock(debugOriginalMessage, mergedDebugEntries, messageDebugSubtotal)
      : null;

  if (lineTotals.length === 0) {
    if (debugBlock && !isWeChatInboundFileXmlQuick(debugOriginalMessage)) {
      return {
        route: { guide_word: '下单', category_word: '' },
        payload: { results: [], debug_detail: { block: debugBlock, entries: mergedDebugEntries } },
        replyText: appendOrderDebugToReply(db, wxGroupId, '', debugBlock),
      };
    }
    return null;
  }
  const routeReplyTotals = routeGroupOrder.map((k) => Number(routeGroupSum.get(k) || 0));
  const messageTotal = Math.round(messageDebugSubtotal * 100) / 100;
  /** 同一条消息内所有玩法、所有行金额累加为一项回执（如 +500） */
  const collapsedForReply = collapseResultRows(mergedResults);
  const baseReceipt = formatPlusTermsFromTotals([messageTotal]);
  return {
    route:
      routeGroupOrder.length > 1
        ? { guide_word: '批量下单', category_word: '' }
        : primaryRoute || { guide_word: '下单', category_word: '' },
    payload: {
      results: collapsedForReply,
      block_totals: blockTotals,
      line_totals: lineTotals,
      route_group_totals: routeReplyTotals,
      ...(debugBlock ? { debug_detail: { block: debugBlock, entries: mergedDebugEntries } } : {}),
    },
    replyText: appendOrderDebugToReply(db, wxGroupId, baseReceipt, debugBlock),
  };
}

/**
 * 管理端：与真实下单相同的预处理、分块与行合并后，列出每行结构化 AST（地区 / 玩法 / 子句），供展示与排障。
 */
export function listOrderLineStructuralPreview(db, wxGroupId, rawText, options = {}) {
  const senderWxid = String(options.senderWxid || '').trim();
  const wxMsgId = String(options.wxMsgId || '').trim();
  const wxNewMsgId = String(options.wxNewMsgId || '').trim();
  let content = stripWeChatAtPrefix(String(rawText || ''), db).trim();
  if (typeof content.normalize === 'function') content = content.normalize('NFKC');
  content = stripLeadingOrderNoise(content);
  content = normalizeEmbeddedMaZhongToTe(db, content);
  content = expandChaInstructionAliases(content, db);
  content = glueStandaloneGuideLineWithFollowing(db, content, wxGroupId);
  content = glueStandaloneCategoryAliasLineWithFollowing(db, content, wxGroupId);
  content = preprocessInboundOrderContent(db, content, wxGroupId) || content;
  content = normalizeOrderStreamText(content, db);
  content = glueOrphanContinuationLinesToPreviousRoute(db, content, wxGroupId);
  content = applyGuideSynonymsToEachLine(db, content);
  if (!content) {
    return { preprocessed_text: '', blocks: [], paragraphs: [], scope_defaults: { region: DEFAULT_ORDER_REGION, play: DEFAULT_ORDER_PLAY } };
  }
  const paragraphs = splitMessageParagraphs(content);
  const blocks = splitInstructionBlocks(content);
  const outBlocks = [];
  let globalLineIndex = 0;
  for (let bi = 0; bi < blocks.length; bi += 1) {
    const blockRaw = blocks[bi];
    const routePrefixes = buildSortedRoutePrefixesForGroup(db, wxGroupId);
    const rawLines = blockRaw
      .split(/\r?\n+/)
      .map((x) => {
        let ln = stripLeadingOrderNoise(String(x || '').trim());
        ln = stripLineLeadingChatTimestamp(ln);
        ln = stripBatchForwardMessageLinePrefix(ln);
        ln = stripTrailingInlineOrderSummary(ln);
        return stripTrailingEmbeddedAtPlusReceipt(ln);
      })
      .filter(
        (x) =>
          x &&
          !looksLikePlusOnlyReceiptLine(x) &&
          !isOrderDeclaredTotalNoiseLine(x) &&
          !looksLikeAtPlusReceiptLine(x) &&
          !isOrderSummaryFooterLine(x, routePrefixes)
      );
    const { contentLines, blockPrepend } = peelTrailingRouteOnlyLinesFromBlock(db, rawLines);
    if (contentLines.length === 0) continue;
    const mergedContentLines = mergeAdjacentUnparsedOrderLines(db, wxGroupId, contentLines, blockPrepend, {
      senderWxid,
      wxMsgId,
      wxNewMsgId,
    });
    const routedLines = mergedContentLines.map((ln) => ensureRoutedOrderLine(db, ln, blockPrepend, wxGroupId));
    let lines = [...routedLines];
    let first = applyLongestGuidePrefixReplacement(db, String(lines[0] || '').trim());
    first = hoistTrailingCategoryAfterZodiacs(db, first);
    first = hoistEmbeddedGuideChannelBeforeBallsEach(db, first, wxGroupId);
    if (!contentMatchesAnyRoute(db, first, wxGroupId)) {
      first = resolveOrderContentWithDefaultPrefix(db, first, wxGroupId);
    }
    first = normalizeRoutePrefixWithSynonyms(db, first);
    lines[0] = first;
    const normalizedLines = mergeZodiacHeadLinesWithEachAlgo(
      mergeBallGridLinesWithAlgo(
        normalizeMultilineCommandLines(db, lines, routePrefixes, wxGroupId).filter(Boolean),
        routePrefixes,
        db
      ),
      routePrefixes,
      db
    );
    const blockLines = [];
    for (const rawLineForExecute0 of normalizedLines) {
      const teNorm = normalizeTeRouteSpaceBallAmountTableSameLine(rawLineForExecute0, routePrefixes);
      for (const rawLineForExecute of fanOutEmbeddedLianXiaoOrderLines(db, wxGroupId, teNorm)) {
        globalLineIndex += 1;
        const ast = buildOrderLineStructuralAst(db, wxGroupId, rawLineForExecute);
        const canonical = ast ? emitCanonicalOrderLine(ast) : null;
        const units = extractOrderUnitsFromAst(ast);
        if (units.length) {
          appendOrderUnitLog({
            source: 'structural_preview',
            wxGroupId,
            rawLine: rawLineForExecute,
            units,
          });
        }
        blockLines.push({
          line_no: globalLineIndex,
          raw_line: rawLineForExecute,
          canonical_line: canonical || rawLineForExecute,
          ast: ast
            ? {
                kind: ast.kind,
                channel: ast.channel,
                play: ast.play,
                clauses: ast.clauses.map((c) => ({
                  target_raw: c.targetRaw,
                  algo: c.algo,
                  value: c.value,
                  items_type: c.itemsType,
                })),
              }
            : null,
          units,
          summary: ast ? formatOrderLineAstDebugOneLine(ast) : '',
        });
      }
    }
    outBlocks.push({ block_index: bi, lines: blockLines });
  }
  return {
    preprocessed_text: content,
    paragraphs,
    scope_defaults: { region: DEFAULT_ORDER_REGION, play: DEFAULT_ORDER_PLAY },
    blocks: outBlocks,
  };
}

export function executeFormulaTest(
  db,
  { typeWord, pipelineExpr, targetText, algo = '各', value = 0 } = {}
) {
  const valid = validateFormulaPipeline(pipelineExpr);
  if (!valid.ok) {
    return { ok: false, error: valid.error };
  }
  const allSetNames = db
    .prepare(
      `SELECT DISTINCT set_name FROM cmd_collections
       WHERE is_active = 1 AND wx_group_id IS NULL`
    )
    .all()
    .map((x) => x.set_name)
    .filter(Boolean);

  const targetRaw = String(targetText || '').trim();
  let items = [];
  let targetMode = 'empty';
  if (targetRaw) {
    const itemList = splitItemList(targetRaw);
    if (itemList.length > 0) {
      items = uniqueNumbers(itemList);
      targetMode = 'item_list';
    } else {
      const zodiacTokens = parseZodiacTokens(targetRaw);
      if (zodiacTokens.length > 0) {
        let ages = [];
        const now = new Date();
        for (const zodiac of zodiacTokens) ages.push(...zodiacBallNumbersForOrder(zodiac, now, 1, 49));
        items = uniqueNumbers(ages);
        targetMode = 'zodiac';
      } else {
        items = resolveSetNamesWithOperators(db, targetRaw, allSetNames);
        targetMode = items.length > 0 ? 'set_expr' : 'unknown';
      }
    }
  }

  const results = applyFormulaPipeline(pipelineExpr, {
    items,
    algo: String(algo || '各'),
    value: Number(value || 0),
    resolveSet: (setName) => resolveSetItems(db, setName),
    resolveVar: (varName) => {
      const row = db
        .prepare(
          `SELECT var_type, default_value_number, default_value_text
           FROM cmd_type_vars
           WHERE category_word = ? AND var_name = ?`
        )
        .get(String(typeWord || '').trim(), String(varName || '').trim());
      if (!row) return 0;
      if (String(row.var_type || 'number') === 'text') {
        const n = Number(row.default_value_text ?? 0);
        return Number.isFinite(n) ? n : 0;
      }
      return Number(row.default_value_number ?? 0);
    },
  });
  return {
    ok: true,
    target_mode: targetMode,
    input_items: items,
    algo: String(algo || '各'),
    value: Number(value || 0),
    results,
  };
}

import { executeViaRustEngine, rustEngineMainEntryEnabled } from './rust_bridge.js';

/** 主入口：USE_RUST_PRD=1 时由 Rust sim-bot-prd 编排，未原生实现相位委托 JS 子进程 */
export function executeConfiguredCommand(db, wxGroupId, text, options = {}) {
  if (rustEngineMainEntryEnabled()) {
    const rustOut = executeViaRustEngine(db, wxGroupId, text, options);
    if (rustOut !== undefined) return rustOut;
  }
  return executeConfiguredCommandImpl(db, wxGroupId, text, options);
}
