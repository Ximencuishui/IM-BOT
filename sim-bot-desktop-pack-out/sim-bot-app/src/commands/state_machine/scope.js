/**
 * PRD 4.x 作用域继承：为缺渠道/玩法的下单单元填充默认值
 */
export const SCOPE_RULES_VERSION = 1;

/**
 * @typedef {Object} OrderUnitDraft
 * @property {string} [region]
 * @property {string} [play]
 * @property {string} [target]
 * @property {number} [amount]
 */

/**
 * PRD 4.1 公理 3：缺少渠道或玩法时用上下文默认填充
 * @param {OrderUnitDraft[]} units
 * @param {{ defaultRegion?: string, defaultPlay?: string }} ctx
 * @returns {OrderUnitDraft[]}
 */
export function applyDefaultScope(units, { defaultRegion = '新澳门', defaultPlay = '特' } = {}) {
  if (!Array.isArray(units)) return [];
  return units.map((u) => ({
    ...u,
    region: String(u.region || '').trim() || defaultRegion,
    play: String(u.play || '').trim() || defaultPlay,
  }));
}

/**
 * PRD 4.1 公理 2：对象须先于金额；金额后再出现对象则切分新块（简化版）
 * @param {{ kind: 'target'|'amount', value: string }[]} tokens
 * @returns {{ kind: 'target'|'amount', value: string }[][]}
 */
export function splitBlocksByTargetBeforeAmount(tokens) {
  /** @type {{ kind: 'target'|'amount', value: string }[][]} */
  const blocks = [];
  let cur = [];
  let seenAmount = false;
  for (const t of tokens || []) {
    if (t.kind === 'amount') {
      seenAmount = true;
      cur.push(t);
      continue;
    }
    if (t.kind === 'target' && seenAmount && cur.length) {
      blocks.push(cur);
      cur = [t];
      seenAmount = false;
      continue;
    }
    cur.push(t);
  }
  if (cur.length) blocks.push(cur);
  return blocks;
}
