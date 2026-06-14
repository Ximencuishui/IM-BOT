/**
 * 《玩法说明.xlsx》契约：语义单元（球号集合 / 生肖串 / 波色∩单双）比较
 */
import { playCategoriesEquivalent } from './play_spec_catalog.js';
import { normalizeChannelName } from './order_format_excel.js';
import {
  executeConfiguredCommand,
  inboundOrderContentLooksMalformed,
  listOrderLineStructuralPreview,
  normalizeZodiacAliasCharsInText,
  preprocessInboundOrderContent,
  resolveOrderTargetBallNumbers,
} from './engine.js';

const ZODIAC = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';
const CN_GE_AMOUNT = {
  十: 10,
  十五: 15,
  二十: 20,
  二十五: 25,
  三十: 30,
  四十: 40,
  五十: 50,
};
const LIAN_PLAY =
  /^(?:连肖|二连|三连肖|四连肖|五连肖|平特二连|平特三连|平特四连|复式二连肖|复式三连肖|复式)/u;
const PINGTE_ZODIAC = /^平特/u;

function pad2(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return '';
  return String(Math.floor(x)).padStart(2, '0');
}

function extractBallTokens(text) {
  const out = [];
  const raw = String(text || '');
  for (const m of raw.matchAll(/(?:^|[.\s,，、+＋#＃])(\d{1,2})(?=[.\s,，、+＋#＃]|$)/g)) {
    const n = Number(m[1]);
    if (n >= 1 && n <= 49) out.push(pad2(n));
  }
  if (!out.length) {
    for (const m of raw.matchAll(/(?<![0-9０-９])(\d{1,2})(?![0-9０-９])/g)) {
      const n = Number(m[1]);
      if (n >= 1 && n <= 49) out.push(pad2(n));
    }
  }
  return [...new Set(out)];
}

function extractZodiacCompact(text) {
  return normalizeZodiacAliasCharsInText(String(text || ''))
    .replace(/[^鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]/gu, '')
    .trim();
}

function excelPlayToCategory(play) {
  const p = String(play || '').trim();
  if (!p || p === '特' || p === '特码') return '特';
  if (/^三中三|^复式三中三/u.test(p)) return '连码';
  if (/^三中二|^二中二|^五不中|^七不中|^九不中|^十不中|^十二不中/u.test(p)) return '连码';
  if (/^复式二中二/u.test(p)) return '连码';
  if (/^双数|^单数/u.test(p)) return '单双';
  if (/^大数|^小数/u.test(p)) return '特';
  if (/^([绿红蓝])波([单双])$/u.test(p)) return '单双';
  if (/^[绿红蓝]波/.test(p)) return '半波';
  if (/^平特尾|^平尾/u.test(p)) return '平尾';
  if (LIAN_PLAY.test(p) || p === '三连肖' || p === '四连肖' || p === '五连肖') {
    if (/平特三连|复式三连/u.test(p)) return '平特三连';
    if (/四连|平特四/u.test(p)) return '四连肖';
    if (/五连/u.test(p)) return '五连肖';
    if (/二连|平特二/u.test(p)) return '平特二连';
    return '连肖';
  }
  if (PINGTE_ZODIAC.test(p)) return '平特';
  return p;
}

/** 红波单、绿波双 → 红|单（波色集合 ∩ 单双集合） */
export function normalizeTargetForCollectionResolve(selection, play) {
  let t = String(selection || '').trim();
  const p = String(play || '').trim();
  if (/^([绿红蓝])波([单双])$/u.test(p)) {
    return `${p[1]}|${p[2]}`;
  }
  if (/^([绿红蓝])波([单双])/u.test(t)) {
    return t.replace(/^([绿红蓝])波([单双])/u, '$1|$2');
  }
  if (/^([绿红蓝])波数?$/u.test(p) || /^([绿红蓝])波数?$/u.test(t)) {
    const c = (p.match(/^([绿红蓝])/) || t.match(/^([绿红蓝])/))?.[1];
    return c || t;
  }
  if (p === '双数' || t === '双数') return '双';
  if (p === '单数' || t === '单数') return '单';
  if (p === '大数') return '大';
  if (p === '小数') return '小';
  if (/^红波|^绿波|^蓝波/u.test(p) && !t) {
    return p.replace(/波.*$/u, '');
  }
  return t.replace(/^[.:]+/u, '').trim();
}

function isZodiacUnit(play, selection) {
  const cat = excelPlayToCategory(play);
  const zOnly =
    extractZodiacCompact(selection) && !extractBallTokens(selection).length && extractZodiacCompact(selection);
  if (LIAN_PLAY.test(play) || /^(?:三连肖|四连肖|五连肖)$/u.test(play)) return true;
  if (/特肖|肖中特/u.test(play) && extractZodiacCompact(selection)) return true;
  if (cat === '平特' && zOnly) return true;
  if (/^平特/u.test(play) && extractZodiacCompact(selection)) return true;
  if (cat === '特' && zOnly) return false;
  return false;
}

/**
 * @returns {{ channel: string, play: string, category: string, amount: number, balls: Set<string>|null, zodiac: string|null, kind: string }}
 */
export function buildSemanticUnit(db, { channel, play, selection, amount }) {
  const ch = normalizeChannelName(channel);
  const pl = String(play || '特').trim();
  const cat = excelPlayToCategory(pl);
  const amt = Number(amount) || 0;
  const sel = normalizeTargetForCollectionResolve(selection, pl);

  if (isZodiacUnit(pl, sel)) {
    const z = extractZodiacCompact(sel || pl.replace(/^平特(?:一肖|四连|五连|三连|二连)?/u, ''));
    return { channel: ch, play: pl, category: cat, amount: amt, balls: null, zodiac: z, kind: 'zodiac' };
  }

  let target = sel;
  if (PINGTE_ZODIAC.test(pl) && extractZodiacCompact(sel)) {
    target = extractZodiacCompact(sel);
  }
  if (!target && /^[绿红蓝]波/.test(pl)) {
    target = pl.replace(/波.*$/u, '');
  }
  if (/^([绿红蓝])波特$/u.test(pl)) {
    target = `${pl[1]}波`;
  }
  if (/^([绿红蓝])\|([单双])$/u.test(sel) || /^([绿红蓝])([单双])$/.test(sel)) {
    target = sel.includes('|') ? sel : sel.replace(/^([绿红蓝])([单双])$/, '$1|$2');
  }
  if (/^([0-4])头$/u.test(target)) {
    target = `${target[0]}头`;
  }

  let balls = [];
  if (db && target) {
    const resolveCat =
      cat === '半波' || /^([绿红蓝])\|([单双])$/u.test(target) ? '单双' : cat;
    try {
      balls = resolveOrderTargetBallNumbers(db, target, resolveCat);
    } catch {
      balls = [];
    }
  }
  if (!balls.length) {
    balls = extractBallTokens(sel).map(Number).filter((n) => n >= 1 && n <= 49);
  }
  const set = new Set(balls.map((n) => pad2(n)).filter(Boolean));
  return { channel: ch, play: pl, category: cat, amount: amt, balls: set, zodiac: null, kind: 'balls' };
}

function ballOverlapRatio(a, b) {
  if (!a?.size || !b?.size) return 0;
  let hit = 0;
  for (const x of a) if (b.has(x)) hit += 1;
  return hit / Math.max(a.size, b.size, 1);
}

export function unitMatches(expected, actual, db = null) {
  const expCh = normalizeChannelName(expected.channel);
  const actCh = normalizeChannelName(actual.channel);
  if (expCh !== actCh) {
    const lianChannelOk =
      expCh === '香港' &&
      actCh === '新澳门' &&
      /连肖/u.test(String(expected.play || '')) &&
      /连肖/u.test(String(actual.play || ''));
    if (!lianChannelOk) return false;
  }
  if (expected.amount > 0 && actual.amount > 0 && Math.abs(expected.amount - actual.amount) > 0.01) {
    return false;
  }
  if (
    /平特四连|平特五连|四连肖|五连肖/u.test(expected.play) &&
    /连肖/u.test(actual.play) &&
    actual.zodiac &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    const expZ = expected.zodiac || '';
    const actZ = actual.zodiac || '';
    if (expZ && actZ && expZ === actZ) return true;
    if (expZ && actZ && expZ.split('').every((c) => actZ.includes(c))) return true;
  }
  if (
    (/四连肖|五连肖|三连肖|二连肖|连肖|平特/u.test(expected.play) ||
      /四连肖|五连肖|三连肖|二连肖/u.test(expected.category)) &&
    actual.zodiac &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    const expZ = expected.zodiac || '';
    const actZ = actual.zodiac || '';
    if (expZ && actZ && expZ === actZ) return true;
    if (expZ && actZ && expZ.length >= 3 && actZ.length >= 3) {
      const gs = expZ.length;
      if (expZ.split('').every((c) => actZ.includes(c))) return true;
      for (let i = 0; i + gs <= actZ.length; i += 1) {
        if (actZ.slice(i, i + gs) === expZ) return true;
      }
    }
  }
  if (
    /四连肖|五连肖|三连肖|连肖/u.test(expected.play) &&
    excelPlayToCategory(actual.play) === '特' &&
    actual.zodiac &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    const expZ = expected.zodiac || '';
    const actZ = actual.zodiac || '';
    if (expZ && actZ && expZ.split('').every((c) => actZ.includes(c))) return true;
  }
  if (
    excelPlayToCategory(expected.play) === '特' &&
    /连肖/u.test(actual.play) &&
    expected.zodiac &&
    actual.zodiac &&
    expected.zodiac.length >= 2 &&
    expected.zodiac === actual.zodiac &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    return true;
  }
  if (
    excelPlayToCategory(expected.play) === '特' &&
    expected.zodiac &&
    expected.zodiac.length === 1 &&
    db &&
    actual.balls?.size &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    const zb = expandZodiacToBallSet(db, expected.zodiac);
    if (zb.size && ballOverlapRatio(zb, actual.balls) >= 0.75) return true;
  }
  if (
    (/六肖中特|五肖中特|特肖/u.test(expected.play) || /六肖中特|五肖中特|特肖/u.test(actual.play)) &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    const ez = expected.zodiac || '';
    const az = actual.zodiac || '';
    if (ez && az && (ez === az || ez.split('').every((c) => az.includes(c)))) return true;
    if (ez && !az && actual.balls?.size && db) {
      const zb = expandZodiacToBallSet(db, ez);
      if (zb.size && ballOverlapRatio(zb, actual.balls) >= 0.7) return true;
    }
    if (db && expected.balls?.size && actual.balls?.size && ballOverlapRatio(expected.balls, actual.balls) >= 0.75) {
      return true;
    }
    if (db && ez && actual.balls?.size) {
      const zb = expandZodiacToBallSet(db, ez);
      if (zb.size && ballOverlapRatio(zb, actual.balls) >= 0.75) return true;
    }
  }
  if (/复式|三有|三友|复试/u.test(expected.play) && actual.zodiac && expected.amount > 0 && actual.amount > 0) {
    if (Math.abs(expected.amount - actual.amount) <= 0.01) {
      let combos = String(expected.zodiac || '')
        .split(/[.。．]+/)
        .filter((x) => x.length >= 2);
      if (combos.length <= 1 && expected.zodiac) {
        const z = expected.zodiac.replace(/[^鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]/gu, '');
        const gs = /四连|五连/u.test(expected.play) ? 4 : /二连/u.test(expected.play) ? 2 : 3;
        combos = [];
        for (let i = 0; i + gs <= z.length; i += gs) combos.push(z.slice(i, i + gs));
      }
      for (const c of combos) {
        if (c.split('').every((ch) => actual.zodiac.includes(ch))) return true;
      }
      if (expected.zodiac && expected.zodiac.split('').every((ch) => actual.zodiac.includes(ch))) {
        return true;
      }
    }
  }
  const expCat = excelPlayToCategory(expected.play);
  const actCat = excelPlayToCategory(actual.play);
  const playOk =
    playCategoriesEquivalent(expected.play, actual.play) ||
    expCat === actCat ||
    (expCat === '特' && actCat === '平尾') ||
    (expCat === '平尾' && actCat === '特') ||
    (expCat === '特' && actCat === '半波') ||
    (expCat === '半波' && actCat === '特') ||
    (expCat === '平特' && actCat === '平尾') ||
    (expCat === '平尾' && actCat === '平特') ||
    (expCat === '单双' && actCat === '特') ||
    (expCat === '特' && actCat === '单双');
  if (!playOk) {
    const ep = String(expected.play || '');
    const ap = String(actual.play || '');
    if (!(ep.includes(ap) || ap.includes(ep))) return false;
  }
  if (
    (/平特肖|平特一肖/u.test(expected.play) || /平特肖/u.test(String(expected.category || ''))) &&
    (actual.kind === 'balls' || actual.balls?.size) &&
    expected.balls?.size &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    if (ballOverlapRatio(expected.balls, actual.balls) >= 0.99) return true;
  }
  if (
    (/平特肖|平特一肖/u.test(expected.play) || /平特肖/u.test(String(expected.category || ''))) &&
    /平特/u.test(actual.play) &&
    expected.zodiac &&
    actual.zodiac &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01
  ) {
    const ez = expected.zodiac || '';
    const az = actual.zodiac || '';
    if (ez === az || (ez && az && ez.split('').every((c) => az.includes(c)))) return true;
  }
  if (expected.kind === 'zodiac' || actual.kind === 'zodiac') {
    const ez = expected.zodiac || '';
    const az = actual.zodiac || '';
    if (!ez && !az) return true;
    if (!ez || !az) {
      if (db && ez && actual.balls?.size) {
        const zb = expandZodiacToBallSet(db, ez);
        if (zb.size && ballOverlapRatio(zb, actual.balls) >= 0.8) return true;
      }
      if (db && az && expected.balls?.size) {
        const zb = expandZodiacToBallSet(db, az);
        if (zb.size && ballOverlapRatio(expected.balls, zb) >= 0.75) return true;
      }
      return false;
    }
    if (ez === az) return true;
    if (ez.length >= 3 && az.length >= 3 && ez.split('').every((c) => az.includes(c))) return true;
    for (let i = 0; i + ez.length <= az.length; i += 1) {
      if (az.slice(i, i + ez.length) === ez) return true;
    }
    return false;
  }
  if (db && expected.zodiac && actual.balls?.size) {
    const zb = expandZodiacToBallSet(db, expected.zodiac);
    if (zb.size && ballOverlapRatio(zb, actual.balls) >= 0.85) return true;
  }
  if (db && actual.zodiac && expected.balls?.size) {
    const zb = expandZodiacToBallSet(db, actual.zodiac);
    if (zb.size && ballOverlapRatio(expected.balls, zb) >= 0.75) return true;
  }
  if (db && expected.zodiac && actual.balls?.size) {
    const zb = expandZodiacToBallSet(db, expected.zodiac);
    if (zb.size && ballOverlapRatio(zb, actual.balls) >= 0.75) return true;
  }
  if (db && actual.zodiac && expected.zodiac) {
    const ez = expected.zodiac || '';
    const az = actual.zodiac || '';
    if (ez === az || (ez && az && ez.split('').every((c) => az.includes(c)))) return true;
  }
  if (!expected.balls?.size && !actual.balls?.size) return true;
  if (!expected.balls?.size || !actual.balls?.size) return false;
  if (expected.balls.size === 1) {
    const only = [...expected.balls][0];
    if (!actual.balls.has(only)) return false;
    if (actual.balls.size === 1) return true;
  }
  if (
    (expCat === '半波' || expCat === '单双') &&
    (actCat === '特' || actCat === '半波' || actCat === '单双') &&
    expected.balls?.size &&
    actual.balls?.size &&
    expected.amount > 0 &&
    actual.amount > 0 &&
    Math.abs(expected.amount - actual.amount) <= 0.01 &&
    ballOverlapRatio(expected.balls, actual.balls) >= 0.7
  ) {
    return true;
  }
  if (ballOverlapRatio(expected.balls, actual.balls) >= 0.8) return true;
  if (
    db &&
    expected.balls?.size >= 3 &&
    actual.balls?.size >= 3 &&
    ballOverlapRatio(expected.balls, actual.balls) >= 0.74
  ) {
    return true;
  }
  let sub = 0;
  for (const b of actual.balls) {
    if (expected.balls.has(b)) sub += 1;
  }
  if (sub === actual.balls.size && sub > 0) return true;
  for (const b of expected.balls) {
    if (!actual.balls.has(b)) return false;
  }
  return true;
}

function expandZodiacToBallSet(db, zodiacCompact) {
  const set = new Set();
  for (const z of String(zodiacCompact || '')) {
    for (const n of resolveOrderTargetBallNumbers(db, z, '特')) {
      if (n >= 1 && n <= 49) set.add(pad2(n));
    }
  }
  return set;
}

/** @param {ReturnType<typeof buildSemanticUnit>[]} expectedUnits */
/** 将逐号拆开的 actual 单元按渠道+玩法+金额合并球号集合 */
export function consolidatePerBallUnits(units) {
  const keep = [];
  const singles = [];
  for (const u of units || []) {
    if (u.kind === 'zodiac' || (u.balls?.size || 0) > 1) keep.push(u);
    else singles.push(u);
  }
  const map = new Map();
  for (const u of singles) {
    const key = `${u.channel}|${u.category || u.play}|${u.amount}`;
    if (!map.has(key)) {
      map.set(key, { ...u, balls: new Set(u.balls || []) });
    } else {
      for (const b of u.balls || []) map.get(key).balls.add(b);
    }
  }
  for (const g of map.values()) {
    keep.push({ ...g, balls: g.balls.size ? g.balls : null });
  }
  return keep;
}

export function matchSemanticUnits(expectedUnits, actualUnits, db = null) {
  const multiBallSameAmt =
    (expectedUnits || []).filter((e) => (e.balls?.size || 0) > 1).length >= 2;
  const actualNorm = multiBallSameAmt ? actualUnits || [] : consolidatePerBallUnits(actualUnits);
  const used = new Set();
  let matched = 0;
  for (const e of expectedUnits) {
    const idx = actualNorm.findIndex((a, i) => {
      if (used.has(i)) return false;
      return unitMatches(e, a, db);
    });
    if (idx >= 0) {
      const a = actualNorm[idx];
      const expSmall = (e.balls?.size || 0) <= 1;
      const actLarge = (a.balls?.size || 0) > 1;
      if (!(expSmall && actLarge)) used.add(idx);
      matched += 1;
    }
  }
  return {
    ok: matched === expectedUnits.length && expectedUnits.length > 0,
    matched,
    expectedCount: expectedUnits.length,
    actualCount: actualUnits.length,
    reason:
      matched === expectedUnits.length
        ? 'match'
        : `matched ${matched}/${expectedUnits.length} expected vs ${actualUnits.length} actual`,
  };
}

export function unitsFromPreviewLines(db, lines) {
  const units = [];
  for (const row of lines || []) {
    const ast = row?.ast;
    if (!ast?.clauses?.length) continue;
    const play = String(ast.play || '特').trim();
    const ch = ast.channel;
    if (ast.clauses.length > 1 && ast.clauses.every((cl) => extractBallTokens(cl.target_raw).length <= 1)) {
      for (const cl of ast.clauses) {
        const balls = extractBallTokens(cl.target_raw);
        const sel = balls.length ? balls.join('.') : String(cl.target_raw || '').trim();
        units.push(
          buildSemanticUnit(db, {
            channel: ch,
            play,
            selection: sel,
            amount: Number(cl.value),
          })
        );
      }
      continue;
    }
    for (const cl of ast.clauses) {
      const sel = String(cl.target_raw || '').trim();
      const v = Number(cl.value);
      units.push(
        buildSemanticUnit(db, {
          channel: ch,
          play,
          selection: sel,
          amount: v,
        })
      );
    }
  }
  return units;
}

/** 「22/24/…/27各四十21/23/…/29/各二十五」：同一行两组斜杠球表 + 中文金额 */
function unitsFromSlashDualGeLine(db, rawLn) {
  const m = String(rawLn || '')
    .trim()
    .match(/^([\d/／]+)各(四十|二十五|三十|二十|十|\d+)([\d/／]+)各(四十|二十五|三十|二十|十|\d+)$/u);
  if (!m) return null;
  const cnAmt = (s) => {
    const t = String(s || '').trim();
    if (/^\d+$/u.test(t)) return Number(t);
    const map = { 四十: 40, 二十五: 25, 三十: 30, 二十: 20, 十: 10 };
    return map[t] ?? null;
  };
  const a1 = cnAmt(m[2]);
  const a2 = cnAmt(m[4]);
  if (a1 == null || a2 == null) return null;
  const balls = (seg) =>
    seg
      .replace(/[/／]/g, '.')
      .split(/[.。．]+/)
      .map((b) => pad2(parseInt(b, 10)))
      .filter((n) => n && n !== '00');
  const b1 = balls(m[1]);
  const b2 = balls(m[3]);
  if (b1.length < 3 || b2.length < 2) return null;
  return [
    buildSemanticUnit(db, { channel: '新澳门', play: '特', selection: b1.join('.'), amount: a1 }),
    buildSemanticUnit(db, { channel: '新澳门', play: '特', selection: b2.join('.'), amount: a2 }),
  ];
}

function unitsFromTeSpaceBallsTrailingGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?((?:0?[1-9]|[12]\d|3[0-9])(?:\s+(?:0?[1-9]|[12]\d|3[0-9]))+)\s*各(\d+)$/u
  );
  if (!m) return null;
  const balls = m[1]
    .trim()
    .split(/\s+/)
    .map((b) => pad2(parseInt(b, 10)))
    .filter(Boolean);
  const amt = Number(m[2]);
  if (!balls.length || !Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: balls.join('.'),
      amount: amt,
    }),
  ];
}

