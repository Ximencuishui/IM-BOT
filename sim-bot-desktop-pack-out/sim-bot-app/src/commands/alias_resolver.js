/**
 * PRD alias_config 与 legacy cmd_keyword_synonyms 统一读取（引擎解析入口）
 */
import { validateAliasEntry } from './alias_guard.js';

const SCOPE_CATEGORIES = {
  guide_word: ['REGION'],
  category_word: ['PLAY'],
  amount_unit: ['SET'],
  collection: ['COLLECTION'],
  algo: ['AMOUNT', 'PLAY'],
  instruction: ['INSTRUCTION'],
};

function pushPair(rows, seen, alias, canonical) {
  const a = String(alias || '').trim();
  const c = String(canonical || '').trim();
  if (!a || !c) return;
  const k = `${a}\0${c}`;
  if (seen.has(k)) return;
  seen.add(k);
  rows.push({ alias_word: a, canonical_word: c });
}

/** @returns {{ alias_word: string, canonical_word: string }[]} */
export function listSynonymPairs(db, scope) {
  const rows = [];
  const seen = new Set();
  if (!db) return rows;
  const cats = SCOPE_CATEGORIES[scope] || [];
  for (const cat of cats) {
    try {
      const prd = db
        .prepare(`SELECT alias_word, standard_word FROM alias_config WHERE category = ?`)
        .all(cat);
      for (const r of prd) pushPair(rows, seen, r.alias_word, r.standard_word);
    } catch {
      /* ignore */
    }
  }
  return rows;
}

/** @returns {string[]} */
export function listSynonymAliasesForCanonical(db, scope, canonicalWord) {
  const canon = String(canonicalWord || '').trim();
  return listSynonymPairs(db, scope)
    .filter((r) => r.canonical_word === canon)
    .map((r) => r.alias_word)
    .filter(Boolean);
}

/** PRD AMOUNT/各：algo scope + alias_config，供入站「各五十」类数字识别 */
export function listEachAlgoAliasWords(db) {
  const seen = new Set();
  const out = [];
  const push = (w) => {
    const t = String(w || '').trim();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  };
  if (!db) return out;
  for (const r of listSynonymPairs(db, 'algo')) {
    if (r.canonical_word !== '各') continue;
    push(r.alias_word);
    push(r.canonical_word);
  }
  try {
    const prd = db
      .prepare(
        `SELECT standard_word, alias_word FROM alias_config WHERE category = 'AMOUNT' AND standard_word = '各'`
      )
      .all();
    for (const r of prd) {
      push(r.standard_word);
      push(r.alias_word);
    }
  } catch {
    /* ignore */
  }
  out.sort((a, b) => b.length - a.length);
  return out;
}

/** SET/元：金额单位后缀（米、闷…），供入站中文金额识别 */
/** 入站指令词检测：instruction scope + alias_config INSTRUCTION */
/** 合集别名：alias_word → standard_word（合集名），长词优先替换 */
export function listCollectionAliasPairs(db) {
  if (!db) return [];
  try {
    return db
      .prepare(
        `SELECT alias_word, standard_word FROM alias_config
         WHERE category = 'COLLECTION'
           AND trim(alias_word) <> ''
           AND trim(standard_word) <> ''
         ORDER BY length(alias_word) DESC`
      )
      .all()
      .map((r) => ({
        alias_word: String(r.alias_word || '').trim(),
        standard_word: String(r.standard_word || '').trim(),
      }))
      .filter((r) => r.alias_word && r.standard_word && r.alias_word !== r.standard_word);
  } catch {
    return [];
  }
}

export function expandCollectionAliasesInTargetText(db, text) {
  let t = String(text || '');
  if (!db || !t) return t;
  for (const { alias_word, standard_word } of listCollectionAliasPairs(db)) {
    if (t.includes(alias_word)) t = t.split(alias_word).join(standard_word);
  }
  return t;
}

export function listInstructionMarkerWords(db) {
  const seen = new Set();
  const out = [];
  const push = (w) => {
    const t = String(w || '').trim();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  };
  if (!db) return out;
  for (const r of listSynonymPairs(db, 'instruction')) {
    push(r.alias_word);
    push(r.canonical_word);
  }
  try {
    const prd = db
      .prepare(`SELECT standard_word, alias_word FROM alias_config WHERE category = 'INSTRUCTION'`)
      .all();
    for (const r of prd) {
      push(r.standard_word);
      push(r.alias_word);
    }
  } catch {
    /* ignore */
  }
  out.sort((a, b) => b.length - a.length);
  return out;
}

/**
 * 从玩法规范词推断连肖每组生肖数（如 四连肖→4、连肖→2；「连码」不算连肖）。
 */
