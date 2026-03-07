import { useState, useEffect, useMemo } from "react"
import { useWizard, DEFAULT_MANDATE, type MandateConfig, type MetricId } from "@/context/WizardContext"
import { SAMPLE_PORTFOLIOS, type Portfolio } from "@/data/sample-portfolios"
import { PageHeader } from "@/components/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Lock } from "lucide-react"

export function MandateForm() {
  const { setMandate, setStep, selectedPortfolioId, setSelectedPortfolioId } = useWizard()

  const selectedPortfolio = useMemo(
    () => SAMPLE_PORTFOLIOS.find((p) => p.id === selectedPortfolioId) ?? null,
    [selectedPortfolioId],
  )
  const gov = selectedPortfolio?.governance ?? null

  const [useDD, setUseDD] = useState(false)
  const [maxDDPct, setMaxDDPct] = useState(20)
  const [useVol, setUseVol] = useState(false)
  const [targetVolPct, setTargetVolPct] = useState(15)
  const [useLiquidity, setUseLiquidity] = useState(false)
  const [minLiqDays, setMinLiqDays] = useState(45)
  const [useMinReturn, setUseMinReturn] = useState(false)
  const [minReturnPct, setMinReturnPct] = useState(5)
  const [useMinSharpe, setUseMinSharpe] = useState(false)
  const [minSharpe, setMinSharpe] = useState(0.5)
  const [minHistory, setMinHistory] = useState(12)
  const [strategyInclude, setStrategyInclude] = useState("")
  const [strategyExclude, setStrategyExclude] = useState("")
  const [filtersOpen, setFiltersOpen] = useState(false)

  // Scoring weights
  const [weights, setWeights] = useState<Record<MetricId, number>>({
    ...DEFAULT_MANDATE.weights,
  })

  // When portfolio changes, pre-fill from governance
  useEffect(() => {
    if (!gov) return
    setUseDD(true)
    setMaxDDPct(Math.abs(gov.max_drawdown_tolerance) * 100)
    setUseVol(true)
    setTargetVolPct(gov.target_volatility * 100)
    setUseLiquidity(true)
    setMinLiqDays(gov.min_liquidity_days)
    setMinHistory(gov.min_history_months)
    if (gov.min_sharpe_ratio != null) {
      setUseMinSharpe(true)
      setMinSharpe(gov.min_sharpe_ratio)
    }
    if (gov.min_annualized_return != null) {
      setUseMinReturn(true)
      setMinReturnPct(gov.min_annualized_return * 100)
    }
    // Auto-set portfolio diversification weight, scaling others to keep sum = 1
    setWeights((prev) => {
      const divWeight = 0.15
      const otherSum = Object.entries(prev)
        .filter(([k]) => k !== "portfolio_diversification")
        .reduce((sum, [, v]) => sum + v, 0)
      const scale = otherSum > 0 ? (1 - divWeight) / otherSum : 1
      const next = { ...prev, portfolio_diversification: divWeight }
      for (const k of Object.keys(next) as MetricId[]) {
        if (k !== "portfolio_diversification") next[k] = +(next[k] * scale).toFixed(4)
      }
      return next
    })
  }, [gov])

  function handlePortfolioChange(value: string) {
    if (value === "none") {
      setSelectedPortfolioId(null)
      setWeights((prev) => {
        const next = { ...prev, portfolio_diversification: 0 }
        const otherSum = Object.entries(next)
          .filter(([k]) => k !== "portfolio_diversification")
          .reduce((sum, [, v]) => sum + v, 0)
        if (otherSum > 0) {
          const scale = 1 / otherSum
          for (const k of Object.keys(next) as MetricId[]) {
            if (k !== "portfolio_diversification") next[k] = +(next[k] * scale).toFixed(4)
          }
        }
        return next
      })
    } else {
      setSelectedPortfolioId(value)
    }
  }

  function handleContinue() {
    const includeList = strategyInclude
      ? strategyInclude.split(",").map((s) => s.trim()).filter(Boolean)
      : []
    const excludeList = strategyExclude
      ? strategyExclude.split(",").map((s) => s.trim()).filter(Boolean)
      : []

    let finalDD = useDD ? -maxDDPct / 100 : null
    let finalVol = useVol ? targetVolPct / 100 : null
    let finalLiq = useLiquidity ? minLiqDays : null
    let finalReturn = useMinReturn ? minReturnPct / 100 : null
    let finalSharpe = useMinSharpe ? minSharpe : null
    let finalHistory = minHistory

    // Merge with governance floors (use the more conservative)
    if (gov) {
      finalDD = finalDD != null
        ? Math.max(finalDD, gov.max_drawdown_tolerance)   // both negative, max = tighter
        : gov.max_drawdown_tolerance
      finalVol = finalVol != null
        ? Math.min(finalVol, gov.target_volatility)        // lower vol = tighter
        : gov.target_volatility
      finalLiq = finalLiq != null
        ? Math.max(finalLiq, gov.min_liquidity_days)       // more days = tighter
        : gov.min_liquidity_days
      finalHistory = Math.max(finalHistory, gov.min_history_months)
      if (gov.min_sharpe_ratio != null) {
        finalSharpe = finalSharpe != null
          ? Math.max(finalSharpe, gov.min_sharpe_ratio)
          : gov.min_sharpe_ratio
      }
      if (gov.min_annualized_return != null) {
        finalReturn = finalReturn != null
          ? Math.max(finalReturn, gov.min_annualized_return)
          : gov.min_annualized_return
      }
    }

    const mandate: MandateConfig = {
      ...DEFAULT_MANDATE,
      min_liquidity_days: finalLiq,
      max_drawdown_tolerance: finalDD,
      target_volatility: finalVol,
      min_annualized_return: finalReturn,
      min_sharpe_ratio: finalSharpe,
      min_history_months: finalHistory,
      weights,
      strategy_include: includeList,
      strategy_exclude: excludeList,
    }
    setMandate(mandate)
    setStep(1)
  }

  // Governance floor helpers
  const ddFloor = gov ? Math.abs(gov.max_drawdown_tolerance) * 100 : null
  const volFloor = gov ? gov.target_volatility * 100 : null

  return (
    <div>
      <PageHeader
        title="Define Your Mandate"
        description="Set your hard constraints before uploading data."
      />

      {/* Portfolio selector */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Allocating for Portfolio</CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={selectedPortfolioId ?? "none"}
            onValueChange={handlePortfolioChange}
          >
            <SelectTrigger className="w-full max-w-sm">
              <SelectValue placeholder="Select a portfolio (optional)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No portfolio (standalone)</SelectItem>
              {SAMPLE_PORTFOLIOS.map((p) => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedPortfolio && (
            <div className="mt-3 flex items-center gap-2">
              <Badge variant="secondary">{selectedPortfolio.name}</Badge>
              <span className="text-xs text-muted-foreground">
                {selectedPortfolio.strategy} &middot; ${(selectedPortfolio.aum / 1_000_000).toFixed(0)}M AUM
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Risk Constraints */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Constraints</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Max Drawdown */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-dd"
                  checked={useDD}
                  onCheckedChange={(v) => { if (!gov) setUseDD(v === true) }}
                  disabled={gov != null}
                />
                <Label htmlFor="use-dd">Max drawdown constraint</Label>
                {gov && <Lock className="h-3.5 w-3.5 text-muted-foreground" />}
              </div>
              {useDD && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">
                    Max drawdown tolerance: {maxDDPct.toFixed(0)}%
                  </Label>
                  <Slider
                    value={[maxDDPct]}
                    onValueChange={([v]) => setMaxDDPct(v)}
                    min={1}
                    max={ddFloor ?? 50}
                    step={1}
                  />
                  {ddFloor != null && (
                    <GovernanceFloorLabel label={`Governance floor: ${ddFloor.toFixed(0)}%`} />
                  )}
                </div>
              )}
            </div>

            {/* Target Volatility */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-vol"
                  checked={useVol}
                  onCheckedChange={(v) => { if (!gov) setUseVol(v === true) }}
                  disabled={gov != null}
                />
                <Label htmlFor="use-vol">Target volatility constraint</Label>
                {gov && <Lock className="h-3.5 w-3.5 text-muted-foreground" />}
              </div>
              {useVol && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">
                    Target volatility: {targetVolPct.toFixed(0)}%
                  </Label>
                  <Slider
                    value={[targetVolPct]}
                    onValueChange={([v]) => setTargetVolPct(v)}
                    min={1}
                    max={volFloor ?? 50}
                    step={1}
                  />
                  {volFloor != null && (
                    <GovernanceFloorLabel label={`Governance floor: ${volFloor.toFixed(0)}%`} />
                  )}
                </div>
              )}
            </div>

            {/* Min Liquidity */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-liq"
                  checked={useLiquidity}
                  onCheckedChange={(v) => { if (!gov) setUseLiquidity(v === true) }}
                  disabled={gov != null}
                />
                <Label htmlFor="use-liq">Min liquidity constraint</Label>
                {gov && <Lock className="h-3.5 w-3.5 text-muted-foreground" />}
              </div>
              {useLiquidity && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">Min liquidity (days)</Label>
                  <Input
                    type="number"
                    min={gov ? gov.min_liquidity_days : 0}
                    max={365}
                    value={minLiqDays}
                    onChange={(e) => {
                      const v = Number(e.target.value)
                      setMinLiqDays(gov ? Math.max(v, gov.min_liquidity_days) : v)
                    }}
                  />
                  {gov && (
                    <GovernanceFloorLabel label={`Governance floor: ${gov.min_liquidity_days} days`} />
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Performance Constraints */}
        <Card>
          <CardHeader>
            <CardTitle>Performance Constraints</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Min Return */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-ret"
                  checked={useMinReturn}
                  onCheckedChange={(v) => {
                    if (gov?.min_annualized_return != null) return
                    setUseMinReturn(v === true)
                  }}
                  disabled={gov?.min_annualized_return != null}
                />
                <Label htmlFor="use-ret">Min annualized return</Label>
                {gov?.min_annualized_return != null && <Lock className="h-3.5 w-3.5 text-muted-foreground" />}
              </div>
              {useMinReturn && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">
                    Min annualized return: {minReturnPct}%
                  </Label>
                  <Slider
                    value={[minReturnPct]}
                    onValueChange={([v]) => setMinReturnPct(v)}
                    min={gov?.min_annualized_return != null ? gov.min_annualized_return * 100 : 0}
                    max={50}
                    step={1}
                  />
                  {gov?.min_annualized_return != null && (
                    <GovernanceFloorLabel label={`Governance floor: ${(gov.min_annualized_return * 100).toFixed(0)}%`} />
                  )}
                </div>
              )}
            </div>

            {/* Min Sharpe */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-sharpe"
                  checked={useMinSharpe}
                  onCheckedChange={(v) => {
                    if (gov?.min_sharpe_ratio != null) return
                    setUseMinSharpe(v === true)
                  }}
                  disabled={gov?.min_sharpe_ratio != null}
                />
                <Label htmlFor="use-sharpe">Min Sharpe ratio</Label>
                {gov?.min_sharpe_ratio != null && <Lock className="h-3.5 w-3.5 text-muted-foreground" />}
              </div>
              {useMinSharpe && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">Min Sharpe ratio</Label>
                  <Input
                    type="number"
                    min={gov?.min_sharpe_ratio ?? 0}
                    max={5}
                    step={0.1}
                    value={minSharpe}
                    onChange={(e) => {
                      const v = Number(e.target.value)
                      setMinSharpe(gov?.min_sharpe_ratio != null ? Math.max(v, gov.min_sharpe_ratio) : v)
                    }}
                  />
                  {gov?.min_sharpe_ratio != null && (
                    <GovernanceFloorLabel label={`Governance floor: ${gov.min_sharpe_ratio.toFixed(1)}`} />
                  )}
                </div>
              )}
            </div>

            {/* Min History */}
            <div className="space-y-2">
              <Label className="text-sm">Min history (months)</Label>
              <Input
                type="number"
                min={gov ? gov.min_history_months : 1}
                max={120}
                value={minHistory}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  setMinHistory(gov ? Math.max(v, gov.min_history_months) : v)
                }}
              />
              {gov && (
                <GovernanceFloorLabel label={`Governance floor: ${gov.min_history_months} months`} />
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Strategy Filters */}
      <Collapsible open={filtersOpen} onOpenChange={setFiltersOpen} className="mb-6">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="font-medium">
            {filtersOpen ? "Hide" : "Show"} Strategy Filters
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-4 mt-2">
          <p className="text-sm text-muted-foreground">
            Optional — filter funds by strategy label before ranking.
          </p>
          <div className="space-y-2">
            <Label>Include only these strategies (comma-separated)</Label>
            <Input
              placeholder="e.g., Long/Short Equity, Global Macro"
              value={strategyInclude}
              onChange={(e) => setStrategyInclude(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Exclude these strategies (comma-separated)</Label>
            <Input
              placeholder="e.g., Credit"
              value={strategyExclude}
              onChange={(e) => setStrategyExclude(e.target.value)}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      <div className="flex justify-end">
        <Button onClick={handleContinue}>Continue</Button>
      </div>
    </div>
  )
}

function GovernanceFloorLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-1 mt-1">
      <Lock className="h-3 w-3 text-amber-500" />
      <span className="text-xs text-amber-600">{label}</span>
    </div>
  )
}
