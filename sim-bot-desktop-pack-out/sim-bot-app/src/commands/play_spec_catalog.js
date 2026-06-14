/**
 * 《玩法说明.xlsx》玩法表 → 系统 category_word + 别名（与引擎/路由对齐）
 * excel: Excel「简称」列；category: cmd_routes.category_word；aliases: 口语别名
 */
export const PLAY_SPEC_CATALOG = [
  { excel: '特码', category: '特', aliases: ['特码'] },
  { excel: '平特', category: '平特', aliases: [] },
  { excel: '平特尾', category: '平尾', aliases: ['平特尾'] },
  { excel: '特肖', category: '特肖', aliases: [] },
  { excel: '平特二连', category: '平特二连', aliases: ['平特二连肖', '二连', '二连肖'] },
  { excel: '平特三连', category: '平特三连', aliases: ['平特三连肖'] },
  { excel: '平特四连', category: '四连肖', aliases: ['平特四连', '平特四连肖', '四连', '四有', '四友'] },
  { excel: '平特五连肖', category: '五连肖', aliases: ['平特五连', '五连', '五连肖'] },
  { excel: '绿波', category: '半波', aliases: ['绿波'] },
  { excel: '绿波单数', category: '单双', aliases: ['绿波单', '绿波单数', '绿单'] },
  { excel: '绿波双数', category: '单双', aliases: ['绿波双', '绿波双数', '绿双'] },
  { excel: '红波', category: '半波', aliases: ['红波'] },
  { excel: '红波单', category: '单双', aliases: ['红波单'] },
  { excel: '红波双', category: '半波', aliases: ['红波双', '红双'] },
  { excel: '蓝波', category: '半波', aliases: ['蓝波'] },
  { excel: '蓝波单', category: '单双', aliases: ['蓝波单', '蓝单'] },
  { excel: '蓝波双数', category: '单双', aliases: ['蓝波双', '蓝波双数', '蓝双'] },
  { excel: '五不中', category: '连码', aliases: ['五不中'] },
  { excel: '七不中', category: '连码', aliases: ['七不中'] },
  { excel: '九不中', category: '连码', aliases: ['九不中'] },
  { excel: '十不中', category: '连码', aliases: ['十不中'] },
  { excel: '十二不中', category: '连码', aliases: ['十二不中'] },
  { excel: '五肖中特', category: '特肖', aliases: ['五肖中特'] },
  { excel: '六肖中特', category: '特肖', aliases: ['六肖中特'] },
  { excel: '单数', category: '单双', aliases: ['单数', '包单数'] },
  { excel: '双数', category: '单双', aliases: ['双数', '包双数'] },
  { excel: '复式二连肖', category: '连肖', aliases: ['复式二连肖', '复式二连', '复试二连肖', '复试二连'] },
  { excel: '复式三连肖', category: '平特三连', aliases: ['复式三连肖', '复式三连', '复试三连肖', '复试三有', '复试三友'] },
  { excel: '包家肖', category: '特', aliases: ['包家肖', '家肖'] },
  { excel: '包野兽', category: '特', aliases: ['包野兽', '野肖', '野兽'] },
  { excel: '天肖', category: '特', aliases: ['天肖'] },
  { excel: '地肖', category: '特', aliases: ['地肖'] },
  { excel: '包双数', category: '单双', aliases: ['包双'] },
  { excel: '包单数', category: '单双', aliases: ['包单'] },
  { excel: '独平一号', category: '平特', aliases: ['独平一号', '独平一', '平特一'] },
  { excel: '包大', category: '特', aliases: ['包大', '大数'] },
  { excel: '包小', category: '特', aliases: ['包小', '小数'] },
  { excel: '包红波', category: '半波', aliases: ['包红波'] },
  { excel: '包绿波', category: '半波', aliases: ['包绿波'] },
  { excel: '包蓝波', category: '半波', aliases: ['包蓝波'] },
  { excel: '包红波单', category: '半波', aliases: ['包红波单'] },
  { excel: '包红波双', category: '半波', aliases: ['包红波双'] },
  { excel: '包绿波单', category: '半波', aliases: ['包绿波单'] },
  { excel: '包绿波双', category: '半波', aliases: ['包绿波双'] },
  { excel: '包蓝波单', category: '半波', aliases: ['包蓝波单'] },
  { excel: '包蓝波双', category: '半波', aliases: ['包蓝波双'] },
  { excel: '三中三', category: '连码', aliases: ['三中三', '复式三中三'] },
  { excel: '三中二', category: '连码', aliases: ['三中二'] },
  { excel: '复式二中二', category: '连码', aliases: ['复式二中二', '二中二'] },
  { excel: '复式三中三', category: '连码', aliases: ['复式三中三'] },
  { excel: '五行中特-金', category: '特', aliases: ['五行金', '金'] },
  { excel: '五行中特-木', category: '特', aliases: ['五行木', '木'] },
  { excel: '五行中特-水', category: '特', aliases: ['五行水', '水'] },
  { excel: '五行中特-火', category: '特', aliases: ['五行火', '火'] },
  { excel: '五行中特-土', category: '特', aliases: ['五行土', '土'] },
];

/** 三连肖口语（非平特三连玩法名） */
export const PLAY_SPEC_EXTRA_ALIASES = [
  { category: '三连肖', aliases: ['三友', '三有', '三连', '三连肖'] },
  { category: '连肖', aliases: ['连肖', '二连', '二连肖'] },
  { category: '四连肖', aliases: ['四连', '四连肖'] },
];

/** 比较契约时：Excel 展示名 → 系统等价玩法集合 */
export const PLAY_COMPARE_EQUIV = {
  特: ['特', '特码'],
  连码: ['连码', '三中三', '三中二', '二中二', '五不中', '七不中', '九不中', '十不中', '十二不中', '复式二中二', '复式三中三'],
  三连肖: ['三连肖', '平特三连', '平特三连肖', '复式三连肖', '连肖'],
  四连肖: ['四连肖', '平特四连', '平特四连肖', '4连肖'],
  五连肖: ['五连肖', '平特五连', '平特五连肖', '5连肖'],
  二连肖: ['二连肖', '平特二连', '平特二连肖', '连肖'],
  平特: ['平特', '平特一', '平特一肖', '平特肖', '独平一', '独平一号'],
  平尾: ['平尾', '平特尾'],
  半波: ['半波', '绿波', '红波', '蓝波', '波段'],
  单双: ['单双', '单数', '双数', '红波单', '红波双', '绿波单', '绿波双', '蓝波单', '蓝波双'],
  特肖: ['特肖', '六肖中特', '五肖中特'],
};

export function allPlaySpecCategoryWords() {
  const s = new Set();
  for (const row of PLAY_SPEC_CATALOG) {
    if (row.category) s.add(row.category);
  }
  for (const row of PLAY_SPEC_EXTRA_ALIASES) {
    if (row.category) s.add(row.category);
  }
  return [...s];
}

export function playCategoriesEquivalent(a, b) {
  const x = String(a || '').trim();
  const y = String(b || '').trim();
  if (!x || !y) return false;
  if (x === y) return true;
  for (const group of Object.values(PLAY_COMPARE_EQUIV)) {
    if (group.includes(x) && group.includes(y)) return true;
  }
  return false;
}
