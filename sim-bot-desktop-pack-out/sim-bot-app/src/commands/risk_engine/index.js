/**
 * PRD 5.1 特码风控：庄家期望 = 总特码额×(1-水) - 单号投注×赔率
 */
export function specialCodeRiskProfit({
  totalSpecialAmount,
  betOnNumber,
  waterRate = 0.04,
  payoutOdds = 47,
}) {
  const total = Number(totalSpecialAmount) || 0;
  const bet = Number(betOnNumber) || 0;
  return total * (1 - waterRate) - bet * payoutOdds;
}

/** 与 engine computeTeHousePnlIfBallDraws 对齐 */
export function teHousePnlIfBallDraws(stake, payoutOdds, totalSpecial, totalWater) {
  const a = Number(stake) || 0;
  const r = Number(payoutOdds) || 0;
  const t = Number(totalSpecial) || 0;
  const w = Number(totalWater) || 0;
  return Math.round(t - a * r - w);
}
