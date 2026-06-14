/**
 * 定位本机 Weixin.exe：注册表 → 常见安装路径 → 全盘遍历（最后手段）
 * 仅适用于 Windows；其它平台返回 null。
 */
import fs from 'fs';
import path from 'path';
import os from 'os';
import { execSync } from 'child_process';

const TARGET = 'weixin.exe';
const MAX_FULL_SCAN_DIRS = 280_000;

function parseRegValue(regOutput) {
  if (!regOutput) return null;
  for (const line of regOutput.split(/\r?\n/)) {
    const m = line.match(/\bREG_SZ\s+(.+)$/i) || line.match(/\bREG_EXPAND_SZ\s+(.+)$/i);
    if (m) return m[1].trim();
  }
  return null;
}

function expandEnvInPath(s) {
  if (!s) return s;
  return s.replace(/%([^%]+)%/g, (_, name) => process.env[name] || '');
}

/** 将注册表路径解析为存在的 Weixin.exe */
function normalizeInstallToWeixinExe(p) {
  if (!p) return null;
  let s = expandEnvInPath(String(p).trim().replace(/^["']|["']$/g, ''));
  if (!s) return null;
  if (s.toLowerCase().endsWith(TARGET)) {
    try {
      return fs.existsSync(s) ? path.resolve(s) : null;
    } catch {
      return null;
    }
  }
  const candidates = [
    path.join(s, 'Weixin.exe'),
    path.join(s, 'Weixin', 'Weixin.exe'),
  ];
  for (const c of candidates) {
    try {
      if (fs.existsSync(c)) return path.resolve(c);
    } catch {
      /* ignore */
    }
  }
  return null;
}

function tryRegistry() {
  if (os.platform() !== 'win32') return null;
  const queries = [
    ['HKCU\\Software\\Tencent\\Weixin', 'InstallPath'],
    ['HKCU\\Software\\Tencent\\Weixin', 'InstallLocation'],
    ['HKCU\\Software\\Tencent\\WeChat', 'InstallPath'],
    ['HKLM\\SOFTWARE\\WOW6432Node\\Tencent\\Weixin', 'InstallPath'],
    ['HKLM\\SOFTWARE\\Tencent\\Weixin', 'InstallPath'],
    ['HKLM\\SOFTWARE\\WOW6432Node\\Tencent\\WeChat', 'InstallPath'],
    ['HKLM\\SOFTWARE\\Tencent\\WeChat', 'InstallPath'],
  ];
  for (const [keyPath, valueName] of queries) {
    try {
      const out = execSync(`reg query "${keyPath}" /v "${valueName}"`, {
        encoding: 'utf8',
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'ignore'],
      });
      const raw = parseRegValue(out);
      const hit = normalizeInstallToWeixinExe(raw);
      if (hit) return hit;
    } catch {
      /* key missing */
    }
  }
  return null;
}

function tryCommonPaths() {
  const programRoots = [process.env.ProgramFiles, process.env['ProgramFiles(x86)']].filter(Boolean);
  for (const root of programRoots) {
    const tencent = path.join(root, 'Tencent');
    if (!fs.existsSync(tencent)) continue;
    let entries;
    try {
      entries = fs.readdirSync(tencent, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      if (!ent.isDirectory()) continue;
      const base = path.join(tencent, ent.name);
      const a = path.join(base, 'Weixin', 'Weixin.exe');
      const b = path.join(base, 'Weixin.exe');
      for (const c of [a, b]) {
        try {
          if (fs.existsSync(c)) return path.resolve(c);
        } catch {
          /* ignore */
        }
      }
    }
  }

  const la = process.env.LOCALAPPDATA;
  if (la) {
    const wxRoot = path.join(la, 'Tencent', 'Weixin');
    if (fs.existsSync(wxRoot)) {
      try {
        const subs = fs.readdirSync(wxRoot, { withFileTypes: true });
        for (const d of subs) {
          if (!d.isDirectory()) continue;
          const ex = path.join(wxRoot, d.name, 'Weixin.exe');
          if (fs.existsSync(ex)) return path.resolve(ex);
        }
      } catch {
        /* ignore */
      }
    }
  }

  return null;
}

function listWindowsDrives() {
  const out = [];
  for (let i = 65; i <= 90; i++) {
    const letter = String.fromCharCode(i);
    const root = `${letter}:\\`;
    try {
      if (fs.existsSync(root)) out.push(root);
    } catch {
      /* ignore */
    }
  }
  return out;
}

const SKIP_DIR_NAMES = new Set([
  'windows',
  '$recycle.bin',
  'system volume information',
  'node_modules',
  '.git',
  'intel',
  'amd',
  'nvidia',
  'program files\\windowsapps',
]);

function tryFullDiskScan(onSlowHint) {
  if (os.platform() !== 'win32') return null;
  if (typeof onSlowHint === 'function') onSlowHint();
  let scanned = 0;
  const drives = listWindowsDrives();
  for (const drive of drives) {
    const stack = [drive];
    while (stack.length > 0 && scanned < MAX_FULL_SCAN_DIRS) {
      const dir = stack.pop();
      let entries;
      try {
        entries = fs.readdirSync(dir, { withFileTypes: true });
      } catch {
        continue;
      }
      for (const ent of entries) {
        if (scanned >= MAX_FULL_SCAN_DIRS) break;
        scanned += 1;
        const full = path.join(dir, ent.name);
        if (ent.isFile() && ent.name.toLowerCase() === TARGET) {
          return path.resolve(full);
        }
        if (!ent.isDirectory()) continue;
        const low = ent.name.toLowerCase();
        if (SKIP_DIR_NAMES.has(low)) continue;
        stack.push(full);
      }
    }
  }
  return null;
}

/**
 * @param {{ onFullScanHint?: () => void }} [opts]
 * @returns {string | null} 绝对路径
 */
export function locateWeixinExe(opts = {}) {
  if (os.platform() !== 'win32') return null;
  const a = tryRegistry();
  if (a) return a;
  const b = tryCommonPaths();
  if (b) return b;
  return tryFullDiskScan(opts.onFullScanHint);
}
