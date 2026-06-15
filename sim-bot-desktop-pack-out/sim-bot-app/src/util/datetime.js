/**
 * SQLite datetime('now') 为 UTC 字符串（无时区后缀）。
 * 管理台等界面按北京时间（默认 UTC+8）展示。
 */
const DEFAULT_OFFSET_HOURS = Number(process.env.BOT_DISPLAY_TZ_OFFSET_HOURS ?? 8);

function pad2(n) {
  return String(n).padStart(2, '0');
}

function formatShifted(d, offsetHours) {
  const bj = new Date(d.getTime() + offsetHours * 3600000);
  return `${bj.getUTCFullYear()}-${pad2(bj.getUTCMonth() + 1)}-${pad2(bj.getUTCDate())} ${pad2(bj.getUTCHours())}:${pad2(bj.getUTCMinutes())}:${pad2(bj.getUTCSeconds())}`;
}

/** @param {string|null|undefined} raw @param {number} [offsetHours] */
export function formatSqliteUtcForDisplay(raw, offsetHours = DEFAULT_OFFSET_HOURS) {
  const text = String(raw ?? '').trim();
  if (!text) return '—';
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(text)) {
    const d = new Date(`${text.replace(' ', 'T')}Z`);
    if (!Number.isNaN(d.getTime())) return formatShifted(d, offsetHours);
  }
  const t = new Date(text);
  if (!Number.isNaN(t.getTime())) return formatShifted(t, 0);
  return text;
}
