/**
 * 微信 Hook 注入 JSON（与 scripts/launch-wechat-hook.mjs 一致）
 * 默认 HTTP 回调到侧车 HTTP_PORT，避免打包版仅开 3000 而回调仍指向 5000 导致收不到群消息。
 */
export function buildHookInjectConfig(projectRoot = process.cwd()) {
  const tcpHost =
    process.env.TCP_HOST && process.env.TCP_HOST !== '0.0.0.0'
      ? process.env.TCP_HOST
      : '127.0.0.1';
  const tcpPort = Number(process.env.TCP_PORT || 61108);
  const httpPort = Number(process.env.HTTP_PORT || 3000);
  const hookDllHttpPort = Number(
    process.env.HOOK_DLL_HTTP_PORT || process.env.HOOK_HTTP_SERVER_PORT || 19088
  );
  const callbackPort = Number(process.env.HOOK_CALLBACK_PORT || 0);
  const callbackHttpPort =
    callbackPort > 0 && callbackPort !== httpPort ? callbackPort : httpPort;
  const callbackUrl =
    process.env.HOOK_CALLBACK_URL ||
    `http://127.0.0.1:${callbackHttpPort}/api/recvMsg`;

  const modeRaw = String(process.env.HOOK_RECEIVE_MODE || 'http').trim().toLowerCase();
  const recivemode =
    modeRaw === 'tcp' ? 'tcp' : modeRaw === 'all' || modeRaw === 'both' ? 'all' : 'http';

  return {
    recivemode,
    tcp_ip: tcpHost,
    tcp_port: tcpPort,
    http_server_port: hookDllHttpPort,
    http_callback_url: callbackUrl,
    usedefault: false,
    start_server_while_login: true,
    _meta: { projectRoot, callbackHttpPort, modeRaw },
  };
}

export function hookInjectConfigJson() {
  const cfg = buildHookInjectConfig();
  const { _meta, ...payload } = cfg;
  return JSON.stringify(payload);
}

/** Node 侧是否应监听/连接 TCP 入站（http 模式仅走 HTTP 回调） */
export function hookReceiveUsesTcp() {
  const m = String(process.env.HOOK_RECEIVE_MODE || 'http').trim().toLowerCase();
  if (process.env.TCP_GATEWAY === '0') return false;
  if (process.env.TCP_GATEWAY === '1') return true;
  return m === 'tcp' || m === 'all' || m === 'both';
}
