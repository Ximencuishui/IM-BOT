/**
 * 解析热路径缓存：别名/路由前缀等按 db 实例缓存，避免每条消息重复查库排序。
 * 库迁移或别名变更后进程内调用 invalidateParseCaches()（openDatabase 已会建新 db 句柄）。
 */
const dbCaches = new WeakMap();

function bucket(db) {
  let b = dbCaches.get(db);
  if (!b) {
    b = {};
    dbCaches.set(db, b);
  }
  return b;
}

export function getParseCache(db, key, factory) {
  if (!db) return factory();
  const b = bucket(db);
  if (b[key] !== undefined) return b[key];
  b[key] = factory();
  return b[key];
}

export function invalidateParseCaches(db) {
  if (db) dbCaches.delete(db);
}
