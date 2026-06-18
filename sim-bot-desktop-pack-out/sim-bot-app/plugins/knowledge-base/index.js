import { knowledgeStore } from './store.js';
import { createRouter } from './routes.js';

export const plugin = {
  id: 'knowledge-base',
  name: 'Knowledge Base',
  version: '1.0.0',
  dependencies: [],
  lifecycle: {
    async install(db) {
      await knowledgeStore.init(db);
    },
    async startup(ctx) {},
    async shutdown(ctx) {},
  },
  api: {
    prefix: '/admin/shop/knowledge',
    router: createRouter,
  },
  handlers: {
    inboundMessage: async (ctx, text, wxid, nick) => {
      const results = knowledgeStore.search(ctx.db, text, 1);
      if (results.length > 0) {
        return `🤖 ${results[0].question}\n${results[0].answer}`;
      }
      return null;
    },
    bossCommand: async (ctx, text) => {
      if (text.startsWith('knowledge')) {
        const items = knowledgeStore.getAll(ctx.db, { pageSize: 5 });
        if (items.total === 0) return 'Knowledge base is empty';
        return items.items.map(i => `${i.id}. ${i.question}`).join('\n');
      }
      return null;
    },
  },
};
