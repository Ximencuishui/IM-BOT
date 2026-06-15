/** PRD 3.1 入站三级路由：指令 → 数字 → 下注对象（USE_RUST_PRD=1 时优先 Rust CLI） */
import { classifyInboundCore } from './classify_core.js';
import { classifyInboundRust } from '../rust_bridge.js';

/**
 * @returns {'empty'|'instruction'|'drop'|'order'}
 */
export function classifyInboundForPipeline(text, opts = {}) {
  if (process.env.USE_RUST_PRD === '1') {
    return classifyInboundRust(text, { ...opts, db: opts.db });
  }
  return classifyInboundCore(text, opts);
}
