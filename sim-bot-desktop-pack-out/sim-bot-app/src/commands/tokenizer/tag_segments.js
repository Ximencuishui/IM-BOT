/**
 * PRD 3.2 词法打标：金额 / 对象 / 玩法 / 地区 四类数据段（轻量启发式）
 */
import { listSynonymPairs } from '../alias_resolver.js';
import { INBOUND_ORDER_CN_AMOUNT_CLASS } from '../pipeline/inbound_filter.js';

const ZODIAC = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';
const SET_NAMES =
  /单|双|大|小|红波|蓝波|绿波|尾数|合单|合双|大单|小单|大双|小双|家野|天地|前后/u;

function aliasRegex(words) {
  const esc = words
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return esc.length ? new RegExp(esc.join('|'), 'gu') : null;
}

function collectAliases(db, scope) {
  return listSynonymPairs(db, scope).map((r) => r.alias_word);
}

/**
 * @returns {{ amount: string[], target: string[], play: string[], region: string[] }}
 */
export function tagLineSegments(db, line) {
  const text = String(line || '').trim();
  const amount = [];
  const target = [];
  const play = [];
  const region = [];

  if (!text) return { amount, target, play, region };

  const regionRe = aliasRegex(collectAliases(db, 'guide_word'));
  const playRe = aliasRegex(collectAliases(db, 'category_word'));
  const amountUnitRe = aliasRegex(collectAliases(db, 'amount_unit'));

  if (regionRe) {
    for (const m of text.matchAll(regionRe)) region.push(m[0]);
  }
  if (playRe) {
    for (const m of text.matchAll(playRe)) play.push(m[0]);
  }

  const ballRe = /\b(0?[1-9]|[1-4][0-9])\b/g;
  for (const m of text.matchAll(ballRe)) target.push(m[1].padStart(2, '0'));

  const zodiacRe = new RegExp(`[${ZODIAC}]`, 'gu');
  for (const m of text.matchAll(zodiacRe)) target.push(m[0]);

  if (SET_NAMES.test(text)) {
    for (const m of text.matchAll(SET_NAMES)) target.push(m[0]);
  }

  const eachRe = new RegExp(
    `(?:各|个数|每个|各数)\\s*([\\d${INBOUND_ORDER_CN_AMOUNT_CLASS}]+)(?:${amountUnitRe ? `(?:${amountUnitRe.source})` : '(?:元|米|块)'})?`,
    'gu'
  );
  for (const m of text.matchAll(eachRe)) amount.push(m[0]);

  const unitSuffix = amountUnitRe ? amountUnitRe.source : '元|米|块|闷';
  const plainAmt = new RegExp(`(\\d+(?:\\.\\d+)?)(?=${unitSuffix})`, 'gu');
  for (const m of text.matchAll(plainAmt)) amount.push(m[0]);

  return { amount, target, play, region };
}
