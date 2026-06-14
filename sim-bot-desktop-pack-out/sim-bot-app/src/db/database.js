import initSqlJs from 'sql.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  syncLegacySynonymsToAliasConfig,
  migrateAppSettingAmountUnitsToAliasConfig,
} from '../commands/alias_resolver.js';
import { purgeMisclassifiedAliasesFromDb } from '../commands/alias_guard.js';
import { allPlaySpecCategoryWords, PLAY_SPEC_CATALOG, PLAY_SPEC_EXTRA_ALIASES } from '../commands/play_spec_catalog.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** 单例，供导入与首轮 openDatabase 共用 */
let sqlJsLoadPromise = null;

export async function ensureSqlJs() {
  if (!sqlJsLoadPromise) {
    const wasmPath = path.join(__dirname, '../../node_modules/sql.js/dist/sql-wasm.wasm');
    sqlJsLoadPromise = initSqlJs({ locateFile: () => wasmPath });
  }
  return sqlJsLoadPromise;
}

/** sql.js 迁移内查单行：原生 Statement.get() 不按占位符绑定，易得到 []；须 bind + step + getAsObject */
function sqlJsSelectOne(sqlDb, sql, params = []) {
  const st = sqlDb.prepare(sql);
  const bindVals = Array.isArray(params) ? params : [...params];
  if (bindVals.length) st.bind(bindVals);
  if (!st.step()) {
    st.free();
    return undefined;
  }
  const row = st.getAsObject();
  st.free();
  return row;
}

/** sql.js 迁移内执行写语句：多占位符时勿用 statement.run(a,b,c)，须 bind([a,b,c]) */
function sqlJsRun(sqlDb, sql, params = []) {
  const st = sqlDb.prepare(sql);
  const bindVals = Array.isArray(params) ? params : [...params];
  if (bindVals.length) st.bind(bindVals);
  st.step();
  st.free();
}

function applyIncrementalMigrations(sqlDb) {
  migrate(sqlDb);
  migrateCustomRulesGlobalWxGroupId(sqlDb);
  migrateCmdRoutesGlobalWxGroupId(sqlDb);
  migrateCmdRoutesGuideCategoryUnique(sqlDb);
  migrateCmdChannelsFromExisting(sqlDb);
  migrateCmdOrderCyclesAddWeekly(sqlDb);
  migrateCmdTypeVarsTypedDefault(sqlDb);
  migrateCmdCollectionsGlobalAndCategory(sqlDb);
  migrateCmdOrdersAddBatchId(sqlDb);
  migrateCmdOrdersWxMsgIds(sqlDb);
  migrateCmdAlgoAliases(sqlDb);
  migrateCmdKeywordSynonyms(sqlDb);
  migrateCmdKeywordSynonymsInstructionScope(sqlDb);
  migrateGuideWordXinAoToMacau(sqlDb);
  migrateGuideWordMacauToLaoMacau(sqlDb);
  migrateLianXiaoCategoryAliases(sqlDb);
  migratePingTeSanLianCategoryAliases(sqlDb);
  migrateSiYouSiLianCategoryAliases(sqlDb);
  migrateSiSanLianXiaoPlayAliases(sqlDb);
  migrateGuideSynonymSingleAoToXinMacau(sqlDb);
  migrateWxGroupsAdminMeta(sqlDb);
  migrateWxGroupsOwnerOrdersFlag(sqlDb);
  migrateWxGroupsDebugOrderReply(sqlDb);
  migrateWxGroupsDebugRuleMissReply(sqlDb);
  migrateWxGroupsManagerPermission(sqlDb);
  migrateWxGroupsStrictPlayRoutes(sqlDb);
  migrateWxGroupRouteEnables(sqlDb);
  migrateCmdOrderCyclesNormalizeStartTime(sqlDb);
  migrateProductSetup(sqlDb);
  migratePrdSchema(sqlDb);
  migrateAliasBuiltinFull(sqlDb);
  migrateAliasSetChineseAmountUnits(sqlDb);
  migrateAliasImportLegacyKeyword(sqlDb);
  migrateAliasAmountAlgoYige(sqlDb);
  migrateAliasBatchOrderPhrases(sqlDb);
  migrateAliasRegressBatch2(sqlDb);
  migrateAliasSegmentTotalMarkers(sqlDb);
  migrateAliasRemoveGeEmbeddedAmount(sqlDb);
  migrateAliasSanitizeMisclassified(sqlDb);
  migrateAliasFixSanYouLianXiao(sqlDb);
  migratePlaySpecRoutesAndAliases(sqlDb);
  migrateAliasFixPingTeErLian(sqlDb);
}

function migrateAliasFixPingTeErLian(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/019_alias_fix_pingte_erlian.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasFixPingTeErLian:', e?.message || e);
  }
}

function migrateAliasSegmentTotalMarkers(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/014_alias_segment_total_markers.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasSegmentTotalMarkers:', e?.message || e);
  }
}

function migrateAliasRegressBatch2(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/013_alias_regress_batch2.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasRegressBatch2:', e?.message || e);
  }
}

function migrateAliasBatchOrderPhrases(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/012_alias_batch_order_phrases.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasBatchOrderPhrases:', e?.message || e);
  }
}

function migrateAliasRemoveGeEmbeddedAmount(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/015_alias_remove_ge_embedded_amount.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasRemoveGeEmbeddedAmount:', e?.message || e);
  }
}

function migratePlaySpecRoutesAndAliases(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/018_play_spec_routes_aliases.sql');
    if (fs.existsSync(sqlPath)) {
      const raw = fs.readFileSync(sqlPath, 'utf8');
      const body = raw
        .split('\n')
        .filter((line) => !line.trim().startsWith('--'))
        .join('\n');
      for (const stmt of body.split(';')) {
        const s = stmt.trim();
        if (s) sqlDb.exec(s);
      }
    }
  } catch (e) {
    console.warn('migratePlaySpecRoutesAndAliases sql:', e?.message || e);
  }
  try {
    const guides = ['新澳门', '老澳门', '香港', '越南'];
    const cats = allPlaySpecCategoryWords();
    const routeSql = `INSERT OR IGNORE INTO cmd_routes
       (wx_group_id, route_name, guide_word, category_word, formula_name, reply_template, priority, is_active, updated_at)
       VALUES (NULL, NULL, ?, ?, 'default_each', ?, 100, 1, datetime('now'))`;
    const tmpl = '命中{route}：目标{targets}，算法{algo}，数值{value}，结果{result}';
    for (const g of guides) {
      for (const cat of cats) {
        const st = sqlDb.prepare(routeSql);
        st.bind([g, cat, tmpl]);
        st.step();
        st.free();
      }
    }
    const aliasSql = `INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES ('PLAY', ?, ?)`;
    for (const row of PLAY_SPEC_CATALOG) {
      for (const alias of row.aliases || []) {
        if (!alias || alias === row.category) continue;
        const st = sqlDb.prepare(aliasSql);
        st.bind([row.category, alias]);
        st.step();
        st.free();
      }
    }
    for (const row of PLAY_SPEC_EXTRA_ALIASES) {
      for (const alias of row.aliases || []) {
        if (!alias || alias === row.category) continue;
        const st = sqlDb.prepare(aliasSql);
        st.bind([row.category, alias]);
        st.step();
        st.free();
      }
    }
  } catch (e) {
    console.warn('migratePlaySpecRoutesAndAliases seed:', e?.message || e);
  }
}

function migrateAliasFixSanYouLianXiao(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/017_alias_fix_san_you_lianxiao.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasFixSanYouLianXiao:', e?.message || e);
  }
}

function migrateAliasSanitizeMisclassified(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/016_alias_sanitize_misclassified.sql');
    if (fs.existsSync(sqlPath)) {
      const raw = fs.readFileSync(sqlPath, 'utf8');
      const body = raw
        .split('\n')
        .filter((line) => !line.trim().startsWith('--'))
        .join('\n');
      for (const stmt of body.split(';')) {
        const s = stmt.trim();
        if (s) sqlDb.exec(s);
      }
    }
  } catch (e) {
    console.warn('migrateAliasSanitizeMisclassified sql:', e?.message || e);
  }
  try {
    const n = purgeMisclassifiedAliasesFromDb(sqlDb);
    if (n > 0) console.log(`migrateAliasSanitizeMisclassified: removed ${n} misclassified alias row(s)`);
  } catch (e) {
    console.warn('migrateAliasSanitizeMisclassified purge:', e?.message || e);
  }
}

function migrateAliasAmountAlgoYige(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/011_alias_amount_algo_yige.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasAmountAlgoYige:', e?.message || e);
  }
}

function migrateAliasImportLegacyKeyword(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/010_alias_import_legacy_keyword.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasImportLegacyKeyword:', e?.message || e);
  }
}

function migrateAliasSetChineseAmountUnits(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/009_alias_set_chinese_amount_units.sql');
    if (!fs.existsSync(sqlPath)) return;
    const raw = fs.readFileSync(sqlPath, 'utf8');
    const body = raw
      .split('\n')
      .filter((line) => !line.trim().startsWith('--'))
      .join('\n');
    for (const stmt of body.split(';')) {
      const s = stmt.trim();
      if (s) sqlDb.exec(s);
    }
  } catch (e) {
    console.warn('migrateAliasSetChineseAmountUnits:', e?.message || e);
  }
}

