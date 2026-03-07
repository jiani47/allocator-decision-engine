import type {
  Claim,
  MetricId,
  NormalizedFund,
  FundMetrics,
  ScoredFund,
  BenchmarkSeries,
  RawFileContext,
} from "@/context/WizardContext"
import { CalcSheet } from "@/components/CalcSheet"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover"
import { exportFundToExcel } from "@/lib/excel-export"
import { Download } from "lucide-react"

const METRIC_LABELS: Record<string, string> = {
  annualized_return: "Ann. Return",
  annualized_volatility: "Ann. Volatility",
  sharpe_ratio: "Sharpe Ratio",
  max_drawdown: "Max Drawdown",
  benchmark_correlation: "Benchmark Corr.",
  portfolio_diversification: "Portfolio Div.",
}

interface CitationBadgeProps {
  number: number
  claim: Claim
  fundLookup: Record<string, NormalizedFund>
  metricsLookup: Record<string, FundMetrics>
  scoredFundLookup: Record<string, ScoredFund>
  rawContext: RawFileContext | null
  benchmark: BenchmarkSeries | null
}

export function CitationBadge({
  number,
  claim,
  fundLookup,
  metricsLookup,
  scoredFundLookup,
  rawContext,
  benchmark,
}: CitationBadgeProps) {
  const calcTabs: { fund: NormalizedFund; fm: FundMetrics; metricId: MetricId; key: string }[] = []
  for (const fundName of claim.referenced_fund_names) {
    const fund = fundLookup[fundName]
    const fm = metricsLookup[fundName]
    if (!fund || !fm) continue
    for (const mid of claim.referenced_metric_ids) {
      calcTabs.push({ fund, fm, metricId: mid as MetricId, key: `${fundName}-${mid}` })
    }
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center justify-center text-[10px] font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer align-super leading-none ml-0.5"
          title={claim.claim_text}
        >
          [{number}]
        </button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="start"
        className="w-[420px] max-h-[400px] overflow-y-auto p-3 pb-5"
      >
        <p className="text-xs font-medium text-muted-foreground mb-1">
          Claim #{number}
        </p>
        <p className="text-sm mb-3">{claim.claim_text}</p>

        {calcTabs.length > 0 ? (
          <>
            <Tabs defaultValue={calcTabs[0]?.key}>
              <TabsList className="w-full flex-wrap h-auto gap-1">
                {calcTabs.map((t) => (
                  <TabsTrigger key={t.key} value={t.key} className="text-xs">
                    {t.fund.fund_name.length > 12
                      ? t.fund.fund_name.slice(0, 12) + "..."
                      : t.fund.fund_name}
                    {" — "}
                    {METRIC_LABELS[t.metricId] ?? t.metricId}
                  </TabsTrigger>
                ))}
              </TabsList>
              {calcTabs.map((t) => (
                <TabsContent
                  key={t.key}
                  value={t.key}
                  className="mt-2 max-h-[250px] overflow-y-auto"
                >
                  <CalcSheet
                    fund={t.fund}
                    metricId={t.metricId}
                    fundMetrics={t.fm}
                    rawContext={rawContext}
                    benchmark={benchmark}
                  />
                </TabsContent>
              ))}
            </Tabs>
            {/* Excel download per referenced fund */}
            <div className="mt-2 mb-0 flex flex-wrap gap-1 justify-end border-t border-border pt-2">
              {claim.referenced_fund_names.map((fundName) => {
                const sf = scoredFundLookup[fundName]
                const fund = fundLookup[fundName]
                const fm = metricsLookup[fundName]
                if (!sf || !fund || !fm) return null
                return (
                  <Button
                    key={fundName}
                    variant="ghost"
                    size="sm"
                    className="h-7 gap-1 text-xs"
                    onClick={() => exportFundToExcel(sf, fund, fm, rawContext, benchmark)}
                  >
                    <Download className="h-3 w-3" />
                    {fundName.length > 18 ? fundName.slice(0, 18) + "..." : fundName} .xlsx
                  </Button>
                )
              })}
            </div>
          </>
        ) : (
          <p className="text-xs text-muted-foreground">
            No matching evidence data found for referenced funds/metrics.
          </p>
        )}
      </PopoverContent>
    </Popover>
  )
}
