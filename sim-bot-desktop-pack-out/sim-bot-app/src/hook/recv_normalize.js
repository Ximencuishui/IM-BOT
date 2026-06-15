/**
 * 规范化 Hook HTTP 回调 / TCP JSON 载荷（兼容多层包装、纯文本 JSON、数组）
 */
export function normalizeHookInboundPayload(raw) {
  if (raw == null) return null;
  let obj = raw;
  if (typeof obj === 'string') {
    const t = obj.trim();
    if (!t) return null;
    try {
      obj = JSON.parse(t);
    } catch {
      return null;
    }
  }
  if (Array.isArray(obj)) {
    const first = obj.find((x) => x && typeof x === 'object');
    return first || null;
  }
  if (typeof obj !== 'object') return null;

  const wrapKeys = ['data', 'Data', 'msg', 'message', 'body', 'Body', 'payload', 'Payload'];
  for (const k of wrapKeys) {
    const inner = obj[k];
    if (inner && typeof inner === 'object' && !Array.isArray(inner)) {
      const { [k]: _drop, ...rest } = obj;
      return { ...rest, ...inner };
    }
  }
  return obj;
}