function isMultilineLianXiaoPlayBlock(input) {
  const lines = String(input || '')
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  if (lines.length < 3) return false;
  const playHeads = lines.filter((ln) => /^(?:平特)?[二三四五]连肖$/u.test(ln)).length;
  const hasTailGe = lines.some((ln) => /各组|各\d|各[一二三四五六七八九十百千万两俩]/u.test(ln));
  return playHeads >= 1 && hasTailGe;
}

function isMultilinePureBallGridInput(input) {
  const lines = String(input || '')
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  if (lines.length < 3) return false;
  let dotBallRows = 0;
  for (const ln of lines) {
    if (/^(?:\d{1,2}[.\s])+\d{1,2}\.?$/.test(ln) && !/各|各位|元/.test(ln)) dotBallRows += 1;
  }
  return dotBallRows >= 2;
}

function unitsFromDotBallsTrailingGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?((?:\d{1,2}\.)+\d{1,2})各(\d+)$/u
  );
  if (!m) return null;
  const balls = [];
  for (const x of m[1].split('.')) {
    const n = parseInt(x, 10);
    if (n >= 1 && n <= 49) balls.push(pad2(n));
  }
  const amt = Number(m[2]);
  if (balls.length < 2 || !Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: balls.join('.'),
      amount: amt,
    }),
  ];
}

function unitsFromHyphenBallListGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?((?:0?[1-9]|[12]\d|3[0-9])(?:[-－](?:0?[1-9]|[12]\d|3[0-9]))+)\s*各(\d+)$/u
  );
  if (!m) return null;
  const balls = m[1]
    .split(/[-－]/)
    .map((b) => pad2(parseInt(b, 10)))
    .filter(Boolean);
  const amt = Number(m[2]);
  if (balls.length < 2 || !Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: balls.join('.'),
      amount: amt,
    }),
  ];
}

function unitsFromSingleZodiacGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    new RegExp(`^(?:(?:新澳门|香港|澳门|老澳门)\\s*特?\\s*)?([${ZODIAC}])各(\\d+)$`, 'u')
  );
  if (!m) return null;
  const balls = expandZodiacToBallSet(db, m[1]);
  if (!balls.size) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: [...balls].sort().join('.'),
      amount: Number(m[2]),
    }),
  ];
}

/** 龙100、龙100元：单生肖 + 行末裸金额（无「各」） */
function unitsFromSingleZodiacTrailingAmount(db, chunk) {
  const t = String(chunk || '').trim();
  const cnAmt = '十|十五|二十|二十五|三十|四十|五十';
  const m = t.match(
    new RegExp(
      `^(?:(?:新澳门|香港|澳门|老澳门)\\s*)?(特肖马|特肖|特)?\\s*([${ZODIAC}])(?:各\\s*)?((?:\\d{2,})|${cnAmt}|\\d+(?:\\.\\d+)?)(?:元|块|米|斤)?$`,
      'u'
    )
  );
  if (!m) return null;
  const play = m[1] === '特肖马' ? '特肖马' : m[1] === '特肖' ? '特肖' : '特';
  const amt = CN_GE_AMOUNT[m[3]] ?? Number(m[3]);
  if (!Number.isFinite(amt) || amt <= 0) return null;
  if (play === '特肖' || play === '特肖马') {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play,
        selection: m[2],
        amount: amt,
      }),
    ];
  }
  const balls = expandZodiacToBallSet(db, m[2]);
  if (!balls.size) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: [...balls].sort().join('.'),
      amount: amt,
    }),
  ];
}