/** 008：原硬编码各/金额/渠道/玩法/指令别名写入 alias_config */
function migrateAliasBuiltinFull(sqlDb) {
  try {
    const sqlPath = path.join(__dirname, '../../sql/migrations/008_alias_builtin_full.sql');
    if (fs.existsSync(sqlPath)) {
      const raw = fs.readFileSync(sqlPath, 'utf8');
      const body = raw
        .split('\n')
        .filter((line) => !line.trim().startsWith('--'))
        .join('\n');
      for (const stmt of body.split(';')) {
        const s = stmt.trim();
        if (s) sqlDb.exec(s);
      }
    }
  } catch (e) {
    console.warn('migrateAliasBuiltinFull file:', e?.message || e);
  }
  try {
    sqlDb.exec(`
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT 'REGION', canonical_word, alias_word FROM cmd_keyword_synonyms
      WHERE scope = 'guide_word' AND is_active = 1
        AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT 'PLAY', canonical_word, alias_word FROM cmd_keyword_synonyms
      WHERE scope = 'category_word' AND is_active = 1
        AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT 'SET', canonical_word, alias_word FROM cmd_keyword_synonyms
      WHERE scope = 'amount_unit' AND is_active = 1
        AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT 'INSTRUCTION', canonical_word, alias_word FROM cmd_keyword_synonyms
      WHERE scope = 'instruction' AND is_active = 1
        AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT 'AMOUNT', maps_to, alias_word FROM cmd_algo_aliases
      WHERE is_active = 1 AND TRIM(alias_word) <> '' AND TRIM(maps_to) <> '';
    `);
  } catch (e) {
    console.warn('migrateAliasBuiltinFull sync:', e?.message || e);
  }
  try {
    migrateAppSettingAmountUnitsToAliasConfig(sqlDb);
    syncLegacySynonymsToAliasConfig(sqlDb);
  } catch (e) {
    console.warn('migrateAliasBuiltinFull app_settings:', e?.message || e);
  }
}

/** 校验为 SQLite 3 主库文件头 */
export function validateSqliteFileBuffer(buffer) {
  const buf = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  if (buf.length < 18) throw new Error('文件过小或不完整');
  const head15 = buf.subarray(0, 15).toString('latin1');
  if (head15 !== 'SQLite format 3') {
    throw new Error('不是有效的 SQLite format 3 数据库文件');
  }
}

/**
 * 用上传文件替换当前运行时数据库（会先备份磁盘上的现有主库）。
 * dbWrapper 必须来自本地 wrapDb。
 */
