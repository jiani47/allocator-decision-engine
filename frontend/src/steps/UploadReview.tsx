import { useCallback, useRef, useState } from "react"
import { useWizard, type WarningResolution } from "@/context/WizardContext"
import { useUpload } from "@/hooks/useUpload"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function UploadReview() {
  const {
    mandate,
    universe,
    llmResult,
    llmValidationErrors,
    eligibility,
    dismissedWarnings,
    setDismissedWarnings,
    setWarningResolutions,
    setStep,
    resetFrom,
  } = useWizard()
  const { upload, loading, error, progressText } = useUpload()
  const fileRef = useRef<HTMLInputElement>(null)
  const [warningNotes, setWarningNotes] = useState<Record<number, string>>({})

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
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

  const handleContinue = () => {
    if (!universe) return
    const resolutions: WarningResolution[] = []
    universe.warnings.forEach((w, idx) => {
      const note = warningNotes[idx] ?? ""
      if (dismissedWarnings.has(idx) || note) {
        resolutions.push({
          category: w.category,
          fund_name: w.fund_name,
          original_message: w.message,
          action: dismissedWarnings.has(idx) ? "ignored" : "acknowledged",
          analyst_note: note,
        })
      }
    })
    setWarningResolutions(resolutions)
    setStep(2)
  }

  const eligibleNames = new Set(eligibility.filter((e) => e.eligible).map((e) => e.fund_name))
  const ineligible = eligibility.filter((e) => !e.eligible)

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Upload & Review</h2>

      {/* File upload */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground mb-4">
            Upload a CSV or Excel file with monthly return time series per fund.
          </p>
          <Input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileChange}
            disabled={loading}
          />
        </CardContent>
      </Card>

      {/* Loading */}
      {loading && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <Progress className="mb-2" />
            <p className="text-sm text-muted-foreground">{progressText}</p>
          </CardContent>
        </Card>
      )}

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
          {/* Eligible funds table */}
          <h3 className="text-lg font-medium mb-2">
            Eligible Funds ({eligibleNames.size})
          </h3>
          <Table className="mb-6">
            <TableHeader>
              <TableRow>
                <TableHead>Fund Name</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Months</TableHead>
                <TableHead>Date Range</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {universe.funds
                .filter((f) => eligibleNames.has(f.fund_name))
                .map((f) => (
                  <TableRow key={f.fund_name}>
                    <TableCell className="font-medium">{f.fund_name}</TableCell>
                    <TableCell>{f.strategy ?? "-"}</TableCell>
                    <TableCell>{f.month_count}</TableCell>
                    <TableCell>
                      {f.date_range_start} to {f.date_range_end}
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>

          {/* Warnings */}
          {universe.warnings.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-2">Warnings (Eligible Funds)</h3>
              <div className="space-y-2">
                {universe.warnings.map((w, idx) => {
                  if (w.fund_name && !eligibleNames.has(w.fund_name)) return null
                  const isDismissed = dismissedWarnings.has(idx)
                  return (
                    <Card key={idx} className={isDismissed ? "opacity-50" : ""}>
                      <CardContent className="py-3 flex items-start gap-3">
                        <Badge variant={isDismissed ? "secondary" : "outline"}>
                          {w.category}
                        </Badge>
                        <div className="flex-1">
                          <p className="text-sm">{w.message}</p>
                          {w.fund_name && (
                            <p className="text-xs text-muted-foreground">
                              Fund: {w.fund_name}
                            </p>
                          )}
                          {!isDismissed && (
                            <Input
                              className="mt-2"
                              placeholder="Add a note (optional)"
                              value={warningNotes[idx] ?? ""}
                              onChange={(e) =>
                                setWarningNotes((prev) => ({
                                  ...prev,
                                  [idx]: e.target.value,
                                }))
                              }
                            />
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            isDismissed ? handleRestore(idx) : handleDismiss(idx)
                          }
                        >
                          {isDismissed ? "Restore" : "Dismiss"}
                        </Button>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}

          {/* Ineligible funds */}
          {ineligible.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-2">
                Ineligible Funds ({ineligible.length})
              </h3>
              <p className="text-sm text-muted-foreground mb-2">
                These funds failed mandate constraints and will not be included in ranking.
              </p>
              <Accordion type="multiple">
                {ineligible.map((e) => (
                  <AccordionItem key={e.fund_name} value={e.fund_name}>
                    <AccordionTrigger>
                      {e.fund_name} — <Badge variant="destructive">INELIGIBLE</Badge>
                    </AccordionTrigger>
                    <AccordionContent>
                      <ul className="list-disc pl-4">
                        {e.failing_constraints.map((c, i) => (
                          <li key={i}>{c.explanation}</li>
                        ))}
                      </ul>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
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
