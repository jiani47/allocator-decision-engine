import { useState, useCallback, useRef } from "react"
import { rankFunds } from "@/api/client"
import { useWizard } from "@/context/WizardContext"

export function useRank() {
  const { universe, mandate, benchmark, eligibility, setGroupRuns } = useWizard()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)

  const rank = useCallback(async () => {
    if (!universe || !mandate) return
    if (inFlight.current) return
    inFlight.current = true
    setLoading(true)
    setError(null)
    try {
      const data = await rankFunds(universe, mandate, benchmark, eligibility)
      setGroupRuns([data.group_run])
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ranking failed")
    } finally {
      setLoading(false)
      inFlight.current = false
    }
  }, [universe, mandate, benchmark, eligibility, setGroupRuns])

  return { rank, loading, error }
}
