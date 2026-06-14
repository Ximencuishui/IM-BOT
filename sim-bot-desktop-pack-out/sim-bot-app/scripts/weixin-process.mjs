/**
 * 检测 / 结束本机微信（Weixin.exe）主进程。仅 Windows。
 */
import { execFileSync } from 'child_process';

/**
 * @returns {number | null} 运行中微信进程 PID；未找到则 null
 */
export function getRunningWeixinPid() {
  if (process.platform !== 'win32') return null;
  try {
    const out = execFileSync(
      'powershell.exe',
      [
        '-NoProfile',
        '-NonInteractive',
        '-Command',
        '$p = Get-Process -Name Weixin -ErrorAction SilentlyContinue | Sort-Object Id | Select-Object -First 1; if ($p) { $p.Id }',
      ],
      { encoding: 'utf8', windowsHide: true, maxBuffer: 64 * 1024 }
    );
    const n = Number(String(out).trim());
    return Number.isFinite(n) && n > 0 ? n : null;
  } catch {
    return null;
  }
}

function sleepMs(ms) {
  try {
    execFileSync(
      'powershell.exe',
      ['-NoProfile', '-NonInteractive', '-Command', `Start-Sleep -Milliseconds ${Math.max(0, ms | 0)}`],
      { windowsHide: true, timeout: Math.max(5000, ms + 2000) }
    );
  } catch {
    /* ignore */
  }
}

/**
 * 结束所有 Weixin.exe（含子进程树）。用于桌面启动前干净注入。
 * @returns {boolean} 结束时是否已无微信进程
 */
export function stopRunningWeixin({ waitMs = 2500 } = {}) {
  if (process.platform !== 'win32') return true;
  if (!getRunningWeixinPid()) return true;
  try {
    execFileSync('taskkill', ['/IM', 'Weixin.exe', '/F', '/T'], {
      windowsHide: true,
      timeout: 15000,
    });
  } catch {
    return !getRunningWeixinPid();
  }
  const deadline = Date.now() + waitMs;
  while (Date.now() < deadline) {
    if (!getRunningWeixinPid()) return true;
    sleepMs(300);
  }
  return !getRunningWeixinPid();
}

/**
 * 仅桌面「首次启动注入」时允许先关微信；看门狗重试不得带此标记。
 * 需同时 WECHAT_BOOTSTRAP_INJECT=1，且 WECHAT_QUIT_BEFORE_INJECT≠0。
 */
export function shouldQuitWeixinBeforeInject() {
  return (
    process.env.WECHAT_BOOTSTRAP_INJECT === '1' &&
    process.env.WECHAT_QUIT_BEFORE_INJECT !== '0'
  );
}
