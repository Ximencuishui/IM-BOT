import axios from 'axios';
import fs from 'fs';
import { parseProfileCacheResponse } from './profile_cache.js';

/**
 * Hook 控制面占位：实际路径以 Apifox 文档为准。
 * 课题中仅演示如何带 Token 发 HTTP，不绑定具体玩法接口。
 */
export function createHookClient(baseURL, token) {
  const client = axios.create({
    baseURL: baseURL.replace(/\/$/, ''),
    timeout: 10000,
    headers: token ? { Authorization: `Bearer ${token}`, 'X-Api-Key': token } : {},
  });

  const isHookSuccess = (data) => {
    if (data && data.errCode != null) return Number(data.errCode) === 0;
    if (data && data.code != null) return Number(data.code) === 0;
    return true;
  };

  return {
    /** 控制面是否可达：GET / 失败时回退 POST 常用接口（部分 Hook 不对 GET 响应） */
    async probeControlPlane() {
      try {
        await client.get('/', { timeout: 4000 });
        return { ok: true, via: 'get_root' };
      } catch {
        /* fall through */
      }
      const fallbacks = ['/api/get_profile_cache', '/api/check_login', '/api/get_chatroom_list'];
      for (const apiPath of fallbacks) {
        try {
          await client.post(apiPath, {}, { timeout: 6000 });
          return { ok: true, via: apiPath };
        } catch {
          /* try next */
        }
      }
      return { ok: false, error: 'control_plane_unreachable' };
    },
    async healthProbe() {
      const r = await this.probeControlPlane();
      return r.ok ? { ok: true } : { ok: false, error: r.error };
    },
    /** 获取个人资料缓存（当前登录 wxid / 昵称 / 头像） */
    async getProfileCache() {
      try {
        const { data } = await client.post('/api/get_profile_cache', {}, { timeout: 10000 });
        return parseProfileCacheResponse(data);
      } catch (e) {
        return {
          ok: false,
          wxid: '',
          nickname: '',
          avatar_url: '',
          raw: null,
          error: e.message,
        };
      }
    },
    /** 探测 Hook 控制面返回的当前登录 wxid（优先 get_profile_cache） */
    async probeLoginWxid() {
      try {
        const prof = await this.getProfileCache();
        if (prof.ok && prof.wxid) {
          return {
            ok: true,
            wxid: prof.wxid,
            apiPath: '/api/get_profile_cache',
            nickname: prof.nickname,
            avatar_url: prof.avatar_url,
            raw: prof.raw,
          };
        }
      } catch {
        /* fallback */
      }
      const paths = [
        '/api/check_login',
        '/api/get_login_info',
        '/api/get_user_info',
        '/api/GetUserInfo',
        '/api/get_account_info',
      ];
      const pickWxid = (data) => {
        if (!data || typeof data !== 'object') return '';
        const top = [
          data.account_wxid,
          data.wxid,
          data.userName,
          data.username,
          data.account,
          data.self_wxid,
          data.login_wxid,
        ];
        const d = data.data && typeof data.data === 'object' ? data.data : data;
        const nested = [d.wxid, d.userName, d.username, d.account, d.self_wxid, d.login_wxid];
        for (const c of [...top, ...nested]) {
          const s = String(c || '').trim();
          if (s && !s.endsWith('@chatroom')) return s;
        }
        return '';
      };
      for (const apiPath of paths) {
        try {
          const { data } = await client.post(apiPath, {}, { timeout: 8000 });
          const wxid = pickWxid(data);
          if (wxid) {
            return { ok: true, wxid, apiPath, raw: data };
          }
        } catch {
          /* try next */
        }
      }
      return { ok: false, wxid: '', message: 'hook login wxid not available' };
    },
    async getChatroomList() {
      try {
        const { data } = await client.post('/api/get_chatroom_list', {});
        const list = Array.isArray(data?.data) ? data.data : [];
        const codeNum = Number(data?.code);
        const msgText = String(data?.msg || '').toLowerCase();
        const ok =
          codeNum === 0 ||
          codeNum === 1 ||
          msgText.includes('success') ||
          (list.length > 0 && Number(data?.total || 0) >= 0);
        return {
          ok,
          message: data?.msg || '',
          total: Number(data?.total || list.length || 0),
          items: list.map((item) => ({
            username: item?.username || '',
            nick_name: item?.nick_name || '',
            remark: item?.remark || '',
            small_head_url: item?.small_head_url || '',
            big_head_url: item?.big_head_url || '',
          })),
          raw: data,
        };
      } catch (e) {
        return { ok: false, message: e.message, items: [], total: 0 };
      }
    },
    async getRoomMembers(roomId) {
      try {
        const { data } = await client.post('/api/get_room_members', { room_id: roomId });
        const owner = data?.chatRoomOwner || '';
        const memberList = data?.newChatroomData?.chatRoomMember;
        const members = Array.isArray(memberList)
          ? memberList.map((item) => ({
              userName: item?.userName || '',
              nickName: item?.nickName || '',
              displayName: item?.displayName || '',
              smallHeadImgUrl: item?.smallHeadImgUrl || '',
              bigHeadImgUrl: item?.bigHeadImgUrl || '',
              inviterUserName: item?.inviterUserName || '',
              status: item?.status ?? null,
            }))
          : [];
        const ret = Number(data?.baseResponse?.ret ?? 0);
        return {
          ok: ret === 0,
          roomId: data?.chatroomUserName || roomId,
          owner,
          members,
          allMemberCount: Number(data?.allMemberCount || members.length || 0),
          raw: data,
        };
      } catch (e) {
        return { ok: false, roomId, owner: '', members: [], allMemberCount: 0, message: e.message };
      }
    },
    async sendTextMsg(wxid, msg) {
      try {
        const { data } = await client.post('/api/send_text_msg', {
          wxid,
          msg,
        }, { timeout: 5000 });
        return {
          ok: isHookSuccess(data),
          message: data?.errMsg || data?.msg || '',
          raw: data,
        };
      } catch (e) {
        return {
          ok: false,
          message: e.message,
          raw: e?.response?.data,
        };
      }
    },
    async sendAtText(roomId, msg, wxids) {
      try {
        const { data } = await client.post('/api/send_at_text', {
          roomId,
          msg,
          wxids,
        }, { timeout: 3000 });
        return {
          // 该接口在部分环境会返回 errCode!=0 但消息实际已发出，避免误判导致重复补发
          ok: true,
          message: data?.errMsg || data?.msg || '',
          raw: data,
        };
      } catch (e) {
        return {
          ok: false,
          message: e.message,
          raw: e?.response?.data,
        };
      }
    },
    async sendFileMsg(wxid, filepath) {
      try {
        const { data } = await client.post(
          '/api/send_file_msg',
          {
            wxid,
            filepath,
          },
          { timeout: 8000 }
        );
        return {
          ok: true,
          message: data?.errMsg || data?.msg || '',
          raw: data,
        };
      } catch (e) {
        return {
          ok: false,
          message: e.message,
          raw: e?.response?.data,
        };
      }
    },
    /**
     * 从 appmsg XML 中的 CDN 字段下载入站附件（不同 Hook 实现路径不一，依次尝试）。
     * 可通过 HOOK_CDN_DOWNLOAD_PATH 指定逗号分隔的 API 路径。
     */
    async downloadInboundAttach(fileInfo, hookMsg, savePath) {
      const info = fileInfo || {};
      const dest = String(savePath || '').trim();
      if (!dest) return { ok: false, message: 'savePath required' };

      const configured = String(process.env.HOOK_CDN_DOWNLOAD_PATH || '')
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean);
      const apiPaths = configured.length
        ? configured
        : [
            '/api/download_attach',
            '/api/cdn_download',
            '/api/cdnDownFile',
            '/api/download_file',
            '/api/CdnDown',
          ];

      const msgId = hookMsg?.msgId != null ? String(hookMsg.msgId) : '';
      const newMsgId = hookMsg?.newMsgId != null ? String(hookMsg.newMsgId) : '';
      const bodies = [
        {
          cdnUrl: info.cdnattachurl,
          aesKey: info.aeskey,
          fileName: info.title,
          savePath: dest,
          fileType: 5,
        },
        {
          cdnattachurl: info.cdnattachurl,
          aeskey: info.aeskey,
          filename: info.title,
          save_path: dest,
        },
        {
          attachid: info.attachid,
          aeskey: info.aeskey,
          save_path: dest,
        },
        {
          msg_id: msgId,
          new_msg_id: newMsgId,
          save_path: dest,
        },
      ].filter((b) => Object.values(b).some((v) => v != null && String(v).trim() !== ''));

      for (const apiPath of apiPaths) {
        for (const body of bodies) {
          try {
            const { data } = await client.post(apiPath, body, { timeout: 12000 });
            if (fs.existsSync(dest)) {
              return { ok: true, path: dest, message: data?.msg || '', raw: data, apiPath };
            }
            const hinted =
              data?.path ||
              data?.file_path ||
              data?.filepath ||
              data?.save_path ||
              data?.data?.path ||
              data?.data?.file_path;
            if (hinted && fs.existsSync(String(hinted))) {
              return { ok: true, path: String(hinted), message: data?.msg || '', raw: data, apiPath };
            }
            if (isHookSuccess(data)) {
              return { ok: true, path: dest, message: data?.msg || '', raw: data, apiPath };
            }
          } catch {
            /* try next */
          }
        }
      }
      return { ok: false, message: 'no hook download API succeeded' };
    },
  };
}
