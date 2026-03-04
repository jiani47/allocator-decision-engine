import { useState, useCallback } from "react"
import { uploadFile, type UploadResponse } from "@/api/client"
import { useWizard, type MandateConfig } from "@/context/WizardContext"

export function useUpload() {
  const { setUploadResult } = useWizard()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progressText, setProgressText] = useState("")

  const upload = useCallback(
    async (file: File, mandate: MandateConfig) => {
      setLoading(true)
      setError(null)
      setProgressText("Uploading and processing file...")

      try {
        const data: UploadResponse = await uploadFile(file, mandate)
        setUploadResult({
          rawContext: data.raw_context,
          llmResult: data.llm_result,
          llmValidationErrors: data.llm_validation_errors,
          universe: data.universe,
          fundMetrics: data.fund_metrics,
          eligibility: data.eligibility,
          fileName: file.name,
        })
        setProgressText("")
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed")
        setProgressText("")
      } finally {
        setLoading(false)
      }
    },
    [setUploadResult],
  )

  return { upload, loading, error, progressText }
}
