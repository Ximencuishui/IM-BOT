import fs from 'fs';
import path from 'path';

/** @returns {string} hk 根目录（含 libGLESv1.dll、x64 inject.exe） */
export function resolveHkRoot(projectRoot = process.cwd()) {
  return process.env.WECHAT_HK_DIR
    ? path.resolve(process.env.WECHAT_HK_DIR)
    : path.join(projectRoot, 'hk');
}

/** 注入可执行文件路径（文件名含空格：x64 inject.exe，非 x64/inject.exe） */
export function resolveHookInjectExe(hkRoot) {
  return path.join(hkRoot, 'x64 inject.exe');
}

export function resolveHookDllPath(hkRoot) {
  return path.join(hkRoot, 'libGLESv1.dll');
}

/** 本地是否具备完整 Hook 注入套件 */
export function hookInjectKitPresent(projectRoot = process.cwd()) {
  const hkRoot = resolveHkRoot(projectRoot);
  return (
    fs.existsSync(resolveHookInjectExe(hkRoot)) && fs.existsSync(resolveHookDllPath(hkRoot))
  );
}

/** 是否应在 Windows 侧自动执行 launch-wechat-hook.mjs */
export function shouldAutoWeChatInject(projectRoot = process.cwd()) {
  if (process.platform !== 'win32') return false;
  if (process.env.AUTO_WECHAT_INJECT === '0') return false;
  if (process.env.AUTO_WECHAT_INJECT === '1' || process.env.HOOK_CONFIG_APPLY_ON_START === '1') {
    return true;
  }
  return hookInjectKitPresent(projectRoot);
}
