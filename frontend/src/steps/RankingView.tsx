import { useEffect, useState, useRef } from "react"
import { useWizard, type MetricId, type ScoredFund } from "@/context/WizardContext"
import { PageHeader } from "@/components/PageHeader"
import { CalcSheet } from "@/components/CalcSheet"
import { useBenchmark } from "@/hooks/useBenchmark"
import { useRank } from "@/hooks/useRank"
import { useMemoStream } from "@/hooks/useMemoStream"
import { formatMetric } from "@/lib/format"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Info, Eye } from "lucide-react"

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
    rawContext,
    warningResolutions,
    fundMetrics,
    setMandate,
    setBenchmarkSymbol,
    setGroupRuns,
    setStep,
    resetFrom,
  } = useWizard()

  const { fetch: fetchBm, loading: bmLoading, error: bmError } = useBenchmark()
  const { rank, loading: rankLoading, error: rankError } = useRank()
  const { generate: generateMemo, loading: memoLoading, error: memoError, progressMessage } = useMemoStream()

  const [wRet, setWRet] = useState(mandate?.weights.annualized_return ?? 0.4)
  const [wSharpe, setWSharpe] = useState(mandate?.weights.sharpe_ratio ?? 0.4)
  const [wDD, setWDD] = useState(mandate?.weights.max_drawdown ?? 0.2)
  const [selectedFund, setSelectedFund] = useState<ScoredFund | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto re-rank when weights change (debounced)
  useEffect(() => {
    if (!mandate) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      const newWeights: Record<string, number> = {}
      if (wRet > 0) newWeights["annualized_return"] = wRet
      if (wSharpe > 0) newWeights["sharpe_ratio"] = wSharpe
      if (wDD > 0) newWeights["max_drawdown"] = wDD

      const changed = JSON.stringify(newWeights) !== JSON.stringify(mandate.weights)
      if (changed) {
        setMandate({ ...mandate, weights: newWeights as Record<MetricId, number> })
        setGroupRuns([])
      }
    }, 500)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [wRet, wSharpe, wDD]) // eslint-disable-line react-hooks/exhaustive-deps

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

  // Look up fund data for the detail dialog
  const selectedFundData = selectedFund && universe
    ? universe.funds.find((f) => f.fund_name === selectedFund.fund_name)
    : null
  const selectedFundMetrics = selectedFund
    ? (gr?.fund_metrics ?? fundMetrics).find((fm) => fm.fund_name === selectedFund.fund_name)
    : null

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
          />
        </div>
        {universe && (
          <Button
            onClick={() => fetchBm(benchmarkSymbol, universe)}
            disabled={bmLoading}
          >
            {bmLoading ? "Fetching..." : "Fetch historical data"}
          </Button>
        )}
      </div>

      {bmError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{bmError}</AlertDescription>
        </Alert>
      )}

      {benchmark && benchmarkMetrics && (
        <p className="text-sm text-green-600 mb-4">
          Benchmark data loaded. {benchmarkSymbol.toUpperCase()} will appear as a reference row in the ranked table.
        </p>
      )}

      <Separator className="my-6" />

      {/* Scoring weights + info popover */}
      <div className="mb-4 flex items-center gap-2">
        <h3 className="text-lg font-medium">Scoring Weights</h3>
        <Popover>
          <PopoverTrigger asChild>
            <button className="text-muted-foreground hover:text-foreground transition-colors">
              <Info className="h-4 w-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-96 max-h-80 overflow-y-auto text-sm space-y-2">
            <p className="font-medium">How are funds ranked?</p>
            <p><strong>Annualized Return:</strong> Geometric mean of monthly growth factors, annualized.</p>
            <p><strong>Annualized Volatility:</strong> Sample std dev of monthly returns x sqrt(12).</p>
            <p><strong>Sharpe Ratio:</strong> Ann. Return / Ann. Volatility (risk-free rate = 0).</p>
            <p><strong>Max Drawdown:</strong> Worst peak-to-trough decline in cumulative wealth.</p>
            <p><strong>Benchmark Correlation:</strong> Pearson correlation over overlapping periods.</p>
            <Separator className="my-2" />
            <p className="font-medium">Ranking Methodology:</p>
            <ol className="list-decimal pl-4 space-y-1">
              <li>Each metric is min-max scaled to [0, 1] across all eligible funds. Max drawdown is inverted.</li>
              <li>Normalized scores are multiplied by your mandate weights.</li>
              <li>Composite score = weighted sum of normalized metrics.</li>
              <li>Funds passing all constraints ranked above those that fail.</li>
            </ol>
          </PopoverContent>
        </Popover>
      </div>

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

      <Separator className="my-6" />

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
          <div className="mb-6 rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rank</TableHead>
                  <TableHead>Fund</TableHead>
                  <TableHead>Score</TableHead>
                  {METRIC_IDS.map((mid) => (
                    <TableHead key={mid}>{METRIC_LABELS[mid]}</TableHead>
                  ))}
                  <TableHead>Constraints</TableHead>
                  <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(() => {
                  // Build rows: funds + optional benchmark, sorted by ann. return
                  const fundRows = gr.ranked_shortlist.map((sf) => ({
                    type: "fund" as const,
                    fund: sf,
                    annReturn: sf.metric_values.annualized_return ?? -Infinity,
                  }))

                  const bmRow = benchmarkMetrics
                    ? {
                        type: "benchmark" as const,
                        fund: null,
                        annReturn: benchmarkMetrics.annualized_return ?? -Infinity,
                      }
                    : null

                  // Find the insertion index: place benchmark after all funds with higher ann. return
                  const rows: typeof fundRows = [...fundRows]
                  if (bmRow) {
                    const insertIdx = rows.findIndex((r) => r.annReturn < bmRow.annReturn)
                    if (insertIdx === -1) {
                      rows.push(bmRow as typeof rows[number])
                    } else {
                      rows.splice(insertIdx, 0, bmRow as typeof rows[number])
                    }
                  }

                  return rows.map((row, i) => {
                    if (row.type === "benchmark") {
                      return (
                        <TableRow key="__benchmark__" className="bg-blue-50">
                          <TableCell className="text-muted-foreground">—</TableCell>
                          <TableCell className="font-medium">
                            {benchmarkSymbol.toUpperCase()}{" "}
                            <span className="text-xs text-blue-600 font-normal">(Benchmark)</span>
                          </TableCell>
                          <TableCell className="text-muted-foreground">—</TableCell>
                          {METRIC_IDS.map((mid) => (
                            <TableCell key={mid}>
                              {mid === "benchmark_correlation"
                                ? "1.000"
                                : formatMetric(mid, benchmarkMetrics![mid as keyof typeof benchmarkMetrics] as number)}
                            </TableCell>
                          ))}
                          <TableCell className="text-muted-foreground">—</TableCell>
                          <TableCell />
                        </TableRow>
                      )
                    }

                    const sf = row.fund!
                    return (
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
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => setSelectedFund(sf)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })
                })()}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {/* Fund detail dialog */}
      <Dialog open={!!selectedFund} onOpenChange={(open) => !open && setSelectedFund(null)}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          {selectedFund && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedFund.fund_name}</DialogTitle>
                <DialogDescription>
                  Rank #{selectedFund.rank} — Composite score: {selectedFund.composite_score?.toFixed(3) ?? "-"}
                </DialogDescription>
              </DialogHeader>

              {/* Score breakdown */}
              {selectedFund.score_breakdown.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Score Breakdown</h4>
                  <div className="rounded-md border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Metric</TableHead>
                          <TableHead>Raw Value</TableHead>
                          <TableHead>Normalized</TableHead>
                          <TableHead>Weight</TableHead>
                          <TableHead>Contribution</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedFund.score_breakdown.map((sc) => (
                          <TableRow key={sc.metric_id}>
                            <TableCell className="font-medium">
                              {METRIC_LABELS[sc.metric_id as MetricId] ?? sc.metric_id}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {sc.raw_value?.toFixed(4) ?? "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {sc.normalized_value?.toFixed(3) ?? "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {sc.weight ?? "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {sc.weighted_contribution?.toFixed(4) ?? "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {/* Constraints */}
              {selectedFund.constraint_results.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Constraints</h4>
                  <ul className="text-sm space-y-1 pl-4">
                    {selectedFund.constraint_results.map((cr, i) => (
                      <li key={i} className={cr.passed ? "text-green-600" : "text-red-600"}>
                        [{cr.passed ? "+" : "x"}] {cr.explanation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Consolidated calc sheets */}
              {selectedFundData && selectedFundMetrics && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Calculation Sheets</h4>
                  <div className="space-y-4">
                    {METRIC_IDS.map((mid) => (
                      <Collapsible key={mid}>
                        <CollapsibleTrigger asChild>
                          <Button variant="outline" size="sm" className="w-full justify-start">
                            {METRIC_LABELS[mid]}
                          </Button>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 pl-2">
                          <CalcSheet
                            fund={selectedFundData}
                            metricId={mid}
                            fundMetrics={selectedFundMetrics}
                            rawContext={rawContext}
                            benchmark={gr?.group?.benchmark ?? benchmark}
                          />
                        </CollapsibleContent>
                      </Collapsible>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>

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
