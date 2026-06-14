import { execFileSync } from 'child_process';

/** 本机是否有 PC 微信主进程（Weixin），与 scripts/weixin-process.mjs 一致 */
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

export function isWeixinProcessRunning() {
  return getRunningWeixinPid() != null;
}
