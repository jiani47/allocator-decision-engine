import { useEffect, useState, useCallback } from "react"
import { useWizard, type MetricId } from "@/context/WizardContext"
import { PageHeader } from "@/components/PageHeader"
import { useBenchmark } from "@/hooks/useBenchmark"
import { useRank } from "@/hooks/useRank"
import { useMemoStream } from "@/hooks/useMemoStream"
import { formatMetric, formatPercent } from "@/lib/format"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const METRIC_IDS: MetricId[] = [
  "annualized_return",
  "annualized_volatility",
  "sharpe_ratio",
  "max_drawdown",
  "benchmark_correlation",
]

const METRIC_LABELS: Record<MetricId, string> = {
  annualized_return: "Ann. Return",
  annualized_volatility: "Ann. Volatility",
  sharpe_ratio: "Sharpe Ratio",
  max_drawdown: "Max Drawdown",
  benchmark_correlation: "Benchmark Corr.",
}

export function RankingView() {
  const {
    mandate,
    universe,
    benchmark,
    benchmarkSymbol,
    benchmarkMetrics,
    groupRuns,
    warningResolutions,
    setMandate,
    setBenchmarkSymbol,
    setGroupRuns,
    setStep,
    resetFrom,
  } = useWizard()

  const { fetch: fetchBm, loading: bmLoading, error: bmError } = useBenchmark()
  const { rank, loading: rankLoading, error: rankError } = useRank()
  const { generate: generateMemo, loading: memoLoading, error: memoError, progressMessage } = useMemoStream()

  const [skipBenchmark, setSkipBenchmark] = useState(false)
  const [wRet, setWRet] = useState(mandate?.weights.annualized_return ?? 0.4)
  const [wSharpe, setWSharpe] = useState(mandate?.weights.sharpe_ratio ?? 0.4)
  const [wDD, setWDD] = useState(mandate?.weights.max_drawdown ?? 0.2)

  // Re-rank when weights change
  const applyWeights = useCallback(() => {
    if (!mandate) return
    const newWeights: Record<string, number> = {}
    if (wRet > 0) newWeights["annualized_return"] = wRet
    if (wSharpe > 0) newWeights["sharpe_ratio"] = wSharpe
    if (wDD > 0) newWeights["max_drawdown"] = wDD

    const changed = JSON.stringify(newWeights) !== JSON.stringify(mandate.weights)
    if (changed) {
      setMandate({ ...mandate, weights: newWeights as Record<MetricId, number> })
      setGroupRuns([])
    }
  }, [mandate, wRet, wSharpe, wDD, setMandate, setGroupRuns])

  // Trigger ranking when groupRuns is empty and we have all prerequisites
  useEffect(() => {
    if (universe && mandate && groupRuns.length === 0 && !rankLoading) {
      rank()
    }
  }, [universe, mandate, groupRuns.length, rankLoading, rank])

  const handleGenerateMemo = async () => {
    if (!groupRuns[0] || !universe || !mandate) return
    const result = await generateMemo(
      groupRuns[0],
      universe,
      mandate,
      warningResolutions,
    )
    if (result) {
      setGroupRuns([result])
      setStep(3)
    }
  }

  const gr = groupRuns[0]
  const total = wRet + wSharpe + wDD

  return (
    <div>
      <PageHeader
        title="Metrics & Ranking"
        description="Configure benchmark, scoring weights, and generate rankings."
      />

      {/* Benchmark config */}
      <h3 className="text-lg font-medium mb-2">Benchmark</h3>
      <p className="text-sm text-muted-foreground mb-3">
        Data source: Yahoo Finance (monthly adjusted close, converted to returns).
      </p>
      <div className="flex items-end gap-4 mb-4">
        <div className="flex-1 max-w-xs">
          <Label>Benchmark ticker</Label>
          <Input
            value={benchmarkSymbol}
            onChange={(e) => setBenchmarkSymbol(e.target.value)}
            disabled={skipBenchmark}
          />
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="skip-bm"
            checked={skipBenchmark}
            onCheckedChange={(v) => setSkipBenchmark(v === true)}
          />
          <Label htmlFor="skip-bm">Skip benchmark</Label>
        </div>
        {!skipBenchmark && universe && (
          <Button
            onClick={() => fetchBm(benchmarkSymbol, universe)}
            disabled={bmLoading}
          >
            {bmLoading ? "Fetching..." : "Fetch Benchmark"}
          </Button>
        )}
      </div>

      {bmError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{bmError}</AlertDescription>
        </Alert>
      )}

      {benchmark && benchmarkMetrics && (
        <div className="grid grid-cols-4 gap-4 mb-4">
          <Card>
            <CardContent className="py-3 text-center">
              <p className="text-sm text-muted-foreground">Ann. Return</p>
              <p className="text-lg font-semibold">
                {formatPercent(benchmarkMetrics.annualized_return)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-3 text-center">
              <p className="text-sm text-muted-foreground">Ann. Volatility</p>
              <p className="text-lg font-semibold">
                {formatPercent(benchmarkMetrics.annualized_volatility)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-3 text-center">
              <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
              <p className="text-lg font-semibold">
                {benchmarkMetrics.sharpe_ratio.toFixed(2)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-3 text-center">
              <p className="text-sm text-muted-foreground">Max Drawdown</p>
              <p className="text-lg font-semibold">
                {formatPercent(benchmarkMetrics.max_drawdown)}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <Separator className="my-6" />

      {/* Scoring weights */}
      <h3 className="text-lg font-medium mb-2">Scoring Weights</h3>
      <div className="grid grid-cols-3 gap-6 mb-2">
        <div>
          <Label className="text-sm">Annualized Return: {wRet.toFixed(2)}</Label>
          <Slider
            value={[wRet]}
            onValueChange={([v]) => setWRet(v)}
            min={0}
            max={1}
            step={0.05}
          />
        </div>
        <div>
          <Label className="text-sm">Sharpe Ratio: {wSharpe.toFixed(2)}</Label>
          <Slider
            value={[wSharpe]}
            onValueChange={([v]) => setWSharpe(v)}
            min={0}
            max={1}
            step={0.05}
          />
        </div>
        <div>
          <Label className="text-sm">Max Drawdown penalty: {wDD.toFixed(2)}</Label>
          <Slider
            value={[wDD]}
            onValueChange={([v]) => setWDD(v)}
            min={0}
            max={1}
            step={0.05}
          />
        </div>
      </div>
      {Math.abs(total - 1) > 0.01 && (
        <p className="text-sm text-amber-600 mb-2">
          Weights sum to {total.toFixed(2)}, not 1.0.
        </p>
      )}
      <Button variant="outline" size="sm" onClick={applyWeights} className="mb-6">
        Apply Weights & Re-Rank
      </Button>

      <Separator className="my-6" />

      {/* Methodology disclosure */}
      <Collapsible className="mb-6">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm">How are funds ranked?</Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2 pl-4">
          <p><strong>Annualized Return:</strong> Geometric mean of monthly growth factors, annualized.</p>
          <p><strong>Annualized Volatility:</strong> Sample std dev of monthly returns x sqrt(12).</p>
          <p><strong>Sharpe Ratio:</strong> Ann. Return / Ann. Volatility (risk-free rate = 0).</p>
          <p><strong>Max Drawdown:</strong> Worst peak-to-trough decline in cumulative wealth.</p>
          <p><strong>Benchmark Correlation:</strong> Pearson correlation over overlapping periods.</p>
          <Separator />
          <p><strong>Ranking Methodology:</strong></p>
          <ol className="list-decimal pl-4 space-y-1">
            <li>Each metric is min-max scaled to [0, 1] across all eligible funds. Max drawdown is inverted.</li>
            <li>Normalized scores are multiplied by your mandate weights.</li>
            <li>Composite score = weighted sum of normalized metrics.</li>
            <li>Funds passing all constraints ranked above those that fail.</li>
          </ol>
        </CollapsibleContent>
      </Collapsible>

      {/* Loading / Error */}
      {rankLoading && <p className="text-sm text-muted-foreground mb-4">Computing metrics and ranking...</p>}
      {rankError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{rankError}</AlertDescription>
        </Alert>
      )}

      {/* Ranking results */}
      {gr && (
        <>
          {/* Excluded candidates */}
          {gr.run_candidates.filter((rc) => !rc.included).length > 0 && (
            <Collapsible className="mb-4">
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm">
                  {gr.run_candidates.filter((rc) => !rc.included).length} fund(s) excluded from ranking
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm pl-4">
                {gr.run_candidates
                  .filter((rc) => !rc.included)
                  .map((rc) => (
                    <p key={rc.fund_name}>
                      <strong>{rc.fund_name}:</strong> {rc.exclusion_reason}
                    </p>
                  ))}
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Ranked shortlist table */}
          <Table className="mb-6">
            <TableHeader>
              <TableRow>
                <TableHead>Rank</TableHead>
                <TableHead>Fund</TableHead>
                <TableHead>Score</TableHead>
                {METRIC_IDS.map((mid) => (
                  <TableHead key={mid}>{METRIC_LABELS[mid]}</TableHead>
                ))}
                <TableHead>Constraints</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {gr.ranked_shortlist.map((sf) => (
                <TableRow key={sf.fund_name}>
                  <TableCell>{sf.rank}</TableCell>
                  <TableCell className="font-medium">{sf.fund_name}</TableCell>
                  <TableCell>{sf.composite_score?.toFixed(3) ?? "-"}</TableCell>
                  {METRIC_IDS.map((mid) => (
                    <TableCell key={mid}>
                      {formatMetric(mid, sf.metric_values[mid])}
                    </TableCell>
                  ))}
                  <TableCell>
                    {sf.all_constraints_passed ? (
                      <span className="text-green-600">Pass</span>
                    ) : (
                      <span className="text-red-600">FAIL</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Score breakdown per fund */}
          <Accordion type="multiple">
            {gr.ranked_shortlist.map((sf) => (
              <AccordionItem key={sf.fund_name} value={sf.fund_name}>
                <AccordionTrigger>{sf.fund_name} — Details</AccordionTrigger>
                <AccordionContent>
                  {sf.score_breakdown.length > 0 && (
                    <div className="mb-3">
                      <p className="font-medium mb-1">Score Breakdown:</p>
                      <ul className="text-sm space-y-1 pl-4">
                        {sf.score_breakdown.map((sc) => (
                          <li key={sc.metric_id}>
                            {sc.metric_id}: raw={sc.raw_value?.toFixed(4) ?? "-"},
                            normalized={sc.normalized_value?.toFixed(3) ?? "-"},
                            weight={sc.weight ?? "-"},
                            contribution={sc.weighted_contribution?.toFixed(4) ?? "-"}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {sf.constraint_results.length > 0 && (
                    <div>
                      <p className="font-medium mb-1">Constraints:</p>
                      <ul className="text-sm space-y-1 pl-4">
                        {sf.constraint_results.map((cr, i) => (
                          <li key={i}>
                            [{cr.passed ? "+" : "x"}] {cr.explanation}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </>
      )}

      {/* Navigation */}
      <Separator className="my-6" />
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => {
            resetFrom(1)
            setStep(1)
          }}
        >
          Back
        </Button>
        <div className="flex items-center gap-4">
          {memoLoading && (
            <p className="text-sm text-muted-foreground">{progressMessage}</p>
          )}
          {memoError && (
            <p className="text-sm text-red-600 max-w-md truncate">{memoError}</p>
          )}
          <Button
            onClick={handleGenerateMemo}
            disabled={!gr || memoLoading}
          >
            {memoLoading ? "Generating..." : "Generate Memo"}
          </Button>
        </div>
      </div>
    </div>
  )
}
