import { useState, useMemo } from "react"
import { useWizard } from "@/context/WizardContext"
import { exportPdf } from "@/api/client"
import { PageHeader } from "@/components/PageHeader"
import { MarkdownRenderer } from "@/components/MarkdownRenderer"
import { ClaimsPanel } from "@/components/ClaimsPanel"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { buildDataAppendix } from "@/lib/data-appendix"
import { Download } from "lucide-react"

export function MemoExport() {
  const {
    groupRuns,
    mandate,
    universe,
    rawContext,
    eligibility,
    benchmarkMetrics,
    memoStreaming,
    streamingMemoText,
    streamingProgressMessage,
    setStep,
    resetFrom,
  } = useWizard()
  const [exporting, setExporting] = useState(false)

  const gr = groupRuns[0]
  const hasMemo = !!gr?.memo

  // Show streaming state if no final memo yet
  if (!hasMemo && !memoStreaming) {
    return (
      <div>
        <p className="text-muted-foreground mb-4">No memo available. Go back to generate one.</p>
        <Button variant="outline" onClick={() => { resetFrom(2); setStep(2) }}>Back</Button>
      </div>
    )
  }

  const fundLookup = universe
    ? Object.fromEntries(universe.funds.map((f) => [f.fund_name, f]))
    : {}
  const metricsLookup = gr?.fund_metrics
    ? Object.fromEntries(gr.fund_metrics.map((m) => [m.fund_name, m]))
    : {}

  const dataAppendix = useMemo(() => {
    if (!universe || !mandate || !gr) return ""
    return buildDataAppendix(universe, mandate, gr, eligibility, benchmarkMetrics)
  }, [universe, mandate, gr, eligibility, benchmarkMetrics])

  // Determine what to render: streaming text or final memo + appendix
  const memoContent = hasMemo
    ? gr.memo!.memo_text + "\n\n" + dataAppendix
    : streamingMemoText

  const handleExportPdf = async () => {
    setExporting(true)
    try {
      const blob = await exportPdf(memoContent)
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

      <div className="flex gap-0">
        {/* Memo content */}
        <div className="flex-1 min-w-0">
          <div className={memoStreaming && !hasMemo ? "border-l-2 border-blue-400 pl-4" : ""}>
            {memoStreaming && !hasMemo && !streamingMemoText && streamingProgressMessage && (
              <p className="text-sm text-muted-foreground mb-2">{streamingProgressMessage}</p>
            )}
            <MarkdownRenderer content={memoContent} className="mb-8" />
          </div>
        </div>

        {/* Claims side panel — only when memo is complete */}
        {hasMemo && gr.memo!.claims.length > 0 && (
          <ClaimsPanel
            claims={gr.memo!.claims}
            fundLookup={fundLookup}
            metricsLookup={metricsLookup}
            rawContext={rawContext}
            benchmark={gr.group.benchmark}
          />
        )}
      </div>

      {/* Navigation */}
      <Separator className="my-6" />
      <div className="flex justify-between items-center">
        <Button
          variant="outline"
          onClick={() => {
            resetFrom(2)
            setStep(2)
          }}
        >
          Back
        </Button>
        {hasMemo && (
          <Button onClick={handleExportPdf} disabled={exporting} className="gap-1.5">
            <Download className="h-4 w-4" />
            {exporting ? "Exporting..." : "Download PDF"}
          </Button>
        )}
      </div>
    </div>
  )
}
