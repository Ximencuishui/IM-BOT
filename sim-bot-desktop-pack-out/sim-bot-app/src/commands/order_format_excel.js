/**
 * 《玩法说明.xlsx》「下单指令样本」格式化列 ↔ 结构化预览互转与契约比较
 */
import { playCategoriesEquivalent } from './play_spec_catalog.js';
import {
  buildSemanticUnit,
  collectSemanticUnitsForInput,
  matchSemanticUnits,
  unitsFromPreviewLines,
} from './play_spec_semantic.js';
import { executeConfiguredCommand, inboundOrderContentLooksMalformed } from './engine.js';

const ZODIAC = '鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬';

const EXCEL_PLAY_LABEL_RE =
  /^(三中三|三中二|二中二|五不中|七不中|九不中|十不中|十二不中|复式三中三|复式二中二|复式三连肖|复式二连肖|五连肖|四连肖|三连肖|二连肖|平特四连肖|平特五连肖|平特四连|平特三连|平特二连|平特一肖|平特尾|平尾|平特|六肖中特|五肖中特|双数|单数|红波单|红波双|绿波单|绿波双|蓝波单|蓝波双|红波特|绿波特|蓝波特|红波数|绿波数|蓝波数|红波|绿波|蓝波|大数|小数)/u;

const EXCEL_PLAY_LEAD_RE =
  /^(三中三|三中二|二中二|五不中|七不中|九不中|十不中|十二不中|五连肖|四连肖|三连肖|二连肖|复式三连肖|复式二连肖|复式三中三|平特一肖|平特四连肖|平特五连肖|平特四连|平特三连|平特二连|平特|六肖中特|五肖中特|双数|单数|红波单|红波双|绿波单|绿波双|蓝波单|蓝波双|红波特|绿波特|蓝波特|红波|绿波|蓝波|红波数|绿波数|蓝波数|大数|小数)(.+)$/u;

