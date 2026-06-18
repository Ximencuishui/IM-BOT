import { appointmentStore } from './store.js';
import { createRouter } from './routes.js';

export const plugin = {
  id: 'appointment',
  name: 'Appointment',
  version: '1.0.0',
  dependencies: [],
  lifecycle: {
    async install(db) {
      await appointmentStore.init(db);
    },
    async startup(ctx) {},
    async shutdown(ctx) {},
  },
  api: {
    prefix: '/admin/shop/appointments',
    router: createRouter,
  },
  handlers: {
    inboundMessage: async (ctx, text, wxid, nick) => {
      if (/预约|预订|订位|今天有空|明天有空/.test(text)) {
        const today = new Date();
        const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        const slots = appointmentStore.getAvailableSlots(ctx.db, dateStr, 60);
        if (slots.length > 0) {
          let reply = '🕐 今日可预约时段：\n';
          for (const slot of slots.slice(0, 8)) {
            reply += `  ${slot.start_time} - ${slot.end_time}\n`;
          }
          reply += '\n回复「预约+时间+项目」即可预约。';
          return reply;
        }
        return '🕐 今日暂无可预约时段，请联系老板。';
      }
      return null;
    },
    bossCommand: async (ctx, text) => {
      if (/预约报表|今日预约|明日预约|本周预约|预约统计/.test(text)) {
        const today = new Date();
        let date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        if (text.includes('明日') || text.includes('明天')) {
          const tomorrow = new Date(today);
          tomorrow.setDate(tomorrow.getDate() + 1);
          date = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`;
        }
        const appointments = appointmentStore.getAll(ctx.db, { date, pageSize: 50 });
        if (appointments.items.length > 0) {
          let reply = `📅 ${date} 预约报表（共${appointments.total}条）：\n`;
          let pending = 0, confirmed = 0;
          for (const a of appointments.items) {
            if (a.status === 'pending') pending++;
            if (a.status === 'confirmed') confirmed++;
            reply += `  ${a.start_time}-${a.end_time} ${a.customer_name}`;
            if (a.status === 'pending') reply += ' ⏳待确认';
            if (a.status === 'confirmed') reply += ' ✅已确认';
            if (a.status === 'completed') reply += ' ✔已完成';
            reply += '\n';
          }
          reply += `\n待确认：${pending} 已确认：${confirmed} 已完成：${appointments.items.filter(a => a.status === 'completed').length}`;
          return reply;
        }
        return `📅 ${date} 暂无预约记录。`;
      }
      return null;
    },
  },
};