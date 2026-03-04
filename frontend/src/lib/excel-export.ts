import * as XLSX from "xlsx"
import type {
  NormalizedFund,
  FundMetrics,
  RawFileContext,
  BenchmarkSeries,
  ScoredFund,
} from "@/context/WizardContext"
import {
  computeAnnualizedReturn,
  computeAnnualizedVolatility,
  computeSharpeRatio,
  computeMaxDrawdown,
  computeBenchmarkCorrelation,
} from "@/lib/calc-sheet"

export function exportFundToExcel(
  scoredFund: ScoredFund,
  fund: NormalizedFund,
  fundMetrics: FundMetrics,
  rawContext: RawFileContext | null,
  benchmark: BenchmarkSeries | null,
): void {
  const wb = XLSX.utils.book_new()

  // --- Summary sheet ---
  const summaryRows: (string | number)[][] = [
    ["Fund Name", fund.fund_name],
    ["Strategy", fund.strategy ?? "-"],
    ["Rank", scoredFund.rank],
    ["Composite Score", scoredFund.composite_score ?? "-"],
    ["Date Range", `${fund.date_range_start} to ${fund.date_range_end}`],
    ["Months", fund.month_count],
    [],
    ["Score Breakdown"],
    ["Metric", "Raw Value", "Normalized", "Weight", "Contribution"],
  ]
  for (const sc of scoredFund.score_breakdown) {
    summaryRows.push([
      sc.metric_id,
      sc.raw_value,
      sc.normalized_value,
      sc.weight,
      sc.weighted_contribution,
    ])
  }
  summaryRows.push([])
  summaryRows.push(["Constraints"])
  summaryRows.push(["Constraint", "Passed", "Explanation"])
  for (const cr of scoredFund.constraint_results) {
    summaryRows.push([cr.constraint_name, cr.passed ? "Pass" : "FAIL", cr.explanation])
  }
  const summaryWs = XLSX.utils.aoa_to_sheet(summaryRows)
  summaryWs["!cols"] = [{ wch: 20 }, { wch: 16 }, { wch: 14 }, { wch: 10 }, { wch: 14 }]
  XLSX.utils.book_append_sheet(wb, summaryWs, "Summary")

  // --- Ann. Return sheet ---
  const annReturn = computeAnnualizedReturn(fund.monthly_returns)
  appendCalcSheet(wb, "Ann. Return", annReturn.rows, [
    "period", "Monthly Return", "1 + r", "Cumulative Product",
  ], annReturn.summary)

  // --- Volatility sheet ---
  const annVol = computeAnnualizedVolatility(fund.monthly_returns)
  appendCalcSheet(wb, "Volatility", annVol.rows, [
    "period", "Monthly Return", "Deviation from Mean", "Squared Deviation",
  ], annVol.summary)

  // --- Sharpe Ratio sheet ---
  const sharpe = computeSharpeRatio(fundMetrics)
  const sharpeWs = XLSX.utils.aoa_to_sheet([
    ["Sharpe Ratio Calculation"],
    [],
    ...sharpe.summary.split("\n").map((line) => [line]),
  ])
  sharpeWs["!cols"] = [{ wch: 50 }]
  XLSX.utils.book_append_sheet(wb, sharpeWs, "Sharpe Ratio")

  // --- Max Drawdown sheet ---
  const maxDD = computeMaxDrawdown(fund.monthly_returns)
  appendCalcSheet(wb, "Max Drawdown", maxDD.rows, [
    "period", "Monthly Return", "Cumulative Wealth", "Running Max", "Drawdown",
  ], maxDD.summary)

  // --- Benchmark Correlation sheet ---
  if (benchmark) {
    const corr = computeBenchmarkCorrelation(fund.monthly_returns, benchmark.monthly_returns)
    if (corr) {
      appendCalcSheet(wb, "Benchmark Corr.", corr.rows, [
        "period", "Fund Return", "Benchmark Return",
      ], corr.summary)
    }
  }

  // --- Source Data sheet ---
  if (rawContext && fund.source_row_indices.length > 0) {
    const rowLookup: Record<number, (string | null)[]> = {}
    for (const row of rawContext.data_rows) {
      rowLookup[row.row_index] = row.cells
    }
    const sourceRows = fund.source_row_indices
      .sort((a, b) => a - b)
      .map((idx) => rowLookup[idx])
      .filter(Boolean) as (string | null)[][]

    const sourceData: (string | null)[][] = [
      rawContext.headers,
      ...sourceRows,
    ]
    const sourceWs = XLSX.utils.aoa_to_sheet(sourceData)
    sourceWs["!cols"] = rawContext.headers.map(() => ({ wch: 16 }))
    XLSX.utils.book_append_sheet(wb, sourceWs, "Source Data")
  }

  const safeName = fund.fund_name.replace(/[^a-zA-Z0-9_-]/g, "_")
  XLSX.writeFile(wb, `${safeName}_calc_sheets.xlsx`)
}

function appendCalcSheet(
  wb: XLSX.WorkBook,
  sheetName: string,
  rows: Record<string, string | number>[],
  columns: string[],
  summary: string,
): void {
  const header = columns
  const data = rows.map((row) =>
    columns.map((col) => row[col] ?? ""),
  )
  const aoa: (string | number)[][] = [header, ...data, [], [summary]]
  const ws = XLSX.utils.aoa_to_sheet(aoa)
  ws["!cols"] = columns.map(() => ({ wch: 18 }))
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
}
