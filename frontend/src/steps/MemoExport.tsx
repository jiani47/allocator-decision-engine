import { useWizard, type MetricId } from "@/context/WizardContext"
import { exportPdf } from "@/api/client"
import { PageHeader } from "@/components/PageHeader"
import { CalcSheet } from "@/components/CalcSheet"
import Markdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { useState } from "react"

const WEIGHT_LABELS: Record<string, string> = {
  annualized_return: "Ann. Return",
  sharpe_ratio: "Sharpe",
  max_drawdown: "Drawdown",
}

export function MemoExport() {
  const {
    groupRuns,
    mandate,
    universe,
    rawContext,
    eligibility,
    fundMetrics,
    selectedClaimIdx,
    setSelectedClaimIdx,
    setStep,
    resetFrom,
  } = useWizard()
  const [exporting, setExporting] = useState(false)

  const gr = groupRuns[0]

  if (!gr?.memo || !mandate || !universe) {
    return (
      <div>
        <p className="text-muted-foreground mb-4">No memo available. Go back to generate one.</p>
        <Button variant="outline" onClick={() => { resetFrom(2); setStep(2) }}>Back</Button>
      </div>
    )
  }

  const fundLookup = Object.fromEntries(universe.funds.map((f) => [f.fund_name, f]))
  const metricsLookup = Object.fromEntries(gr.fund_metrics.map((m) => [m.fund_name, m]))

  const handleExportPdf = async () => {
    setExporting(true)
    try {
      const blob = await exportPdf(universe, mandate, eligibility, groupRuns, fundMetrics)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "equi_memo.pdf"
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // Error handling — user sees download fail
    } finally {
      setExporting(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="IC Memo & Export"
        description="Review the generated memo, audit claims, and export."
      />

      {/* Memo text */}
      <div className="prose prose-sm max-w-none mb-8">
        <Markdown>{gr.memo.memo_text}</Markdown>
      </div>

      <Separator className="my-6" />

      {/* Claims & Evidence */}
      {gr.memo.claims.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-medium mb-4">Claims & Evidence</h3>

          <RadioGroup
            value={String(selectedClaimIdx)}
            onValueChange={(v) => setSelectedClaimIdx(Number(v))}
            className="mb-4"
          >
            {gr.memo.claims.map((c, i) => (
              <div key={c.claim_id} className="flex items-start gap-2">
                <RadioGroupItem value={String(i)} id={`claim-${i}`} className="mt-1" />
                <Label htmlFor={`claim-${i}`} className="text-sm leading-relaxed cursor-pointer">
                  [{c.claim_id}] {c.claim_text.length > 80 ? c.claim_text.slice(0, 80) + "..." : c.claim_text}
                </Label>
              </div>
            ))}
          </RadioGroup>

          {/* Selected claim details */}
          {gr.memo.claims[selectedClaimIdx] && (() => {
            const claim = gr.memo.claims[selectedClaimIdx]
            return (
              <div>
                <p className="text-sm font-medium mb-3">
                  Claim: {claim.claim_text}
                </p>
                <Accordion type="multiple" defaultValue={
                  claim.referenced_fund_names.flatMap(fn =>
                    claim.referenced_metric_ids.map(mid => `${fn}-${mid}`)
                  )
                }>
                  {claim.referenced_fund_names.map((fundName) => {
                    const fund = fundLookup[fundName]
                    const fm = metricsLookup[fundName]
                    if (!fund || !fm) return null
                    return claim.referenced_metric_ids.map((metricId) => (
                      <AccordionItem key={`${fundName}-${metricId}`} value={`${fundName}-${metricId}`}>
                        <AccordionTrigger>
                          {fundName} — {metricId}
                        </AccordionTrigger>
                        <AccordionContent>
                          <CalcSheet
                            fund={fund}
                            metricId={metricId as MetricId}
                            fundMetrics={fm}
                            rawContext={rawContext}
                            benchmark={gr.group.benchmark}
                          />
                        </AccordionContent>
                      </AccordionItem>
                    ))
                  })}
                </Accordion>
              </div>
            )
          })()}
        </div>
      )}

      <Separator className="my-6" />

      {/* Data Appendix */}
      <Collapsible className="mb-8">
        <CollapsibleTrigger asChild>
          <Button variant="ghost">Data Appendix</Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 text-sm space-y-2 pl-4">
          <p>
            <strong>Fund Universe:</strong> {universe.funds.length} funds
          </p>

          <p>
            <strong>Mandate Constraints:</strong>{" "}
            {[
              mandate.min_liquidity_days != null && `Min liquidity: ${mandate.min_liquidity_days} days`,
              mandate.max_drawdown_tolerance != null && `Max drawdown: ${(mandate.max_drawdown_tolerance * 100).toFixed(0)}%`,
              mandate.target_volatility != null && `Target volatility: ${(mandate.target_volatility * 100).toFixed(0)}%`,
              mandate.min_annualized_return != null && `Min return: ${(mandate.min_annualized_return * 100).toFixed(0)}%`,
              mandate.min_sharpe_ratio != null && `Min Sharpe: ${mandate.min_sharpe_ratio.toFixed(2)}`,
              `Min history: ${mandate.min_history_months} months`,
            ].filter(Boolean).join(" · ")}
          </p>

          {(mandate.strategy_include.length > 0 || mandate.strategy_exclude.length > 0) ? (
            <p>
              <strong>Strategy Filters:</strong>{" "}
              {[
                mandate.strategy_include.length > 0 && `Include: ${mandate.strategy_include.join(", ")}`,
                mandate.strategy_exclude.length > 0 && `Exclude: ${mandate.strategy_exclude.join(", ")}`,
              ].filter(Boolean).join(" · ")}
            </p>
          ) : (
            <p><strong>Strategy Filters:</strong> None</p>
          )}

          {gr.group.benchmark ? (
            <p>
              <strong>Benchmark:</strong> {gr.group.benchmark.symbol} —{" "}
              {Object.keys(gr.group.benchmark.monthly_returns).length} months, source: Yahoo Finance
            </p>
          ) : (
            <p><strong>Benchmark:</strong> None</p>
          )}

          <p>
            <strong>Ranking Model:</strong>{" "}
            {Object.entries(mandate.weights)
              .map(([mid, w]) => `${WEIGHT_LABELS[mid] ?? mid} ${(w * 100).toFixed(0)}%`)
              .join(", ")}
          </p>
          <p className="text-xs text-muted-foreground">
            Min-max normalized, weighted composite score, constraint-pass priority.
          </p>
        </CollapsibleContent>
      </Collapsible>

      <Separator className="my-6" />

      {/* Export */}
      <h3 className="text-lg font-medium mb-4">Export</h3>
      <Button onClick={handleExportPdf} disabled={exporting}>
        {exporting ? "Exporting..." : "Download PDF"}
      </Button>

      <Separator className="my-6" />

      {/* Navigation */}
      <Button
        variant="outline"
        onClick={() => {
          resetFrom(2)
          setStep(2)
        }}
      >
        Back
      </Button>
    </div>
  )
}