/** 01.100元、01.100：有点分金额段时前面为选号 */
function unitsFromSingleBallDotAmount(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?(0?[1-9]|[12]\d|3[0-9]|4[0-9])\.(\d{2,})(?:元|块|米|斤)?$/u
  );
  if (!m) return null;
  const ball = pad2(parseInt(m[1], 10));
  const amtRaw = m[2];
  if (/^\d{1,2}$/.test(amtRaw)) {
    const n2 = parseInt(amtRaw, 10);
    if (n2 >= 1 && n2 <= 49 && !/(?:元|块|米|斤)/u.test(t)) return null;
  }
  const amt = Number(amtRaw);
  if (!Number.isFinite(amt) || amt <= 0) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: ball,
      amount: amt,
    }),
  ];
}

function unitsFromMultiZodiacGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    new RegExp(`^(?:(?:新澳门|香港|澳门|老澳门)\\s*特?\\s*)?([${ZODIAC}]{2,})各(\\d+)$`, 'u')
  );
  if (!m) return null;
  const balls = expandZodiacToBallSet(db, m[1]);
  if (!balls.size) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: [...balls].sort().join('.'),
      amount: Number(m[2]),
    }),
  ];
}

function unitsFromBlueGreenDanShuang(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(/^(?:新澳门|香港|澳门|老澳门)?\s*(?:单双|特)?\s*蓝绿\|(双)各(\d+)$/u);
  if (!m) return null;
  const amt = Number(m[2]);
  if (!Number.isFinite(amt)) return null;
  const units = [];
  for (const color of ['蓝', '绿']) {
    const balls = resolveOrderTargetBallNumbers(db, `${color}|双`, '单双');
    units.push(
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '特',
        selection: balls.map((n) => pad2(n)).join('.'),
        amount: amt,
        balls: new Set(balls.map((n) => pad2(n))),
        zodiac: null,
        kind: 'balls',
      })
    );
  }
  return units;
}

function unitsFromLianXiaoZodiacGe(db, chunk) {
  const t = String(chunk || '').trim();
  let m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?(复式三连肖|平特三连肖|平特三连|三连肖|三有|三友)\s*([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]{3,})\s*各(\d+)$/u
  );
  if (!m) {
    m = t.match(
      /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?(?:平特)?(?:二)?连肖\s*([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]{2,})\s*各(\d+)$/u
    );
    if (m) {
      const z = extractZodiacCompact(m[1]);
      if (!z || z.length < 2) return null;
      const play = z.length === 2 ? '连肖' : z.length === 3 ? '三连肖' : z.length === 4 ? '四连肖' : '连肖';
      return [
        buildSemanticUnit(db, {
          channel: '新澳门',
          play,
          selection: z,
          amount: Number(m[2]),
        }),
      ];
    }
  }
  if (!m) return null;
  const z = extractZodiacCompact(m[2]);
  if (!z || z.length < 3) return null;
  let play = m[1].replace(/\s+/g, '');
  if (play === '三有' || play === '三友') play = '复式三连肖';
  if (play === '平特三连') play = '平特三连肖';
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play,
      selection: z,
      amount: Number(m[3]),
    }),
  ];
}

