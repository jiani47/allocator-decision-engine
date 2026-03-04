import { useCallback } from "react"
import { streamMemo } from "@/api/client"
import { useWizard } from "@/context/WizardContext"
import type {
  GroupRun,
  NormalizedUniverse,
  MandateConfig,
  WarningResolution,
} from "@/context/WizardContext"

export function useMemoStream() {
  const {
    memoStreaming: loading,
    streamingMemoText: memoText,
    streamingError: error,
    streamingProgressMessage: progressMessage,
    setMemoStreaming,
    appendMemoText,
    setStreamingMemoText,
    setStreamingProgressMessage,
    setStreamingError,
  } = useWizard()

  const generate = useCallback(
    async (
      groupRun: GroupRun,
      universe: NormalizedUniverse,
      mandate: MandateConfig,
      warningResolutions: WarningResolution[],
    ): Promise<GroupRun | null> => {
      setMemoStreaming(true)
      setStreamingError(null)
      setStreamingMemoText("")
      setStreamingProgressMessage("Starting memo generation...")

      try {
        let result: GroupRun | null = null
        for await (const event of streamMemo(
          groupRun,
          universe,
          mandate,
          warningResolutions,
        )) {
          switch (event.event) {
            case "progress":
              setStreamingProgressMessage(event.message)
              break
            case "text_delta":
              appendMemoText(event.text)
              break
            case "complete":
              result = event.group_run
              if (result.memo) {
                setStreamingMemoText(result.memo.memo_text)
              }
              break
            case "error":
              setStreamingError(event.message)
              break
          }
        }
        return result
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Memo generation failed"
        console.error("Memo stream error:", msg)
        setStreamingError(msg)
        return null
      } finally {
        setMemoStreaming(false)
        setStreamingProgressMessage("")
      }
    },
    [setMemoStreaming, setStreamingError, setStreamingMemoText, setStreamingProgressMessage, appendMemoText],
  )

  return { generate, memoText, loading, error, progressMessage }
}
