/** 微信 appmsg XML（文件/链接等）识别，不做业务解释 */

/** Hook msgType：非文本类入站（表情/图/音视频等），不参与下单与「无法识别」回执 */
const WECHAT_NON_TEXT_MSG_TYPES = new Set([
  3, 34, 42, 43, 47, 48, 50, 62, 66, 10000,
]);

export function isWeChatNonTextXmlContent(text) {
  const s = String(text || '').trim();
  if (!s || s.length < 8 || !/[<＜]/.test(s)) return false;
  if (/<msg>\s*<emoji\b/i.test(s) || (/<emoji\b/i.test(s) && /<\/emoji>/i.test(s))) return true;
  if (/<img\b/i.test(s) || /<imgmsg\b/i.test(s) || /<videomsg\b/i.test(s) || /<voicemsg\b/i.test(s))
    return true;
  if (/<location\b/i.test(s) || /<pat\b/i.test(s)) return true;
  if (/<card\b/i.test(s) || /<namecard\b/i.test(s)) return true;
  if (isWeChatAppMsgXml(s) && !isWeChatInboundFileXml(s)) return true;
  if (/^<msg>\s*<appmsg\b/i.test(s)) return true;
  if (/^<msg>[\s\S]*<\/msg>\s*$/i.test(s) && !/[\u4e00-\u9fff]{2,}/.test(s.replace(/<[^>]+>/g, ''))) return true;
  return false;
}

/** 是否应静默忽略的入站（表情、图片、链接卡片等） */
export function isWeChatNonTextInbound(obj, content) {
  const mt = Number(obj?.msgType ?? obj?.msg_type);
  if (Number.isFinite(mt)) {
    if (mt === 1) {
      /* 个别 Hook 仍把表情 XML 标成文本，靠正文再判 */
    } else if (mt === 49) {
      const c = String(content || '').trim();
      if (isWeChatInboundFileXml(c)) return false;
      return true;
    } else if (mt === 10002) {
      return true;
    } else if (WECHAT_NON_TEXT_MSG_TYPES.has(mt) || (mt !== 1 && mt !== 49)) {
      return true;
    }
  }
  const rt = String(obj?.recive_type || obj?.receive_type || '');
  if (/表情|图片|语音|视频|名片|位置|动画表情|贴纸/u.test(rt)) return true;
  return isWeChatNonTextXmlContent(content);
}

export function isWeChatAppMsgXml(text) {
  const s = String(text || '').trim();
  if (!s || s.length < 24) return false;
  if (!/<appmsg\b/i.test(s)) return false;
  return s.includes('<?xml') || /<msg\b/i.test(s) || /<appmsg\b/i.test(s);
}

/** appmsg type=6：群文件/附件 */
export function parseWeChatFileAppMsg(text) {
  const s = String(text || '');
  if (!isWeChatAppMsgXml(s)) return null;
  const typeM = s.match(/<type>\s*(\d+)\s*<\/type>/i);
  const appType = typeM ? Number(typeM[1]) : NaN;
  if (appType !== 6) return null;
  const pick = (re) => {
    const m = s.match(re);
    return m ? String(m[1] || '').trim() : '';
  };
  return {
    appType,
    title: pick(/<title>([^<]*)<\/title>/i),
    fileext: pick(/<fileext>([^<]*)<\/fileext>/i).toLowerCase(),
    aeskey: pick(/<aeskey>([^<]*)<\/aeskey>/i),
    cdnattachurl: pick(/<cdnattachurl>([^<]*)<\/cdnattachurl>/i),
    attachid: pick(/<attachid>([^<]*)<\/attachid>/i),
    totallen: Number(pick(/<totallen>\s*(\d+)/i) || 0),
  };
}

export function isWeChatInboundFileXml(text) {
  return parseWeChatFileAppMsg(text) != null;
}

export function hookPayloadLooksLikeFileMessage(obj) {
  if (!obj || typeof obj !== 'object') return false;
  const mt = Number(obj.msgType);
  const rt = String(obj.recive_type || obj.receive_type || '');
  if (mt === 49 && /文件|附件/u.test(rt)) return true;
  const c = String(
    (obj.real_content != null ? obj.real_content : '') ||
      (obj.content && typeof obj.content === 'object' ? obj.content.String : obj.content) ||
      ''
  );
  return isWeChatInboundFileXml(c);
}
