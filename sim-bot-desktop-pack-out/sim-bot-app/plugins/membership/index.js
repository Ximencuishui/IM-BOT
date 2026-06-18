import { membershipStore } from './store.js';
import { createRouter } from './routes.js';

export const plugin = {
  id: 'membership',
  name: 'Membership Cards',
  version: '1.0.0',
  dependencies: [],
  lifecycle: {
    async install(db) {
      await membershipStore.init(db);
    },
    async startup(ctx) {},
    async shutdown(ctx) {},
  },
  api: {
    prefix: '/admin/shop/membership-cards',
    router: createRouter,
  },
  handlers: {
    inboundMessage: async (ctx, text, wxid, nick) => {
      if (/会员卡|会员|次卡|余额|还剩|多少次/.test(text)) {
        if (wxid) {
          const cards = membershipStore.getAll(ctx.db, { customer_wxid: wxid, status: 'active' });
          if (cards.items.length > 0) {
            let reply = '💳 您的会员卡：\n';
            for (const card of cards.items) {
              reply += `  ${card.card_no} - ${card.customer_name}\n`;
              reply += `  总次数：${card.total_services} 次\n`;
              reply += `  已使用：${card.used_services} 次\n`;
              reply += `  剩余：${card.remaining_services} 次\n`;
              if (card.expire_date) reply += `  有效期至：${card.expire_date}\n`;
            }
            return reply;
          }
        }
        const match = text.match(/\b([A-Z0-9]{6,})\b/i);
        if (match) {
          const card = membershipStore.getByNo(ctx.db, match[1]);
          if (card) {
            return `💳 会员卡 ${card.card_no}\n客户：${card.customer_name}\n总次数：${card.total_services} 次\n已使用：${card.used_services} 次\n剩余：${card.remaining_services} 次${card.expire_date ? `\n有效期至：${card.expire_date}` : ''}`;
          }
        }
      }
      return null;
    },
    bossCommand: async (ctx, text) => {
      if (/会员卡报表|会员卡统计|会员统计/.test(text)) {
        const cards = membershipStore.getAll(ctx.db, { pageSize: 200 });
        const active = cards.items.filter(c => c.status === 'active');
        let reply = '💳 会员卡统计报表：\n';
        reply += `总会员卡数：${cards.total} 张\n`;
        reply += `有效会员卡：${active.length} 张\n`;
        const totalServices = active.reduce((sum, c) => sum + c.total_services, 0);
        const totalUsed = active.reduce((sum, c) => sum + c.used_services, 0);
        reply += `总服务次数：${totalServices} 次\n`;
        reply += `已使用次数：${totalUsed} 次\n`;
        reply += `剩余次数：${totalServices - totalUsed} 次\n`;
        return reply;
      }

      const useMatch = text.match(/销卡[：:]?\s*(\S+)/);
      if (useMatch) {
        const card = membershipStore.getByNo(ctx.db, useMatch[1].trim());
        if (!card) return `未找到卡号「${useMatch[1]}」的会员卡。`;
        try {
          const result = membershipStore.use(ctx.db, card.id, null, '');
          return `✅ 销卡成功！\n卡号：${result.card_no}\n客户：${result.customer_name}\n总次数：${result.total_services} 次\n已使用：${result.used_services} 次\n剩余：${result.remaining_services} 次`;
        } catch (e) {
          return `销卡失败：${e.message}`;
        }
      }
      return null;
    },
  },
};