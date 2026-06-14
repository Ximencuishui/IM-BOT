import fs from 'fs';
import path from 'path';

const DEFAULT_MAX_MB = 20;
const DEFAULT_KEEP = 2;
const DEFAULT_MAX_LINE = 2048;

function maxLogBytes() {
  const mb = Number(process.env.SIM_BOT_LOG_MAX_MB || DEFAULT_MAX_MB);
  return Math.max(1, mb) * 1024 * 1024;
}

function maxLineLen() {
  return Math.max(256, Number(process.env.SIM_BOT_LOG_MAX_LINE || DEFAULT_MAX_LINE));
}

function keepRotatedCount() {
  return Math.max(1, Math.min(5, Number(process.env.SIM_BOT_LOG_KEEP || DEFAULT_KEEP)));
}

/**
 * 侧车日志轮转：node-server.log → .1 → .2（超出 SIM_BOT_LOG_MAX_MB 时）
 */
export function rotateLogFileIfNeeded(logPath) {
  const p = logPath ? path.resolve(String(logPath)) : '';
  if (!p || !fs.existsSync(p)) return;
  try {
    const st = fs.statSync(p);
    if (st.size < maxLogBytes()) return;
    const dir = path.dirname(p);
    const base = path.basename(p);
    const keep = keepRotatedCount();
    const oldest = path.join(dir, `${base}.${keep}`);
    if (fs.existsSync(oldest)) fs.unlinkSync(oldest);
    for (let i = keep - 1; i >= 1; i -= 1) {
      const from = path.join(dir, `${base}.${i}`);
      const to = path.join(dir, `${base}.${i + 1}`);
      if (fs.existsSync(from)) fs.renameSync(from, to);
    }
    const first = path.join(dir, `${base}.1`);
    fs.renameSync(p, first);
    fs.writeFileSync(p, '', { encoding: 'utf8' });
    console.log(
      new Date().toISOString(),
      '-',
      `[log] 已轮转 ${base}（超过 ${Math.round(st.size / 1024 / 1024)}MB）`
    );
  } catch (e) {
    console.warn(new Date().toISOString(), '-', `[log] 轮转失败: ${e?.message || e}`);
  }
}

function clipArg(arg) {
  const max = maxLineLen();
  if (arg == null) return arg;
  if (typeof arg === 'string') {
    if (arg.length <= max) return arg;
    return `${arg.slice(0, max)}…[+${arg.length - max} chars]`;
  }
  if (typeof arg === 'object') {
    try {
      const s = JSON.stringify(arg);
      if (s.length <= max) return arg;
      return `${s.slice(0, max)}…[+${s.length - max} chars]`;
    } catch {
      return arg;
    }
  }
  return arg;
}

function clipArgs(args) {
  return args.map(clipArg);
}

/** 桌面侧车用 logger：启动时轮转；debug 仅 DEBUG=1；超长行截断 */
export function createSidecarLogger() {
  const diag = process.env.SIM_BOT_DIAG_LOG;
  if (diag) rotateLogFileIfNeeded(diag);

  const prefix = () => new Date().toISOString();
  return {
    info: (...a) => console.log(prefix(), '-', ...clipArgs(a)),
    warn: (...a) => console.warn(prefix(), '-', ...clipArgs(a)),
    error: (...a) => console.error(prefix(), '-', ...clipArgs(a)),
    debug: (...a) => {
      if (process.env.DEBUG === '1') console.log(prefix(), '-', ...clipArgs(a));
    },
  };
}

/** Hook 原始 JSON 体积摘要（避免 info 打全量） */
export function hookRawPayloadSummary(raw) {
  try {
    const bytes = Buffer.byteLength(JSON.stringify(raw ?? {}), 'utf8');
    return { raw_kb: Math.round(bytes / 1024), raw_bytes: bytes };
  } catch {
    return { raw_kb: 0, raw_bytes: 0 };
  }
}
