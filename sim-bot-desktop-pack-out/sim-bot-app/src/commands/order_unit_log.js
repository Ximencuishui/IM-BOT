import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function logFilePath() {
  const dir = process.env.ORDER_UNIT_LOG_DIR || path.join(__dirname, '../../data/logs');
  return path.join(dir, 'order-units.log');
}

function ensureLogDir(file) {
  const dir = path.dirname(file);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

/**
 * 追加一条下单单元结构化记录（预处理后的四段式）。
 * @param {{ wxGroupId?: string, rawLine?: string, units?: object[], source?: string }} entry
 */
export function appendOrderUnitLog(entry) {
  try {
    const file = logFilePath();
    ensureLogDir(file);
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      ...entry,
    });
    fs.appendFileSync(file, `${line}\n`, 'utf8');
  } catch {
    /* 日志失败不影响下单 */
  }
}
