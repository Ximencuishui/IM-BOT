/**
 * 别名配置校验：拦截应由引擎预处理处理的误分类项，避免写入 alias_config。
 */

function removeLegacyAliasRow(db, category, alias_word) {
  const alias = String(alias_word || '').trim();
  if (!db || !alias) return;
  const scopeMap = {
    REGION: 'guide_word',
    PLAY: 'category_word',
    SET: 'amount_unit',
    AMOUNT: 'algo',
    INSTRUCTION: 'instruction',
  };
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

export const GE_EACH_ALIAS_WHITELIST = new Set([
  '各',
  '各数',
  '各位',
  '各个',
  '各位数',
  '各号',
  '个数',
  '每号',
  '每各',
  '个个',
  '各组',
  '每个号',
  '一个',
  '个',
  '每个',
]);

export const SET_AMOUNT_UNIT_WHITELIST = new Set([
  '元',
  '块',
  '整',
  '角',
  '分',
  '米',
  '闷',
  '焖',
  '蒙',
  'A',
  'a',
  '斤',
  '刀',
]);

/** 与 engine PREPROC_ZODIAC_CLASS 一致 */
const ZODIAC_CLASS = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';

const CN_DIGIT_ONLY = /^[零〇○一二三四五六七八九十百千万两俩贰廿卅]+$/u;

const ENGINE_REGION_ALIASES = new Set(['新奥特', '噢待码', '待码']);

const ZODIAC_PING_TE = new RegExp(`^[${ZODIAC_CLASS}]平$`, 'u');

const INVALID_SI_SAN_PLAY_ALIASES = new Set(['三四有', '三四友', '三四连肖']);

export function isGeEmbeddedAmountAlias(alias) {
  const a = String(alias || '').trim();
  if (!a || a === '各') return false;
  if (GE_EACH_ALIAS_WHITELIST.has(a)) return false;
  if (/^各[0-9]/u.test(a)) return true;
  if (/^各/u.test(a)) return true;
  return false;
}

export function isChineseDigitAsAmountUnit(alias) {
  const a = String(alias || '').trim();
  if (!a || SET_AMOUNT_UNIT_WHITELIST.has(a)) return false;
  if (/^[A-Za-z]{1,4}$/.test(a)) return false;
  return CN_DIGIT_ONLY.test(a);
}

export function isEnginePreprocessRegionAlias(alias) {
  return ENGINE_REGION_ALIASES.has(String(alias || '').trim());
}

export function isZodiacPingTeShorthandAlias(alias) {
  return ZODIAC_PING_TE.test(String(alias || '').trim());
}

/**
 * @param {{ category?: string, standard_word?: string, alias_word?: string }} entry
 * @returns {{ ok: true } | { ok: false, error: string }}
 */
export function validateAliasEntry({ category, standard_word, alias_word }) {
  const cat = String(category || '').trim();
  const std = String(standard_word || '').trim();
  const alias = String(alias_word || '').trim();
  if (!cat || !std || !alias) {
    return { ok: false, error: 'category / standard_word / alias_word 必填' };
  }
  if (alias === std) {
    return { ok: true };
  }

  if (cat === 'AMOUNT' && std === '各' && isGeEmbeddedAmountAlias(alias)) {
    return {
      ok: false,
      error: `「${alias}」属于「各+金额」，由引擎自动展开，勿配置为「各」的同义词`,
    };
  }

  if (cat === 'SET' && std === '元' && isChineseDigitAsAmountUnit(alias)) {
    return {
      ok: false,
      error: `「${alias}」是中文数字而非金额单位，勿写入 SET`,
    };
  }

  if (cat === 'REGION' && std === '新澳门' && isEnginePreprocessRegionAlias(alias)) {
    return {
      ok: false,
      error: `「${alias}」由引擎渠道预处理识别，勿配置为地区别名`,
    };
  }

  if (cat === 'PLAY' && std === '平特' && isZodiacPingTeShorthandAlias(alias)) {
    return {
      ok: false,
      error: `「${alias}」属于「生肖+平」口语，由引擎自动规整为平特，勿配置为玩法别名`,
    };
  }

  if (cat === 'PLAY' && INVALID_SI_SAN_PLAY_ALIASES.has(alias)) {
    return {
      ok: false,
      error: `「${alias}」为三四复式口语，由引擎按句式展开，勿写入玩法别名（请用三有/三友→三连肖、四有/四友→四连肖）`,
    };
  }

  if (cat === 'PLAY' && std === '平特三连' && (alias === '三有' || alias === '三友')) {
    return {
      ok: false,
      error: `「${alias}」应对应标准词「三连肖」，勿挂在「平特三连」`,
    };
  }

  if (cat === 'PLAY' && std === '连肖' && (alias === '平特二连' || alias === '平特二连肖')) {
    return {
      ok: false,
      error: `「${alias}」为独立玩法「平特二连」，勿映射到「连肖」`,
    };
  }

  return { ok: true };
}

/** @returns {{ id, category, standard_word, alias_word, reason: string }[]} */
export function listMisclassifiedAliases(db) {
  if (!db) return [];
  let rows = [];
  try {
    rows = db
      .prepare(
        `SELECT id, category, standard_word, alias_word FROM alias_config ORDER BY category, id`
      )
      .all();
  } catch {
    return [];
  }
  const out = [];
  for (const row of rows) {
    const v = validateAliasEntry(row);
    if (!v.ok) {
      out.push({
        id: row.id,
        category: row.category,
        standard_word: row.standard_word,
        alias_word: row.alias_word,
        reason: v.error,
      });
    }
  }
  return out;
}

/** 幂等清理 alias_config 与 legacy 表中的误分类项 */
export function purgeMisclassifiedAliasesFromDb(db) {
  if (!db) return 0;
  const issues = listMisclassifiedAliases(db);
  const del = db.prepare(`DELETE FROM alias_config WHERE id = ?`);
  let n = 0;
  for (const row of issues) {
    del.run(row.id);
    removeLegacyAliasRow(db, row.category, row.alias_word);
    n += 1;
  }
  return n;
}
