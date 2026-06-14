/** 入站消息去重（进程内 TTL Map，替代 Redis SET NX EX） */

const DEFAULT_TTL_SEC = 300;
const CLEANUP_INTERVAL_MS = 60_000;

export function createInboundDedupe({ ttlSec = DEFAULT_TTL_SEC } = {}) {
  const ttlMs = Math.max(1, ttlSec) * 1000;
  const seen = new Map();

  function purge(now = Date.now()) {
    for (const [k, exp] of seen) {
      if (exp <= now) seen.delete(k);
    }
  }

  const timer = setInterval(() => purge(), CLEANUP_INTERVAL_MS);
  if (typeof timer.unref === 'function') timer.unref();

  /** @returns {boolean} true 表示首次见到（应处理）；false 为重复 */
  function tryAcquire(dedupeText) {
    const text = String(dedupeText || '').trim();
    if (!text) return true;
    const now = Date.now();
    const exp = seen.get(text);
    if (exp != null && exp > now) return false;
    seen.set(text, now + ttlMs);
    if (seen.size > 50_000) purge(now);
    return true;
  }

  function close() {
    clearInterval(timer);
    seen.clear();
  }

  return { tryAcquire, close };
}