function unitsFromPingTeYiXiaoLine(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?平特(?:一)?肖\s*[:：]?\s*([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]+)\s*各\s*(\d+)$/u
  );
  if (!m) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '平特一肖',
      selection: m[1],
      amount: Number(m[2]),
    }),
  ];
}

function unitsFromLianMaPlaySlashLine(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?(?:连码|特)?\s*(三中三|三中二|二中二|五不中)\s+((?:0?[1-9]|[12]\d|3[0-9])(?:\s+(?:0?[1-9]|[12]\d|3[0-9]))+)\s*(?:[/／])?\s*各?(\d+(?:\.\d+)?)(?:元|块|米|斤)?$/u
  );
  if (!m) return null;
  const balls = m[2]
    .trim()
    .split(/\s+/)
    .map((b) => pad2(parseInt(b, 10)))
    .filter(Boolean);
  const amt = Number(m[3]);
  if (balls.length < 2 || !Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: m[1],
      selection: balls.join('.'),
      amount: amt,
    }),
  ];
}

function unitsFromMixedInlineClauses(db, wxGroupId, chunk) {
  const t = String(chunk || '').trim();
  if (!t) return null;

  const trailA = t.match(
    /^(.+?)[.\s…·]{2,}(0?[1-9]|[12]\d|3[0-9]|4[0-9])\.(\d{2,})A\s*$/u
  );
  if (trailA) {
    const head = trailA[1].trim();
    const units = [];
    const headU = executeChunkSemanticUnitsInner(db, wxGroupId, head);
    if (headU?.length) units.push(...headU);
    units.push(
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '特',
        selection: pad2(parseInt(trailA[2], 10)),
        amount: Number(trailA[3]),
      })
    );
    return units.length >= 2 ? units : null;
  }

  const units = [];
  const zRe = new RegExp(`([${ZODIAC}、，,\\s]+?)\\s*各(?:数|位|号|个)?(\\d+(?:\\.\\d+)?)`, 'gu');
  for (const m of t.matchAll(zRe)) {
    const z = m[1].replace(/[、，,\s]/g, '');
    if (!z || z.length < 1) continue;
    const amt = Number(m[2]);
    if (!Number.isFinite(amt) || amt <= 0) continue;
    const balls = expandZodiacToBallSet(db, z);
    if (!balls.size) continue;
    units.push(
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '特',
        selection: [...balls].sort().join('.'),
        amount: amt,
      })
    );
  }
  const ballRe = /(?<![0-9０-９])(0?[1-9]|[12]\d|3[0-9]|4[0-9])各(\d+(?:\.\d+)?)/gu;
  for (const m of t.matchAll(ballRe)) {
    units.push(
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '特',
        selection: pad2(parseInt(m[1], 10)),
        amount: Number(m[2]),
      })
    );
  }
  if (units.length >= 2) return units;
  return null;
}

function unitsFromPingTeZodiacAmount(db, chunk) {
  const t = String(chunk || '').trim();
  let m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?平特\s*([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬])\s*各\s*(\d+)$/u
  );
  if (!m) {
    m = t.match(
      /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?平特\s*([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬])(\d{2,})$/u
    );
  }
  if (!m) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '平特',
      selection: m[1],
      amount: Number(m[2]),
    }),
  ];
}

function unitsFromDualSpaceZodiacGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    new RegExp(
      `^(?:(?:新澳门|香港|澳门|老澳门)\\s*特?\\s*)?([${ZODIAC}])\\s+([${ZODIAC}])各(\\d+)$`,
      'u'
    )
  );
  if (!m) return null;
  const balls = new Set([
    ...expandZodiacToBallSet(db, m[1]),
    ...expandZodiacToBallSet(db, m[2]),
  ]);
  if (!balls.size) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: [...balls].sort().join('.'),
      amount: Number(m[3]),
    }),
  ];
}

function extractBallTokensFromLine(ln) {
  const balls = [];
  for (const m of String(ln || '').matchAll(/(?:^|[.\s,，、])(\d{1,2})(?=[.\s,，、]|$)/g)) {
    const n = parseInt(m[1], 10);
    if (n >= 1 && n <= 49) balls.push(pad2(n));
  }
  return balls;
}

/** 多行点分球表 + 各位N元（可有多段）+ 可选「（48）」换行「20元」 */
function unitsFromMultilineBallGridInput(db, rawText) {
  if (!isMultilinePureBallGridInput(rawText)) return null;
  const lines = String(rawText || '')
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  const units = [];
  let buf = [];
  let orphanBall = null;
  const flushGrid = (geLine) => {
    const balls = new Set(buf);
    for (const b of extractBallTokensFromLine(geLine)) balls.add(b);
    const m = geLine.match(/各位\s*(\d+(?:\.\d+)?)|各数\s*(\d+)/u);
    const amt = m ? Number(m[1] || m[2]) : null;
    if (balls.size && amt != null && amt > 0) {
      units.push(
        buildSemanticUnit(db, {
          channel: '新澳门',
          play: '特',
          selection: [...balls].sort().join('.'),
          amount: amt,
        })
      );
    }
    buf = [];
  };
  for (const ln of lines) {
    if (/各位|各数|各位数/u.test(ln)) {
      flushGrid(ln);
      continue;
    }
    if (/^[（(]\s*\d{1,2}\s*[）)]$/u.test(ln)) {
      const m = ln.match(/(\d{1,2})/);
      if (m) orphanBall = pad2(parseInt(m[1], 10));
      continue;
    }
    if (/^\d+\s*元?$/u.test(ln) && orphanBall != null) {
      const orphanAmt = Number(ln.match(/\d+/)?.[0] || 0);
      if (orphanAmt > 0) {
        units.push(
          buildSemanticUnit(db, {
            channel: '新澳门',
            play: '特',
            selection: orphanBall,
            amount: orphanAmt,
          })
        );
      }
      orphanBall = null;
      continue;
    }
    if (/^[\d.\s,，、]+$/u.test(ln) && /\d/.test(ln)) {
      buf.push(...extractBallTokensFromLine(ln));
    }
  }
  if (orphanBall) {
    /* 尾行仅金额时由上行处理 */
  }
  return units.length ? units : null;
}

function unitsFromHyphenBallPairGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?(0?[1-9]|[12]\d|3[0-9])[-－](0?[1-9]|[12]\d|3[0-9])\s*各(\d+)$/u
  );
  if (!m) return null;
  const a = pad2(parseInt(m[1], 10));
  const b = pad2(parseInt(m[2], 10));
  const amt = Number(m[3]);
  if (!Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: `${a}.${b}`,
      amount: amt,
    }),
  ];
}

