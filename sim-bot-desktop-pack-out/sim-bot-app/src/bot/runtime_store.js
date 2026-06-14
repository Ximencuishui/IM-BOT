/** 机器人入站处理开关与工作日志（SQLite app_settings / bot_work_logs） */

export const BOT_INBOUND_KEY = 'bot_inbound_enabled';
export const BOT_RUNTIME_STARTED_KEY = 'bot_runtime_started_at';

const MAX_WORK_LOGS = 800;

export function getBotInboundEnabled(db) {
  const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BOT_INBOUND_KEY);
  /** 无记录时视为开启，与库内默认 bot_inbound_enabled=1 一致 */
  if (!row) return true;
  const v = String(row.value || '').toLowerCase();
  return v !== '0' && v !== 'false' && v !== 'off';
}

export function setBotInboundEnabled(db, enabled) {
  const v = enabled ? '1' : '0';
  const row = db.prepare('SELECT key FROM app_settings WHERE key = ?').get(BOT_INBOUND_KEY);
  if (row) {
    db.prepare(`UPDATE app_settings SET value = ?, updated_at = datetime('now') WHERE key = ?`).run(
      v,
      BOT_INBOUND_KEY
    );
  } else {
    db.prepare(`INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`).run(
      BOT_INBOUND_KEY,
      v
    );
  }
}

/** 启动时写入本轮开始时间；暂停时清除（前端展示「启动时间 / 运行时间」） */
export function syncBotRuntimeStartedAt(db, enabled) {
  if (enabled) {
    const row = db.prepare('SELECT key FROM app_settings WHERE key = ?').get(BOT_RUNTIME_STARTED_KEY);
    if (row) {
      db.prepare(
        `UPDATE app_settings SET value = datetime('now'), updated_at = datetime('now') WHERE key = ?`
      ).run(BOT_RUNTIME_STARTED_KEY);
    } else {
      db.prepare(
        `INSERT INTO app_settings (key, value, updated_at) VALUES (?, datetime('now'), datetime('now'))`
      ).run(BOT_RUNTIME_STARTED_KEY);
    }
  } else {
    db.prepare('DELETE FROM app_settings WHERE key = ?').run(BOT_RUNTIME_STARTED_KEY);
  }
}

export function appendBotWorkLog(db, level, message, detailJson = null) {
  const detail = detailJson == null ? null : String(detailJson);
  db.prepare(
    `INSERT INTO bot_work_logs (level, message, detail_json, created_at)
     VALUES (?, ?, ?, datetime('now'))`
  ).run(String(level || 'info'), String(message || '').slice(0, 2000), detail);
  pruneBotWorkLogs(db);
}

function pruneBotWorkLogs(db) {
  const row = db.prepare('SELECT COUNT(*) AS n FROM bot_work_logs').get();
  const n = Number(row?.n || 0);
  if (n <= MAX_WORK_LOGS) return;
  const del = n - MAX_WORK_LOGS;
  db.prepare(
    `DELETE FROM bot_work_logs WHERE id IN (SELECT id FROM bot_work_logs ORDER BY id ASC LIMIT ?)`
  ).run(del);
}

/** 记录有价值的入站处理结果（避免每条群聊都打日志） */
export function recordInboundWorkSummary(db, ex, skipReason, ruleHits) {
  if (!getBotInboundEnabled(db)) return;

  const preview = String(ex.content || '').trim().slice(0, 200);
  const handled = new Set(['command_route_handled', 'revoke_event_handled', 'private_report_handled']);
  if (handled.has(skipReason)) {
    appendBotWorkLog(
      db,
      'info',
      `[${skipReason}] ${preview || '—'}`,
      JSON.stringify({ wx_group_id: ex.groupId || null, sender_wxid: ex.senderWxid || null })
    );
    return;
  }
  if (Array.isArray(ruleHits) && ruleHits.length > 0) {
    appendBotWorkLog(
      db,
      'info',
      `[rule_hit] ${preview || '—'}`,
      JSON.stringify({
        rule_ids: ruleHits.map((h) => h.ruleId),
        wx_group_id: ex.groupId || null,
      })
    );
  }
}
