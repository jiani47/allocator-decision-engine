import type {
  NormalizedUniverse,
  MandateConfig,
  GroupRun,
  FundEligibility,
  MetricId,
} from "@/context/WizardContext"
import { formatMetric } from "@/lib/format"

const METRIC_LABELS: Record<MetricId, string> = {
  annualized_return: "Ann. Return",
  annualized_volatility: "Ann. Volatility",
  sharpe_ratio: "Sharpe Ratio",
  max_drawdown: "Max Drawdown",
  benchmark_correlation: "Benchmark Corr.",
}

const WEIGHT_LABELS: Record<string, string> = {
  annualized_return: "Ann. Return",
  annualized_volatility: "Ann. Volatility",
  sharpe_ratio: "Sharpe Ratio",
  max_drawdown: "Max Drawdown",
  benchmark_correlation: "Benchmark Corr.",
}

export function buildDataAppendix(
  universe: NormalizedUniverse,
  mandate: MandateConfig,
  gr: GroupRun,
  eligibility: FundEligibility[],
  benchmarkMetrics: Record<string, number> | null,
): string {
  const today = new Date().toISOString().split("T")[0]
  const n = universe.funds.length
  const starts = universe.funds.map((f) => f.date_range_start).sort()
  const ends = universe.funds.map((f) => f.date_range_end).sort()
  const dateRange = `${starts[0]} to ${ends[ends.length - 1]}`
  const strategies = [...new Set(universe.funds.map((f) => f.strategy).filter(Boolean))]

  const lines: string[] = []
  lines.push("---")
  lines.push("")
  lines.push("## Data Appendix")
  lines.push("")
  lines.push(`**Report Date:** ${today}`)
  lines.push(`**Fund Universe:** ${n} funds, date range ${dateRange}`)
  if (strategies.length > 0) {
    lines.push(`**Strategies:** ${strategies.join(", ")}`)
  }
  lines.push("")

  // Mandate constraints
  lines.push("### Mandate Constraints")
  const constraints: string[] = []
  if (mandate.min_liquidity_days != null)
    constraints.push(`- Min liquidity: ${mandate.min_liquidity_days} days`)
  if (mandate.max_drawdown_tolerance != null)
    constraints.push(`- Max drawdown tolerance: ${(mandate.max_drawdown_tolerance * 100).toFixed(0)}%`)
  if (mandate.target_volatility != null)
    constraints.push(`- Target volatility: ${(mandate.target_volatility * 100).toFixed(0)}%`)
  if (mandate.min_annualized_return != null)
    constraints.push(`- Min annualized return: ${(mandate.min_annualized_return * 100).toFixed(0)}%`)
  if (mandate.min_sharpe_ratio != null)
    constraints.push(`- Min Sharpe ratio: ${mandate.min_sharpe_ratio.toFixed(2)}`)
  constraints.push(`- Min history: ${mandate.min_history_months} months`)
  if (mandate.strategy_include.length > 0)
    constraints.push(`- Strategy include: ${mandate.strategy_include.join(", ")}`)
  if (mandate.strategy_exclude.length > 0)
    constraints.push(`- Strategy exclude: ${mandate.strategy_exclude.join(", ")}`)
  if (constraints.length === 0) constraints.push("- None")
  lines.push(...constraints)
  lines.push("")

  // Scoring weights
  lines.push("### Scoring Weights")
  lines.push("| Metric | Weight |")
  lines.push("|--------|--------|")
  for (const [mid, w] of Object.entries(mandate.weights)) {
    if (w > 0) {
      lines.push(`| ${WEIGHT_LABELS[mid] ?? mid} | ${(w * 100).toFixed(0)}% |`)
    }
  }
  lines.push("")

  // Ranked shortlist
  lines.push("### Ranked Shortlist")
  lines.push("| Rank | Fund | Ann. Return | Volatility | Sharpe | Max DD | Benchmark Corr. | Constraints |")
  lines.push("|------|------|-------------|------------|--------|--------|-----------------|-------------|")
  for (const sf of gr.ranked_shortlist) {
    const passed = sf.all_constraints_passed ? "Pass" : "Fail"
    lines.push(
      `| ${sf.rank} | ${sf.fund_name} | ${formatMetric("annualized_return", sf.metric_values.annualized_return)} | ${formatMetric("annualized_volatility", sf.metric_values.annualized_volatility)} | ${formatMetric("sharpe_ratio", sf.metric_values.sharpe_ratio)} | ${formatMetric("max_drawdown", sf.metric_values.max_drawdown)} | ${formatMetric("benchmark_correlation", sf.metric_values.benchmark_correlation)} | ${passed} |`,
    )
  }
  lines.push("")

  // Benchmark
  if (gr.group.benchmark && benchmarkMetrics) {
    lines.push("### Benchmark")
    lines.push(
      `${gr.group.benchmark.symbol} — Ann. Return: ${formatMetric("annualized_return", benchmarkMetrics.annualized_return)}, Volatility: ${formatMetric("annualized_volatility", benchmarkMetrics.annualized_volatility)}, Sharpe: ${formatMetric("sharpe_ratio", benchmarkMetrics.sharpe_ratio)}, Max DD: ${formatMetric("max_drawdown", benchmarkMetrics.max_drawdown)}`,
    )
    lines.push("")
  }

  // Methodology
  lines.push("### Methodology")
  lines.push("Min-max normalized, weighted composite score, constraint-pass priority ranking.")

  return lines.join("\n")
}
