/** PRD 3.1 入站三级路由（纯 JS，供 route / rust_bridge 共用） */
import {
  inboundTextHasOrderDigits,
  looksLikeDrawCommandLine,
  looksLikeInboundOrderAttempt,
} from './inbound_filter.js';
import { listInstructionMarkerWords } from '../alias_resolver.js';

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function instructionPatternFromDb(db) {
  const words = listInstructionMarkerWords(db);
  if (!words.length) return null;
  return new RegExp(words.map(escapeRegExp).join('|'), 'u');
}

/**
 * @returns {'empty'|'instruction'|'drop'|'order'}
 */
export function classifyInboundCore(text, { isInstruction, db } = {}) {
  const t = String(text || '').trim();
  if (!t) return 'empty';
  if (looksLikeDrawCommandLine(t)) return 'instruction';
  if (typeof isInstruction === 'function' && isInstruction(t)) return 'instruction';
  const instRe = instructionPatternFromDb(db);
  if (instRe && instRe.test(t)) return 'instruction';
  if (!inboundTextHasOrderDigits(t, db)) return 'drop';
  if (!looksLikeInboundOrderAttempt(t, db)) return 'drop';
  return 'order';
}