function excelPlayLabelOnly(label) {
  return String(label || '')
    .replace(/[（(].*$/u, '')
    .trim();
}

function isExcelPlayLabel(label) {
  return EXCEL_PLAY_LABEL_RE.test(excelPlayLabelOnly(label));
}

function isExcelChannelLabel(label) {
  const t = normalizeChannelName(label);
  if (t === '新澳门' || t === '香港') return true;
  return /^(?:新)?澳|港|门$/u.test(String(label || '').trim());
}

export function normalizeChannelName(ch) {
  const t = String(ch || '').trim().replace(/\s+/g, '');
  if (!t || t === '澳门' || t === '奥' || t === '噢' || t === '澳') return '新澳门';
  if (/^新澳(?!门)/u.test(t)) return '新澳门';
  if (/^新{2,}澳门$/u.test(t)) return '新澳门';
  if (t === '香' || t === '港') return '香港';
  return t;
}

export function normalizeFormatText(s) {
  return String(s || '')
    .replace(/\s+/g, '')
    .replace(/，/g, '；')
    .replace(/,/g, ',')
    .replace(/[米斤块A]/g, '元')
    .replace(/十元/g, '10元')
    .replace(/二十/g, '20')
    .replace(/三十/g, '30')
    .replace(/三十五/g, '35')
    .replace(/五十/g, '50')
    .replace(/八十/g, '80')
    .replace(/一百/g, '100')
    .replace(/澳门:/g, '新澳门:')
    .replace(/^澳:/u, '新澳门:');
}

export function isExcelExpectError(formatted) {
  const raw = String(formatted || '');
  return /识别为报错|无法识别|报错|■【此消息有问题|格式错误/u.test(raw);
}

/** @returns {{ skip?: boolean, expectError?: boolean, note?: string, channel?: string, play?: string, selection?: string, amount?: number, algo?: string }[]} */
export function parseExcelFormattedSegments(formatted) {
  const raw = String(formatted || '').trim();
  if (!raw) return [];
  if (isExcelExpectError(raw)) {
    return [{ skip: true, expectError: true, note: raw }];
  }
  const noteMatch = raw.match(/（总金额[:：]?\d+）/u);
  const body = raw.replace(/（总金额[:：]?\d+）/gu, '').trim();
  const parts = body.split(/[；;\r\n]+/).map((p) => p.trim()).filter(Boolean);
  const out = [];
  let defaultChannel = '新澳门';
  let lastPlay = '特';
  for (let part of parts) {
    part = String(part || '')
      .replace(/\s*金额合计[:：]?\d+\s*/u, '')
      .trim();
    if (!part) continue;
    let seg = parseExcelSegment(part, defaultChannel);
    if (!seg && !/[：:]/.test(part) && /^(复式|复试|平特|三连|四连|五连|二连|特肖)/u.test(part)) {
      seg = parseExcelSegment(`${defaultChannel}:${part}`, defaultChannel);
    }
    if (!seg && !/[：:]/.test(part)) {
      seg = parseExcelSegment(`${defaultChannel}:${lastPlay}:${part}`, defaultChannel);
    }
    if (!seg && !/[：:]/.test(part)) {
      seg = parseExcelSegment(`${defaultChannel}:${part}`, defaultChannel);
    }
    if (seg) {
      defaultChannel = normalizeChannelName(seg.channel) || defaultChannel;
      if (seg.play) lastPlay = seg.play;
      out.push(seg);
    }
  }
  if (noteMatch) out.push({ skip: true, note: noteMatch[0] });
  return out;
}

function parseExcelAmountAndSelection(rest) {
  let body = String(rest || '')
    .replace(/\*注.*$/u, '')
    .replace(/，合计金额[:：]?\d+元?/u, '')
    .trim();
  let algo = '各';
  let amount = 0;
  const amtM =
    body.match(/(?:各|组)([\d.]+)元?$/u) ||
    body.match(/[.。．]组([\d.]+)元?$/u) ||
    body.match(/组([\d.]+)元?$/u);
  if (amtM) {
    amount = Number(amtM[1]);
    algo = /组/.test(amtM[0]) && !/各/.test(body.slice(-amtM[0].length - 2)) ? '组' : '各';
    body = body.slice(0, body.length - amtM[0].length);
  }
  body = body.replace(/^[.:：]+/u, '').replace(/[.:：]+$/u, '').trim();
  return { selection: body.trim(), amount, algo };
}

function parseExcelSegment(part, defaultChannel = '新澳门') {
  const p = String(part || '').trim();
  if (!p) return null;
  const head = p.match(/^([^:：]+)[:：](.+)$/u);
  if (!head) return null;

  const label = head[1].trim();
  const rest = head[2].trim();

  if (/合计金额/u.test(label)) {
    return { skip: true, note: p };
  }

  if (isExcelPlayLabel(label) && !isExcelChannelLabel(label)) {
    const play = excelPlayLabelOnly(label);
    const { selection, amount, algo } = parseExcelAmountAndSelection(rest);
    return {
      channel: normalizeChannelName(defaultChannel),
      play,
      selection,
      amount,
      algo,
    };
  }

  const channel = normalizeChannelName(label);
  let play = '特';
  let body = rest;
  const nestedPlay = body.match(/^(复式三中三|复式二中二|三中三|三中二|二中二|五不中)(.+)$/u);
  if (nestedPlay) {
    play = excelPlayLabelOnly(nestedPlay[1]);
    body = nestedPlay[2];
  } else {
  const playColon = body.match(/^([^.:各组（(]+)[:：](.+)$/u);
  if (playColon && !/^\d{1,2}(?:\.\d{1,2})+/u.test(playColon[1])) {
    play = excelPlayLabelOnly(playColon[1]);
    body = playColon[2];
    const innerPlay = body.match(/^(复式三中三|复式二中二|三中三|三中二|二中二|五不中)[:：](.+)$/u);
    if (innerPlay && /肖中特/u.test(play)) {
      play = excelPlayLabelOnly(innerPlay[1]);
      body = innerPlay[2];
    }
  } else {
    const playParen = body.match(
      /^(三中三|三中二|二中二|五不中|七不中|九不中|十不中|十二不中|五连肖|四连肖|三连肖|复式三连肖|复式二连肖|复式三中三|平特一肖|平特四连肖|平特五连肖|平特四连|平特三连|平特二连|平特|六肖中特|五肖中特|双数|单数|红波单|红波双|绿波单|绿波双|蓝波单|蓝波双|红波特|绿波特|蓝波特|红波|绿波|蓝波|红波数|绿波数|蓝波数|大数|小数)(?:[（(][^）)]*[）)])?(.+)$/u
    );
    const playLead = playParen || body.match(EXCEL_PLAY_LEAD_RE);
    if (playLead) {
      play = excelPlayLabelOnly(playLead[1]);
      body = playLead[2];
    }
  }
  }

  const { selection, amount, algo } = parseExcelAmountAndSelection(body);
  return { channel, play, selection, amount, algo };
}

/** 将 parseExcelFormattedSegments 的段展开为语义单元（连肖多组按 `.` 拆开） */
export function excelSegmentsToSemanticUnits(db, segs) {
  const units = [];
  for (const s of segs || []) {
    if (s?.skip || s?.expectError) continue;
    let play = String(s.play || '特').trim();
    let sel = String(s.selection || '').trim();
    const amt = Number(s.amount) || 0;
    if (/^二连肖|^平特二/u.test(play)) {
      play = '平特二连肖';
    }
    sel = sel.replace(/[（(][^）)]*[）)]/gu, '').trim();
    if ((/连肖|平特四|平特五|平特二/u.test(play) || /复式|复试/u.test(play)) && /[.。．]/.test(sel)) {
      const parts = sel
        .split(/[.。．]+/)
        .map((x) => x.trim())
        .filter((x) => extractZodiacCompactFromSel(x));
      if (parts.length > 1 && amt > 0) {
        const rowPlay = /复式|复试/u.test(play) ? '三连肖' : play;
        for (const part of parts) {
          units.push(
            buildSemanticUnit(db, {
              channel: s.channel,
              play: rowPlay,
              selection: part,
              amount: amt,
            })
          );
        }
        continue;
      }
    }
    units.push(
      buildSemanticUnit(db, {
        channel: s.channel,
        play: s.play,
        selection: sel,
        amount: s.amount,
      })
    );
  }
  return units;
}

