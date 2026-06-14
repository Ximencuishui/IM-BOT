import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';

/**
 * 分层加载环境变量：仓库 .env → 安装包 config/runtime.env → %APPDATA%\\SimBot\\config.env
 * 后加载的覆盖先加载的，便于桌面端核销 32 位卡密与用户本地覆盖。
 */
export function loadRuntimeEnv(projectRoot) {
  dotenv.config();
  const root = path.resolve(projectRoot || '.');
  const layered = [path.join(root, 'config', 'runtime.env')];
  const appData = process.env.APPDATA;
  if (appData) {
    layered.push(path.join(appData, 'SimBot', 'config.env'));
  }
  for (const envPath of layered) {
    if (fs.existsSync(envPath)) {
      dotenv.config({ path: envPath, override: true });
    }
  }
  if (!process.env.ACTIVATION_PUBLIC_KEY_PATH) {
    const pub = path.join(root, 'keys', 'activation_public.pem');
    if (fs.existsSync(pub)) {
      process.env.ACTIVATION_PUBLIC_KEY_PATH = pub;
    }
  }
}
