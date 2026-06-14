import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  isWeChatAppMsgXml,
  isWeChatInboundFileXml,
  isWeChatNonTextInbound,
  parseWeChatFileAppMsg,
  hookPayloadLooksLikeFileMessage,
} from './wechat_appmsg.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_INBOUND_DIR = path.join(__dirname, '../../data/inbound_attach');

const LOCAL_PATH_KEYS = [
  'file_path',
  'filepath',
  'local_path',
  'localPath',
  'save_path',
  'savePath',
  'attach_path',
  'attachPath',
  'full_path',
  'fullpath',
  'downloaded_path',
  'downloadedPath',
];

function strFieldLoose(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v.trim();
  if (typeof v === 'object' && typeof v.String === 'string') return v.String.trim();
  return String(v).trim();
}

function pickLocalPathFromPayload(obj) {
  if (!obj || typeof obj !== 'object') return '';
  for (const k of LOCAL_PATH_KEYS) {
    const p = strFieldLoose(obj[k]);
    if (p && fs.existsSync(p)) return p;
  }
  const nested = obj.attach || obj.file || obj.appattach;
  if (nested && typeof nested === 'object') {
    for (const k of LOCAL_PATH_KEYS) {
      const p = strFieldLoose(nested[k]);
      if (p && fs.existsSync(p)) return p;
    }
  }
  return '';
}

function isTextLikeExt(ext) {
  const e = String(ext || '').toLowerCase().replace(/^\./, '');
  return !e || e === 'txt' || e === 'text' || e === 'log' || e === 'csv';
}

export function tryReadUtf8TextFile(filePath, fileext = '') {
  const p = String(filePath || '').trim();
  if (!p || !fs.existsSync(p)) return null;
  const ext = path.extname(p).replace(/^\./, '') || String(fileext || '');
  if (!isTextLikeExt(ext)) return null;
  try {
    const stat = fs.statSync(p);
    if (!stat.isFile() || stat.size > 2 * 1024 * 1024) return null;
    const buf = fs.readFileSync(p);
    if (!buf.length) return '';
    let text = buf.toString('utf8');
    if (text.includes('\uFFFD') && buf.includes(0)) {
      text = buf.toString('latin1');
    }
    return String(text).replace(/^\uFEFF/, '').trim();
  } catch {
    return null;
  }
}

function inboundAttachSaveDir() {
  const dir = String(process.env.HOOK_INBOUND_FILE_DIR || DEFAULT_INBOUND_DIR).trim();
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function safeFileBaseName(title, fileext) {
  let name = String(title || 'attach').trim() || 'attach';
  name = name.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_');
  if (fileext && !name.toLowerCase().endsWith(`.${fileext}`)) {
    name = `${name}.${fileext}`;
  }
  return name.slice(0, 120);
}

/**
 * 将 Hook 入站中的文件 XML 解析为可下单文本；无法读取时返回 kind=file_unresolved。
 * @returns {Promise<{ text: string | null, kind: string, fileInfo?: object, path?: string }>}
 */
export async function resolveInboundOrderText(obj, ex, hookClient, logger) {
  const content = String(ex?.content || '').trim();
  const original = String(ex?.originalContent || '').trim();
  const realRaw = obj?.real_content != null ? String(obj.real_content).trim() : '';

  if (realRaw && !isWeChatAppMsgXml(realRaw) && realRaw !== content) {
    return { text: realRaw, kind: 'real_content' };
  }

  if (
    isWeChatNonTextInbound(obj, content) ||
    isWeChatNonTextInbound(obj, original) ||
    isWeChatNonTextInbound(obj, realRaw)
  ) {
    return { text: null, kind: 'non_text' };
  }

  const fileInfo =
    parseWeChatFileAppMsg(content) ||
    parseWeChatFileAppMsg(original) ||
    (hookPayloadLooksLikeFileMessage(obj) ? parseWeChatFileAppMsg(content || original) : null);

  if (!fileInfo && !isWeChatAppMsgXml(content) && !isWeChatAppMsgXml(original)) {
    return { text: content, kind: 'plain' };
  }

  if (!fileInfo) {
    if (isWeChatAppMsgXml(content) || isWeChatAppMsgXml(original)) {
      return { text: null, kind: 'unsupported_appmsg' };
    }
    return { text: content, kind: 'plain' };
  }

  const localPath = pickLocalPathFromPayload(obj);
  if (localPath) {
    const text = tryReadUtf8TextFile(localPath, fileInfo.fileext);
    if (text != null) return { text, kind: 'local_file', path: localPath, fileInfo };
  }

  if (
    hookClient &&
    typeof hookClient.downloadInboundAttach === 'function' &&
    isTextLikeExt(fileInfo.fileext || path.extname(fileInfo.title))
  ) {
    try {
      const saveDir = inboundAttachSaveDir();
      const savePath = path.join(
        saveDir,
        `${Date.now()}_${safeFileBaseName(fileInfo.title, fileInfo.fileext || 'txt')}`
      );
      const dl = await hookClient.downloadInboundAttach(fileInfo, obj, savePath);
      if (dl?.path && fs.existsSync(dl.path)) {
        const text = tryReadUtf8TextFile(dl.path, fileInfo.fileext);
        if (text != null) return { text, kind: 'downloaded', path: dl.path, fileInfo };
      }
    } catch (e) {
      logger?.warn?.(`[inbound-file] download failed: ${e?.message || e}`);
    }
  }

  return { text: null, kind: 'file_unresolved', fileInfo };
}

export {
  isWeChatInboundFileXml,
  isWeChatAppMsgXml,
  isWeChatNonTextInbound,
  hookPayloadLooksLikeFileMessage,
};
