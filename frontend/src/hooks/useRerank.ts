import { useCallback, useRef } from "react"
import { rerankFunds } from "@/api/client"
import { useWizard, type PortfolioContext } from "@/context/WizardContext"
import { SAMPLE_PORTFOLIOS } from "@/data/sample-portfolios"

export function useRerank() {
  const {
    universe,
    mandate,
    groupRuns,
    warningResolutions,
    selectedPortfolioId,
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

    let portfolioCtx: PortfolioContext | null = null
    if (selectedPortfolioId) {
      const p = SAMPLE_PORTFOLIOS.find((sp) => sp.id === selectedPortfolioId)
      if (p) {
        portfolioCtx = {
          portfolio_name: p.name,
          strategy: p.strategy,
          aum: p.aum,
          holdings: p.holdings.map((h) => ({
            fund_name: h.fund_name,
            strategy: h.strategy,
            weight: h.weight,
          })),
          governance: p.governance as unknown as Record<string, unknown>,
        }
      }
    }

    try {
      const data = await rerankFunds(gr, universe, mandate, warningResolutions, portfolioCtx)
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
    selectedPortfolioId,
    setGroupRuns,
    setRerankLoading,
    setRerankError,
  ])

  return { rerank, loading: useWizard().rerankLoading, error: useWizard().rerankError }
}
