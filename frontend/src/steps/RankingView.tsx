import { useEffect, useState, useRef } from "react"
import { useWizard, type MetricId, type ScoredFund, type ReRankRationale, type PortfolioContext } from "@/context/WizardContext"
import { SAMPLE_PORTFOLIOS } from "@/data/sample-portfolios"
import { PageHeader } from "@/components/PageHeader"
import { CalcSheet, SourceData } from "@/components/CalcSheet"
import { useBenchmark } from "@/hooks/useBenchmark"
import { useRank } from "@/hooks/useRank"
import { useRerank } from "@/hooks/useRerank"
import { useMemoStream } from "@/hooks/useMemoStream"
import { formatMetric } from "@/lib/format"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { exportFundToExcel } from "@/lib/excel-export"
import { Info, Eye, Download, Sparkles } from "lucide-react"

const METRIC_IDS: MetricId[] = [
  "annualized_return",
  "annualized_volatility",
  "sharpe_ratio",
  "max_drawdown",
  "benchmark_correlation",
  "portfolio_diversification",
]

const METRIC_LABELS: Record<MetricId, string> = {
  annualized_return: "Ann. Return",
  annualized_volatility: "Ann. Volatility",
  sharpe_ratio: "Sharpe Ratio",
  max_drawdown: "Max Drawdown",
  benchmark_correlation: "Benchmark Corr.",
  portfolio_diversification: "Portfolio Div.",
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
    selectedPortfolioId,
    setMandate,
    setBenchmarkSymbol,
    setGroupRuns,
    setStep,
    resetFrom,
  } = useWizard()

  const { fetch: fetchBm, loading: bmLoading, error: bmError } = useBenchmark()
  const { rank, loading: rankLoading, error: rankError } = useRank()
  const { rerank, loading: rerankLoading, error: rerankError } = useRerank()
  const { generate: generateMemo, loading: memoLoading, error: memoError } = useMemoStream()

  const [wRet, setWRet] = useState(mandate?.weights.annualized_return ?? 0.4)
  const [wSharpe, setWSharpe] = useState(mandate?.weights.sharpe_ratio ?? 0.4)
  const [wDD, setWDD] = useState(mandate?.weights.max_drawdown ?? 0.2)
  const [wCorr, setWCorr] = useState(mandate?.weights.benchmark_correlation ?? 0)
  const [wDiv, setWDiv] = useState(mandate?.weights.portfolio_diversification ?? 0)
  const [selectedFund, setSelectedFund] = useState<ScoredFund | null>(null)
  const [rankingTab, setRankingTab] = useState<"quantitative" | "ai-assisted">("quantitative")
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Track whether initial ranking has been triggered
  const initialRanked = useRef(false)

  // Auto re-rank when weights change (debounced)
  useEffect(() => {
    if (!mandate) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      const newWeights: Record<string, number> = {}
      if (wRet > 0) newWeights["annualized_return"] = wRet
      if (wSharpe > 0) newWeights["sharpe_ratio"] = wSharpe
      if (wDD > 0) newWeights["max_drawdown"] = wDD
      if (wCorr > 0) newWeights["benchmark_correlation"] = wCorr
      if (wDiv > 0) newWeights["portfolio_diversification"] = wDiv

      const changed = JSON.stringify(newWeights) !== JSON.stringify(mandate.weights)
      if (changed) {
        setMandate({ ...mandate, weights: newWeights as Record<MetricId, number> })
      }
    }, 500)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [wRet, wSharpe, wDD, wCorr, wDiv]) // eslint-disable-line react-hooks/exhaustive-deps

  // Re-rank when mandate or benchmark changes (keeps stale data visible with loading overlay)
  useEffect(() => {
    if (universe && mandate && !rankLoading) {
      // Skip the very first render — initial rank is handled below
      if (!initialRanked.current) return
      rank()
    }
  }, [mandate, benchmark]) // eslint-disable-line react-hooks/exhaustive-deps

  // Initial ranking on mount
  useEffect(() => {
    if (universe && mandate && groupRuns.length === 0 && !rankLoading && !initialRanked.current) {
      initialRanked.current = true
      rank()
    }
  }, [universe, mandate, groupRuns.length, rankLoading, rank])

  const useAiRanking = rankingTab === "ai-assisted" && !!groupRuns[0]?.llm_rerank

  const handleGenerateMemo = async () => {
    if (!groupRuns[0] || !universe || !mandate) return
    setStep(3)

    let portfolioCtx: PortfolioContext | null = null
    if (selectedPortfolioId) {
      const p = SAMPLE_PORTFOLIOS.find((sp) => sp.id === selectedPortfolioId)
      if (p) {
        portfolioCtx = {
          portfolio_name: p.name,
          strategy: p.strategy,
          aum: p.aum,
          holdings: p.holdings.map((h) => ({
            fund_name: h.fund_name,
            strategy: h.strategy,
            weight: h.weight,
          })),
          governance: p.governance as unknown as Record<string, unknown>,
        }
      }
    }

    const result = await generateMemo(
      groupRuns[0],
      universe,
      mandate,
      warningResolutions,
      useAiRanking,
      portfolioCtx,
    )
    if (result) {
      setGroupRuns([result])
    }
  }

  const gr = groupRuns[0]
  const total = wRet + wSharpe + wDD + wCorr + wDiv

  // Look up fund data for the detail dialog
  const selectedFundData = selectedFund && universe
    ? universe.funds.find((f) => f.fund_name === selectedFund.fund_name)
    : null
  const selectedFundMetrics = selectedFund
    ? (gr?.fund_metrics ?? fundMetrics).find((fm) => fm.fund_name === selectedFund.fund_name)
    : null
  const selectedFundRerank: ReRankRationale | null = selectedFund && gr?.llm_rerank
    ? gr.llm_rerank.reranked_funds.find((r) => r.fund_name === selectedFund.fund_name) ?? null
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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-2">
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
        <div>
          <Label className="text-sm">Benchmark Corr.: {wCorr.toFixed(2)}</Label>
          <Slider
            value={[wCorr]}
            onValueChange={([v]) => setWCorr(v)}
            min={0}
            max={1}
            step={0.05}
          />
        </div>
        <div>
          <Label className="text-sm">Portfolio Div.: {wDiv.toFixed(2)}</Label>
          <Slider
            value={[wDiv]}
            onValueChange={([v]) => setWDiv(v)}
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

      {/* Error */}
      {rankError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{rankError}</AlertDescription>
        </Alert>
      )}

      {/* Ranking results */}
      {(gr || rankLoading) && (
        <div className="relative">
          {rankLoading && (
            <div className="absolute inset-0 bg-background/60 z-10 flex items-center justify-center rounded-md">
              <div className="flex items-center gap-2 text-sm text-muted-foreground bg-background px-4 py-2 rounded-md shadow-sm border">
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Re-ranking...
              </div>
            </div>
          )}
          {/* Excluded candidates */}
          {gr && gr.run_candidates.filter((rc) => !rc.included).length > 0 && (
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

          {/* Tab toggle when AI re-rank is available */}
          {gr?.llm_rerank && (
            <Tabs value={rankingTab} onValueChange={(v) => setRankingTab(v as "quantitative" | "ai-assisted")} className="mb-4">
              <TabsList>
                <TabsTrigger value="quantitative">Quantitative</TabsTrigger>
                <TabsTrigger value="ai-assisted">AI-Assisted</TabsTrigger>
              </TabsList>
            </Tabs>
          )}

          {/* Re-rank error */}
          {rerankError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{rerankError}</AlertDescription>
            </Alert>
          )}

          {/* AI-Assisted view */}
          {rankingTab === "ai-assisted" && gr?.llm_rerank && (
            <>
              <div className="mb-4 rounded-md bg-muted/50 p-4 text-sm whitespace-pre-wrap">
                {gr.llm_rerank.overall_commentary}
              </div>
              <div className="mb-6 rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>AI Rank</TableHead>
                      <TableHead>Fund</TableHead>
                      <TableHead>Det. Rank</TableHead>
                      {METRIC_IDS.map((mid) => (
                        <TableHead key={mid}>{METRIC_LABELS[mid]}</TableHead>
                      ))}
                      <TableHead>Rationale</TableHead>
                      <TableHead className="w-[60px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[...gr.llm_rerank.reranked_funds]
                      .sort((a, b) => a.llm_rank - b.llm_rank)
                      .map((rr) => {
                        const sf = gr.ranked_shortlist.find((s) => s.fund_name === rr.fund_name)
                        return (
                          <TableRow key={rr.fund_name}>
                            <TableCell className="font-medium">{rr.llm_rank}</TableCell>
                            <TableCell className="font-medium">{rr.fund_name}</TableCell>
                            <TableCell className="text-muted-foreground">{rr.deterministic_rank}</TableCell>
                            {METRIC_IDS.map((mid) => (
                              <TableCell key={mid}>
                                {sf ? formatMetric(mid, sf.metric_values[mid]) : "-"}
                              </TableCell>
                            ))}
                            <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground" title={rr.rationale}>
                              {rr.rationale}
                            </TableCell>
                            <TableCell>
                              {sf && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0"
                                  onClick={() => setSelectedFund(sf)}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                  </TableBody>
                </Table>
              </div>
            </>
          )}

          {/* Quantitative view (original table) */}
          {rankingTab === "quantitative" && gr && (
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
                    type FundTableRow = {
                      type: "fund"
                      fund: ScoredFund
                      annReturn: number
                    }
                    type BenchmarkTableRow = {
                      type: "benchmark"
                      fund: null
                      annReturn: number
                    }
                    type TableRowType = FundTableRow | BenchmarkTableRow

                    const fundRows: FundTableRow[] = gr.ranked_shortlist.map((sf) => ({
                      type: "fund" as const,
                      fund: sf,
                      annReturn: sf.metric_values.annualized_return ?? -Infinity,
                    }))

                    const bmRow: BenchmarkTableRow | null = benchmarkMetrics
                      ? {
                          type: "benchmark" as const,
                          fund: null,
                          annReturn: benchmarkMetrics.annualized_return ?? -Infinity,
                        }
                      : null

                    const rows: TableRowType[] = [...fundRows]
                    if (bmRow) {
                      const insertIdx = rows.findIndex((r) => r.annReturn < bmRow.annReturn)
                      if (insertIdx === -1) {
                        rows.push(bmRow)
                      } else {
                        rows.splice(insertIdx, 0, bmRow)
                      }
                    }

                    return rows.map((row) => {
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
          )}
        </div>
      )}

      {/* Fund detail dialog */}
      <Dialog open={!!selectedFund} onOpenChange={(open) => !open && setSelectedFund(null)}>
        <DialogContent className="max-w-[calc(100vw-4rem)] sm:max-w-5xl h-[85vh] flex flex-col overflow-hidden">
          {selectedFund && (
            <>
              <DialogHeader className="flex-row items-center justify-between gap-4 space-y-0">
                <div>
                  <DialogTitle>{selectedFund.fund_name}</DialogTitle>
                  <DialogDescription>
                    Rank #{selectedFund.rank} — Composite score: {selectedFund.composite_score?.toFixed(3) ?? "-"}
                  </DialogDescription>
                </div>
                {selectedFundData && selectedFundMetrics && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 mr-8"
                    onClick={() =>
                      exportFundToExcel(
                        selectedFund,
                        selectedFundData,
                        selectedFundMetrics,
                        rawContext,
                        gr?.group?.benchmark ?? benchmark,
                      )
                    }
                  >
                    <Download className="h-4 w-4" />
                    Export to Excel
                  </Button>
                )}
              </DialogHeader>

              <Tabs defaultValue="summary" className="flex-1 min-h-0 flex flex-col">
                <TabsList className="shrink-0">
                  <TabsTrigger value="summary">Summary</TabsTrigger>
                  {METRIC_IDS.map((mid) => (
                    <TabsTrigger key={mid} value={mid}>
                      {METRIC_LABELS[mid]}
                    </TabsTrigger>
                  ))}
                  <TabsTrigger value="source">Source Data</TabsTrigger>
                </TabsList>

                {/* Summary tab */}
                <TabsContent value="summary" className="flex-1 overflow-y-auto mt-2">
                  {/* Score breakdown */}
                  {selectedFund.score_breakdown.length > 0 && (
                    <div className="mb-4">
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

                  {/* AI Rationale */}
                  {selectedFundRerank && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
                        <Sparkles className="h-4 w-4" />
                        AI Rationale
                      </h4>
                      <p className="text-sm mb-2">
                        AI Rank: <strong>#{selectedFundRerank.llm_rank}</strong>{" "}
                        <span className="text-muted-foreground">
                          (Det. Rank: #{selectedFundRerank.deterministic_rank})
                        </span>
                      </p>
                      <p className="text-sm mb-3">{selectedFundRerank.rationale}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedFundRerank.key_factors.map((factor) => (
                          <Badge key={factor} variant="secondary">{factor}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </TabsContent>

                {/* Per-metric tabs */}
                {selectedFundData && selectedFundMetrics && METRIC_IDS.map((mid) => (
                  <TabsContent key={mid} value={mid} className="flex-1 overflow-y-auto mt-2">
                    <CalcSheet
                      fund={selectedFundData}
                      metricId={mid}
                      fundMetrics={selectedFundMetrics}
                      rawContext={rawContext}
                      benchmark={gr?.group?.benchmark ?? benchmark}
                    />
                  </TabsContent>
                ))}

                {/* Source Data tab */}
                <TabsContent value="source" className="flex-1 overflow-y-auto mt-2">
                  {selectedFundData ? (
                    <SourceData fund={selectedFundData} rawContext={rawContext} />
                  ) : (
                    <p className="text-sm text-muted-foreground">No source data available.</p>
                  )}
                </TabsContent>
              </Tabs>
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
          {memoError && (
            <p className="text-sm text-red-600 max-w-md truncate">{memoError}</p>
          )}
          <Button
            variant="outline"
            onClick={() => {
              rerank()
              setRankingTab("ai-assisted")
            }}
            disabled={!gr || rerankLoading}
          >
            <Sparkles className="h-4 w-4 mr-1.5" />
            {rerankLoading ? "Re-Ranking..." : "AI Re-Rank"}
          </Button>
          <Button
            onClick={handleGenerateMemo}
            disabled={!gr || memoLoading}
          >
            {memoLoading
              ? "Generating..."
              : useAiRanking
                ? "Generate Memo (AI-Ranked)"
                : "Generate Memo"}
          </Button>
        </div>
      </div>
    </div>
  )
}
