/**
 * 中性规则引擎：仅 keyword / regex / noop，不涉及任何具体博彩语义。
 * 命中后可由 action_json 描述课题内的「模拟动作」（如 reply_text）。
 */

export function evaluateRules(rules, text) {
  const hits = [];
  const sorted = [...rules].sort((a, b) => (b.priority || 0) - (a.priority || 0));
  const content = String(text || '').trim();
  for (const r of sorted) {
    if (!r.is_active) continue;
    if (r.rule_type === 'noop') continue;
    if (r.rule_type === 'keyword') {
      if (content.includes(r.pattern)) hits.push({ ruleId: r.id, name: r.name, type: 'keyword' });
    } else if (r.rule_type === 'regex') {
      try {
        const re = new RegExp(r.pattern);
        if (re.test(content)) hits.push({ ruleId: r.id, name: r.name, type: 'regex' });
      } catch {
        /* 无效正则跳过 */
      }
    }
  }
  return hits;
}

const RULE_MISS_PATTERN_PREVIEW = 56;

function truncateRulePatternDisplay(s, maxLen = RULE_MISS_PATTERN_PREVIEW) {
  const t = String(s || '');
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen)}…`;
}

/**
 * 调试开时追加：仅列出本次未命中的 keyword/regex（命中规则仍按 action 正常回复）。
 * @param {object[]} rules 与 evaluateRules 同源列表
 * @param {{ ruleId: number }[]} hits evaluateRules 结果
 * @returns {string} 无未命中规则时返回空串
 */
export function buildRuleMissDebugReplyText(rules, hits) {
  const hitIds = new Set((hits || []).map((h) => Number(h.ruleId)));
  const sorted = [...rules].sort((a, b) => (b.priority || 0) - (a.priority || 0));
  const lines = [];
  for (const r of sorted) {
    if (!r.is_active) continue;
    if (r.rule_type === 'noop') continue;
    if (hitIds.has(Number(r.id))) continue;
    let invalidNote = '';
    if (r.rule_type === 'regex') {
      try {
        new RegExp(r.pattern);
      } catch {
        invalidNote = '（正则无效）';
      }
    }
    const pat = truncateRulePatternDisplay(String(r.pattern ?? ''));
    const label = String(r.name || '').trim() || '(无名)';
    if (r.rule_type === 'keyword') {
      lines.push(`· #${r.id} ${label} keyword「${pat}」${invalidNote}`);
    } else if (r.rule_type === 'regex') {
      lines.push(`· #${r.id} ${label} regex /${pat}/${invalidNote}`);
    }
  }
  if (lines.length === 0) return '';
  return ['[调试·未命中规则]', ...lines].join('\n');
}

export function parseActionJson(actionJson) {
  if (!actionJson) return {};
  try {
    return JSON.parse(actionJson);
  } catch {
    return {};
  }
}
