/**
 * 下单行结构化模型（重度管线）：地区 / 玩法 / 子句（目标 + 算法 + 金额）→ 规范串。
 * 与 engine 内 peel + parseAllDataSegmentClauses 结果对齐；单条子句语义见 engine 中 parseDataSegment 文档。便于统一重写行再入 execute。
 */

/** @typedef {'balls'|'zodiac'|'set'|'mixed'|'unknown'} OrderClauseItemsType */

/**
 * @typedef {Object} OrderLineClauseAst
 * @property {string} targetRaw
 * @property {string} algo
 * @property {number} value
 * @property {OrderClauseItemsType} itemsType
 */

/**
 * @typedef {Object} OrderLineAst
 * @property {'order_line_v1'} kind
 * @property {string} channel 规范化渠道（与 cmd_routes.guide 归一一致）
 * @property {string} play    规范化玩法分类（与 cmd_routes.category_word 一致）
 * @property {OrderLineClauseAst[]} clauses
 * @property {string} rawLine 原始行（供调试）
 */

const ZODIAC_CLASS = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';
const LIAN_STYLE = new Set(['连肖', '三连肖', '四连肖', '五连肖']);

/**
 * 根据玩法与目标字面推断子句目标类型（粗粒度，供回执/扩展用）。
 * @param {string} categoryWord
 * @param {string} targetRaw
 * @returns {OrderClauseItemsType}
 */
export function inferClauseItemsTypeForAst(categoryWord, targetRaw) {
  const cat = String(categoryWord || '').trim();
  const t0 = String(targetRaw || '').trim();
  if (!t0) return 'unknown';
  const t = t0.replace(/^[\s，,、·•]+/u, '');
  const parts = t.split(/[\s，,、]+/).filter(Boolean);
  if (
    parts.length > 0 &&
    parts.every((p) => {
      if (!/^\d{1,2}$/.test(p)) return false;
      const n = Number(p);
      return Number.isInteger(n) && n >= 1 && n <= 49;
    })
  ) {
    return 'balls';
  }
  if (new RegExp(`^[${ZODIAC_CLASS}]+$`, 'u').test(t.replace(/[,\s，、]/gu, ''))) return 'zodiac';
  if (LIAN_STYLE.has(cat) || cat === '特肖' || cat === '特肖马') return 'mixed';
  return 'unknown';
}

/** 与 engine normalizeOrderTargetSeparators 对齐：两数字间任意分隔（无运算语义） */
const AST_TARGET_INTERT_DIGIT_SEP_CLASS =
  '.\\-*＊_\\\\、,，;；/｜\\s\\uff0c\\uff0d\\uff0f\\u3001＋=%<>^&$#@_｀';

/** 与 engine normalizeOrderTargetSeparators 对齐的瘦身版，仅用于规范串输出 */
export function normalizeTargetsForCanonical(raw) {
  let t = String(raw || '').trim();
  const leadTrail = new RegExp(`^[${AST_TARGET_INTERT_DIGIT_SEP_CLASS}]+`, 'g');
  const between = new RegExp(
    `(\\d)(?:[${AST_TARGET_INTERT_DIGIT_SEP_CLASS}]|/)+(?=\\d)`,
    'g'
  );
  const trail = new RegExp(`[${AST_TARGET_INTERT_DIGIT_SEP_CLASS}]+$`, 'g');
  t = t.replace(leadTrail, '');
  t = t.replace(between, '$1 ').replace(/\s+/g, ' ').trim();
  t = t.replace(trail, '');
  return t.trim();
}

/**
 * 将 AST 打成一条可再入解析器的规范行：`渠道+玩法+子句…`
 * 多子句之间用空格分隔，避免「各1039各」类粘连歧义。
 * @param {OrderLineAst | null | undefined} ast
 * @returns {string | null}
 */
export function emitCanonicalOrderLine(ast) {
  if (!ast || ast.kind !== 'order_line_v1') return null;
  const ch = String(ast.channel || '').trim();
  const pl = String(ast.play || '').trim();
  if (!ch || !pl) return null;
  const prefix = `${ch}${pl}`;
  /** @type {string[]} */
  const parts = [];
  for (const cl of ast.clauses || []) {
    const tgt = normalizeTargetsForCanonical(cl.targetRaw);
    const algo = String(cl.algo ?? '各').trim();
    const v = Number(cl.value);
    if (!tgt || !Number.isFinite(v)) continue;
    if (algo === '各') parts.push(`${tgt}各${v}`);
    else parts.push(`${tgt}${algo}${v}`);
  }
  if (parts.length === 0) return null;
  const body = parts.length === 1 ? parts[0] : parts.join(' ');
  return `${prefix}${body}`;
}

/**
 * 从 AST 拆出下单单元四段（渠道、玩法、选号段、金额段）。
 * 一行多子句时：选号/金额按子句用「；」连接。
 * @param {OrderLineAst | null | undefined} ast
 */
export function extractOrderUnitsFromAst(ast) {
  if (!ast || ast.kind !== 'order_line_v1') return [];
  const channel = String(ast.channel || '').trim();
  const play = String(ast.play || '').trim();
  const clauses = ast.clauses || [];
  if (!channel || !play || clauses.length === 0) return [];
  const selections = [];
  const amounts = [];
  for (const c of clauses) {
    const sel = normalizeTargetsForCanonical(c.targetRaw);
    const algo = String(c.algo ?? '各').trim();
    const v = Number(c.value);
    if (!sel || !Number.isFinite(v)) continue;
    selections.push(sel);
    amounts.push(algo === '各' ? `各${v}` : `${algo}${v}`);
  }
  if (selections.length === 0) return [];
  return [
    {
      channel,
      play,
      selection: selections.join('；'),
      amount: amounts.join('；'),
      formatted: `渠道:${channel} | 玩法:${play} | 选号:${selections.join('；')} | 金额:${amounts.join('；')}`,
    },
  ];
}

/**
 * 调试：单行结构摘要（四段式，拼入回执/日志）
 * @param {OrderLineAst | null | undefined} ast
 * @returns {string}
 */
export function formatOrderLineAstDebugOneLine(ast) {
  const units = extractOrderUnitsFromAst(ast);
  if (units.length === 0) return '';
  return units.map((u) => u.formatted).join('\n');
}
