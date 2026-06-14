/**
 * SQLite 快照备份：每日一次（可调整钟点）、保留最近 N 天；支持手动备份。
 * 备份目录：环境变量默认值，可被 app_settings.backup_dir（控制台）覆盖。
 */
import fs from 'fs';
import path from 'path';

const BACKUP_DIR_SETTING_KEY = 'backup_dir';

function safeDailyName(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `sim_bot_daily_${y}-${m}-${d}.db`;
}

function safeManualName(date = new Date()) {
  const iso = date.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `sim_bot_manual_${iso}.db`;
}

function isManagedBackupFilename(name) {
  return /^sim_bot_(daily_\d{4}-\d{2}-\d{2}|manual_.+)\.db$/.test(name);
}

function resolveStoredPath(sqlitePath, defaultBackupDir, rawStored) {
  const t = rawStored != null ? String(rawStored).trim() : '';
  if (!t) return path.normalize(defaultBackupDir);
  const resolved = path.isAbsolute(t) ? t : path.join(path.dirname(sqlitePath), t);
  return path.normalize(resolved);
}

export function createDataBackupService(options) {
  const {
    db,
    sqlitePath,
    defaultBackupDir,
    retentionDays: rd = 7,
    backupHour: bhRaw = 3,
    logger,
  } = options;

  if (!sqlitePath) throw new Error('sqlitePath required');
  if (!defaultBackupDir) throw new Error('defaultBackupDir required');
  if (!db?._raw) throw new Error('db._raw missing');

  const retentionDays = Math.min(90, Math.max(1, Number(rd) || 7));
  const backupHour = Math.min(23, Math.max(0, Math.floor(Number(bhRaw))));

  let schedulerTimer = null;
  let lastScheduledDate = null;

  function getBackupDirRawFromDb() {
    const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BACKUP_DIR_SETTING_KEY);
    const v = row?.value != null ? String(row.value).trim() : '';
    return v;
  }

  function getResolvedBackupDir() {
    return resolveStoredPath(sqlitePath, defaultBackupDir, getBackupDirRawFromDb() || '');
  }

  function pruneByAge() {
    const backupDir = getResolvedBackupDir();
    if (!fs.existsSync(backupDir)) return [];
    const maxAgeMs = Math.max(1, retentionDays) * 24 * 60 * 60 * 1000;
    const now = Date.now();
    const removed = [];
    for (const name of fs.readdirSync(backupDir)) {
      if (!isManagedBackupFilename(name)) continue;
      const full = path.join(backupDir, name);
      let st;
      try {
        st = fs.statSync(full);
      } catch {
        continue;
      }
      if (now - st.mtimeMs > maxAgeMs) {
        fs.unlinkSync(full);
        removed.push(name);
      }
    }
    if (removed.length && typeof logger?.info === 'function') {
      logger.info(`[backup] 已删除超 ${retentionDays} 天备份: ${removed.join(', ')}`);
    }
    return removed;
  }

  /** 从内存 SQLite 导出与主库一致的快照字节 */
  function writeSnapshot(destPath) {
    const buf = Buffer.from(db._raw.export());
    fs.mkdirSync(path.dirname(destPath), { recursive: true });
    fs.writeFileSync(destPath, buf);
    return buf.length;
  }

  function listFiles() {
    const backupDir = getResolvedBackupDir();
    if (!fs.existsSync(backupDir)) return [];
    const out = [];
    for (const name of fs.readdirSync(backupDir)) {
      if (!isManagedBackupFilename(name)) continue;
      const full = path.join(backupDir, name);
      let st;
      try {
        st = fs.statSync(full);
      } catch {
        continue;
      }
      out.push({
        name,
        bytes: st.size,
        mtime_iso: st.mtime.toISOString(),
      });
    }
    out.sort((a, b) => (a.mtime_iso < b.mtime_iso ? 1 : -1));
    return out;
  }

  function tryWriteDailyBackup(now, reason) {
    const backupDir = getResolvedBackupDir();
    const pad = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    if (pad === lastScheduledDate) return null;

    const dest = path.join(backupDir, safeDailyName(now));
    try {
      const bytes = writeSnapshot(dest);
      pruneByAge();
      lastScheduledDate = pad;
      if (typeof logger?.info === 'function') logger.info(`[backup] ${reason} 完成`, dest);
      return {
        ok: true,
        type: 'scheduled',
        filename: safeDailyName(now),
        path: dest,
        bytes,
      };
    } catch (e) {
      if (typeof logger?.warn === 'function') logger.warn(`[backup] ${reason} 失败`, e?.message || e);
      return {
        ok: false,
        type: 'scheduled',
        error: String(e?.message || e),
      };
    }
  }

  /** 每日 backupHour:00 整点一次；若错过整点则当天在已过钟点后补跑一次 */
  function runScheduledIfDue(now = new Date()) {
    const backupDir = getResolvedBackupDir();
    const pad = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const dest = path.join(backupDir, safeDailyName(now));
    const alreadyFile = fs.existsSync(dest);

    if (pad === lastScheduledDate) return null;

    const atWindow =
      now.getHours() === backupHour && now.getMinutes() === 0;
    const catchUp =
      !alreadyFile &&
      now.getHours() >= backupHour &&
      lastScheduledDate !== pad;

    if (!atWindow && !catchUp) return null;

    return tryWriteDailyBackup(now, atWindow ? '定时备份' : '补跑备份');
  }

  /** 每分钟检查是否在「整点的定时备份时刻」并完成当日一次备份 */
  function startScheduler() {
    if (schedulerTimer) return;
    schedulerTimer = setInterval(() => {
      try {
        runScheduledIfDue();
      } catch (e) {
        if (typeof logger?.warn === 'function') logger.warn('[backup] scheduler', e?.message || e);
      }
    }, 60 * 1000);
    try {
      runScheduledIfDue(new Date());
    } catch {}
  }

  function runManual() {
    const backupDir = getResolvedBackupDir();
    const fname = safeManualName();
    const dest = path.join(backupDir, fname);
    try {
      const bytes = writeSnapshot(dest);
      pruneByAge();
      if (typeof logger?.info === 'function') logger.info('[backup] 手动备份完成', dest);
      return { ok: true, type: 'manual', filename: fname, path: dest, bytes };
    } catch (e) {
      if (typeof logger?.warn === 'function') logger.warn('[backup] 手动备份失败', e?.message || e);
      return { ok: false, type: 'manual', error: String(e?.message || e) };
    }
  }

  function getStatus() {
    const raw = getBackupDirRawFromDb();
    const resolved = getResolvedBackupDir();
    return {
      backup_dir: resolved,
      backup_dir_setting: raw,
      backup_dir_default: path.normalize(defaultBackupDir),
      retention_days: retentionDays,
      backup_hour_local: backupHour,
      last_scheduled_date: lastScheduledDate,
      hint: `每日 ${backupHour}:00（服务器本地时钟）自动生成一份；最多保留最近 ${retentionDays} 天；手动备份的文件名包含 manual。路径可在下方配置，留空则使用默认目录。`,
      files: listFiles(),
    };
  }

  /**
   * @param {string} userInput 空字符串表示恢复默认（环境变量/建库旁 backups）
   */
  function setBackupDir(userInput) {
    const trimmed = userInput == null ? '' : String(userInput).trim();
    if (!trimmed) {
      try {
        db.prepare('DELETE FROM app_settings WHERE key = ?').run(BACKUP_DIR_SETTING_KEY);
      } catch (e) {
        return { ok: false, error: String(e?.message || e) };
      }
      if (typeof logger?.info === 'function') logger.info('[backup] 已恢复默认备份目录');
      return {
        ok: true,
        backup_dir: getResolvedBackupDir(),
        backup_dir_setting: '',
        backup_dir_default: path.normalize(defaultBackupDir),
      };
    }

    let resolved;
    try {
      resolved = resolveStoredPath(sqlitePath, defaultBackupDir, trimmed);
    } catch (e) {
      return { ok: false, error: `路径无效: ${e?.message || e}` };
    }

    try {
      fs.mkdirSync(resolved, { recursive: true });
      const testFile = path.join(resolved, `.sim_bot_backup_write_test_${Date.now()}`);
      fs.writeFileSync(testFile, 'ok');
      fs.unlinkSync(testFile);
    } catch (e) {
      return { ok: false, error: `无法写入该目录: ${e?.message || e}` };
    }

    try {
      db.prepare(
        `INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`
      ).run(BACKUP_DIR_SETTING_KEY, trimmed);
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }

    if (typeof logger?.info === 'function') logger.info('[backup] 备份目录已更新', resolved);
    return {
      ok: true,
      backup_dir: getResolvedBackupDir(),
      backup_dir_setting: trimmed,
      backup_dir_default: path.normalize(defaultBackupDir),
    };
  }

  return {
    startScheduler,
    runManual,
    getStatus,
    setBackupDir,
    pruneByAge,
  };
}
