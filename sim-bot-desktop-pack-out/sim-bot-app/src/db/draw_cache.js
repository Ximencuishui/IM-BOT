export function isDrawDeferSummaryEnabled(db) {
  try {
    const row = db.prepare(`SELECT value FROM app_settings WHERE key = 'draw_defer_summary'`).get();
    if (row == null) return true;
    return String(row.value || '1') !== '0';
  } catch {
    return true;
  }
}

export function saveGroupDrawCache(
  db,
  wxGroupId,
  { drawBatchId, guideWord, ballTxt, teMaOnly, scopes, hitDetails, reportGuideWords }
) {
  const gid = String(wxGroupId || '').trim();
  if (!gid || !drawBatchId) return;
  db.prepare(
    `INSERT INTO group_draw_cache (
       wx_group_id, draw_batch_id, guide_word, ball_txt, te_ma_only, scopes_json, hit_details_json, report_guide_words_json, created_at
     ) VALUES (?,?,?,?,?,?,?,?, datetime('now'))
     ON CONFLICT(wx_group_id) DO UPDATE SET
       draw_batch_id = excluded.draw_batch_id,
       guide_word = excluded.guide_word,
       ball_txt = excluded.ball_txt,
       te_ma_only = excluded.te_ma_only,
       scopes_json = excluded.scopes_json,
       hit_details_json = excluded.hit_details_json,
       report_guide_words_json = excluded.report_guide_words_json,
       created_at = datetime('now')`
  ).run(
    gid,
    String(drawBatchId),
    String(guideWord || ''),
    String(ballTxt || ''),
    teMaOnly ? 1 : 0,
    JSON.stringify(scopes || []),
    JSON.stringify(hitDetails || []),
    JSON.stringify(reportGuideWords || [])
  );
}

export function loadGroupDrawCache(db, wxGroupId) {
  const gid = String(wxGroupId || '').trim();
  if (!gid) return null;
  const row = db.prepare(`SELECT * FROM group_draw_cache WHERE wx_group_id = ?`).get(gid);
  if (!row) return null;
  try {
    let reportGuideWords = [];
    try {
      reportGuideWords = JSON.parse(row.report_guide_words_json || '[]');
    } catch {
      reportGuideWords = [];
    }
    return {
      drawBatchId: row.draw_batch_id,
      guideWord: row.guide_word,
      ballTxt: row.ball_txt || '',
      teMaOnly: Number(row.te_ma_only) === 1,
      scopes: JSON.parse(row.scopes_json || '[]'),
      hitDetails: JSON.parse(row.hit_details_json || '[]'),
      reportGuideWords: Array.isArray(reportGuideWords) ? reportGuideWords : [],
      createdAt: row.created_at,
    };
  } catch {
    return null;
  }
}
