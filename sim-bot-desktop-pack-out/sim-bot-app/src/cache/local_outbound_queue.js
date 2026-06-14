/** 延迟出站队列（按 notBeforeMs 排序，替代 Redis ZSET） */

const POLL_MS = Math.max(50, Number(process.env.OUTBOUND_QUEUE_POLL_MS ?? 100));

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** 最小堆：堆顶为最早 notBeforeMs */
function heapPush(heap, item) {
  heap.push(item);
  let i = heap.length - 1;
  while (i > 0) {
    const p = (i - 1) >> 1;
    if (heap[p].notBeforeMs <= heap[i].notBeforeMs) break;
    [heap[p], heap[i]] = [heap[i], heap[p]];
    i = p;
  }
}

function heapPop(heap) {
  if (heap.length === 0) return null;
  const top = heap[0];
  const last = heap.pop();
  if (heap.length > 0 && last) {
    heap[0] = last;
    let i = 0;
    for (;;) {
      const l = i * 2 + 1;
      const r = l + 1;
      let smallest = i;
      if (l < heap.length && heap[l].notBeforeMs < heap[smallest].notBeforeMs) smallest = l;
      if (r < heap.length && heap[r].notBeforeMs < heap[smallest].notBeforeMs) smallest = r;
      if (smallest === i) break;
      [heap[i], heap[smallest]] = [heap[smallest], heap[i]];
      i = smallest;
    }
  }
  return top;
}

function heapPeek(heap) {
  return heap.length > 0 ? heap[0] : null;
}

export function createLocalOutboundQueue({ executeJob, randomGapMs = () => 0, logger } = {}) {
  const heap = [];
  let workerRunning = false;
  let nextAllowedSendAtMs = 0;
  let pollTimer = null;

  function wakeWorker() {
    if (!workerRunning) {
      runWorker().catch((e) => {
        logger?.warn?.(`[reply-queue] worker failed: ${e?.message || 'unknown'}`);
      });
    }
  }

  async function runWorker() {
    workerRunning = true;
    try {
      while (heap.length > 0) {
        const head = heapPeek(heap);
        const now = Date.now();
        if (head && head.notBeforeMs > now) break;
        const task = heapPop(heap);
        if (!task) break;
        const waitUntil = Math.max(task.notBeforeMs || now, nextAllowedSendAtMs || 0);
        const waitMs = waitUntil - Date.now();
        if (waitMs > 0) await sleep(waitMs);
        try {
          await executeJob(task);
        } catch (e) {
          logger?.warn?.(`[reply-queue] task failed: ${e?.message || 'unknown'}`);
        }
        const gap = typeof randomGapMs === 'function' ? randomGapMs() : 0;
        nextAllowedSendAtMs = Date.now() + Math.max(0, gap);
      }
    } finally {
      workerRunning = false;
    }
  }

  function enqueue(job) {
    const notBeforeMs = Number(job.notBeforeMs) || Date.now();
    heapPush(heap, { ...job, notBeforeMs });
    wakeWorker();
  }

  function startPoll() {
    if (pollTimer) return;
    pollTimer = setInterval(() => {
      if (!workerRunning && heap.length > 0) wakeWorker();
    }, POLL_MS);
    if (typeof pollTimer.unref === 'function') pollTimer.unref();
    logger?.info?.(`outbound local queue poll=${POLL_MS}ms`);
  }

  function close() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    heap.length = 0;
  }

  return { enqueue, startPoll, close, _heapSize: () => heap.length };
}
