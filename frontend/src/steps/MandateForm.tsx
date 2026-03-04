import { useState } from "react"
import { useWizard, DEFAULT_MANDATE, type MandateConfig } from "@/context/WizardContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

export function MandateForm() {
  const { setMandate, setStep } = useWizard()

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

  function handleContinue() {
    const includeList = strategyInclude
      ? strategyInclude.split(",").map((s) => s.trim()).filter(Boolean)
      : []
    const excludeList = strategyExclude
      ? strategyExclude.split(",").map((s) => s.trim()).filter(Boolean)
      : []

    const mandate: MandateConfig = {
      ...DEFAULT_MANDATE,
      min_liquidity_days: useLiquidity ? minLiqDays : null,
      max_drawdown_tolerance: useDD ? -maxDDPct / 100 : null,
      target_volatility: useVol ? targetVolPct / 100 : null,
      min_annualized_return: useMinReturn ? minReturnPct / 100 : null,
      min_sharpe_ratio: useMinSharpe ? minSharpe : null,
      min_history_months: minHistory,
      strategy_include: includeList,
      strategy_exclude: excludeList,
    }
    setMandate(mandate)
    setStep(1)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Equi</h1>
      <p className="text-muted-foreground mb-6">
        Turn messy manager data into normalized, validated, and defendable investment decisions.
      </p>

      <h2 className="text-xl font-semibold mb-4">Define Your Mandate</h2>
      <p className="text-sm text-muted-foreground mb-6">Set your hard constraints before uploading data.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Risk Constraints */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Constraints</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-dd"
                  checked={useDD}
                  onCheckedChange={(v) => setUseDD(v === true)}
                />
                <Label htmlFor="use-dd">Max drawdown constraint</Label>
              </div>
              {useDD && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">
                    Max drawdown tolerance: {maxDDPct}%
                  </Label>
                  <Slider
                    value={[maxDDPct]}
                    onValueChange={([v]) => setMaxDDPct(v)}
                    min={1}
                    max={50}
                    step={1}
                  />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-vol"
                  checked={useVol}
                  onCheckedChange={(v) => setUseVol(v === true)}
                />
                <Label htmlFor="use-vol">Target volatility constraint</Label>
              </div>
              {useVol && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">
                    Target volatility: {targetVolPct}%
                  </Label>
                  <Slider
                    value={[targetVolPct]}
                    onValueChange={([v]) => setTargetVolPct(v)}
                    min={1}
                    max={50}
                    step={1}
                  />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-liq"
                  checked={useLiquidity}
                  onCheckedChange={(v) => setUseLiquidity(v === true)}
                />
                <Label htmlFor="use-liq">Min liquidity constraint</Label>
              </div>
              {useLiquidity && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">Min liquidity (days)</Label>
                  <Input
                    type="number"
                    min={0}
                    max={365}
                    value={minLiqDays}
                    onChange={(e) => setMinLiqDays(Number(e.target.value))}
                  />
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
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-ret"
                  checked={useMinReturn}
                  onCheckedChange={(v) => setUseMinReturn(v === true)}
                />
                <Label htmlFor="use-ret">Min annualized return</Label>
              </div>
              {useMinReturn && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">
                    Min annualized return: {minReturnPct}%
                  </Label>
                  <Slider
                    value={[minReturnPct]}
                    onValueChange={([v]) => setMinReturnPct(v)}
                    min={0}
                    max={50}
                    step={1}
                  />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="use-sharpe"
                  checked={useMinSharpe}
                  onCheckedChange={(v) => setUseMinSharpe(v === true)}
                />
                <Label htmlFor="use-sharpe">Min Sharpe ratio</Label>
              </div>
              {useMinSharpe && (
                <div className="pl-6 space-y-1">
                  <Label className="text-sm text-muted-foreground">Min Sharpe ratio</Label>
                  <Input
                    type="number"
                    min={0}
                    max={5}
                    step={0.1}
                    value={minSharpe}
                    onChange={(e) => setMinSharpe(Number(e.target.value))}
                  />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-sm">Min history (months)</Label>
              <Input
                type="number"
                min={1}
                max={120}
                value={minHistory}
                onChange={(e) => setMinHistory(Number(e.target.value))}
              />
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
