/**
 * Typed API client wrapping fetch calls to the FastAPI backend.
 * All endpoints proxy through Vite's dev server (/api → localhost:8000).
 */

import type {
  MandateConfig,
  NormalizedUniverse,
  BenchmarkSeries,
  FundEligibility,
  FundMetrics,
  GroupRun,
  LLMReRankResult,
  PortfolioContext,
  WarningResolution,
  RawFileContext,
  LLMIngestionResult,
} from "@/context/WizardContext"

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface UploadResponse {
  raw_context: RawFileContext
  llm_result: LLMIngestionResult
  llm_validation_errors: string[]
  universe: NormalizedUniverse
  fund_metrics: FundMetrics[]
  eligibility: FundEligibility[]
}

export interface BenchmarkResponse {
  benchmark: BenchmarkSeries
  benchmark_metrics: Record<string, number>
}

export interface RankResponse {
  group_run: GroupRun
}

export interface ReRankResponse {
  llm_rerank: LLMReRankResult
}

// ---------------------------------------------------------------------------
// SSE event types
// ---------------------------------------------------------------------------

export type MemoSSEEvent =
  | { event: "progress"; message: string }
  | { event: "text_delta"; text: string }
  | { event: "complete"; group_run: GroupRun }
  | { event: "error"; message: string }

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const text = await resp.text()
    throw new ApiError(resp.status, text)
  }
  return resp.json() as Promise<T>
}

export async function uploadFile(
  file: File,
  mandate: MandateConfig,
): Promise<UploadResponse> {
  const form = new FormData()
  form.append("file", file)
  form.append("mandate", JSON.stringify(mandate))
  const resp = await fetch("/api/upload", { method: "POST", body: form })
  return handleResponse<UploadResponse>(resp)
}

export async function fetchBenchmark(
  symbol: string,
  universe: NormalizedUniverse,
): Promise<BenchmarkResponse> {
  const resp = await fetch("/api/benchmark", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, universe }),
  })
  return handleResponse<BenchmarkResponse>(resp)
}

export async function rankFunds(
  universe: NormalizedUniverse,
  mandate: MandateConfig,
  benchmark: BenchmarkSeries | null,
  eligibility: FundEligibility[],
): Promise<RankResponse> {
  const resp = await fetch("/api/rank", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      universe,
      mandate,
      benchmark,
      eligibility,
      use_existing_portfolio: (mandate.weights.portfolio_diversification ?? 0) > 0,
    }),
  })
  return handleResponse<RankResponse>(resp)
}

export async function rerankFunds(
  groupRun: GroupRun,
  universe: NormalizedUniverse,
  mandate: MandateConfig,
  warningResolutions: WarningResolution[],
  portfolioContext: PortfolioContext | null = null,
): Promise<ReRankResponse> {
  const resp = await fetch("/api/rerank", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      group_run: groupRun,
      universe,
      mandate,
      warning_resolutions: warningResolutions,
      portfolio_context: portfolioContext,
    }),
  })
  return handleResponse<ReRankResponse>(resp)
}

export async function* streamMemo(
  groupRun: GroupRun,
  universe: NormalizedUniverse,
  mandate: MandateConfig,
  warningResolutions: WarningResolution[],
  useAiRanking: boolean = false,
  portfolioContext: PortfolioContext | null = null,
): AsyncGenerator<MemoSSEEvent> {
  const resp = await fetch("/api/memo/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      group_run: groupRun,
      universe,
      mandate,
      warning_resolutions: warningResolutions,
      use_ai_ranking: useAiRanking,
      portfolio_context: portfolioContext,
    }),
  })

  if (!resp.ok) {
    const text = await resp.text()
    throw new ApiError(resp.status, text)
  }

  const reader = resp.body?.getReader()
  if (!reader) throw new Error("No response body")

  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n\n")
    buffer = lines.pop() ?? ""

    for (const chunk of lines) {
      const line = chunk.trim()
      if (line.startsWith("data: ")) {
        const json = line.slice(6)
        yield JSON.parse(json) as MemoSSEEvent
      }
    }
  }
}

export async function exportPdf(markdown: string): Promise<Blob> {
  const resp = await fetch("/api/export/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown }),
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new ApiError(resp.status, text)
  }
  return resp.blob()
}
