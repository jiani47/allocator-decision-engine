import { useCallback, useRef } from "react"
import { rerankFunds } from "@/api/client"
import { useWizard } from "@/context/WizardContext"

export function useRerank() {
  const {
    universe,
    mandate,
    groupRuns,
    warningResolutions,
    setGroupRuns,
    setRerankLoading,
    setRerankError,
  } = useWizard()

  const inFlight = useRef(false)

  const rerank = useCallback(async () => {
    const gr = groupRuns[0]
    if (!gr || !universe || !mandate) return
    if (inFlight.current) return
    inFlight.current = true
    setRerankLoading(true)
    setRerankError(null)
    try {
      const data = await rerankFunds(gr, universe, mandate, warningResolutions)
      setGroupRuns([{ ...gr, llm_rerank: data.llm_rerank }])
    } catch (e) {
      setRerankError(e instanceof Error ? e.message : "Re-ranking failed")
    } finally {
      setRerankLoading(false)
      inFlight.current = false
    }
  }, [
    groupRuns,
    universe,
    mandate,
    warningResolutions,
    setGroupRuns,
    setRerankLoading,
    setRerankError,
  ])

  return { rerank, loading: useWizard().rerankLoading, error: useWizard().rerankError }
}
