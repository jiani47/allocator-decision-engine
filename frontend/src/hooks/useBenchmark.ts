import { useState, useCallback } from "react"
import { fetchBenchmark } from "@/api/client"
import { useWizard, type NormalizedUniverse } from "@/context/WizardContext"

export function useBenchmark() {
  const { setBenchmark, clearBenchmark } = useWizard()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(
    async (symbol: string, universe: NormalizedUniverse) => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchBenchmark(symbol, universe)
        setBenchmark(data.benchmark, data.benchmark_metrics)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Benchmark fetch failed")
        clearBenchmark()
      } finally {
        setLoading(false)
      }
    },
    [setBenchmark, clearBenchmark],
  )

  return { fetch, loading, error }
}
