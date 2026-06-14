/**
 * 下单单元作用域：段落划分与渠道/玩法声明作用范围（PRD 4.2 骨架）。
 * 完整级联仍由 engine 路由/合并管线承担；此处提供段落切分与规则说明供预览/日志。
 */

export const DEFAULT_ORDER_REGION = '新澳门';
export const DEFAULT_ORDER_PLAY = '特';

/** 段落切分优先级：换行 → 句号 → 分号 */
export function splitMessageParagraphs(text) {
  const raw = String(text || '');
  if (!raw.trim()) return [];
  const byNewline = raw.split(/\r?\n+/).map((s) => s.trim()).filter(Boolean);
  const out = [];
  for (const chunk of byNewline) {
    for (const part of chunk.split(/[。．]+/u)) {
      const t = String(part || '').trim();
      if (!t) continue;
      for (const seg of t.split(/[;；]+/u)) {
        const s = String(seg || '').trim();
        if (s) out.push(s);
      }
    }
  }
  return out.length ? out : [raw.trim()];
}

/**
 * 全消息渠道/玩法声明出现次数与位置（粗检测，供排障标注）。
 * @param {string} text
 * @param {string[]} markerWords 渠道或玩法 token
 */
export function scanDeclarationOccurrences(text, markerWords = []) {
  const t = String(text || '');
  const markers = (markerWords || []).map((w) => String(w || '').trim()).filter(Boolean);
  const hits = [];
  for (const w of markers) {
    let idx = 0;
    while (idx < t.length) {
      const at = t.indexOf(w, idx);
      if (at < 0) break;
      hits.push({ word: w, index: at });
      idx = at + w.length;
    }
  }
  hits.sort((a, b) => a.index - b.index);
  return hits;
}

/**
 * @param {'row_head_tail'|'block_punctuation'|'global_singleton'|'global_multi'} ruleId
 */
export function describeScopeApplicationHint(ruleId) {
  const map = {
    row_head_tail: '同行有下单单元：声明在行首/行尾对该行单元生效；夹在单元间则仅对后续单元',
    block_punctuation: '无同行单元时，行末句号/分号锁定块级；块内首尾声明对整块生效',
    global_singleton: '全消息仅出现一次且独占首行或末行：对该消息全部单元生效',
    global_multi: '出现多次：先按段落（换行→句号→分号），段落首尾声明对段落生效',
  };
  return map[ruleId] || '';
}