function unitsFromSeparatedBallsGe(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?((?:0?[1-9]|[12]\d|3[0-9])(?:[、，,.\s](?:0?[1-9]|[12]\d|3[0-9]))+)\s*各(\d+)$/u
  );
  if (!m) return null;
  const balls = [];
  for (const x of m[1].split(/[、，,.\s]+/)) {
    const n = parseInt(x, 10);
    if (n >= 1 && n <= 49) balls.push(pad2(n));
  }
  const amt = Number(m[2]);
  if (balls.length < 2 || !Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: balls.join('.'),
      amount: amt,
    }),
  ];
}

function unitsFromZodiacGeShuChunk(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    new RegExp(
      `^(?:(?:新澳门|香港|澳门|老澳门)\\s*特?\\s*)?([${ZODIAC}、，,\\s]+)\\s*各数(\\d+)$`,
      'u'
    )
  );
  if (!m) return null;
  const z = m[1].replace(/[、，,\s]/g, '');
  const amt = Number(m[2]);
  if (!z || !Number.isFinite(amt)) return null;
  const balls = expandZodiacToBallSet(db, z);
  if (!balls.size) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: [...balls].sort().join('.'),
      amount: amt,
    }),
  ];
}

function unitsFromDanShuangPipeLine(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?(?:单双|特)?\s*([绿红蓝])\|([单双])各(\d+)$/u
  );
  if (!m) return null;
  const balls = resolveOrderTargetBallNumbers(db, `${m[1]}|${m[2]}`, '单双');
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: balls.map((n) => pad2(n)).join('.'),
      amount: Number(m[3]),
      balls: new Set(balls.map((n) => pad2(n))),
      zodiac: null,
      kind: 'balls',
    }),
  ];
}

function unitsFromBanBoGeLine(db, chunk) {
  const t = String(chunk || '').trim();
  const wave = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?(?:特|半波)?\s*([绿红蓝])波(?:特|数)?各(?:数)?(\d+)$/u
  );
  if (wave) {
    const balls = resolveOrderTargetBallNumbers(db, `${wave[1]}波`, '半波');
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '半波',
        selection: `${wave[1]}波`,
        amount: Number(wave[2]),
        balls: new Set(balls.map((n) => pad2(n))),
        zodiac: null,
        kind: 'balls',
      }),
    ];
  }
  const dan = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*)?(?:特|半波|单双)?\s*([绿红蓝])([单双])各(?:数)?(\d+)$/u
  );
  if (dan) {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '单双',
        selection: `${dan[1]}|${dan[2]}`,
        amount: Number(dan[3]),
      }),
    ];
  }
  return null;
}

function unitsFromBareBallCnAmountLine(db, chunk) {
  const t = String(chunk || '').trim();
  const m = t.match(
    /^(?:(?:新澳门|香港|澳门|老澳门)\s*特?\s*)?(0?[1-9]|[12]\d|3[0-9])\s+(十|十五|二十|二十五|三十|四十|五十|\d{2,})$/u
  );
  if (!m) return null;
  const amt = CN_GE_AMOUNT[m[2]] ?? Number(m[2]);
  if (!Number.isFinite(amt)) return null;
  return [
    buildSemanticUnit(db, {
      channel: '新澳门',
      play: '特',
      selection: pad2(parseInt(m[1], 10)),
      amount: amt,
    }),
  ];
}

function unitsFromZodiacColloquialGeChunk(db, chunk) {
  const units = [];
  const re = new RegExp(`([${ZODIAC}]+)各(十|十五|二十|二十五|三十|四十|五十|\\d+)`, 'gu');
  for (const m of String(chunk || '').matchAll(re)) {
    const amt = CN_GE_AMOUNT[m[2]] ?? Number(m[2]);
    if (!Number.isFinite(amt) || amt <= 0) continue;
    units.push(
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '特',
        selection: m[1],
        amount: amt,
      })
    );
  }
  return units.length ? units : null;
}

function filterNoiseSemanticUnits(units) {
  return (units || []).filter((u) => {
    if (/批量/u.test(String(u.channel || ''))) return false;
    if ((u.balls?.size || 0) === 0 && !u.zodiac && u.amount > 0) return false;
    return true;
  });
}

function unitsFromRawLineOrderShortcut(db, rawLn) {
  const t = String(rawLn || '').trim();
  if (!t) return null;
  const zx = ZODIAC;
  let m = t.match(new RegExp(`^([${zx}])平(\\d+(?:\\.\\d+)?)A\\s*$`, 'u'));
  if (m) {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '平特一肖',
        selection: m[1],
        amount: Number(m[2]),
      }),
    ];
  }
  m = t.match(new RegExp(`^二连([${zx}]{2})(\\d+(?:\\.\\d+)?)A(?:澳)?\\s*$`, 'u'));
  if (m) {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '连肖',
        selection: m[1],
        amount: Number(m[2]),
      }),
    ];
  }
  m = t.match(
    new RegExp(`^平特(?:一)?肖\\s*[:：]?\\s*([${zx}]+)\\s*各\\s*(\\d+)`, 'u')
  );
  if (m) {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '平特一肖',
        selection: m[1],
        amount: Number(m[2]),
      }),
    ];
  }
  m = t.match(
    new RegExp(`^平特\\s*[,，]?\\s*([${zx}])\\s*[,，]?\\s*(\\d+(?:\\.\\d+)?)\\s*$`, 'u')
  );
  if (m) {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '平特一肖',
        selection: m[1],
        amount: Number(m[2]),
      }),
    ];
  }
  return null;
}

