/**
 * 启动微信 Hook 注入：查找 Weixin.exe → 调用 hk\x64 inject.exe
 *
 * 若检测到微信已在运行，则向 inject 传入 PID（仅注入，不再拉起新微信）。
 * 若需始终传入 Weixin.exe 路径（可能再启实例），设置 WECHAT_INJECT_ALWAYS_LAUNCH=1。
 *
 * 用法（在项目根目录）: node scripts/launch-wechat-hook.mjs
 * 依赖环境变量见 .env（TCP_PORT、HOOK_CALLBACK_PORT、HOOK_DLL_HTTP_PORT 等）
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { loadRuntimeEnv } from '../src/util/load_runtime_env.js';
import { hookInjectConfigJson } from '../src/hook/inject_config.js';
import { spawn } from 'child_process';
import os from 'os';
import { locateWeixinExe } from './weixin-locate.mjs';
import {
  getRunningWeixinPid,
  shouldQuitWeixinBeforeInject,
  stopRunningWeixin,
} from './weixin-process.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = process.env.SIM_BOT_ROOT
  ? path.resolve(process.env.SIM_BOT_ROOT)
  : path.resolve(__dirname, '..');
loadRuntimeEnv(projectRoot);

function main() {
  if (os.platform() !== 'win32') {
    console.error('本脚本仅支持 Windows。');
    process.exit(1);
  }

  const hkRoot = process.env.WECHAT_HK_DIR
    ? path.resolve(process.env.WECHAT_HK_DIR)
    : path.join(projectRoot, 'hk');
  const injectExe = path.join(hkRoot, 'x64 inject.exe');
  const dllPath = path.join(hkRoot, 'libGLESv1.dll');

  if (!fs.existsSync(injectExe)) {
    console.error('未找到注入程序：', injectExe);
    process.exit(1);
  }
  if (!fs.existsSync(dllPath)) {
    console.error('未找到 DLL：', dllPath);
    process.exit(1);
  }

  const alwaysLaunch = process.env.WECHAT_INJECT_ALWAYS_LAUNCH === '1';
  if (!alwaysLaunch && shouldQuitWeixinBeforeInject() && getRunningWeixinPid()) {
    console.log('[bootstrap] 关闭已运行的微信，以便按当前配置重新注入（仅此一次）…');
    stopRunningWeixin({ waitMs: 3000 });
  }

  let runningPid = alwaysLaunch ? null : getRunningWeixinPid();
  let weixinAbs = null;

  if (runningPid == null) {
    console.log('查找微信…');
    const weixin = locateWeixinExe({
      onFullScanHint: () => {
        console.log('   （注册表与常见路径未命中，正在进行全盘搜索，可能需要较长时间…）');
      },
    });

    if (!weixin) {
      console.error('未找到 Weixin.exe，请确认已安装 PC 版微信（Weixin）。');
      process.exit(1);
    }

    console.log(`找到——${weixin}`);
    weixinAbs = path.resolve(weixin);
  } else {
    console.log(`检测到微信已在运行（PID ${runningPid}），跳过定位安装路径，直接注入…`);
  }

  const jsonArg = hookInjectConfigJson();

  const targetArg = runningPid != null ? String(runningPid) : weixinAbs;

  if (runningPid == null) {
    if (alwaysLaunch) {
      console.log('WECHAT_INJECT_ALWAYS_LAUNCH=1，将向 inject 传入 Weixin.exe 路径…');
    } else {
      console.log('未检测到运行中的微信，将向 inject 传入 Weixin.exe 路径（由 inject 拉起）…');
    }
  }

  console.log('启动…');
  // inject.exe 参数须为绝对路径（含 DLL），避免依赖工作目录；首参为已有进程时为十进制 PID
  const child = spawn(injectExe, [targetArg, dllPath, jsonArg], {
    cwd: path.dirname(injectExe),
    detached: true,
    stdio: 'ignore',
    windowsHide: false,
  });
  child.unref();
  console.log('完成');
  console.log('');
  console.log('注入参数摘要：');
  if (runningPid != null) {
    console.log('  目标          PID', runningPid);
  } else {
    console.log('  Weixin.exe   ', weixinAbs);
  }
  console.log('  inject       ', injectExe);
  console.log('  DLL          ', dllPath);
  console.log('  JSON         ', jsonArg);
}

main();
