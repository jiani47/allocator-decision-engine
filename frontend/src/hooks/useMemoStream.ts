import { useState, useCallback } from "react"
import { streamMemo } from "@/api/client"
import type {
  GroupRun,
  NormalizedUniverse,
  MandateConfig,
  WarningResolution,
} from "@/context/WizardContext"

export function useMemoStream() {
  const [memoText, setMemoText] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progressMessage, setProgressMessage] = useState("")

  const generate = useCallback(
    async (
      groupRun: GroupRun,
      universe: NormalizedUniverse,
      mandate: MandateConfig,
      warningResolutions: WarningResolution[],
    ): Promise<GroupRun | null> => {
      setLoading(true)
      setError(null)
      setMemoText("")
      setProgressMessage("Starting memo generation...")

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
              setProgressMessage(event.message)
              break
            case "text_delta":
              setMemoText((prev) => prev + event.text)
              break
            case "complete":
              result = event.group_run
              if (result.memo) {
                setMemoText(result.memo.memo_text)
              }
              break
            case "error":
              setError(event.message)
              break
          }
        }
        return result
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Memo generation failed"
        console.error("Memo stream error:", msg)
        setError(msg)
        return null
      } finally {
        setLoading(false)
        setProgressMessage("")
      }
    },
    [],
  )

  return { generate, memoText, loading, error, progressMessage }
}
