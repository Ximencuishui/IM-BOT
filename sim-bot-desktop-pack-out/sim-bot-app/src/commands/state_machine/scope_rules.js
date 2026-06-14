/**
 * PRD 4.2 作用域级联规则（骨架，完整逻辑仍在 engine.js）
 * 规则 1：同行有单元 → 行级头尾；规则 2：行末标点 → 块级；规则 3/4：全局单次/多次声明
 */
export const SCOPE_RULE_IDS = ['row_head_tail', 'block_punctuation', 'global_singleton', 'global_multi'];

/**
 * @param {'row_head_tail'|'block_punctuation'|'global_singleton'|'global_multi'} ruleId
 */
export function describeScopeRule(ruleId) {
  const map = {
    row_head_tail: '同一行内有下单单元时，渠道/玩法按行级头尾生效',
    block_punctuation: '行末有分号/句号时锁定块级区域',
    global_singleton: '全消息仅出现一次且在头/尾时全局覆盖',
    global_multi: '多次出现时按指向词或顺/逆序降临',
  };
  return map[ruleId] || '';
}
