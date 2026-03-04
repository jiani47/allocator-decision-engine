/**
 * Pure metric computation functions for CalcSheet display.
 * Port of app/ui/widgets/calc_sheet.py math.
 */

export interface CalcRow {
  period: string
  [key: string]: string | number
}

export interface CalcResult {
  rows: CalcRow[]
  summary: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sortedReturns(monthlyReturns: Record<string, number>): [string, number][] {
  return Object.entries(monthlyReturns).sort(([a], [b]) => a.localeCompare(b))
}

function cumulativeProduct(arr: number[]): number[] {
  const result: number[] = []
  let product = 1
  for (const v of arr) {
    product *= v
    result.push(product)
  }
  return result
}

function mean(arr: number[]): number {
  return arr.reduce((s, v) => s + v, 0) / arr.length
}

function stdDev(arr: number[]): number {
  const m = mean(arr)
  const variance = arr.reduce((s, v) => s + (v - m) ** 2, 0) / (arr.length - 1)
  return Math.sqrt(variance)
}

// ---------------------------------------------------------------------------
// Annualized Return
// ---------------------------------------------------------------------------

export function computeAnnualizedReturn(
  monthlyReturns: Record<string, number>,
): CalcResult {
  const sorted = sortedReturns(monthlyReturns)
  const returns = sorted.map(([, r]) => r)
  const growthFactors = returns.map((r) => 1 + r)
  const cumProd = cumulativeProduct(growthFactors)

  const rows: CalcRow[] = sorted.map(([period, r], i) => ({
    period,
    "Monthly Return": r,
    "1 + r": growthFactors[i],
    "Cumulative Product": cumProd[i],
  }))

  const n = returns.length
  const years = n / 12
  const growth = cumProd[cumProd.length - 1]
  const annRet = growth ** (1 / years) - 1

  const summary =
    `n = ${n}, years = ${years.toFixed(2)}, ` +
    `growth = ${growth.toFixed(6)}, ` +
    `ann. return = (${growth.toFixed(6)})^(1/${years.toFixed(2)}) - 1 = ${(annRet * 100).toFixed(2)}%`

  return { rows, summary }
}

// ---------------------------------------------------------------------------
// Annualized Volatility
// ---------------------------------------------------------------------------

export function computeAnnualizedVolatility(
  monthlyReturns: Record<string, number>,
): CalcResult {
  const sorted = sortedReturns(monthlyReturns)
  const returns = sorted.map(([, r]) => r)
  const m = mean(returns)
  const deviations = returns.map((r) => r - m)
  const sqDeviations = deviations.map((d) => d ** 2)

  const rows: CalcRow[] = sorted.map(([period, r], i) => ({
    period,
    "Monthly Return": r,
    "Deviation from Mean": deviations[i],
    "Squared Deviation": sqDeviations[i],
  }))

  const n = returns.length
  const std = stdDev(returns)
  const annVol = std * Math.sqrt(12)
  const variance = sqDeviations.reduce((s, v) => s + v, 0) / (n - 1)

  const summary =
    `mean = ${m.toFixed(6)}, ` +
    `variance = ${variance.toFixed(8)}, ` +
    `std = ${std.toFixed(6)}, ` +
    `ann. vol = ${std.toFixed(6)} x sqrt(12) = ${(annVol * 100).toFixed(2)}%`

  return { rows, summary }
}

// ---------------------------------------------------------------------------
// Sharpe Ratio
// ---------------------------------------------------------------------------

export interface SharpeResult {
  annualizedReturn: number
  annualizedVolatility: number
  sharpe: number
  summary: string
}

export function computeSharpeRatio(
  fundMetrics: { metric_results: { metric_id: string; value: number }[] },
): SharpeResult {
  const getVal = (id: string) =>
    fundMetrics.metric_results.find((r) => r.metric_id === id)?.value ?? 0

  const annRet = getVal("annualized_return")
  const annVol = getVal("annualized_volatility")
  const sharpe = getVal("sharpe_ratio")

  const summary =
    `Annualized Return = ${(annRet * 100).toFixed(2)}%\n` +
    `Annualized Volatility = ${(annVol * 100).toFixed(2)}%\n` +
    `Risk-Free Rate = 0%\n` +
    `Sharpe = ${(annRet * 100).toFixed(2)}% / ${(annVol * 100).toFixed(2)}% = ${sharpe.toFixed(4)}`

  return { annualizedReturn: annRet, annualizedVolatility: annVol, sharpe, summary }
}

// ---------------------------------------------------------------------------
// Max Drawdown
// ---------------------------------------------------------------------------

export interface DrawdownResult extends CalcResult {
  worstIdx: number
  worstPeriod: string
  worstDrawdown: number
}

export function computeMaxDrawdown(
  monthlyReturns: Record<string, number>,
): DrawdownResult {
  const sorted = sortedReturns(monthlyReturns)
  const returns = sorted.map(([, r]) => r)
  const cumWealth = cumulativeProduct(returns.map((r) => 1 + r))

  let runningMax = -Infinity
  const runningMaxArr: number[] = []
  for (const w of cumWealth) {
    runningMax = Math.max(runningMax, w)
    runningMaxArr.push(runningMax)
  }
  const drawdowns = cumWealth.map((w, i) => w / runningMaxArr[i] - 1)

  const rows: CalcRow[] = sorted.map(([period, r], i) => ({
    period,
    "Monthly Return": r,
    "Cumulative Wealth": cumWealth[i],
    "Running Max": runningMaxArr[i],
    Drawdown: drawdowns[i],
  }))

  let worstIdx = 0
  let worstDD = 0
  for (let i = 0; i < drawdowns.length; i++) {
    if (drawdowns[i] < worstDD) {
      worstDD = drawdowns[i]
      worstIdx = i
    }
  }

  const summary = `Max drawdown = ${(worstDD * 100).toFixed(2)}% at ${sorted[worstIdx][0]}`

  return {
    rows,
    summary,
    worstIdx,
    worstPeriod: sorted[worstIdx][0],
    worstDrawdown: worstDD,
  }
}

// ---------------------------------------------------------------------------
// Benchmark Correlation
// ---------------------------------------------------------------------------

export interface CorrelationResult {
  rows: CalcRow[]
  correlation: number
  overlapCount: number
  summary: string
}

export function computeBenchmarkCorrelation(
  fundReturns: Record<string, number>,
  benchmarkReturns: Record<string, number>,
): CorrelationResult | null {
  const periods = Object.keys(fundReturns)
    .filter((p) => p in benchmarkReturns)
    .sort()

  if (periods.length < 3) return null

  const fundVals = periods.map((p) => fundReturns[p])
  const bmVals = periods.map((p) => benchmarkReturns[p])

  const rows: CalcRow[] = periods.map((period, i) => ({
    period,
    "Fund Return": fundVals[i],
    "Benchmark Return": bmVals[i],
  }))

  // Pearson correlation
  const n = fundVals.length
  const mF = mean(fundVals)
  const mB = mean(bmVals)
  let cov = 0
  let varF = 0
  let varB = 0
  for (let i = 0; i < n; i++) {
    const df = fundVals[i] - mF
    const db = bmVals[i] - mB
    cov += df * db
    varF += df ** 2
    varB += db ** 2
  }
  const correlation = cov / Math.sqrt(varF * varB)

  const summary = `N = ${n} overlapping periods, Pearson r = ${correlation.toFixed(4)}`

  return { rows, correlation, overlapCount: n, summary }
}