export async function importMainDatabaseFromBuffer(dbWrapper, sqlitePath, buffer, { logger } = {}) {
  validateSqliteFileBuffer(buffer);
  const SQL = await ensureSqlJs();
  let newSqlDb;
  try {
    newSqlDb = new SQL.Database(buffer);
  } catch (e) {
    throw new Error(`无法载入 SQLite：${String(e?.message || e)}`);
  }
  applyIncrementalMigrations(newSqlDb);

  const backups = path.join(path.dirname(sqlitePath), 'backups');
  fs.mkdirSync(backups, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const priorBackupPath = path.join(backups, `sim_bot_before_import_${stamp}.db`);

  try {
    if (fs.existsSync(sqlitePath)) {
      fs.copyFileSync(sqlitePath, priorBackupPath);
      if (typeof logger?.info === 'function') {
        logger.info('[db import] 已备份当前库', priorBackupPath);
      }
    }
  } catch (e) {
    throw new Error(`备份当前库失败，已取消导入：${String(e?.message || e)}`);
  }

  dbWrapper.replaceEngine(newSqlDb);
  seedCommandMeta(dbWrapper);
  dbWrapper.persist();

  return {
    ok: true,
    prior_backup_path: fs.existsSync(priorBackupPath) ? priorBackupPath : null,
    sqlite_path: sqlitePath,
  };
}

function migrate(sqlDb) {
  sqlDb.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('super','group_admin','user')),
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wx_groups (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wx_group_id TEXT UNIQUE NOT NULL,
      name TEXT,
      group_admin_user_id INTEGER REFERENCES users(id),
      expires_at TEXT,
      is_active INTEGER DEFAULT 1,
      owner_orders_enabled INTEGER DEFAULT 1,
      debug_order_reply INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      admin_label TEXT,
      manual_owner TEXT,
      admin_remark TEXT
    );

    CREATE TABLE IF NOT EXISTS custom_rules (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wx_group_id TEXT,
      name TEXT NOT NULL,
      priority INTEGER DEFAULT 0,
      rule_type TEXT NOT NULL CHECK(rule_type IN ('keyword','regex','noop')),
      pattern TEXT NOT NULL,
      action_json TEXT,
      is_active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS activation_redemptions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code_fingerprint TEXT NOT NULL,
      raw_payload TEXT,
      wx_group_id TEXT,
      redeemed_by_user_id INTEGER,
      redeemed_at TEXT DEFAULT (datetime('now')),
      UNIQUE(code_fingerprint)
    );

    CREATE TABLE IF NOT EXISTS message_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wx_group_id TEXT,
      sender_wxid TEXT,
      content_preview TEXT,
      raw_json TEXT,
      rule_hits TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wx_contact_profiles (
      wxid TEXT PRIMARY KEY,
      nick_name TEXT,
      display_name TEXT,
      small_head_url TEXT,
      big_head_url TEXT,
      source TEXT,
      last_seen_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wx_chatroom_cache (
      room_id TEXT PRIMARY KEY,
      nick_name TEXT,
      remark TEXT,
      small_head_url TEXT,
      big_head_url TEXT,
      owner_wxid TEXT,
      owner_nick TEXT,
      member_count INTEGER DEFAULT 0,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wx_chatroom_members (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      room_id TEXT NOT NULL,
      wxid TEXT NOT NULL,
      nick_name TEXT,
      display_name TEXT,
      small_head_url TEXT,
      big_head_url TEXT,
      inviter_wxid TEXT,
      status INTEGER,
      is_owner INTEGER DEFAULT 0,
      updated_at TEXT DEFAULT (datetime('now')),
      UNIQUE(room_id, wxid)
    );

    CREATE TABLE IF NOT EXISTS cmd_collections (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wx_group_id TEXT,
      set_category TEXT DEFAULT '',
      set_name TEXT NOT NULL,
      source_set_name TEXT,
      derive_indexes_json TEXT,
      items_json TEXT,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now')),
      UNIQUE(wx_group_id, set_name)
    );

    CREATE TABLE IF NOT EXISTS cmd_formulas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      formula_name TEXT UNIQUE NOT NULL,
      pipeline_expr TEXT NOT NULL,
      description TEXT,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cmd_routes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wx_group_id TEXT,
      route_name TEXT,
      guide_word TEXT NOT NULL,
      category_word TEXT NOT NULL,
      formula_name TEXT,
      reply_template TEXT,
      priority INTEGER DEFAULT 0,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cmd_channels (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      guide_word TEXT UNIQUE NOT NULL,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cmd_order_cycles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      guide_word TEXT UNIQUE NOT NULL,
      cycle_type TEXT NOT NULL CHECK(cycle_type IN ('daily','weekly','date_list')),
      start_time TEXT DEFAULT '08:00',
      cutoff_time TEXT DEFAULT '19:00',
      date_list_json TEXT,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cmd_type_vars (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      category_word TEXT NOT NULL,
      var_name TEXT NOT NULL,
      var_type TEXT NOT NULL DEFAULT 'number' CHECK(var_type IN ('number','text')),
      default_value_number REAL,
      default_value_text TEXT,
      updated_at TEXT DEFAULT (datetime('now')),
      UNIQUE(category_word, var_name)
    );

    CREATE TABLE IF NOT EXISTS cmd_orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_batch_id TEXT,
      wx_group_id TEXT NOT NULL,
      sender_wxid TEXT NOT NULL,
      guide_word TEXT NOT NULL,
      category_word TEXT NOT NULL,
      target_label TEXT,
      algo TEXT,
      cmd_value REAL,
      item_value REAL NOT NULL,
      order_amount REAL NOT NULL,
      settlement_date TEXT NOT NULL,
      content_preview TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_cmd_orders_group_date ON cmd_orders(wx_group_id, settlement_date);
    CREATE INDEX IF NOT EXISTS idx_cmd_orders_group_sender_date ON cmd_orders(wx_group_id, sender_wxid, settlement_date);

    CREATE TABLE IF NOT EXISTS cmd_algo_aliases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      alias_word TEXT NOT NULL,
      maps_to TEXT NOT NULL,
      sort_order INTEGER DEFAULT 0,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now')),
      UNIQUE(alias_word)
    );

    CREATE TABLE IF NOT EXISTS cmd_keyword_synonyms (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      scope TEXT NOT NULL CHECK (scope IN ('guide_word','category_word','amount_unit','algo','instruction')),
      canonical_word TEXT NOT NULL,
      alias_word TEXT NOT NULL,
      sort_order INTEGER DEFAULT 0,
      is_active INTEGER DEFAULT 1,
      updated_at TEXT DEFAULT (datetime('now')),
      UNIQUE(scope, alias_word)
    );
    CREATE INDEX IF NOT EXISTS idx_cmd_keyword_synonyms_scope ON cmd_keyword_synonyms(scope, is_active);

    CREATE TABLE IF NOT EXISTS app_settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS bot_work_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      level TEXT NOT NULL,
      message TEXT NOT NULL,
      detail_json TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_bot_work_logs_created ON bot_work_logs(created_at);

    INSERT OR IGNORE INTO app_settings (key, value) VALUES ('bot_inbound_enabled', '1');

  `);
}

function migrateCmdOrdersAddBatchId(sqlDb) {
  try {
    const info = sqlDb.exec('PRAGMA table_info(cmd_orders)');
    const cols = (info?.[0]?.values || []).map((c) => String(c[1] || ''));
    if (cols.length === 0) return;
    if (!cols.includes('order_batch_id')) {
      sqlDb.exec(`ALTER TABLE cmd_orders ADD COLUMN order_batch_id TEXT`);
    }
    sqlDb.exec(`CREATE INDEX IF NOT EXISTS idx_cmd_orders_batch ON cmd_orders(order_batch_id)`);
  } catch (e) {
    console.warn('migrateCmdOrdersAddBatchId:', e?.message || e);
  }
}

/** 撤回时按微信 msgId/newMsgId 定位到订单行 */
function migrateCmdOrdersWxMsgIds(sqlDb) {
  try {
    const info = sqlDb.exec('PRAGMA table_info(cmd_orders)');
    const cols = (info?.[0]?.values || []).map((c) => String(c[1] || ''));
    if (cols.length === 0) return;
    if (!cols.includes('wx_msg_id')) {
      sqlDb.exec(`ALTER TABLE cmd_orders ADD COLUMN wx_msg_id TEXT`);
    }
    if (!cols.includes('wx_new_msg_id')) {
      sqlDb.exec(`ALTER TABLE cmd_orders ADD COLUMN wx_new_msg_id TEXT`);
    }
    sqlDb.exec(
      `CREATE INDEX IF NOT EXISTS idx_cmd_orders_revoke ON cmd_orders(wx_group_id, sender_wxid, wx_new_msg_id, wx_msg_id)`
    );
  } catch (e) {
    console.warn('migrateCmdOrdersWxMsgIds:', e?.message || e);
  }
}

function migrateCmdCollectionsGlobalAndCategory(sqlDb) {
  try {
    const info = sqlDb.exec('PRAGMA table_info(cmd_collections)');
    const cols = info?.[0]?.values || [];
    const hasCategory = cols.some((c) => c[1] === 'set_category');
    if (!hasCategory) {
      sqlDb.exec(`ALTER TABLE cmd_collections ADD COLUMN set_category TEXT DEFAULT ''`);
    }
    sqlDb.exec(`UPDATE cmd_collections SET wx_group_id = NULL WHERE wx_group_id IS NOT NULL`);
    sqlDb.exec(`
      DELETE FROM cmd_collections
      WHERE wx_group_id IS NULL
        AND id NOT IN (
          SELECT MAX(id) FROM cmd_collections WHERE wx_group_id IS NULL GROUP BY set_name
        );
    `);
    sqlDb.exec(
      `CREATE UNIQUE INDEX IF NOT EXISTS ux_cmd_collections_global_set_name
       ON cmd_collections(set_name) WHERE wx_group_id IS NULL`
    );
  } catch (e) {
    console.warn('migrateCmdCollectionsGlobalAndCategory:', e?.message || e);
  }
}

/** 旧库 custom_rules.wx_group_id 为 NOT NULL 时重建为可空，并统一为全局规则（wx_group_id 置空） */
function migrateCustomRulesGlobalWxGroupId(sqlDb) {
  try {
    const res = sqlDb.exec('PRAGMA table_info(custom_rules)');
    if (!res?.length || !res[0].values?.length) return;
    const wxCol = res[0].values.find((row) => row[1] === 'wx_group_id');
    if (!wxCol || wxCol[3] !== 1) return;
    sqlDb.exec(`
      BEGIN;
      CREATE TABLE custom_rules__new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wx_group_id TEXT,
        name TEXT NOT NULL,
        priority INTEGER DEFAULT 0,
        rule_type TEXT NOT NULL CHECK(rule_type IN ('keyword','regex','noop')),
        pattern TEXT NOT NULL,
        action_json TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
      );
      INSERT INTO custom_rules__new (id, wx_group_id, name, priority, rule_type, pattern, action_json, is_active, created_at)
        SELECT id, wx_group_id, name, priority, rule_type, pattern, action_json, is_active,
          COALESCE(created_at, datetime('now')) FROM custom_rules;
      DROP TABLE custom_rules;
      ALTER TABLE custom_rules__new RENAME TO custom_rules;
      COMMIT;
    `);
    sqlDb.exec(`UPDATE custom_rules SET wx_group_id = NULL`);
  } catch (e) {
    console.warn('migrateCustomRulesGlobalWxGroupId:', e?.message || e);
  }
}

/** 命令路由全部改为全局：清除按群绑定的 wx_group_id */
function migrateCmdRoutesGlobalWxGroupId(sqlDb) {
  try {
    sqlDb.exec(`UPDATE cmd_routes SET wx_group_id = NULL WHERE wx_group_id IS NOT NULL`);
  } catch (e) {
    console.warn('migrateCmdRoutesGlobalWxGroupId:', e?.message || e);
  }
}

/**
 * 路由表：route_name 可空；(guide_word, category_word) 全局唯一；去重后建索引
 */
function migrateCmdRoutesGuideCategoryUnique(sqlDb) {
  try {
    const idx = sqlDb.exec(
      `SELECT 1 FROM sqlite_master WHERE type='index' AND name='ux_cmd_routes_guide_cat'`
    );
    if (idx?.length && idx[0]?.values?.length) return;

    sqlDb.exec(`
      DELETE FROM cmd_routes WHERE id NOT IN (
        SELECT MAX(id) FROM cmd_routes GROUP BY guide_word, category_word
      );
    `);

    const info = sqlDb.exec('PRAGMA table_info(cmd_routes)');
    const cols = info?.[0]?.values || [];
    const rnCol = cols.find((c) => c[1] === 'route_name');
    const needRebuild = rnCol && rnCol[3] === 1;

    if (needRebuild) {
      sqlDb.exec(`
        BEGIN;
        CREATE TABLE cmd_routes__new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          wx_group_id TEXT,
          route_name TEXT,
          guide_word TEXT NOT NULL,
          category_word TEXT NOT NULL,
          formula_name TEXT,
          reply_template TEXT,
          priority INTEGER DEFAULT 0,
          is_active INTEGER DEFAULT 1,
          updated_at TEXT DEFAULT (datetime('now'))
        );
        INSERT INTO cmd_routes__new (id, wx_group_id, route_name, guide_word, category_word, formula_name, reply_template, priority, is_active, updated_at)
          SELECT id, wx_group_id, NULL, guide_word, category_word, formula_name, reply_template, priority, is_active,
            COALESCE(updated_at, datetime('now')) FROM cmd_routes;
        DROP TABLE cmd_routes;
        ALTER TABLE cmd_routes__new RENAME TO cmd_routes;
        CREATE UNIQUE INDEX IF NOT EXISTS ux_cmd_routes_guide_cat ON cmd_routes(guide_word, category_word);
        COMMIT;
      `);
    } else {
      sqlDb.exec(`CREATE UNIQUE INDEX IF NOT EXISTS ux_cmd_routes_guide_cat ON cmd_routes(guide_word, category_word)`);
    }
    sqlDb.exec(`UPDATE cmd_routes SET route_name = NULL`);
  } catch (e) {
    console.warn('migrateCmdRoutesGuideCategoryUnique:', e?.message || e);
  }
}

function migrateCmdChannelsFromExisting(sqlDb) {
  try {
    sqlDb.exec(`
      INSERT OR IGNORE INTO cmd_channels (guide_word, is_active, updated_at)
      SELECT DISTINCT TRIM(guide_word), 1, datetime('now')
      FROM cmd_routes
      WHERE TRIM(COALESCE(guide_word, '')) <> '';
    `);
    sqlDb.exec(`
      INSERT OR IGNORE INTO cmd_channels (guide_word, is_active, updated_at)
      SELECT DISTINCT TRIM(guide_word), 1, datetime('now')
      FROM cmd_order_cycles
      WHERE TRIM(COALESCE(guide_word, '')) <> '';
    `);
  } catch (e) {
    console.warn('migrateCmdChannelsFromExisting:', e?.message || e);
  }
}

function migrateCmdOrderCyclesAddWeekly(sqlDb) {
  try {
    const meta = sqlDb.exec(
      `SELECT sql FROM sqlite_master WHERE type='table' AND name='cmd_order_cycles' LIMIT 1`
    );
    const createSql = String(meta?.[0]?.values?.[0]?.[0] || '');
    if (createSql.includes("'weekly'")) return;
    sqlDb.exec(`
      BEGIN;
      ALTER TABLE cmd_order_cycles RENAME TO cmd_order_cycles__old;
      CREATE TABLE cmd_order_cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guide_word TEXT UNIQUE NOT NULL,
        cycle_type TEXT NOT NULL CHECK(cycle_type IN ('daily','weekly','date_list')),
        start_time TEXT DEFAULT '08:00',
        cutoff_time TEXT DEFAULT '19:00',
        date_list_json TEXT,
        is_active INTEGER DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now'))
      );
      INSERT INTO cmd_order_cycles
      (id, guide_word, cycle_type, start_time, cutoff_time, date_list_json, is_active, updated_at)
      SELECT
        id,
        guide_word,
        CASE WHEN cycle_type IN ('daily','date_list') THEN cycle_type ELSE 'daily' END,
        COALESCE(start_time, '08:00'),
        COALESCE(cutoff_time, '19:00'),
        date_list_json,
        COALESCE(is_active, 1),
        COALESCE(updated_at, datetime('now'))
      FROM cmd_order_cycles__old;
      DROP TABLE cmd_order_cycles__old;
      COMMIT;
    `);
  } catch (e) {
    console.warn('migrateCmdOrderCyclesAddWeekly:', e?.message || e);
  }
}

function migrateWxGroupsAdminMeta(sqlDb) {
  const tryAdd = (col) => {
    try {
      sqlDb.exec(`ALTER TABLE wx_groups ADD COLUMN ${col} TEXT`);
    } catch (e) {
      const msg = String(e?.message || e);
      if (!msg.includes('duplicate column')) {
        console.warn(`migrateWxGroupsAdminMeta ${col}:`, msg);
      }
    }
  };
  tryAdd('admin_label');
  tryAdd('manual_owner');
  tryAdd('admin_remark');
}

function migrateWxGroupsStrictPlayRoutes(sqlDb) {
  try {
    sqlDb.exec(`ALTER TABLE wx_groups ADD COLUMN strict_play_routes INTEGER NOT NULL DEFAULT 0`);
  } catch (e) {
    const msg = String(e?.message || e);
    if (!msg.includes('duplicate column')) {
      console.warn('migrateWxGroupsStrictPlayRoutes:', msg);
    }
  }
}

function migrateWxGroupRouteEnables(sqlDb) {
  try {
    sqlDb.exec(`
      CREATE TABLE IF NOT EXISTS wx_group_route_enables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wx_group_id TEXT NOT NULL,
        guide_word TEXT NOT NULL,
        category_word TEXT NOT NULL,
        is_enabled INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(wx_group_id, guide_word, category_word)
      );
      CREATE INDEX IF NOT EXISTS idx_wx_group_route_enables_wx ON wx_group_route_enables(wx_group_id);
    `);
  } catch (e) {
    console.warn('migrateWxGroupRouteEnables:', e?.message || e);
  }
}

/** PRD 四表 + 与 wx_groups / 同义词表兼容同步 */
function migratePrdSchema(sqlDb) {
  try {
    sqlDb.exec(`
      CREATE TABLE IF NOT EXISTS robot_config (
        wxid TEXT PRIMARY KEY,
        expire_date TEXT NOT NULL,
        last_card_cipher TEXT,
        integrity_hash TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS group_whitelist (
        group_id TEXT PRIMARY KEY,
        group_name TEXT,
        owner_wxid TEXT,
        member_count INTEGER DEFAULT 0,
        expire_datetime TEXT NOT NULL,
        last_card_cipher TEXT,
        integrity_hash TEXT NOT NULL DEFAULT ''
      );
      CREATE TABLE IF NOT EXISTS alias_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        standard_word TEXT NOT NULL,
        alias_word TEXT NOT NULL UNIQUE
      );
      CREATE TABLE IF NOT EXISTS card_history (
        card_no TEXT PRIMARY KEY,
        used_at TEXT NOT NULL,
        target_id TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS group_draw_cache (
        wx_group_id TEXT PRIMARY KEY,
        draw_batch_id TEXT NOT NULL,
        guide_word TEXT NOT NULL,
        ball_txt TEXT,
        te_ma_only INTEGER DEFAULT 0,
        scopes_json TEXT NOT NULL,
        hit_details_json TEXT NOT NULL,
        report_guide_words_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
      );
    `);
    sqlDb.exec(`
      INSERT OR IGNORE INTO group_whitelist (
        group_id, group_name, owner_wxid, member_count, expire_datetime, last_card_cipher, integrity_hash
      )
      SELECT
        wx_group_id,
        COALESCE(name, ''),
        COALESCE(manual_owner, ''),
        0,
        COALESCE(expires_at, datetime('now', '+30 days')),
        '',
        ''
      FROM wx_groups
      WHERE is_active = 1
    `);
    sqlDb.exec(`
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT
        CASE scope
          WHEN 'guide_word' THEN 'REGION'
          WHEN 'category_word' THEN 'PLAY'
          WHEN 'amount_unit' THEN 'SET'
          WHEN 'instruction' THEN 'PLAY'
          WHEN 'algo' THEN 'PLAY'
          ELSE 'PLAY'
        END,
        canonical_word,
        alias_word
      FROM cmd_keyword_synonyms
      WHERE is_active = 1
        AND TRIM(COALESCE(alias_word,'')) != ''
        AND TRIM(COALESCE(canonical_word,'')) != ''
    `);
    sqlDb.exec(`
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
      SELECT 'PLAY', maps_to, alias_word
      FROM cmd_algo_aliases
      WHERE is_active = 1
        AND TRIM(COALESCE(alias_word,'')) != ''
        AND TRIM(COALESCE(maps_to,'')) != ''
    `);
    sqlDb.exec(`
      INSERT OR IGNORE INTO card_history (card_no, used_at, target_id)
      SELECT code_fingerprint, COALESCE(redeemed_at, datetime('now')), COALESCE(raw_payload, code_fingerprint)
      FROM setup_license_claims
    `);
    sqlDb.exec(`
      INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
        ('AMOUNT', '各', '各数'),
        ('AMOUNT', '各', '个数'),
        ('AMOUNT', '各', '个'),
        ('AMOUNT', '各', '各组'),
        ('AMOUNT', '各', '每个'),
        ('SET', '元', '米'),
        ('SET', '元', '闷'),
        ('SET', '元', '焖'),
        ('SET', '元', '蒙'),
        ('SET', '元', 'A'),
        ('SET', '元', 'a'),
        ('REGION', '新澳门', '新奥'),
        ('REGION', '新澳门', '奥'),
        ('REGION', '老澳门', '老奥'),
        ('INSTRUCTION', 'help', '帮助'),
        ('INSTRUCTION', 'clear_order', '清零'),
        ('INSTRUCTION', 'group_report', '报表'),
        ('INSTRUCTION', 'settlement_summary', '总结')
    `);
    const gdcInfo = sqlDb.exec('PRAGMA table_info(group_draw_cache)');
    const gdcCols = new Set(
      (gdcInfo[0]?.values || []).map((row) => String(row[1] || ''))
    );
    if (gdcCols.size && !gdcCols.has('report_guide_words_json')) {
      sqlDb.exec(`ALTER TABLE group_draw_cache ADD COLUMN report_guide_words_json TEXT`);
    }
  } catch (e) {
    console.warn('migratePrdSchema:', e?.message || e);
  }
}

/** 产品安装授权状态、首装「一个群一年」权益（与离线激活码签发体系共用 RSA 公钥验签） */
function migrateProductSetup(sqlDb) {
  try {
    sqlDb.exec(`
      CREATE TABLE IF NOT EXISTS setup_license_claims (
        code_fingerprint TEXT PRIMARY KEY NOT NULL,
        raw_payload TEXT,
        redeemed_at TEXT DEFAULT (datetime('now'))
      );
    `);
    const row = sqlJsSelectOne(sqlDb, `SELECT value FROM app_settings WHERE key = ?`, ['product_setup_completed']);
    if (row == null) {
      const g = sqlJsSelectOne(sqlDb, `SELECT COUNT(*) as n FROM wx_groups`, []);
      const gc = Number(g?.n ?? 0);
      const val = gc > 0 ? '1' : '0';
      sqlJsRun(sqlDb, `INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`, [
        'product_setup_completed',
        val,
      ]);
    }
    sqlJsRun(sqlDb, `INSERT OR IGNORE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`, [
      'install_group_bonus_available',
      '0',
    ]);
    sqlJsRun(sqlDb, `INSERT OR IGNORE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`, [
      'install_group_bonus_days',
      '365',
    ]);
  } catch (e) {
    console.warn('migrateProductSetup:', e?.message || e);
  }
}

function migrateCmdKeywordSynonyms(sqlDb) {
  try {
    const exists = sqlDb.exec("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cmd_keyword_synonyms' LIMIT 1");
    if (exists?.[0]?.values?.length) {
      return;
    }
    sqlDb.exec(`
      CREATE TABLE cmd_keyword_synonyms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT NOT NULL CHECK (scope IN ('guide_word','category_word','amount_unit','algo','instruction')),
        canonical_word TEXT NOT NULL,
        alias_word TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(scope, alias_word)
      );
      CREATE INDEX idx_cmd_keyword_synonyms_scope ON cmd_keyword_synonyms(scope, is_active);
    `);
  } catch (e) {
    console.warn('migrateCmdKeywordSynonyms:', e?.message || e);
  }
}

/** 扩展 scope：instruction（指令触发词，canonical_word 为固定键名） */
function migrateCmdKeywordSynonymsInstructionScope(sqlDb) {
  try {
    const res = sqlDb.exec(`SELECT sql FROM sqlite_master WHERE type='table' AND name='cmd_keyword_synonyms' LIMIT 1`);
    const createSql = String(res?.[0]?.values?.[0]?.[0] || '');
    if (createSql.includes("'instruction'")) return;
    if (!createSql.includes('cmd_keyword_synonyms')) return;
    sqlDb.exec(`
      BEGIN;
      ALTER TABLE cmd_keyword_synonyms RENAME TO cmd_keyword_synonyms__old;
      CREATE TABLE cmd_keyword_synonyms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT NOT NULL CHECK (scope IN ('guide_word','category_word','amount_unit','algo','instruction')),
        canonical_word TEXT NOT NULL,
        alias_word TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(scope, alias_word)
      );
      INSERT INTO cmd_keyword_synonyms (id, scope, canonical_word, alias_word, sort_order, is_active, updated_at)
        SELECT id, scope, canonical_word, alias_word, sort_order, is_active, updated_at FROM cmd_keyword_synonyms__old;
      DROP TABLE cmd_keyword_synonyms__old;
      CREATE INDEX idx_cmd_keyword_synonyms_scope ON cmd_keyword_synonyms(scope, is_active);
      COMMIT;
    `);
  } catch (e) {
    console.warn('migrateCmdKeywordSynonymsInstructionScope:', e?.message || e);
  }
}

/**
 * 渠道规范词：新奥 → 新澳门；同步订单/周期/同义词键等（可重复执行）。
 */
function migrateGuideWordXinAoToMacau(sqlDb) {
  try {
    const tbl = (name) =>
      sqlDb.exec(`SELECT 1 FROM sqlite_master WHERE type='table' AND name='${name}' LIMIT 1`)?.[0]?.values?.length >
      0;
    if (!tbl('cmd_routes')) return;

    sqlDb.exec(`
      DELETE FROM cmd_routes
      WHERE guide_word = '新奥'
        AND EXISTS (
          SELECT 1 FROM cmd_routes r2
          WHERE r2.guide_word = '新澳门'
            AND r2.category_word = cmd_routes.category_word
            AND COALESCE(r2.wx_group_id, '') = COALESCE(cmd_routes.wx_group_id, '')
        );
    `);
    sqlDb.exec(`UPDATE cmd_routes SET guide_word = '新澳门' WHERE guide_word = '新奥'`);

    sqlDb.exec(`UPDATE cmd_orders SET guide_word = '新澳门' WHERE guide_word = '新奥'`);

    const hasMacauCh = sqlJsSelectOne(sqlDb, `SELECT 1 FROM cmd_channels WHERE guide_word = '新澳门' LIMIT 1`, []);
    if (hasMacauCh) {
      sqlDb.exec(`DELETE FROM cmd_channels WHERE guide_word = '新奥'`);
    } else {
      sqlDb.exec(`UPDATE cmd_channels SET guide_word = '新澳门' WHERE guide_word = '新奥'`);
    }

    const hasMacauCyc = sqlJsSelectOne(sqlDb, `SELECT 1 FROM cmd_order_cycles WHERE guide_word = '新澳门' LIMIT 1`, []);
    if (hasMacauCyc) {
      sqlDb.exec(`DELETE FROM cmd_order_cycles WHERE guide_word = '新奥'`);
    } else {
      sqlDb.exec(`UPDATE cmd_order_cycles SET guide_word = '新澳门' WHERE guide_word = '新奥'`);
    }

    sqlDb.exec(
      `UPDATE app_settings SET value = '新澳门', updated_at = datetime('now') WHERE key = 'default_order_guide_word' AND value = '新奥'`
    );

    sqlDb.exec(
      `UPDATE cmd_keyword_synonyms SET canonical_word = '新澳门', updated_at = datetime('now')
       WHERE scope = 'guide_word' AND canonical_word = '新奥'`
    );

    const expRow = sqlJsSelectOne(sqlDb, `SELECT value FROM app_settings WHERE key = 'order_guide_expires_json'`, []);
    if (expRow?.value) {
      try {
        const o = JSON.parse(String(expRow.value));
        if (o && typeof o === 'object' && !Array.isArray(o) && Object.prototype.hasOwnProperty.call(o, '新奥')) {
          if (!Object.prototype.hasOwnProperty.call(o, '新澳门')) {
            o['新澳门'] = o['新奥'];
          }
          delete o['新奥'];
          sqlDb
            .prepare(
              `UPDATE app_settings SET value = ?, updated_at = datetime('now') WHERE key = 'order_guide_expires_json'`
            )
            .run(JSON.stringify(o));
        }
      } catch {
        /* ignore */
      }
    }
  } catch (e) {
    console.warn('migrateGuideWordXinAoToMacau:', e?.message || e);
  }
}

/**
 * 渠道「澳门」规范名改为「老澳门」，与「新澳门」并存；同步订单/周期/渠道/到期 JSON 等。
 */
function migrateGuideWordMacauToLaoMacau(sqlDb) {
  try {
    const tbl = (name) =>
      sqlDb.exec(`SELECT 1 FROM sqlite_master WHERE type='table' AND name='${name}' LIMIT 1`)?.[0]?.values?.length >
      0;
    if (!tbl('cmd_routes')) return;

    sqlDb.exec(`
      DELETE FROM cmd_routes
      WHERE guide_word = '澳门'
        AND EXISTS (
          SELECT 1 FROM cmd_routes r2
          WHERE r2.guide_word = '老澳门'
            AND r2.category_word = cmd_routes.category_word
            AND COALESCE(r2.wx_group_id, '') = COALESCE(cmd_routes.wx_group_id, '')
        );
    `);
    sqlDb.exec(`UPDATE cmd_routes SET guide_word = '老澳门' WHERE guide_word = '澳门'`);

    sqlDb.exec(`UPDATE cmd_orders SET guide_word = '老澳门' WHERE guide_word = '澳门'`);

    const bothCyc = sqlJsSelectOne(
      sqlDb,
      `SELECT 1 FROM cmd_order_cycles WHERE guide_word = '老澳门' LIMIT 1`,
      []
    );
    if (bothCyc) {
      sqlDb.exec(`DELETE FROM cmd_order_cycles WHERE guide_word = '澳门'`);
    } else {
      sqlDb.exec(`UPDATE cmd_order_cycles SET guide_word = '老澳门' WHERE guide_word = '澳门'`);
    }

    const bothCh = sqlJsSelectOne(sqlDb, `SELECT 1 FROM cmd_channels WHERE guide_word = '老澳门' LIMIT 1`, []);
    if (bothCh) {
      sqlDb.exec(`DELETE FROM cmd_channels WHERE guide_word = '澳门'`);
    } else {
      sqlDb.exec(`UPDATE cmd_channels SET guide_word = '老澳门' WHERE guide_word = '澳门'`);
    }

    sqlDb.exec(
      `UPDATE app_settings SET value = '老澳门', updated_at = datetime('now') WHERE key = 'default_order_guide_word' AND value = '澳门'`
    );

    sqlDb.exec(
      `UPDATE cmd_keyword_synonyms SET canonical_word = '老澳门', updated_at = datetime('now')
       WHERE scope = 'guide_word' AND canonical_word = '澳门'`
    );

    const expRow = sqlJsSelectOne(sqlDb, `SELECT value FROM app_settings WHERE key = 'order_guide_expires_json'`, []);
    if (expRow?.value) {
      try {
        const o = JSON.parse(String(expRow.value));
        if (
          o &&
          typeof o === 'object' &&
          !Array.isArray(o) &&
          Object.prototype.hasOwnProperty.call(o, '澳门')
        ) {
          if (!Object.prototype.hasOwnProperty.call(o, '老澳门')) {
            o['老澳门'] = o['澳门'];
          }
          delete o['澳门'];
          sqlDb
            .prepare(
              `UPDATE app_settings SET value = ?, updated_at = datetime('now') WHERE key = 'order_guide_expires_json'`
            )
            .run(JSON.stringify(o));
        }
      } catch {
        /* ignore */
      }
    }
  } catch (e) {
    console.warn('migrateGuideWordMacauToLaoMacau:', e?.message || e);
  }
}

/** 口语「二连虎狗」等与路由分类词对齐（规范词须已在 cmd_routes 中存在） */
function migrateLianXiaoCategoryAliases(sqlDb) {
  const upsert = (canonical, alias, sortOrder) => {
    try {
      const a = String(alias || '').trim();
      const c = String(canonical || '').trim();
      if (!a || !c) return;
      const ex = sqlJsSelectOne(sqlDb, `SELECT id FROM cmd_keyword_synonyms WHERE scope = 'category_word' AND alias_word = ?`, [
        a,
      ]);
      if (ex) {
        const st = sqlDb.prepare(
          `UPDATE cmd_keyword_synonyms SET canonical_word = ?, sort_order = ?, is_active = 1, updated_at = datetime('now')
           WHERE scope = 'category_word' AND alias_word = ?`
        );
        st.bind([c, sortOrder, a]);
        st.step();
        st.free();
      } else {
        const st = sqlDb.prepare(
          `INSERT INTO cmd_keyword_synonyms (scope, canonical_word, alias_word, sort_order, is_active, updated_at)
           VALUES ('category_word', ?, ?, ?, 1, datetime('now'))`
        );
        st.bind([c, a, sortOrder]);
        st.step();
        st.free();
      }
    } catch (e) {
      console.warn('migrateLianXiaoCategoryAliases:', e?.message || e);
    }
  };
  upsert('连肖', '二连', 88);
  upsert('连肖', '二连肖', 89);
  upsert('三连肖', '三连', 88);
  upsert('四连肖', '四连', 88);
  upsert('五连肖', '五连', 88);
  upsert('连码', '平特连码', 88);
}

/** 「三友」「三有」→ 三连肖（四有/四友→四连肖见 migrateSiYouSiLianCategoryAliases） */
function migratePingTeSanLianCategoryAliases(sqlDb) {
  const upsert = (canonical, alias, sortOrder) => {
    try {
      const a = String(alias || '').trim();
      const c = String(canonical || '').trim();
      if (!a || !c) return;
      const ex = sqlJsSelectOne(sqlDb, `SELECT id FROM cmd_keyword_synonyms WHERE scope = 'category_word' AND alias_word = ?`, [
        a,
      ]);
      if (ex) {
        const st = sqlDb.prepare(
          `UPDATE cmd_keyword_synonyms SET canonical_word = ?, sort_order = ?, is_active = 1, updated_at = datetime('now')
           WHERE scope = 'category_word' AND alias_word = ?`
        );
        st.bind([c, sortOrder, a]);
        st.step();
        st.free();
      } else {
        const st = sqlDb.prepare(
          `INSERT INTO cmd_keyword_synonyms (scope, canonical_word, alias_word, sort_order, is_active, updated_at)
           VALUES ('category_word', ?, ?, ?, 1, datetime('now'))`
        );
        st.bind([c, a, sortOrder]);
        st.step();
        st.free();
      }
    } catch (e) {
      console.warn('migratePingTeSanLianCategoryAliases:', e?.message || e);
    }
  };
  upsert('三连肖', '三友', 88);
  upsert('三连肖', '三有', 89);
  upsert('平特三连', '平特三连肖', 87);
}

/** 「四有」「四友」→ 四连肖（平特四连肖口语，规范词为库内四连肖） */
function migrateSiYouSiLianCategoryAliases(sqlDb) {
  const upsert = (canonical, alias, sortOrder) => {
    try {
      const a = String(alias || '').trim();
      const c = String(canonical || '').trim();
      if (!a || !c) return;
      const ex = sqlJsSelectOne(sqlDb, `SELECT id FROM cmd_keyword_synonyms WHERE scope = 'category_word' AND alias_word = ?`, [
        a,
      ]);
      if (ex) {
        const st = sqlDb.prepare(
          `UPDATE cmd_keyword_synonyms SET canonical_word = ?, sort_order = ?, is_active = 1, updated_at = datetime('now')
           WHERE scope = 'category_word' AND alias_word = ?`
        );
        st.bind([c, sortOrder, a]);
        st.step();
        st.free();
      } else {
        const st = sqlDb.prepare(
          `INSERT INTO cmd_keyword_synonyms (scope, canonical_word, alias_word, sort_order, is_active, updated_at)
           VALUES ('category_word', ?, ?, ?, 1, datetime('now'))`
        );
        st.bind([c, a, sortOrder]);
        st.step();
        st.free();
      }
    } catch (e) {
      console.warn('migrateSiYouSiLianCategoryAliases:', e?.message || e);
    }
  };
  upsert('四连肖', '四友', 88);
  upsert('四连肖', '四有', 89);
  upsert('四连肖', '平特四连肖', 87);
  upsert('四连肖', '平特四连', 86);
}

/** 移除误配的「三四*」玩法别名（引擎仍按句式做三四复式展开） */
function migrateSiSanLianXiaoPlayAliases(sqlDb) {
  try {
    sqlDb.exec(`
      DELETE FROM alias_config
      WHERE category = 'PLAY' AND alias_word IN ('三四有', '三四友', '三四连肖');
      DELETE FROM cmd_keyword_synonyms
      WHERE scope = 'category_word' AND alias_word IN ('三四有', '三四友', '三四连肖');
    `);
  } catch (e) {
    console.warn('migrateSiSanLianXiaoPlayAliases:', e?.message || e);
  }
}

/**
 * 单字「澳」指新澳门；老澳门须显式「老/老澳/老澳门」，不再用「澳门/奥/噢/澳」等歧义映射到老澳门。
 */
function migrateGuideSynonymSingleAoToXinMacau(sqlDb) {
  try {
    sqlDb.exec(`
      UPDATE cmd_keyword_synonyms
      SET canonical_word = '新澳门', sort_order = 38, is_active = 1, updated_at = datetime('now')
      WHERE scope = 'guide_word' AND alias_word = '澳'
    `);
    sqlDb.exec(`
      DELETE FROM cmd_keyword_synonyms
      WHERE scope = 'guide_word' AND canonical_word = '老澳门' AND alias_word IN ('澳门','奥','噢')
    `);
  } catch (e) {
    console.warn('migrateGuideSynonymSingleAoToXinMacau:', e?.message || e);
  }
}

function migrateWxGroupsOwnerOrdersFlag(sqlDb) {
  try {
    sqlDb.exec(`ALTER TABLE wx_groups ADD COLUMN owner_orders_enabled INTEGER DEFAULT 1`);
  } catch (e) {
    const msg = String(e?.message || e);
    if (!msg.includes('duplicate column')) {
      console.warn('migrateWxGroupsOwnerOrdersFlag:', msg);
    }
  }
}

function migrateWxGroupsDebugOrderReply(sqlDb) {
  try {
    sqlDb.exec(`ALTER TABLE wx_groups ADD COLUMN debug_order_reply INTEGER DEFAULT 0`);
  } catch (e) {
    const msg = String(e?.message || e);
    if (!msg.includes('duplicate column')) {
      console.warn('migrateWxGroupsDebugOrderReply:', msg);
    }
  }
}

function migrateWxGroupsDebugRuleMissReply(sqlDb) {
  try {
    sqlDb.exec(`ALTER TABLE wx_groups ADD COLUMN debug_rule_miss_reply INTEGER DEFAULT 0`);
  } catch (e) {
    const msg = String(e?.message || e);
    if (!msg.includes('duplicate column')) {
      console.warn('migrateWxGroupsDebugRuleMissReply:', msg);
    }
  }
}

function migrateWxGroupsManagerPermission(sqlDb) {
  try {
    sqlDb.exec(`ALTER TABLE wx_groups ADD COLUMN manager_permission_enabled INTEGER DEFAULT 1`);
  } catch (e) {
    const msg = String(e?.message || e);
    if (!msg.includes('duplicate column')) {
      console.warn('migrateWxGroupsManagerPermission:', msg);
    }
  }
}

/** 产品仅使用结单时间，开始时间统一为 00:00（旧库升级） */
function migrateCmdOrderCyclesNormalizeStartTime(sqlDb) {
  try {
    sqlDb.exec(`UPDATE cmd_order_cycles SET start_time = '00:00'`);
  } catch (e) {
    console.warn('migrateCmdOrderCyclesNormalizeStartTime:', e?.message || e);
  }
}

function migrateCmdAlgoAliases(sqlDb) {
  try {
    const exists = sqlDb.exec("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cmd_algo_aliases' LIMIT 1");
    if (exists?.[0]?.values?.length) {
      return;
    }
    sqlDb.exec(`
      CREATE TABLE cmd_algo_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alias_word TEXT NOT NULL,
        maps_to TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(alias_word)
      );
    `);
  } catch (e) {
    console.warn('migrateCmdAlgoAliases:', e?.message || e);
  }
}

function migrateCmdTypeVarsTypedDefault(sqlDb) {
  try {
    const info = sqlDb.exec('PRAGMA table_info(cmd_type_vars)');
    const cols = (info?.[0]?.values || []).map((c) => String(c[1] || ''));
    if (cols.length === 0) return;
    if (cols.includes('var_type') && cols.includes('default_value_number') && cols.includes('default_value_text')) {
      return;
    }
    sqlDb.exec(`
      BEGIN;
      ALTER TABLE cmd_type_vars RENAME TO cmd_type_vars__old;
      CREATE TABLE cmd_type_vars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_word TEXT NOT NULL,
        var_name TEXT NOT NULL,
        var_type TEXT NOT NULL DEFAULT 'number' CHECK(var_type IN ('number','text')),
        default_value_number REAL,
        default_value_text TEXT,
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(category_word, var_name)
      );
      INSERT INTO cmd_type_vars
      (id, category_word, var_name, var_type, default_value_number, default_value_text, updated_at)
      SELECT
        id,
        category_word,
        var_name,
        'number',
        COALESCE(var_value, 0),
        NULL,
        COALESCE(updated_at, datetime('now'))
      FROM cmd_type_vars__old;
      DROP TABLE cmd_type_vars__old;
      COMMIT;
    `);
  } catch (e) {
    console.warn('migrateCmdTypeVarsTypedDefault:', e?.message || e);
  }
}

function buildZodiacPresetGroups() {
  const defs = [
    { n: '家禽', s: ['牛', '马', '羊', '鸡', '狗', '猪'] },
    { n: '野兽', s: ['鼠', '虎', '兔', '龙', '蛇', '猴'] },
    { n: '单笔', s: ['鼠', '龙', '马', '蛇', '鸡', '猪'] },
    { n: '双笔', s: ['虎', '猴', '狗', '兔', '羊', '牛'] },
    { n: '女肖', s: ['兔', '蛇', '羊', '鸡', '猪'] },
    { n: '男肖', s: ['鼠', '牛', '虎', '龙', '马', '猴', '狗'] },
    { n: '吉美', s: ['兔', '龙', '蛇', '马', '羊', '鸡'] },
    { n: '凶丑', s: ['鼠', '牛', '虎', '猴', '狗', '猪'] },
    { n: '天肖', s: ['兔', '马', '猴', '猪', '牛', '龙'] },
    { n: '地肖', s: ['蛇', '羊', '鸡', '狗', '鼠', '虎'] },
    { n: '阴性', s: ['鼠', '龙', '蛇', '马', '狗', '猪'] },
    { n: '阳性', s: ['牛', '虎', '兔', '羊', '猴', '鸡'] },
    { n: '白边', s: ['鼠', '牛', '虎', '鸡', '狗', '猪'] },
    { n: '黑中', s: ['兔', '龙', '蛇', '马', '羊', '猴'] },
    { n: '红肖', s: ['马', '兔', '鼠', '鸡'] },
    { n: '蓝肖', s: ['蛇', '虎', '猪', '猴'] },
    { n: '绿肖', s: ['羊', '龙', '牛', '狗'] },
    { n: '琴', s: ['兔', '蛇', '鸡'] },
    { n: '棋', s: ['鼠', '牛', '狗'] },
    { n: '书', s: ['虎', '龙', '马'] },
    { n: '画', s: ['羊', '猴', '猪'] },
    { n: '五福肖', s: ['鼠', '虎', '兔', '蛇', '猴'] },
  ];
  return defs.map((x) => ({ name: x.n, num: [...x.s] }));
}

/** 管理台「恢复预置合集」：按内置波色/生肖等表重建全局合集（已有同名则更新并启用） */
export function reseedGlobalCollections(db) {
  seedGlobalCollectionsV2(db);
}

function seedGlobalCollectionsV2(db) {
  const zodiacPreset = buildZodiacPresetGroups();
  const groups = [
    {
      title: '波色',
      content: [
        { name: '红', num: [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46] },
        { name: '绿', num: [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49] },
        { name: '蓝', num: [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48] },
      ],
    },
    {
      title: '大小',
      content: [
        { name: '大', num: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49] },
        { name: '小', num: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24] },
      ],
    },
    {
      title: '单双',
      content: [
        { name: '单', num: [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49] },
        { name: '双', num: [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48] },
      ],
    },
    {
      title: '大小单双',
      content: [
        { name: '大单', num: [25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49] },
        { name: '小单', num: [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23] },
        { name: '大双', num: [26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48] },
        { name: '小双', num: [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24] },
      ],
    },
    {
      title: '波色单双',
      content: [
        { name: '红单', num: [1, 7, 13, 19, 23, 29, 35, 45] },
        { name: '红双', num: [2, 8, 12, 18, 24, 30, 34, 40, 46] },
        { name: '绿单', num: [5, 11, 17, 21, 27, 33, 39, 43, 49] },
        { name: '绿双', num: [6, 16, 22, 28, 32, 38, 44] },
        { name: '蓝单', num: [3, 9, 15, 25, 31, 37, 41, 47] },
        { name: '蓝双', num: [4, 10, 14, 20, 26, 36, 42, 48] },
      ],
    },
    {
      title: '七段',
      content: [
        { name: '1段', num: [1, 2, 3, 4, 5, 6, 7] },
        { name: '2段', num: [8, 9, 10, 11, 12, 13, 14] },
        { name: '3段', num: [15, 16, 17, 18, 19, 20, 21] },
        { name: '4段', num: [22, 23, 24, 25, 26, 27, 28] },
        { name: '5段', num: [29, 30, 31, 32, 33, 34, 35] },
        { name: '6段', num: [36, 37, 38, 39, 40, 41, 42] },
        { name: '7段', num: [43, 44, 45, 46, 47, 48, 49] },
      ],
    },
    {
      title: '五门',
      content: [
        { name: '1门', num: [1, 2, 3, 4, 5, 6, 7, 8, 9] },
        { name: '2门', num: [10, 11, 12, 13, 14, 15, 16, 17, 18] },
        { name: '3门', num: [19, 20, 21, 22, 23, 24, 25, 26, 27] },
        { name: '4门', num: [28, 29, 30, 31, 32, 33, 34, 35, 36, 37] },
        { name: '5门', num: [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49] },
      ],
    },
    {
      title: '头数',
      content: [
        { name: '0头', num: [1, 2, 3, 4, 5, 6, 7, 8, 9] },
        { name: '1头', num: [10, 11, 12, 13, 14, 15, 16, 17, 18, 19] },
        { name: '2头', num: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29] },
        { name: '3头', num: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39] },
        { name: '4头', num: [40, 41, 42, 43, 44, 45, 46, 47, 48, 49] },
      ],
    },
    {
      title: '尾数',
      content: [
        { name: '0尾', num: [10, 20, 30, 40] },
        { name: '1尾', num: [1, 11, 21, 31, 41] },
        { name: '2尾', num: [2, 12, 22, 32, 42] },
        { name: '3尾', num: [3, 13, 23, 33, 43] },
        { name: '4尾', num: [4, 14, 24, 34, 44] },
        { name: '5尾', num: [5, 15, 25, 35, 45] },
        { name: '6尾', num: [6, 16, 26, 36, 46] },
        { name: '7尾', num: [7, 17, 27, 37, 47] },
        { name: '8尾', num: [8, 18, 28, 38, 48] },
        { name: '9尾', num: [9, 19, 29, 39, 49] },
      ],
    },
    {
      title: '合数',
      content: [
        { name: '合01', num: [1, 10] },
        { name: '合02', num: [2, 11, 20] },
        { name: '合03', num: [3, 12, 21, 30] },
        { name: '合04', num: [4, 13, 22, 31, 40] },
        { name: '合05', num: [5, 14, 23, 32, 41] },
        { name: '合06', num: [6, 15, 24, 33, 42] },
        { name: '合07', num: [7, 16, 25, 34, 43] },
        { name: '合08', num: [8, 17, 26, 35, 44] },
        { name: '合09', num: [9, 18, 27, 36, 45] },
        { name: '合10', num: [19, 28, 37, 46] },
        { name: '合11', num: [29, 38, 47] },
        { name: '合12', num: [39, 48] },
        { name: '合13', num: [49] },
      ],
    },
    {
      title: '合单双',
      content: [
        { name: '合单', num: [1, 3, 5, 7, 9, 10, 12, 14, 16, 18, 21, 23, 25, 27, 29, 30, 32, 34, 36, 38, 41, 43, 45, 47, 49] },
        { name: '合双', num: [2, 4, 6, 8, 11, 13, 15, 17, 19, 20, 22, 24, 26, 28, 31, 33, 35, 37, 39, 40, 42, 44, 46, 48] },
      ],
    },
    {
      title: '余七',
      content: [
        { name: '6余0', num: [6, 12, 18, 24, 30, 36, 42, 48] },
        { name: '6余1', num: [1, 7, 13, 19, 25, 31, 37, 43, 49] },
        { name: '6余2', num: [2, 8, 14, 20, 26, 32, 38, 44] },
        { name: '6余3', num: [3, 9, 15, 21, 27, 33, 39, 45] },
        { name: '6余4', num: [4, 10, 16, 22, 28, 34, 40, 46] },
        { name: '6余5', num: [5, 11, 17, 23, 29, 35, 41, 47] },
      ],
    },
    {
      title: '余六',
      content: [
        { name: '7余0', num: [7, 14, 21, 28, 35, 42, 49] },
        { name: '7余1', num: [1, 8, 15, 22, 29, 36, 43] },
        { name: '7余2', num: [2, 9, 16, 23, 30, 37, 44] },
        { name: '7余3', num: [3, 10, 17, 24, 31, 38, 45] },
        { name: '7余4', num: [4, 11, 18, 25, 32, 39, 46] },
        { name: '7余5', num: [5, 12, 19, 26, 33, 40, 47] },
        { name: '7余6', num: [6, 13, 20, 27, 34, 41, 48] },
      ],
    },
    {
      title: '生肖分类',
      content: zodiacPreset,
    },
  ];
  const marker = db
    .prepare(
      'SELECT id FROM cmd_collections WHERE wx_group_id IS NULL AND set_category = ? AND set_name = ?'
    )
    .get('波色', '红');
  if (!marker?.id) {
    db.prepare('DELETE FROM cmd_collections WHERE wx_group_id IS NULL').run();
  }
  for (const g of groups) {
    for (const item of g.content) {
      const ex = db
        .prepare('SELECT id FROM cmd_collections WHERE wx_group_id IS NULL AND set_name = ?')
        .get(item.name);
      if (ex?.id) {
        db.prepare(
          `UPDATE cmd_collections
           SET set_category = ?, source_set_name = NULL, derive_indexes_json = NULL, items_json = ?, is_active = 1, updated_at = datetime('now')
           WHERE id = ?`
        ).run(g.title, JSON.stringify(item.num), ex.id);
      } else {
        db.prepare(
          `INSERT INTO cmd_collections
          (wx_group_id, set_category, set_name, source_set_name, derive_indexes_json, items_json, is_active, updated_at)
          VALUES (NULL, ?, ?, NULL, NULL, ?, 1, datetime('now'))`
        ).run(g.title, item.name, JSON.stringify(item.num));
      }
    }
  }
}

/**
 * 单个渠道：玩法路由 + 类型变量默认值（只补缺行，不覆盖已有数值）。
 * 费率=中奖倍率；水=下单返点比例（查单展示）；连肖/连码赔率表为 JSON 文本变量。
 */
function seedMacauChannelPlaybooks(db, guideWord) {
  const G = String(guideWord || '').trim();
  if (!G) return;
  const ROUTE_TMPL = '命中{route}：目标{targets}，算法{algo}，数值{value}，结果{result}';
  const categories = [
    ...new Set([
      '特',
      '平特',
      '平特马',
      '平特二连',
      '平特三连',
      '平尾',
      '平尾0尾',
      '单双',
      '合单双',
      '特肖',
      '特肖马',
      '半波',
      '波段',
      '连肖',
      '连码',
      '三连肖',
      '四连肖',
      '五连肖',
      ...allPlaySpecCategoryWords(),
    ]),
  ];
  for (const cat of categories) {
    const ex = db
      .prepare(
        `SELECT id FROM cmd_routes WHERE (wx_group_id IS NULL OR TRIM(IFNULL(wx_group_id,''))='' OR wx_group_id='__global__') AND guide_word = ? AND category_word = ?`
      )
      .get(G, cat);
    if (ex) continue;
    db.prepare(
      `INSERT INTO cmd_routes
       (wx_group_id, route_name, guide_word, category_word, formula_name, reply_template, priority, is_active, updated_at)
       VALUES (NULL, NULL, ?, ?, 'default_each', ?, 100, 1, datetime('now'))`
    ).run(G, cat, ROUTE_TMPL);
  }

  const ensureNum = (cat, varName, num) => {
    const ex = db.prepare(`SELECT id FROM cmd_type_vars WHERE category_word = ? AND var_name = ?`).get(cat, varName);
    if (ex) return;
    db.prepare(
      `INSERT INTO cmd_type_vars (category_word, var_name, var_type, default_value_number, default_value_text, updated_at)
       VALUES (?, ?, 'number', ?, NULL, datetime('now'))`
    ).run(cat, varName, num);
  };
  const ensureText = (cat, varName, text) => {
    const ex = db.prepare(`SELECT id FROM cmd_type_vars WHERE category_word = ? AND var_name = ?`).get(cat, varName);
    if (ex) return;
    db.prepare(
      `INSERT INTO cmd_type_vars (category_word, var_name, var_type, default_value_number, default_value_text, updated_at)
       VALUES (?, ?, 'text', NULL, ?, datetime('now'))`
    ).run(cat, varName, text);
  };

  ensureNum('特', '固定费率', 47);
  ensureNum('特', '特费率', 47);
  ensureNum('特', '水', 0.04);

  const rateWater = [
    ['平特', 2],
    ['平特马', 1.75],
    ['平特三连', 2],
    ['平尾', 1.75],
    ['平尾0尾', 1.75],
    ['单双', 1.8],
    ['合单双', 1.8],
    ['特肖', 11],
    ['特肖马', 11],
    ['半波', 5.4],
    ['波段', 2.7],
  ];
  for (const [c, r] of rateWater) {
    ensureNum(c, '费率', r);
    ensureNum(c, '水', 0.04);
  }

  ensureNum('连肖', '水', 0.04);
  /** 带马/不带：含当年肖 vs 不含（键名历史沿用「带马」；结单按公历年生肖 zodiacOfYear） */
  ensureText(
    '连肖',
    '连肖赔率',
    JSON.stringify({
      二联: { 带马: 3.5, 不带: 4 },
      三联: { 带马: 8.5, 不带: 10 },
      四联: { 带马: 25, 不带: 30 },
      五联: { 带马: 85, 不带: 100 },
    })
  );

  ensureNum('连码', '水', 0.04);
  ensureText(
    '连码',
    '连码赔率',
    JSON.stringify({
      二中二: 60,
      三中三: 600,
      三中二: 20,
      中三: 80,
    })
  );

  ensureNum('三连肖', '水', 0.04);
  ensureNum('四连肖', '水', 0.04);
  ensureNum('五连肖', '水', 0.04);

  db.prepare(
    `UPDATE cmd_type_vars SET default_value_number = 47, updated_at = datetime('now')
     WHERE category_word = '特' AND var_name IN ('特费率', '固定费率') AND IFNULL(default_value_number, 0) <= 1`
  ).run();
}

function upsertAliasConfigSeed(db, category, standard_word, alias_word) {
  const cat = String(category || '').trim();
  const std = String(standard_word || '').trim();
  const alias = String(alias_word || '').trim();
  if (!cat || !std || !alias) return;
  db.prepare(
    `INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES (?,?,?)`
  ).run(cat, std, alias);
}

/** 渠道词同义词落库（规范词须与 cmd_routes.guide_word 一致）→ alias_config REGION */
function ensureMacauGuideSynonyms(db) {
  const upsert = (canonical, alias) => {
    upsertAliasConfigSeed(db, 'REGION', canonical, alias);
  };
  upsert('新澳门', '新奥');
  upsert('新澳门', '新澳');
  upsert('新澳门', '新噢');
  upsert('新澳门', '新');
  upsert('新澳门', '澳');
  upsert('新澳门', '奥');
  upsert('新澳门', '噢');
  upsert('老澳门', '老澳');
  upsert('越南', '越');
  upsert('香港', '港');
  upsert('香港', '香');
  upsert('新澳门', '门');
}

function seedInstructionSynonyms(db) {
  try {
    const row = db.prepare(`SELECT COUNT(*) AS n FROM alias_config WHERE category = 'INSTRUCTION'`).get();
    if (Number(row?.n || 0) > 0) return;
  } catch {
    return;
  }
  const rows = [
    ['help', '帮助', 10],
    ['help', '菜单', 20],
    ['help', '指令', 30],
    ['help', '指令帮助', 40],
    ['help', '使用帮助', 50],
    ['help', '报表帮助', 60],
    ['help', '报表指令', 70],
    ['clear_order', '清空订单', 10],
    ['clear_order', '清空', 20],
    ['clear_order', '清零', 30],
    ['clear_order', '清单', 40],
    ['clear_order', '清空当前订单', 50],
    ['order_query', '查单', 10],
    ['order_query', '查订单', 20],
    ['order_query', '查询订单', 30],
    ['order_query_detail', '查明细单', 10],
    ['order_query_detail', '查订单明细', 20],
    ['query_group_config', '查询群配置', 10],
    ['query_group_config', '查群配置', 20],
    ['query_group_config', '群配置查询', 30],
    ['query_group_config', '查看群配置', 40],
    ['odds_table', '赔率表', 10],
    ['odds_table', '查询赔率表', 20],
    ['odds_table', '查赔率表', 30],
    ['odds_table', '查看赔率表', 40],
    ['group_config_mark', '群配置', 100],
    ['group_config_mark', '设置费率', 90],
    ['group_config_mark', '设置水率', 80],
    ['group_config_mark', '群设置', 70],
    ['group_config_mark', '配置', 60],
    ['group_config_mark', '设置', 50],
    ['set_var', '设变量', 10],
    ['settlement_summary', '总结', 15],
  ];
  for (const row of rows) upsertAliasConfigSeed(db, 'INSTRUCTION', row[0], row[1]);
}

/** 默认渠道/玩法设置指令别名（可重复执行以补缺） */
function ensureDefaultOrderInstructionSynonyms(db) {
  const rows = [
    ['default_order', '查默认', 10],
    ['default_order', '查看默认', 20],
    ['default_order', '默认配置', 30],
    ['default_order', '默认设置', 40],
    ['default_order', '设置默认', 50],
    ['default_order', '设置默认渠道', 60],
    ['default_order', '设置默认玩法', 70],
  ];
  for (const row of rows) upsertAliasConfigSeed(db, 'INSTRUCTION', row[0], row[1]);
}

/** 将原硬编码算法词迁入 alias_config AMOUNT */
function seedBuiltinAlgoAliasBundle(db) {
  const pairs = [
    ['各位', '各'],
    ['各个', '各'],
    ['各数', '各'],
    ['各位数', '各'],
    ['各号', '各'],
    ['个数', '各'],
    ['每号', '各'],
    ['每各', '各'],
    ['个个', '各'],
    ['各组', '各'],
    ['每个号', '各'],
    ['一个', '各'],
  ];
  for (const [alias, mapsTo] of pairs) upsertAliasConfigSeed(db, 'AMOUNT', mapsTo, alias);
  for (const op of ['各', '加', '减', '乘', '除', '+', '*', '/', 'x', 'X']) {
    upsertAliasConfigSeed(db, 'AMOUNT', op, op);
  }
  upsertAliasConfigSeed(db, 'AMOUNT', '各', '个');
  upsertAliasConfigSeed(db, 'AMOUNT', '各', '每个');
}

function seedCommandMeta(db) {
  seedGlobalCollectionsV2(db);
  const hasFormula = db.prepare('SELECT id FROM cmd_formulas WHERE formula_name = ?').get('default_each');
  if (!hasFormula) {
    db.prepare(
      `INSERT INTO cmd_formulas (formula_name, pipeline_expr, description, is_active, updated_at)
       VALUES (?, ?, ?, 1, datetime('now'))`
    ).run('default_each', 'identity|algo|order', '默认流水线：先取目标，执行算法并落单');
  }
  const primaryGuide = '新澳门';
  const hasRoute = db
    .prepare(
      'SELECT id FROM cmd_routes WHERE wx_group_id IS NULL AND guide_word = ? AND category_word = ?'
    )
    .get(primaryGuide, '特');
  if (!hasRoute) {
    db.prepare(
      `INSERT INTO cmd_routes
      (wx_group_id, route_name, guide_word, category_word, formula_name, reply_template, priority, is_active, updated_at)
      VALUES (NULL, NULL, ?, ?, ?, ?, ?, 1, datetime('now'))`
    ).run(
      primaryGuide,
      '特',
      'default_each',
      '命中{route}：目标{targets}，算法{algo}，数值{value}，结果{result}',
      100
    );
  }
  const hasPrimaryCycle = db.prepare('SELECT id FROM cmd_order_cycles WHERE guide_word = ?').get(primaryGuide);
  if (!hasPrimaryCycle) {
    db.prepare(
      `INSERT INTO cmd_order_cycles
      (guide_word, cycle_type, start_time, cutoff_time, date_list_json, is_active, updated_at)
      VALUES (?, 'daily', '00:00', '20:59', NULL, 1, datetime('now'))`
    ).run(primaryGuide);
  }
  const fourGuides = ['新澳门', '老澳门', '香港', '越南'];
  for (const gw of fourGuides) {
    const hasCy = db.prepare(`SELECT id FROM cmd_order_cycles WHERE guide_word = ?`).get(gw);
    if (!hasCy) {
      db.prepare(
        `INSERT INTO cmd_order_cycles
        (guide_word, cycle_type, start_time, cutoff_time, date_list_json, is_active, updated_at)
        VALUES (?, 'daily', '00:00', '20:59', NULL, 1, datetime('now'))`
      ).run(gw);
    }
    db.prepare(
      `INSERT OR IGNORE INTO cmd_channels (guide_word, is_active, updated_at) VALUES (?, 1, datetime('now'))`
    ).run(gw);
    seedMacauChannelPlaybooks(db, gw);
  }
  ensureMacauGuideSynonyms(db);
  seedInstructionSynonyms(db);
  ensureDefaultOrderInstructionSynonyms(db);
  seedBuiltinAlgoAliasBundle(db);
  syncLegacySynonymsToAliasConfig(db);
  try {
    db.prepare(
      `INSERT OR IGNORE INTO app_settings (key, value, updated_at) VALUES ('draw_defer_summary', '1', datetime('now'))`
    ).run();
  } catch {
    /* ignore */
  }
}

function wrapDb(initialSqlDb, filePath) {
  let sqlDb = initialSqlDb;
  const SqlDatabase = initialSqlDb.constructor;

  const persist = () => {
    const data = sqlDb.export();
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, Buffer.from(data));
  };

  const out = {
    sqlitePath: filePath,
    prepare(sql) {
      return {
        get(...params) {
          const st = sqlDb.prepare(sql);
          st.bind(params);
          if (!st.step()) {
            st.free();
            return undefined;
          }
          const row = st.getAsObject();
          st.free();
          return row;
        },
        all(...params) {
          const st = sqlDb.prepare(sql);
          st.bind(params);
          const rows = [];
          while (st.step()) rows.push(st.getAsObject());
          st.free();
          return rows;
        },
        run(...params) {
          const st = sqlDb.prepare(sql);
          st.bind(params);
          st.step();
          st.free();
          persist();
        },
      };
    },
    exec(sql) {
      sqlDb.exec(sql);
      persist();
    },
    persist,
    /** Rust 引擎写盘后，从磁盘重载 sql.js 实例 */
    reloadFromDisk() {
      if (!fs.existsSync(filePath)) return;
      sqlDb = new SqlDatabase(fs.readFileSync(filePath));
    },
    /** 运行时替换底层 sql.js 实例（如从备份导入） */
    replaceEngine(nextSqlDb) {
      sqlDb = nextSqlDb;
      persist();
    },
  };

  Object.defineProperty(out, '_raw', {
    enumerable: true,
    configurable: true,
    get() {
      return sqlDb;
    },
  });

  return out;
}

function flushSqlDbToDisk(sqlDb, filePath) {
  const resolved = path.resolve(filePath);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  fs.writeFileSync(resolved, Buffer.from(sqlDb.export()));
}

export async function openDatabase(dbPath) {
  const SQL = await ensureSqlJs();
  const resolvedPath = path.resolve(dbPath);

  const existed = fs.existsSync(resolvedPath);
  let sqlDb;
  if (existed) {
    sqlDb = new SQL.Database(fs.readFileSync(resolvedPath));
  } else {
    sqlDb = new SQL.Database();
  }
  applyIncrementalMigrations(sqlDb);
  /** 迁移在 wrap 前执行，须先落盘，避免热重启时结构/数据仅留在内存 */
  flushSqlDbToDisk(sqlDb, resolvedPath);
  const db = wrapDb(sqlDb, resolvedPath);
  seedCommandMeta(db);
  db.persist();
  return db;
}

export function seedSuperAdmin(db, username, passwordHash) {
  const row = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
  if (row) return;
  db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?,?,?)').run(
    username,
    passwordHash,
    'super'
  );
}

/**
 * 创建或更新为超级管理员（用于本地开发者账号：口令由启动时哈希写入）。
 */
export function upsertSuperAdminUser(db, username, passwordHash) {
  const u = String(username || '').normalize('NFKC').trim().slice(0, 128);
  if (!u) throw new Error('upsertSuperAdminUser: username required');
  const row = db.prepare('SELECT id FROM users WHERE username = ?').get(u);
  if (row) {
    db.prepare('UPDATE users SET password_hash = ?, role = ? WHERE id = ?').run(passwordHash, 'super', row.id);
  } else {
    db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?,?,?)').run(u, passwordHash, 'super');
  }
}
