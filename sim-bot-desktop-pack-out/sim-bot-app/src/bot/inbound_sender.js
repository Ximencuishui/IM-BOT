/** 入站群消息：解析真实发送者 wxid（避免误用群 id） */
export function resolveInboundSenderWxid(ex) {
  let wxid = String(ex?.senderWxid || '').trim();
  if (wxid && !wxid.endsWith('@chatroom')) return wxid;
  const m = String(ex?.originalContent || '').match(/^([^:\n：]+)[:：]\s*\n/);
  const guessed = m?.[1]?.trim();
  if (guessed && !guessed.endsWith('@chatroom')) return guessed;
  return wxid && !wxid.endsWith('@chatroom') ? wxid : '';
}