export function expectedToSemanticUnits(db, formatted) {
  const segs = parseExcelFormattedSegments(formatted).filter((s) => !s.skip && !s.expectError);
  return excelSegmentsToSemanticUnits(db, segs);
}

function extractZodiacCompactFromSel(s) {
  return String(s || '')
    .replace(/[^鼠牛虎兔龙龍蛇马馬羊猴鸡雞鷄狗猪豬]/gu, '')
    .trim();
}

/**
 * 结构化语义比较（球号集合 / 生肖 / 波色∩单双）
 */
export function compareExcelSegments(expectedSegs, lines, db = null, wxGroupId = null, rawInput = '') {
  const expRaw = expectedSegs;
  if (expRaw?.some((s) => s.expectError)) {
    const previewEmpty = !lines?.length || lines.every((r) => !r.ast);
    if (previewEmpty) return { ok: true, reason: 'expect_error' };
    if (rawInput && inboundOrderContentLooksMalformed(rawInput)) {
      return { ok: true, reason: 'expect_error_malformed' };
    }
    if (db && wxGroupId && rawInput) {
      const r = executeConfiguredCommand(db, wxGroupId, rawInput, { persist: false });
      if (r?.blocked || /无法识别|有问题/i.test(String(r?.replyText || ''))) {
        return { ok: true, reason: 'expect_error_exec' };
      }
    }
    return { ok: false, reason: 'expect_error_but_parsed' };
  }

  if (!db) {
    return { ok: false, reason: 'no_db' };
  }

  const expectedUnits = excelSegmentsToSemanticUnits(
    db,
    (expectedSegs || []).filter((s) => !s.skip && !s.expectError)
  );

  if (expectedUnits.length === 0) return { ok: false, reason: 'no_expected' };

  let actualUnits =
    wxGroupId && rawInput ? collectSemanticUnitsForInput(db, wxGroupId, rawInput) : unitsFromPreviewLines(db, lines);

  if (actualUnits.length === 0) return { ok: false, reason: 'no_actual' };

  return matchSemanticUnits(expectedUnits, actualUnits, db);
}

/**
 * 从 listOrderLineStructuralPreview 的一行生成 Excel 风格片段（展示用）
 */
export function formatPreviewLineExcel(lineRow) {
  const ast = lineRow?.ast;
  if (!ast) return null;
  const ch = normalizeChannelName(ast.channel);
  const play = String(ast.play || '特').trim();
  const clauses = ast.clauses || [];
  if (!clauses.length) return null;

  const parts = [];
  for (const cl of clauses) {
    const sel = String(cl.target_raw || '')
      .trim()
      .replace(/\s+/g, '.')
      .replace(/[，,、]/g, '.');
    const v = Number(cl.value);
    if (!Number.isFinite(v)) continue;
    const algo = String(cl.algo || '各').trim();
    if (play === '特' || play === '单双' || play === '半波') {
      const balls = sel.replace(/\s/g, '.');
      parts.push(`${ch}:${balls}.${algo === '各' ? '各' : algo}${v}元`);
    } else if (/连肖|连码|平特|平尾|不中|三中|二中|复式/u.test(play)) {
      const playLabel =
        play === '连码' && /三中三/u.test(sel) ? '三中三' : play === '平特三连' ? '三连肖' : play;
      const useColon = /连肖|复式|三连肖|五连肖|四连肖/u.test(playLabel);
      const amtWord = algo === '各' ? '各' : '组';
      if (useColon) {
        parts.push(`${ch}:${playLabel}:${sel.replace(/\./g, '')}.${amtWord}${v}元`);
      } else {
        parts.push(`${ch}:${playLabel}${sel}.${amtWord}${v}元`);
      }
    } else {
      parts.push(`${ch}:${play}${sel}.${algo}${v}元`);
    }
  }
  return parts.join('；');
}

export function formatPreviewToExcelString(preview) {
  const parts = [];
  for (const blk of preview?.blocks || []) {
    for (const row of blk.lines || []) {
      const f = formatPreviewLineExcel(row);
      if (f) parts.push(f);
    }
  }
  return parts.join('；');
}
