import { useState } from "react"
import { useWizard } from "@/context/WizardContext"
import { PageHeader } from "@/components/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { SAMPLE_PORTFOLIOS, type Portfolio } from "@/data/sample-portfolios"
import { cn } from "@/lib/utils"
import { Plus } from "lucide-react"

function fmt(n: number, style: "pct" | "currency" | "ratio" | "days") {
  if (style === "pct") return `${(n * 100).toFixed(1)}%`
  if (style === "ratio") return n.toFixed(2)
  if (style === "days") return `${n} days`
  return `$${(n / 1_000_000).toFixed(0)}M`
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  )
}

export function PortfoliosPage() {
  const { startAllocation, setSelectedPortfolioId } = useWizard()
  const [selectedId, setSelectedId] = useState(SAMPLE_PORTFOLIOS[0].id)
  const portfolio = SAMPLE_PORTFOLIOS.find((p) => p.id === selectedId) as Portfolio

  function handleNewAllocation() {
    startAllocation()
    setSelectedPortfolioId(selectedId)
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <PageHeader
          title="Portfolios"
          description="Portfolio overview, holdings, and governance mandates."
        />
        <Button onClick={handleNewAllocation} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          New Allocation
        </Button>
      </div>

      {/* Portfolio selector */}
      <div className="flex gap-3 mb-6">
        {SAMPLE_PORTFOLIOS.map((p) => (
          <button
            key={p.id}
            onClick={() => setSelectedId(p.id)}
            className={cn(
              "rounded-lg border px-4 py-3 text-left transition-colors",
              p.id === selectedId
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/40",
            )}
          >
            <div className="font-medium text-sm">{p.name}</div>
            <div className="text-xs text-muted-foreground">{p.strategy}</div>
          </button>
        ))}
      </div>

      {/* Overview + Metrics in two side-by-side cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
              <Stat label="Strategy" value={portfolio.strategy} />
              <Stat label="AUM" value={fmt(portfolio.aum, "currency")} />
              <Stat label="Target Return" value={fmt(portfolio.targetReturn, "pct")} />
              <Stat label="Target Volatility" value={fmt(portfolio.targetVolatility, "pct")} />
              <Stat label="Inception" value={portfolio.inceptionDate} />
              <Stat label="Holdings" value={`${portfolio.holdings.length} funds`} />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Current Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
              <Stat label="Ann. Return" value={fmt(portfolio.metrics.annualized_return, "pct")} />
              <Stat label="Ann. Volatility" value={fmt(portfolio.metrics.annualized_volatility, "pct")} />
              <Stat label="Sharpe Ratio" value={fmt(portfolio.metrics.sharpe_ratio, "ratio")} />
              <Stat label="Max Drawdown" value={fmt(portfolio.metrics.max_drawdown, "pct")} />
              <Stat label="YTD Return" value={fmt(portfolio.metrics.ytd_return, "pct")} />
            </dl>
          </CardContent>
        </Card>
      </div>

      {/* Holdings table */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Current Holdings</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fund Name</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead className="text-right">Allocation</TableHead>
                <TableHead className="text-right">Ann. Return</TableHead>
                <TableHead className="text-right">Ann. Vol</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {portfolio.holdings.map((h) => (
                <TableRow key={h.fund_name}>
                  <TableCell className="font-medium">{h.fund_name}</TableCell>
                  <TableCell>{h.strategy}</TableCell>
                  <TableCell className="text-right">{fmt(h.weight, "pct")}</TableCell>
                  <TableCell className="text-right">
                    {h.annualized_return != null ? fmt(h.annualized_return, "pct") : "\u2014"}
                  </TableCell>
                  <TableCell className="text-right">
                    {h.annualized_volatility != null ? fmt(h.annualized_volatility, "pct") : "\u2014"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Governance mandate */}
      <Card>
        <CardHeader>
          <CardTitle>Governance Mandate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Max Drawdown: {fmt(Math.abs(portfolio.governance.max_drawdown_tolerance), "pct")}</Badge>
            <Badge variant="outline">Target Vol: {fmt(portfolio.governance.target_volatility, "pct")}</Badge>
            <Badge variant="outline">Min Liquidity: {fmt(portfolio.governance.min_liquidity_days, "days")}</Badge>
            <Badge variant="outline">Min History: {portfolio.governance.min_history_months} months</Badge>
            {portfolio.governance.min_sharpe_ratio != null && (
              <Badge variant="outline">Min Sharpe: {fmt(portfolio.governance.min_sharpe_ratio, "ratio")}</Badge>
            )}
            {portfolio.governance.min_annualized_return != null && (
              <Badge variant="outline">Min Return: {fmt(portfolio.governance.min_annualized_return, "pct")}</Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
