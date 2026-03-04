import type { MetricId, NormalizedFund, FundMetrics, BenchmarkSeries, RawFileContext } from "@/context/WizardContext"
import {
  computeAnnualizedReturn,
  computeAnnualizedVolatility,
  computeSharpeRatio,
  computeMaxDrawdown,
  computeBenchmarkCorrelation,
  type CalcRow,
} from "@/lib/calc-sheet"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface CalcSheetProps {
  fund: NormalizedFund
  metricId: MetricId
  fundMetrics: FundMetrics
  rawContext: RawFileContext | null
  benchmark: BenchmarkSeries | null
}

function DataTable({ rows, columns }: { rows: CalcRow[]; columns: string[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead key={col}>{col}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, i) => (
          <TableRow key={i}>
            {columns.map((col) => (
              <TableCell key={col} className="font-mono text-xs">
                {typeof row[col] === "number"
                  ? (row[col] as number).toFixed(6)
                  : String(row[col] ?? "-")}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function CalcSheet({ fund, metricId, fundMetrics, rawContext: _rawContext, benchmark }: CalcSheetProps) {
  if (metricId === "annualized_return") {
    const result = computeAnnualizedReturn(fund.monthly_returns)
    return (
      <div>
        <DataTable
          rows={result.rows}
          columns={["period", "Monthly Return", "1 + r", "Cumulative Product"]}
        />
        <p className="text-xs text-muted-foreground mt-2">{result.summary}</p>
      </div>
    )
  }

  if (metricId === "annualized_volatility") {
    const result = computeAnnualizedVolatility(fund.monthly_returns)
    return (
      <div>
        <DataTable
          rows={result.rows}
          columns={["period", "Monthly Return", "Deviation from Mean", "Squared Deviation"]}
        />
        <p className="text-xs text-muted-foreground mt-2">{result.summary}</p>
      </div>
    )
  }

  if (metricId === "sharpe_ratio") {
    const result = computeSharpeRatio(fundMetrics)
    return (
      <div className="text-sm whitespace-pre-line">{result.summary}</div>
    )
  }

  if (metricId === "max_drawdown") {
    const result = computeMaxDrawdown(fund.monthly_returns)
    return (
      <div>
        <DataTable
          rows={result.rows}
          columns={["period", "Monthly Return", "Cumulative Wealth", "Running Max", "Drawdown"]}
        />
        <p className="text-xs text-muted-foreground mt-2">{result.summary}</p>
      </div>
    )
  }

  if (metricId === "benchmark_correlation") {
    if (!benchmark) {
      return <p className="text-sm text-muted-foreground">No benchmark available for correlation calculation.</p>
    }
    const result = computeBenchmarkCorrelation(fund.monthly_returns, benchmark.monthly_returns)
    if (!result) {
      return <p className="text-sm text-muted-foreground">Insufficient overlapping periods (need at least 3).</p>
    }
    return (
      <div>
        <DataTable
          rows={result.rows}
          columns={["period", "Fund Return", "Benchmark Return"]}
        />
        <p className="text-xs text-muted-foreground mt-2">{result.summary}</p>
      </div>
    )
  }

  return <p className="text-sm text-muted-foreground">No calculation sheet available for {metricId}.</p>
}

export function SourceData({ fund, rawContext }: { fund: NormalizedFund; rawContext: RawFileContext | null }) {
  if (!rawContext || !fund.source_row_indices.length) return null

  const rowLookup: Record<number, (string | null)[]> = {}
  for (const row of rawContext.data_rows) {
    rowLookup[row.row_index] = row.cells
  }

  const sourceRows = fund.source_row_indices
    .sort((a, b) => a - b)
    .map((idx) => rowLookup[idx])
    .filter(Boolean)

  if (!sourceRows.length) return null

  return (
    <div className="mt-4">
      <p className="text-xs text-muted-foreground mb-1">Source data (original CSV rows)</p>
      <Table>
        <TableHeader>
          <TableRow>
            {rawContext.headers.map((h) => (
              <TableHead key={h} className="text-xs">{h}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sourceRows.map((cells, i) => (
            <TableRow key={i}>
              {cells!.map((cell, j) => (
                <TableCell key={j} className="text-xs">{cell ?? ""}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