export function inferLianXiaoGroupSizeFromCategoryWord(cat) {
  const c = String(cat || '').trim();
  if (!c || c === '连码') return 0;
  const m = c.match(/([二三四五])连/u);
  if (m) {
    const n = { 二: 2, 三: 3, 四: 4, 五: 5 }[m[1]];
    if (n) return n;
  }
  if (/连肖/u.test(c)) return 2;
  return 0;
}

export function isLianXiaoCategoryWord(cat) {
  return inferLianXiaoGroupSizeFromCategoryWord(cat) > 0;
}

/** 已启用全局路由中的连肖玩法前缀（规范词 + category_word 同义词，长词优先，供预处理补「各」） */
export function listLianXiaoPlayPrefixTokensFromDb(db) {
  if (!db) return [];
  const tokens = new Set();
  const push = (w) => {
    const t = String(w || '').trim();
    if (t) tokens.add(t);
  };
  let rows = [];
  try {
    rows = db
      .prepare(
        `SELECT DISTINCT category_word FROM cmd_routes
         WHERE is_active = 1 AND TRIM(IFNULL(category_word, '')) <> ''
           AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id, '')) = '' OR wx_group_id = '__global__')`
      )
      .all();
  } catch {
    rows = [];
  }
  for (const r of rows) {
    const raw = String(r.category_word || '').trim();
    if (!raw) continue;
    let canon = raw;
    try {
      const resolved = resolveSynonymCanonical(db, 'category_word', raw);
      if (resolved) canon = resolved;
    } catch {
      /* empty */
    }
    if (!isLianXiaoCategoryWord(canon)) continue;
    push(raw);
    push(canon);
    try {
      for (const alias of listSynonymAliasesForCanonical(db, 'category_word', canon)) {
        push(alias);
      }
    } catch {
      /* empty */
    }
  }
  return [...tokens].sort((a, b) => b.length - a.length);
}

/**
 * 将 cmd_keyword_synonyms / cmd_algo_aliases 已有数据同步进 alias_config（幂等）
 */
export function syncLegacySynonymsToAliasConfig(db) {
  if (!db) return;
  const ins = db.prepare(
    `INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES (?,?,?)`
  );
  const scopeToCat = {
    guide_word: 'REGION',
    category_word: 'PLAY',
    amount_unit: 'SET',
    algo: 'AMOUNT',
    instruction: 'INSTRUCTION',
  };
  for (const [scope, cat] of Object.entries(scopeToCat)) {
    try {
      const rows = db
        .prepare(
          `SELECT canonical_word, alias_word FROM cmd_keyword_synonyms
           WHERE scope = ? AND is_active = 1`
        )
        .all(scope);
      for (const r of rows) {
        ins.run(cat, String(r.canonical_word || '').trim(), String(r.alias_word || '').trim());
      }
    } catch {
      /* ignore */
    }
  }
  try {
    const algos = db
      .prepare(`SELECT alias_word, maps_to FROM cmd_algo_aliases WHERE is_active = 1`)
      .all();
    for (const r of algos) {
      const maps = String(r.maps_to || '').trim();
      const alias = String(r.alias_word || '').trim();
      if (!maps || !alias) continue;
      ins.run('AMOUNT', maps, alias);
    }
  } catch {
    /* ignore */
  }
}

/** 与 engine getAlgoAliasData 一致：AMOUNT/各 + legacy algo scope */
export function buildAlgoAliasData(db) {
  const aliasToCanonical = new Map();
  if (!db) {
    return { aliasToCanonical, orderedTokens: [] };
  }
  for (const r of listSynonymPairs(db, 'algo')) {
    const a = String(r.alias_word || '').trim();
    const b = String(r.canonical_word || '').trim();
    if (a && b) aliasToCanonical.set(a, b);
  }
  for (const [a, b] of [...aliasToCanonical.entries()]) {
    const maps = String(b || '').trim();
    if (maps === '-' || maps === '－') aliasToCanonical.delete(a);
  }
  aliasToCanonical.delete('-');
  aliasToCanonical.delete('－');
  const orderedTokens = [...aliasToCanonical.keys()].sort((a, b) => b.length - a.length);
  return { aliasToCanonical, orderedTokens };
}

