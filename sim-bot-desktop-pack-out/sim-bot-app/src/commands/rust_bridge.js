/**
 * PRD Rust 引擎桥接：USE_RUST_PRD=1 时调用 desktop-tauri 构建的 sim-bot-prd CLI
 */
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';
import { getMachineSecretKey } from '../db/integrity.js';
import { specialCodeRiskProfit, teHousePnlIfBallDraws } from './risk_engine/index.js';
import { classifyInboundCore } from './pipeline/classify_core.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function findPrdCli() {
  if (process.env.SIM_BOT_PRD_CLI) {
    const p = path.resolve(process.env.SIM_BOT_PRD_CLI);
    if (fs.existsSync(p)) return p;
  }
  const candidates = [
    path.join(__dirname, '../../desktop-tauri/src-tauri/target/debug/sim-bot-prd.exe'),
    path.join(__dirname, '../../desktop-tauri/src-tauri/target/release/sim-bot-prd.exe'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

function callRust(op, payload, { timeoutMs = 5000 } = {}) {
  const cli = findPrdCli();
  if (!cli || process.env.USE_RUST_PRD !== '1') return null;
  try {
    const r = spawnSync(cli, [], {
      input: JSON.stringify({ op, ...payload }),
      encoding: 'utf8',
      timeout: timeoutMs,
      windowsHide: true,
      env: {
        ...process.env,
        SIM_BOT_ROOT: process.env.SIM_BOT_ROOT || path.join(__dirname, '../..'),
        SIM_BOT_NODE_EXE: process.env.SIM_BOT_NODE_EXE || process.execPath,
      },
    });
    if (r.status !== 0 || !r.stdout) return null;
    return JSON.parse(r.stdout.trim());
  } catch {
    return null;
  }
}

export function rustEngineAvailable() {
  return Boolean(findPrdCli()) && process.env.USE_RUST_PRD === '1';
}

/** 主引擎入口走 Rust 编排（可设 USE_RUST_ENGINE=0 关闭） */
export function rustEngineMainEntryEnabled() {
  return rustEngineAvailable() && process.env.USE_RUST_ENGINE !== '0';
}

/**
 * Rust sim-bot-prd execute：handled=false 时回退 JS；drop 时返回 null
 * @returns {object|null|undefined} undefined = Rust 未响应，走 JS 直连
 */
export function executeViaRustEngine(db, wxGroupId, text, options = {}) {
  const dbPath = db?.sqlitePath;
  if (!dbPath) return undefined;
  db.persist?.();
  const rust = callRust(
    'execute',
    {
      db_path: path.resolve(dbPath),
      wx_group_id: wxGroupId ?? null,
      text: String(text ?? ''),
      sender_wxid: String(options.senderWxid || ''),
      persist: options.persist !== false,
      wx_msg_id: String(options.wxMsgId || ''),
      wx_new_msg_id: String(options.wxNewMsgId || ''),
    },
    { timeoutMs: Number(process.env.RUST_ENGINE_TIMEOUT_MS || 120000) }
  );
  if (!rust || rust.error) return undefined;
  if (rust.handled === false) return undefined;
  if (typeof db.reloadFromDisk === 'function') db.reloadFromDisk();
  if (rust.drop) return null;
  return rust.result ?? null;
}

export function computeSpecialCodeRisk(opts) {
  const js = specialCodeRiskProfit(opts);
  const rust = callRust('risk', {
    total_special_amount: opts.totalSpecialAmount,
    bet_on_number: opts.betOnNumber,
    water_rate: opts.waterRate,
    payout_odds: opts.payoutOdds,
  });
  if (rust && typeof rust.profit === 'number') return rust.profit;
  return js;
}

export function computeTeHousePnl(stake, payoutOdds, totalTe, totalWaterTe) {
  const js = teHousePnlIfBallDraws(stake, payoutOdds, totalTe, totalWaterTe);
  const rust = callRust('te_pnl', {
    stake,
    payout_odds: payoutOdds,
    total_te: totalTe,
    total_water_te: totalWaterTe,
  });
  if (rust && typeof rust.pnl === 'number') return rust.pnl;
  return js;
}

export function classifyInboundRust(text, { isInstruction } = {}) {
  const isInst = typeof isInstruction === 'function' ? isInstruction(text) : false;
  const rust = callRust('classify', { text, is_instruction: isInst });
  if (rust?.route) return rust.route;
  return classifyInboundCore(text, { isInstruction });
}

export function verifyIntegrityRust(expireData, cipher, savedHash) {
  const key = getMachineSecretKey();
  const payload = `${String(expireData || '')}${String(cipher || '')}`;
  const js = crypto.createHmac('sha256', key).update(payload, 'utf8').digest('hex') === String(savedHash);
  const rust = callRust('integrity_verify', {
    expire_data: expireData,
    cipher,
    saved_hash: savedHash,
  });
  if (rust && typeof rust.ok === 'boolean') return rust.ok;
  return js;
}

export function computeIntegrityHashRust(expireData, cipher) {
  const key = getMachineSecretKey();
  const payload = `${String(expireData || '')}${String(cipher || '')}`;
  const js = crypto.createHmac('sha256', key).update(payload, 'utf8').digest('hex');
  const rust = callRust('integrity_hash', { expire_data: expireData, cipher });
  if (rust?.hash) return rust.hash;
  return js;
}
