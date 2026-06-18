/**
 * 在线授权认证模块
 * 与云端后端通信进行在线登录和授权验证
 */
import https from 'https';
import http from 'http';

/**
 * 获取云端API基础URL
 * 优先使用环境变量 TONJCLAW_API_BASE，否则使用默认值
 */
export function getApiBase() {
  return String(
    process.env.TONJCLAW_API_BASE || process.env.CLOUD_API_BASE || 'https://api.tonjclaw.com'
  ).trim().replace(/\/+$/, '');
}

/**
 * 发起HTTP请求到云端API
 */
function requestApi(method, path, body = null, token = null) {
  return new Promise((resolve, reject) => {
    const base = getApiBase();
    const url = new URL(path, base);
    const isHttps = url.protocol === 'https:';
    const transport = isHttps ? https : http;

    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
      hostname: url.hostname,
      port: url.port || (isHttps ? 443 : 80),
      path: url.pathname + url.search,
      method: method.toUpperCase(),
      headers,
      timeout: 15000,
    };

    const req = transport.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ status: res.statusCode, data: parsed });
        } catch {
          resolve({ status: res.statusCode, data: { raw: data } });
        }
      });
    });

    req.on('error', (err) => {
      if (err.code === 'ENOTFOUND' || err.code === 'EAI_AGAIN') {
        reject(new Error('无法连接到服务器，请检查网络设置'));
      } else if (err.code === 'ETIMEDOUT' || err.code === 'ESOCKETTIMEDOUT') {
        reject(new Error('连接超时，请检查网络连接'));
      } else if (err.code === 'ECONNREFUSED') {
        reject(new Error('服务器拒绝连接，请稍后重试'));
      } else {
        reject(new Error(`网络错误：${err.message}`));
      }
    });
    req.on('timeout', () => { req.destroy(); reject(new Error('请求超时')); });

    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

/**
 * 在线登录
 * @param {string} email - 用户邮箱
 * @param {string} password - 密码
 * @returns {Promise<{ok: boolean, data?: object, error?: string}>}
 */
export async function onlineLogin(email, password) {
  try {
    const em = String(email || '').trim();
    const pw = String(password || '');
    if (!em || !pw) return { ok: false, error: '请输入邮箱和密码' };

    const result = await requestApi('POST', '/api/auth/login', {
      username: em,
      password: pw,
    });

    if (result.status >= 200 && result.status < 300 && result.data?.success) {
      return {
        ok: true,
        user: result.data.user,
        token: result.data.token,
        license: result.data.license,
      };
    }

    const errMsg = result.data?.error || '登录失败，请检查账号密码';
    return { ok: false, error: errMsg };
  } catch (err) {
    return { ok: false, error: `网络错误：${err?.message || '无法连接到服务器'}` };
  }
}

/**
 * 检查授权状态
 * @param {string} token - JWT Token
 * @returns {Promise<{ok: boolean, license?: object, error?: string}>}
 */
export async function checkLicense(token) {
  try {
    if (!token) return { ok: false, error: '未提供认证令牌' };

    const result = await requestApi('GET', '/api/license/check', null, token);

    if (result.status >= 200 && result.status < 300 && result.data?.success) {
      return { ok: true, license: result.data.license };
    }

    return { ok: false, error: result.data?.error || '授权检查失败' };
  } catch (err) {
    return { ok: false, error: `网络错误：${err?.message || '无法连接到服务器'}` };
  }
}