/** 将逗号/JSON 金额单位写入 alias_config（SET → 元） */
export function importAmountUnitAliasesToAliasConfig(db, rawSynonyms) {
  if (!db) return 0;
  let units = [];
  if (Array.isArray(rawSynonyms)) {
    units = rawSynonyms.map((x) => String(x || '').trim()).filter(Boolean);
  } else {
    const raw = String(rawSynonyms || '').trim();
    if (!raw) return 0;
    try {
      const j = JSON.parse(raw);
      if (Array.isArray(j)) units = j.map((x) => String(x).trim()).filter(Boolean);
      else units = raw.split(/[,，\s|]+/).map((x) => x.trim()).filter(Boolean);
    } catch {
      units = raw.split(/[,，\s|]+/).map((x) => x.trim()).filter(Boolean);
    }
  }
  const ins = db.prepare(
    `INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES ('SET', '元', ?)`
  );
  let n = 0;
  for (const u of units) {
    if (!u || u === '元') continue;
    const guard = validateAliasEntry({ category: 'SET', standard_word: '元', alias_word: u });
    if (!guard.ok) continue;
    const r = ins.run(u);
    if (r.changes) n += 1;
  }
  return n;
}

/** 启动时把 app_settings.order_amount_unit_synonyms 迁入 alias_config */
export function migrateAppSettingAmountUnitsToAliasConfig(db) {
  if (!db) return;
  try {
    const row = db.prepare(`SELECT value FROM app_settings WHERE key = ?`).get('order_amount_unit_synonyms');
    if (!row?.value) return;
    importAmountUnitAliasesToAliasConfig(db, row.value);
  } catch {
    /* ignore */
  }
}

export const PRD_SCOPE_TO_CATEGORY = {
  guide_word: 'REGION',
  category_word: 'PLAY',
  amount_unit: 'SET',
  algo: 'AMOUNT',
  instruction: 'INSTRUCTION',
};

export function listSetAmountUnitSuffixWords(db) {
  const seen = new Set();
  const out = [];
  const push = (w) => {
    const t = String(w || '').trim();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  };
  if (!db) return out;
  for (const r of listSynonymPairs(db, 'amount_unit')) {
    push(r.alias_word);
    push(r.canonical_word);
  }
  try {
    const prd = db
      .prepare(`SELECT standard_word, alias_word FROM alias_config WHERE category = 'SET'`)
      .all();
    for (const r of prd) {
      push(r.standard_word);
      push(r.alias_word);
    }
  } catch {
    /* ignore */
  }
  return out;
}

/** PRD 别名写入时同步 legacy 表，便于旧运维页与引擎双路径一致 */
export function syncAliasConfigToLegacy(db, { category, standard_word, alias_word }) {
  const cat = String(category || '').trim();
  const std = String(standard_word || '').trim();
  const alias = String(alias_word || '').trim();
  if (!db || !cat || !std || !alias) return;
  const scopeMap = {
    REGION: 'guide_word',
    PLAY: 'category_word',
    SET: 'amount_unit',
    AMOUNT: 'algo',
    INSTRUCTION: 'instruction',
  };
  const scope = scopeMap[cat];
  if (!scope) return;
  try {
    const mapsTo = scope === 'algo' ? std : undefined;
    if (scope === 'algo') {
      db.prepare(
        `INSERT INTO cmd_algo_aliases (alias_word, maps_to, is_active, updated_at)
         VALUES (?, ?, 1, datetime('now'))
         ON CONFLICT(alias_word) DO UPDATE SET maps_to = excluded.maps_to, is_active = 1, updated_at = datetime('now')`
      ).run(alias, std);
    } else {
      db.prepare(
        `INSERT INTO cmd_keyword_synonyms (scope, canonical_word, alias_word, is_active, updated_at)
         VALUES (?, ?, ?, 1, datetime('now'))
         ON CONFLICT(scope, alias_word) DO UPDATE SET
           canonical_word = excluded.canonical_word, is_active = 1, updated_at = datetime('now')`
      ).run(scope, std, alias);
    }
  } catch {
    /* legacy 表未就绪时忽略 */
  }
}

/** @returns {string|null} */
export function resolveSynonymCanonical(db, scope, aliasWord) {
  const alias = String(aliasWord || '').trim();
  if (!alias) return null;
  for (const r of listSynonymPairs(db, scope)) {
    if (r.alias_word === alias) return r.canonical_word;
  }
  return null;
}

export function removeAliasConfigFromLegacy(db, { category, alias_word }) {
  const alias = String(alias_word || '').trim();
  if (!db || !alias) return;
  const scopeMap = { REGION: 'guide_word', PLAY: 'category_word', SET: 'amount_unit', AMOUNT: 'algo', INSTRUCTION: 'instruction' };
  const scope = scopeMap[String(category || '').trim()];
  if (!scope) return;
  try {
    if (scope === 'algo') {
      db.prepare(`DELETE FROM cmd_algo_aliases WHERE alias_word = ?`).run(alias);
    } else {
      db.prepare(`DELETE FROM cmd_keyword_synonyms WHERE scope = ? AND alias_word = ?`).run(scope, alias);
    }
  } catch {
    /* ignore */
  }
}