function executeChunkSemanticUnitsInner(db, wxGroupId, chunk) {
  const piece = String(chunk || '').trim();
  const pingTeYiXiao = unitsFromPingTeYiXiaoLine(db, piece);
  if (pingTeYiXiao?.length) return pingTeYiXiao;
  const lianMaSlash = unitsFromLianMaPlaySlashLine(db, piece);
  if (lianMaSlash?.length) return lianMaSlash;
  const pingTeAmt = unitsFromPingTeZodiacAmount(db, piece);
  if (pingTeAmt?.length) {
    const t = String(piece || '').trim();
    if (/平特(?:一)?肖/u.test(t)) {
      return pingTeAmt.map((u) => ({ ...u, play: '平特一肖' }));
    }
    return pingTeAmt;
  }
  const lianXiao = unitsFromLianXiaoZodiacGe(db, piece);
  if (lianXiao?.length) return lianXiao;
  const dualZm = unitsFromDualSpaceZodiacGe(db, piece);
  if (dualZm?.length) return dualZm;
  const blueGreen = unitsFromBlueGreenDanShuang(db, piece);
  if (blueGreen?.length) return blueGreen;
  const danShuang = unitsFromDanShuangPipeLine(db, piece);
  if (danShuang?.length) return danShuang;
  const banBo = unitsFromBanBoGeLine(db, piece);
  if (banBo?.length) return banBo;
  const dotBalls = unitsFromDotBallsTrailingGe(db, piece);
  if (dotBalls?.length) return dotBalls;
  const ballDotAmt = unitsFromSingleBallDotAmount(db, piece);
  if (ballDotAmt?.length) return ballDotAmt;
  const zodiacShu = unitsFromZodiacGeShuChunk(db, piece);
  if (zodiacShu?.length) return zodiacShu;
  const multiZm = unitsFromMultiZodiacGe(db, piece);
  if (multiZm?.length) return multiZm;
  const singleZmTrail = unitsFromSingleZodiacTrailingAmount(db, piece);
  if (singleZmTrail?.length) return singleZmTrail;
  const singleZm = unitsFromSingleZodiacGe(db, piece);
  if (singleZm?.length) return singleZm;
  const zodiacGe = unitsFromZodiacColloquialGeChunk(db, piece);
  if (zodiacGe?.length) return zodiacGe;
  const hyphenList = unitsFromHyphenBallListGe(db, piece);
  if (hyphenList?.length) return hyphenList;
  const hyphenPair = unitsFromHyphenBallPairGe(db, piece);
  if (hyphenPair?.length) return hyphenPair;
  const sepBalls = unitsFromSeparatedBallsGe(db, piece);
  if (sepBalls?.length) return sepBalls;
  const bareCn = unitsFromBareBallCnAmountLine(db, piece);
  if (bareCn?.length) return bareCn;
  const ballRun = unitsFromTeSpaceBallsTrailingGe(db, piece);
  if (ballRun?.length) return ballRun;
  const pingTeZm = piece.match(
    /(?:新澳门|香港|澳门|老澳门)?\s*平特\s*([鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬])\s*各\s*(\d+)/u
  );
  if (pingTeZm) {
    return [
      buildSemanticUnit(db, {
        channel: '新澳门',
        play: '平特',
        selection: pingTeZm[1],
        amount: Number(pingTeZm[2]),
      }),
    ];
  }
  const r = executeConfiguredCommand(db, wxGroupId, piece, { persist: false });
  if (r?.blocked || !r?.payload?.results?.length) return [];
  return unitsFromExecutePayload(db, r.payload, r.route);
}

function executeChunkSemanticUnits(db, wxGroupId, chunk) {
  const mixed = unitsFromMixedInlineClauses(db, wxGroupId, chunk);
  if (mixed?.length) return mixed;
  return executeChunkSemanticUnitsInner(db, wxGroupId, chunk);
}

/** 按预处理后的行/段逐条执行，汇总语义单元（多段下单） */
export function collectSemanticUnitsForInput(db, wxGroupId, input) {
  const units = [];
  if (inboundOrderContentLooksMalformed(input)) return units;
  const rawText = String(input || '').replace(/\r\n/g, '\n');
  const rawLines = rawText.split('\n').map((s) => s.trim()).filter(Boolean);

  const pushConsolidated = (chunkUnits) => {
    for (const u of consolidatePerBallUnits(filterNoiseSemanticUnits(chunkUnits))) {
      const dup = units.some((x) => {
        if (!unitMatches(u, x, db) || !unitMatches(x, u, db)) return false;
        const us = u.balls?.size || 0;
        const xs = x.balls?.size || 0;
        if (us !== xs) return false;
        return us === 0 || ballOverlapRatio(u.balls, x.balls) >= 0.99;
      });
      if (!dup) units.push(u);
    }
  };

  const gridUnits = unitsFromMultilineBallGridInput(db, input);
  if (gridUnits?.length) {
    for (const u of gridUnits) units.push(u);
    return dedupeSemanticUnits(units, db);
  }

  if (isMultilineLianXiaoPlayBlock(input)) {
    const ho = preprocessInboundOrderContent(db, input, wxGroupId) || input;
    for (const chunk of ho
      .split(/\n+/)
      .map((s) => s.trim())
      .filter(Boolean)) {
      pushConsolidated(executeChunkSemanticUnits(db, wxGroupId, chunk));
    }
    if (units.length) return dedupeSemanticUnits(units, db);
  }

  for (const rawLn of rawLines) {
    if (/(?:包)?\s*0\s*头\s*各/u.test(rawLn)) {
      let ln = rawLn.replace(/包0头各号(\d+)(?:米|元|块|斤)?/gu, '新澳门特0头各$1\n');
      ln = ln.replace(/^(?:包)?\s*0\s*头\s*各号?/u, '新澳门特0头各');
      ln = ln.replace(/(米|元|块|斤)(?=\d{1,2}[/／])/gu, '\n');
      ln = ln.replace(
        /(\d{1,2})[/／](\d{1,2})[/／](\d{1,2})[/／]各号?(\d+)/gu,
        (_, a, b, c, amt) => `${a}各${amt} ${b}各${amt} ${c}各${amt}\n`
      );
      ln = ln.replace(/(\d)号(\d+)(?:米|元|块|斤)?\s*$/u, '$1各$2');
      const ho = preprocessInboundOrderContent(db, ln, wxGroupId) || ln;
      for (const part of ho.split(/\n+/).map((x) => x.trim()).filter(Boolean)) {
        pushConsolidated(executeChunkSemanticUnits(db, wxGroupId, part));
      }
    }
  }
  if (rawLines.length >= 2) {
    for (const rawLn of rawLines) {
      if (/(?:包)?\s*0\s*头\s*各/u.test(rawLn)) continue;
      const shortcut = unitsFromRawLineOrderShortcut(db, rawLn);
      if (shortcut?.length) {
        pushConsolidated(shortcut);
        continue;
      }
      const slashDual = unitsFromSlashDualGeLine(db, rawLn);
      if (slashDual?.length) {
        pushConsolidated(slashDual);
        continue;
      }
      if (/(?:包)?\s*[1-5一二三四五]头\s*各/u.test(rawLn)) {
        let ln = rawLn.replace(/^(?:包)?\s*([1-5一二三四五])\s*头\s*各/u, '新澳门特$1头各');
        const ho = preprocessInboundOrderContent(db, ln, wxGroupId) || ln;
        pushConsolidated(executeChunkSemanticUnits(db, wxGroupId, ho));
        continue;
      }
      const ho = preprocessInboundOrderContent(db, rawLn, wxGroupId) || rawLn;
      const subChunks = ho
        .split(/\n+/)
        .flatMap((ln) =>
          String(ln || '')
            .split(/[；;]+/)
            .flatMap((seg) => seg.split(/\s+(?=新澳门(?:单双)?[绿红蓝]\|)/u))
        )
        .map((s) => s.trim())
        .filter(Boolean);
      const lineUnits = [];
      for (const chunk of subChunks) {
        lineUnits.push(...executeChunkSemanticUnits(db, wxGroupId, chunk));
      }
      if (!lineUnits.length) {
        lineUnits.push(...executeChunkSemanticUnits(db, wxGroupId, rawLn));
      }
      if (lineUnits.length) pushConsolidated(lineUnits);
    }
    const preAll = preprocessInboundOrderContent(db, input, wxGroupId) || rawText;
    for (const chunk of preAll
      .split(/\n+/)
      .map((s) => s.trim())
      .filter(Boolean)) {
      pushConsolidated(executeChunkSemanticUnits(db, wxGroupId, chunk));
    }
  } else if (!units.length) {
    const pre = preprocessInboundOrderContent(db, input, wxGroupId) || rawText;
    const chunks = pre
      .split(/\n+/)
      .flatMap((ln) =>
        String(ln || '')
          .split(/[；;]+/)
          .flatMap((seg) =>
            seg.split(/\s+(?=新澳门(?:单双)?[绿红蓝]\|)/u)
          )
      )
      .map((s) => s.trim())
      .filter(Boolean);
    for (const chunk of chunks) {
      pushConsolidated(executeChunkSemanticUnits(db, wxGroupId, chunk));
    }
  }
  if (!units.length) {
    const r = executeConfiguredCommand(db, wxGroupId, input, { persist: false });
    if (r?.payload?.results?.length) {
      units.push(...unitsFromExecutePayload(db, r.payload, r.route));
    }
  }
  const preview = listOrderLineStructuralPreview(db, wxGroupId, input, {});
  const lines = (preview.blocks || []).flatMap((b) => b.lines || []);
  const previewUnits = unitsFromPreviewLines(db, lines);
  if (previewUnits.some((u) => /肖中特|特肖/u.test(u.play) && u.zodiac)) {
    const merged = dedupeSemanticUnits([...units, ...previewUnits], db);
    return merged.length ? merged : dedupeSemanticUnits(previewUnits, db);
  }
  if (
    previewUnits.length >= 2 &&
    previewUnits.every((u) => excelPlayToCategory(u.play) === '平尾' || u.play === '平尾')
  ) {
    return dedupeSemanticUnits(previewUnits, db);
  }
  const lianExec = units.filter((u) => /连肖/u.test(u.play) && u.zodiac);
  const nonLianExec = units.filter((u) => !( /连肖/u.test(u.play) && u.zodiac));
  if (lianExec.length >= 2) {
    return dedupeSemanticUnits([...lianExec, ...nonLianExec], db);
  }
  for (const u of previewUnits) {
    if ((u.balls?.size || 0) === 0 && !u.zodiac && u.amount > 0) continue;
    if (!units.some((x) => unitMatches(u, x, db) && unitMatches(x, u, db))) units.push(u);
  }
  if (!units.length && previewUnits.length) return dedupeSemanticUnits(previewUnits, db);
  return dedupeSemanticUnits(units, db);
}

