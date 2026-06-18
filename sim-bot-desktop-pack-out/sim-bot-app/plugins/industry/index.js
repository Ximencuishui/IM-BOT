import { industryStore } from './store.js';
import { createRouter } from './routes.js';

export const plugin = {
  id: 'industry',
  name: '行业管理',
  version: '1.0.0',
  dependencies: ['knowledge-base', 'membership', 'appointment'],
  lifecycle: {
    async install(db) {
      await industryStore.init(db);
    },
    async startup(ctx) {},
    async shutdown(ctx) {},
  },
  api: {
    prefix: '/admin/shop/industry',
    router: createRouter,
  },
  handlers: {
    inboundMessage: async (ctx, text, wxid, nick) => {
      // 服务项目查询
      if (/项目|服务|怎么收费|多少钱|价格|按摩|理疗|美容/.test(text)) {
        const services = industryStore.listServices(ctx.db, { is_active: true, pageSize: 50 });
        if (services.items.length > 0) {
          let reply = '📋 服务项目及收费标准：\n';
          let lastCategory = '';
          for (const s of services.items) {
            if (s.category && s.category !== lastCategory) {
              reply += `\n【${s.category}】\n`;
              lastCategory = s.category;
            }
            reply += `  ${s.name}  ${s.duration_minutes}分钟  ¥${s.price}`;
            if (s.original_price > s.price) reply += ` (原价¥${s.original_price})`;
            reply += '\n';
          }
          reply += '\n回复「预约+项目+时间」即可预约，或联系老板咨询详情。';
          return reply;
        }
      }

      // 位置/地址查询
      if (/怎么去|怎么到|在哪里|位置|地址|导航|路线/.test(text)) {
        const info = industryStore.getShopInfo(ctx.db);
        if (info && info.address) {
          let reply = `📍 ${info.name || '本店'}\n地址：${info.address}`;
          if (info.phone) reply += `\n电话：${info.phone}`;
          if (info.business_hours) reply += `\n营业时间：${info.business_hours}`;
          if (info.latitude && info.longitude) {
            reply += `\n导航：https://uri.amap.com/marker?position=${info.longitude},${info.latitude}&name=${encodeURIComponent(info.name || '本店')}`;
          }
          return reply;
        }
        return '📍 本店地址请咨询老板获取。';
      }

      // 营业信息
      if (/营业|开门|关门|电话|联系方式/.test(text)) {
        const info = industryStore.getShopInfo(ctx.db);
        if (info) {
          let reply = '';
          if (info.name) reply += `🏪 ${info.name}\n`;
          if (info.business_hours) reply += `⏰ 营业时间：${info.business_hours}\n`;
          if (info.phone) reply += `📞 电话：${info.phone}`;
          return reply.trim() || '请联系老板了解营业信息。';
        }
      }

      // 创建待回答问题
      if (/咨询|问题|想问|请问/.test(text) || text.endsWith('？') || text.endsWith('?')) {
        try {
          industryStore.createPendingQuestion(ctx.db, { question: text, asker_name: nick || '', asker_wxid: wxid || '' });
          return `🤔 这个问题我需要请教一下老板，稍后给您回复！\n（已通知老板）`;
        } catch (e) {
          return null;
        }
      }

      return null;
    },
    bossCommand: async (ctx, text) => {
      // 回答提问
      const answerMatch = text.match(/^回答[#]?(\d+)[：:](.+)/);
      if (answerMatch) {
        try {
          const result = industryStore.answerPendingQuestion(ctx.db, Number(answerMatch[1]), answerMatch[2].trim());
          if (result.ok) {
            return `✅ 已回答问题「${result.question}」，答案已加入知识库。`;
          }
        } catch (e) {
          return `回答失败：${e.message}`;
        }
      }
      return null;
    },
  },
};