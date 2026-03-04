import { useState, useCallback, useRef } from "react"
import { uploadFile, type UploadResponse } from "@/api/client"
import { useWizard, type MandateConfig } from "@/context/WizardContext"

const PROGRESS_STAGES = [
  { progress: 10, text: "Uploading file..." },
  { progress: 25, text: "Parsing spreadsheet..." },
  { progress: 45, text: "Extracting fund data..." },
  { progress: 65, text: "Computing metrics..." },
  { progress: 80, text: "Checking eligibility..." },
]

export function useUpload() {
  const { setUploadResult } = useWizard()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progressText, setProgressText] = useState("")
  const [uploadProgress, setUploadProgress] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const upload = useCallback(
    async (file: File, mandate: MandateConfig) => {
      setLoading(true)
      setError(null)
      setUploadProgress(0)
      setProgressText(PROGRESS_STAGES[0].text)

      let stageIndex = 0
      timerRef.current = setInterval(() => {
        stageIndex++
        if (stageIndex < PROGRESS_STAGES.length) {
          setUploadProgress(PROGRESS_STAGES[stageIndex].progress)
          setProgressText(PROGRESS_STAGES[stageIndex].text)
        }
      }, 1500)

      try {
        const data: UploadResponse = await uploadFile(file, mandate)
        clearTimer()
        setUploadProgress(100)
        setProgressText("")
        setUploadResult({
          rawContext: data.raw_context,
          llmResult: data.llm_result,
          llmValidationErrors: data.llm_validation_errors,
          universe: data.universe,
          fundMetrics: data.fund_metrics,
          eligibility: data.eligibility,
          fileName: file.name,
        })
      } catch (e) {
        clearTimer()
        setError(e instanceof Error ? e.message : "Upload failed")
        setProgressText("")
        setUploadProgress(0)
      } finally {
        setLoading(false)
      }
    },
    [setUploadResult, clearTimer],
  )

  return { upload, loading, error, progressText, uploadProgress }
}
