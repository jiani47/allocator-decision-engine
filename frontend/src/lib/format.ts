/**
 * Metric value formatting utilities.
 * Port of app/ui/widgets/metric_format.py
 */

import type { MetricId } from "@/context/WizardContext"

export function formatMetric(metricId: MetricId, value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return "-"

  const pctMetrics: MetricId[] = [
    "annualized_return",
    "annualized_volatility",
    "max_drawdown",
  ]

  if (pctMetrics.includes(metricId)) {
    return `${(value * 100).toFixed(2)}%`
  }
  if (metricId === "sharpe_ratio") {
    return value.toFixed(2)
  }
  return value.toFixed(3)
}

export function formatPercent(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`
}