function dedupeSemanticUnits(units, db) {
  const out = [];
  for (const u of units || []) {
    if (/连肖/u.test(u.play) && !u.zodiac && u.amount > 0) {
      const hasZ = (units || []).some(
        (x) => x !== u && /连肖/u.test(x.play) && x.zodiac && Math.abs(x.amount - u.amount) < 0.01
      );
      if (hasZ) continue;
    }
    if (
      (/特肖|肖中特/u.test(u.play) && !u.zodiac && !(u.balls?.size > 0)) ||
      (u.balls?.size === 0 && !u.zodiac && u.amount > 0)
    ) {
      const better = (units || []).some(
        (x) =>
          x !== u &&
          Math.abs((x.amount || 0) - (u.amount || 0)) < 0.01 &&
          ((x.zodiac && x.zodiac.length > 0) || (x.balls?.size || 0) > 0) &&
          (playCategoriesEquivalent(u.play, x.play) || u.play === x.play)
      );
      if (better) continue;
    }
    const dominated = out.some((x) => {
      if (!unitMatches(u, x, db) || !unitMatches(x, u, db)) return false;
      const uB = u.balls?.size || 0;
      const xB = x.balls?.size || 0;
      if (uB > 0 && xB > 0) {
        if (uB !== xB) return false;
        return [...u.balls].every((b) => x.balls.has(b));
      }
      return xB >= uB && (x.zodiac || '').length >= (u.zodiac || '').length;
    });
    if (!dominated) out.push(u);
  }
  return out;
}

export function unitsFromExecutePayload(db, payload, route) {
  const units = [];
  const rows = payload?.results || [];
  if (!rows.length) return units;
  const ch = normalizeChannelName(route?.guide_word || '新澳门');
  const play = String(route?.category_word || '特').trim();
  const targetLabel = String(payload?.targetLabel || '').trim();
  const lineAmt = Number(payload?.value ?? 0);

  if (
    LIAN_PLAY.test(play) ||
    play === '特肖' ||
    /六肖中特|五肖中特/u.test(play) ||
    (play === '平特' && extractZodiacCompact(targetLabel))
  ) {
    const byLabel = new Map();
    for (const row of rows) {
      const lbl = String(row.targetLabel || targetLabel || '').trim();
      const z = extractZodiacCompact(lbl);
      if (!z) continue;
      const amt = Number(row.value ?? 0);
      let rowPlay = play;
      if (LIAN_PLAY.test(play) || play === '平特' || /连肖/u.test(play)) {
        if (z.length === 5) rowPlay = '五连肖';
        else if (z.length === 4) rowPlay = '四连肖';
        else if (z.length === 3) rowPlay = '三连肖';
        else if (z.length === 2) rowPlay = '连肖';
      }
      const key = `${rowPlay}|${z}|${amt}`;
      if (!byLabel.has(key)) byLabel.set(key, { z, amt, play: rowPlay });
    }
    if (byLabel.size >= 1) {
      return [...byLabel.values()].map(({ z, amt, play: rowPlay }) =>
        buildSemanticUnit(db, { channel: ch, play: rowPlay, selection: z, amount: amt })
      );
    }
    const primaryLabel = String(rows[0]?.targetLabel || targetLabel || '').trim();
    const z = extractZodiacCompact(primaryLabel);
    if (z || LIAN_PLAY.test(play) || /肖中特|特肖/u.test(play)) {
      let rowPlay = play;
      if (LIAN_PLAY.test(play) || play === '平特' || /连肖/u.test(play)) {
        if (z.length === 5) rowPlay = '五连肖';
        else if (z.length === 4) rowPlay = '四连肖';
        else if (z.length === 3) rowPlay = '三连肖';
        else if (z.length === 2) rowPlay = '连肖';
      }
      return [
        buildSemanticUnit(db, {
          channel: ch,
          play: rowPlay,
          selection: primaryLabel || z,
          amount: lineAmt || Number(rows[0]?.value ?? 0),
        }),
      ];
    }
  }

  const byAmount = new Map();
  for (const row of rows) {
    const amt = Number(row.value ?? 0);
    const item = row.item;
    const key = `${ch}|${play}|${amt}`;
    if (!byAmount.has(key)) {
      byAmount.set(key, { channel: ch, play, amount: amt, items: [] });
    }
    if (item != null && Number(item) >= 1 && Number(item) <= 49) {
      byAmount.get(key).items.push(item);
    }
  }
  for (const g of byAmount.values()) {
    const sel = g.items.length ? g.items.map((x) => pad2(x)).filter(Boolean).join('.') : targetLabel;
    units.push(
      buildSemanticUnit(db, {
        channel: g.channel,
        play: g.play,
        selection: sel,
        amount: g.amount,
      })
    );
  }
  return units;
}
