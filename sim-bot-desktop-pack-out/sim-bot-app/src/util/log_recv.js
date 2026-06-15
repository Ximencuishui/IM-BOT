/** 是否记录所有入站群消息到 info 日志（设 BOT_INBOUND_LOG_GROUP=0 可关闭） */
export function shouldLogAllGroupInbound() {
  const off = String(process.env.BOT_INBOUND_LOG_GROUP ?? '').trim();
  if (off === '0' || off.toLowerCase() === 'false') return false;
  return true;
}

function previewInboundText(text, max = 200) {
  const s = String(text || '')
    .replace(/\r\n/g, '\\n')
    .replace(/\n/g, '\\n')
    .trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max)}…[+${s.length - max}]`;
}

/** 是否将入站摘要写入 info 级日志 */
export function shouldLogInboundAtInfo(result) {
  if (String(process.env.BOT_INBOUND_LOG_VERBOSE ?? process.env.INBOUND_LOG_VERBOSE ?? '') === '1') {
    return true;
  }
  const line = String(result?.logLine || '');
  if (!line) return false;
  if (result?.logLevel === 'info') return true;
  if (shouldLogAllGroupInbound() && /@chatroom/.test(line)) return true;
  if (/skip=command_route_handled|group_whitelist_card|group_draw|private_help/.test(line)) {
    return true;
  }
  return false;
}

/**
 * 每条入站群消息打一行 info（便于对照 Hook 是否回调到侧车）
 * @param {'http'|'tcp'} channel
 */
export function logInboundGroupMessage(
  { ex, skipReason, channel = 'http' },
  logger
) {
  if (!shouldLogAllGroupInbound() || !logger || !ex?.groupId) return;
  if (!/@chatroom/i.test(String(ex.groupId))) return;
  const preview = previewInboundText(ex.content, 200);
  if (!preview && !ex.senderWxid) return;

  const logFn = typeof logger.info === 'function' ? logger.info : console.log;
  logFn.call(
    logger,
    `[入站:群][${channel}] group=${ex.groupId} sender=${ex.senderWxid || '-'} skip=${skipReason || '-'} text=${preview || '(空)'}`
  );
}

export function logInboundDispatchResult(result, logger, tag = 'recvMsg') {
  if (!result?.logLine || !logger) return;
  const line = `[${tag}] ${result.logLine}`;
  if (shouldLogInboundAtInfo(result)) {
    const logFn = typeof logger.info === 'function' ? logger.info : console.log;
    logFn.call(logger, line);
  } else if (process.env.DEBUG === '1' && typeof logger.debug === 'function') {
    logger.debug(line);
  }
}
