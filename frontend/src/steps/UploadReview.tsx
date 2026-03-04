import { useCallback, useState } from "react"
import { useWizard, type WarningResolution } from "@/context/WizardContext"
import { useUpload } from "@/hooks/useUpload"
import { PageHeader } from "@/components/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { FileDropzone } from "@/components/ui/file-dropzone"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { AlertTriangle, FileSpreadsheet, Upload } from "lucide-react"

function formatCategory(s: string): string {
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function UploadReview() {
  const {
    mandate,
    universe,
    llmResult,
    llmValidationErrors,
    eligibility,
    uploadedFileName,
    dismissedWarnings,
    setDismissedWarnings,
    setWarningResolutions,
    setStep,
    resetFrom,
  } = useWizard()
  const { upload, loading, error, progressText, uploadProgress } = useUpload()
  const [dropzoneExpanded, setDropzoneExpanded] = useState(false)
  const [showIneligible, setShowIneligible] = useState(false)
  const [excludedFunds, setExcludedFunds] = useState<Set<string>>(new Set())

  const handleDrop = useCallback(
    (files: File[]) => {
      const file = files[0]
      if (file && mandate) {
        upload(file, mandate)
      }
    },
    [mandate, upload],
  )

  const handleDismiss = (idx: number) => {
    const next = new Set(dismissedWarnings)
    next.add(idx)
    setDismissedWarnings(next)
  }

  const handleRestore = (idx: number) => {
    const next = new Set(dismissedWarnings)
    next.delete(idx)
    setDismissedWarnings(next)
  }

  const handleExcludeFund = (fundName: string) => {
    setExcludedFunds((prev) => new Set(prev).add(fundName))
  }

  const handleContinue = () => {
    if (!universe) return
    const resolutions: WarningResolution[] = []
    universe.warnings.forEach((w, idx) => {
      if (dismissedWarnings.has(idx)) {
        resolutions.push({
          category: w.category,
          fund_name: w.fund_name,
          original_message: w.message,
          action: "ignored",
          analyst_note: "",
        })
      } else if (w.fund_name && excludedFunds.has(w.fund_name)) {
        resolutions.push({
          category: w.category,
          fund_name: w.fund_name,
          original_message: w.message,
          action: "acknowledged",
          analyst_note: "Fund excluded by analyst",
        })
      }
    })
    setWarningResolutions(resolutions)
    setStep(2)
  }

  const eligibleNames = new Set(
    eligibility
      .filter((e) => e.eligible)
      .map((e) => e.fund_name)
      .filter((name) => !excludedFunds.has(name)),
  )
  const ineligibleMap = new Map(
    eligibility.filter((e) => !e.eligible).map((e) => [e.fund_name, e]),
  )
  const ineligibleCount = ineligibleMap.size + excludedFunds.size

  const showDropzone = !universe || dropzoneExpanded || loading

  const visibleFunds = universe
    ? universe.funds.filter((f) => {
        const isEligible = eligibleNames.has(f.fund_name)
        const isExcluded = excludedFunds.has(f.fund_name)
        if (isEligible && !isExcluded) return true
        if (showIneligible) return true
        return false
      })
    : []

  return (
    <div>
      <PageHeader
        title="Upload Funds"
        description="Upload your CSV file and review the parsed fund universe."
      />

      {/* File upload — collapsed or expanded */}
      <div className="mb-6">
        {showDropzone ? (
          <>
            <FileDropzone
              onDrop={handleDrop}
              isUploading={loading}
              uploadProgress={uploadProgress}
              accept={{
                "text/csv": [".csv"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                "application/vnd.ms-excel": [".xls"],
              }}
              hint="Supports CSV, XLS, and XLSX files"
            />
            {loading && progressText && (
              <p className="mt-2 text-sm text-muted-foreground">{progressText}</p>
            )}
          </>
        ) : (
          <div className="flex items-center gap-3 rounded-md border px-4 py-3">
            <FileSpreadsheet className="h-5 w-5 text-muted-foreground" />
            <span className="flex-1 text-sm font-medium">{uploadedFileName ?? "Uploaded file"}</span>
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5"
              onClick={() => setDropzoneExpanded(true)}
            >
              <Upload className="h-3.5 w-3.5" />
              Upload more
            </Button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* LLM validation errors */}
      {llmValidationErrors.length > 0 && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>
            <ul className="list-disc pl-4">
              {llmValidationErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {universe && llmResult && (
        <>
          {/* Funds table header + ineligible toggle */}
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-medium">
              Funds ({eligibleNames.size}{ineligibleCount > 0 ? ` of ${universe.funds.length}` : ""})
            </h3>
            {ineligibleCount > 0 && (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  checked={showIneligible}
                  onCheckedChange={(v) => setShowIneligible(v === true)}
                />
                Show ineligible ({ineligibleCount})
              </label>
            )}
          </div>

          <div className="mb-6 rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fund Name</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Months</TableHead>
                  <TableHead>Date Range</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleFunds.map((f) => {
                  const isIneligible = ineligibleMap.has(f.fund_name)
                  const isExcluded = excludedFunds.has(f.fund_name)
                  const ineligibleEntry = ineligibleMap.get(f.fund_name)
                  return (
                    <TableRow key={f.fund_name} className={isIneligible || isExcluded ? "opacity-60" : ""}>
                      <TableCell className="font-medium">{f.fund_name}</TableCell>
                      <TableCell>{f.strategy ?? "-"}</TableCell>
                      <TableCell>{f.month_count}</TableCell>
                      <TableCell>
                        {f.date_range_start} to {f.date_range_end}
                      </TableCell>
                      <TableCell>
                        {isExcluded ? (
                          <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">Excluded</Badge>
                        ) : isIneligible ? (
                          <div>
                            <Badge variant="destructive">Ineligible</Badge>
                            {ineligibleEntry && (
                              <ul className="mt-1 text-xs text-muted-foreground list-disc pl-4">
                                {ineligibleEntry.failing_constraints.map((c, i) => (
                                  <li key={i}>{c.explanation}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ) : (
                          <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Eligible</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>

          {/* Warnings */}
          {universe.warnings.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-2 flex items-center gap-2 text-lg font-medium">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                Warnings
              </h3>
              <div className="space-y-2">
                {universe.warnings.map((w, idx) => {
                  const isDismissed = dismissedWarnings.has(idx)
                  const isFundExcluded = w.fund_name ? excludedFunds.has(w.fund_name) : false
                  if (isFundExcluded) return null
                  return (
                    <Card key={idx} className={isDismissed ? "opacity-50" : ""}>
                      <CardContent className="py-3">
                        <div className="flex items-start gap-2 flex-wrap">
                          {w.fund_name && (
                            <Badge>{w.fund_name}</Badge>
                          )}
                          <Badge variant={isDismissed ? "secondary" : "outline"}>
                            {formatCategory(w.category)}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm">{w.message}</p>
                        <div className="mt-3 flex justify-end gap-2">
                          {!isDismissed && w.fund_name && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-destructive"
                              onClick={() => handleExcludeFund(w.fund_name!)}
                            >
                              Exclude Fund
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              isDismissed ? handleRestore(idx) : handleDismiss(idx)
                            }
                          >
                            {isDismissed ? "Restore" : "Dismiss"}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => {
            resetFrom(0)
            setStep(0)
          }}
        >
          Back
        </Button>
        {universe && (
          <Button onClick={handleContinue}>Continue</Button>
        )}
      </div>
    </div>
  )
}
