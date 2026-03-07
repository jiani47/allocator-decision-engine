import { useState } from "react"
import type {
  Claim,
  MetricId,
  NormalizedFund,
  FundMetrics,
  BenchmarkSeries,
  RawFileContext,
} from "@/context/WizardContext"
import { CalcSheet } from "@/components/CalcSheet"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const METRIC_LABELS: Record<string, string> = {
  annualized_return: "Ann. Return",
  annualized_volatility: "Ann. Volatility",
  sharpe_ratio: "Sharpe Ratio",
  max_drawdown: "Max Drawdown",
  benchmark_correlation: "Benchmark Corr.",
  portfolio_diversification: "Portfolio Div.",
}

interface ClaimsPanelProps {
  claims: Claim[]
  fundLookup: Record<string, NormalizedFund>
  metricsLookup: Record<string, FundMetrics>
  rawContext: RawFileContext | null
  benchmark: BenchmarkSeries | null
}

export function ClaimsPanel({
  claims,
  fundLookup,
  metricsLookup,
  rawContext,
  benchmark,
}: ClaimsPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(
    claims[0]?.claim_id ?? null,
  )
  const [reviewedClaims, setReviewedClaims] = useState<Set<string>>(new Set())

  if (claims.length === 0) return null

  const reviewedCount = reviewedClaims.size
  const selectedClaim = claims.find((c) => c.claim_id === selectedClaimId)

  const toggleReviewed = (claimId: string) => {
    setReviewedClaims((prev) => {
      const next = new Set(prev)
      if (next.has(claimId)) {
        next.delete(claimId)
      } else {
        next.add(claimId)
      }
      return next
    })
  }

  // Collapsed state
  if (!expanded) {
    return (
      <div
        className="flex-shrink-0 w-10 border-l border-border flex flex-col items-center pt-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded(true)}
      >
        <ChevronLeft className="h-4 w-4" />
        <div className="mt-4 [writing-mode:vertical-lr] text-sm text-foreground font-bold tracking-wider">
          Claims ({reviewedCount}/{claims.length})
        </div>
      </div>
    )
  }

  // Build unique fund+metric combos for the selected claim
  const calcTabs: { fund: NormalizedFund; fm: FundMetrics; metricId: MetricId; key: string }[] = []
  if (selectedClaim) {
    for (const fundName of selectedClaim.referenced_fund_names) {
      const fund = fundLookup[fundName]
      const fm = metricsLookup[fundName]
      if (!fund || !fm) continue
      for (const mid of selectedClaim.referenced_metric_ids) {
        calcTabs.push({ fund, fm, metricId: mid as MetricId, key: `${fundName}-${mid}` })
      }
    }
  }

  return (
    <div className="flex-shrink-0 w-[420px] border-l border-border flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">Claims Audit</h3>
          <span className="text-xs bg-muted text-muted-foreground rounded-full px-2 py-0.5">
            {reviewedCount}/{claims.length}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setExpanded(false)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Claims list */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="divide-y divide-border">
          {claims.map((c) => (
            <div
              key={c.claim_id}
              className={cn(
                "flex items-start gap-2 px-4 py-3 cursor-pointer transition-colors hover:bg-muted/50",
                selectedClaimId === c.claim_id && "bg-muted/70",
              )}
              onClick={() => setSelectedClaimId(c.claim_id)}
            >
              <Checkbox
                checked={reviewedClaims.has(c.claim_id)}
                onCheckedChange={() => toggleReviewed(c.claim_id)}
                onClick={(e) => e.stopPropagation()}
                className="mt-0.5 shrink-0"
              />
              <div className="min-w-0">
                <span className="text-xs text-muted-foreground font-mono">[{c.claim_id}]</span>
                <p className="text-sm leading-snug mt-0.5">
                  {c.claim_text.length > 100 ? c.claim_text.slice(0, 100) + "..." : c.claim_text}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Selected claim calc sheets */}
        {selectedClaim && calcTabs.length > 0 && (
          <div className="border-t border-border px-4 py-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Evidence for: {selectedClaim.claim_id}
            </p>
            <Tabs defaultValue={calcTabs[0]?.key}>
              <TabsList className="w-full flex-wrap h-auto gap-1">
                {calcTabs.map((t) => (
                  <TabsTrigger key={t.key} value={t.key} className="text-xs">
                    {t.fund.fund_name.length > 12 ? t.fund.fund_name.slice(0, 12) + "..." : t.fund.fund_name}
                    {" — "}
                    {METRIC_LABELS[t.metricId] ?? t.metricId}
                  </TabsTrigger>
                ))}
              </TabsList>
              {calcTabs.map((t) => (
                <TabsContent key={t.key} value={t.key} className="mt-2 max-h-[300px] overflow-y-auto">
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
          </div>
        )}
      </div>
    </div>
  )
}
