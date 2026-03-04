import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from "react"

// ---------------------------------------------------------------------------
// Domain types (mirrors core/schemas.py)
// ---------------------------------------------------------------------------

export type MetricId =
  | "annualized_return"
  | "annualized_volatility"
  | "sharpe_ratio"
  | "max_drawdown"
  | "benchmark_correlation"

export interface RawRow {
  row_index: number
  cells: (string | null)[]
  classification: string
}

export interface RawFileContext {
  filename: string
  file_hash: string
  headers: string[]
  header_row_index: number
  data_rows: RawRow[]
  aggregated_rows: RawRow[]
  empty_rows: RawRow[]
  total_rows: number
}

export interface ValidationWarning {
  category: string
  fund_name: string | null
  message: string
  row_indices: number[]
  severity: string
}

export interface NormalizedFund {
  fund_name: string
  strategy: string | null
  liquidity_days: number | null
  management_fee: number | null
  performance_fee: number | null
  monthly_returns: Record<string, number>
  date_range_start: string
  date_range_end: string
  month_count: number
  source_row_indices: number[]
}

export interface NormalizedUniverse {
  funds: NormalizedFund[]
  warnings: ValidationWarning[]
  source_file_hash: string
  column_mapping: unknown
  normalization_timestamp: string
  ingestion_method: string
  raw_context: RawFileContext | null
  llm_interpretation_notes: string | null
}

export interface MetricResult {
  metric_id: MetricId
  value: number
  period_start: string
  period_end: string
  formula_text: string
  dependencies: MetricId[]
}

export interface FundMetrics {
  fund_name: string
  metric_results: MetricResult[]
  date_range_start: string
  date_range_end: string
  month_count: number
  insufficient_history: boolean
}

export interface BenchmarkSeries {
  symbol: string
  monthly_returns: Record<string, number>
  source: string
}

export interface ConstraintResult {
  constraint_name: string
  passed: boolean
  explanation: string
  threshold: number | null
  actual_value: number | null
}

export interface MandateConfig {
  name: string
  min_liquidity_days: number | null
  max_drawdown_tolerance: number | null
  target_volatility: number | null
  min_annualized_return: number | null
  min_sharpe_ratio: number | null
  min_history_months: number
  weights: Record<MetricId, number>
  shortlist_top_k: number
  strategy_include: string[]
  strategy_exclude: string[]
}

export interface ScoreComponent {
  metric_id: MetricId
  raw_value: number
  normalized_value: number
  weight: number
  weighted_contribution: number
}

export interface ScoredFund {
  fund_name: string
  metric_values: Record<MetricId, number>
  score_breakdown: ScoreComponent[]
  composite_score: number
  rank: number
  constraint_results: ConstraintResult[]
  all_constraints_passed: boolean
}

export interface RunCandidate {
  fund_name: string
  included: boolean
  exclusion_reason: string | null
}

export interface FundEligibility {
  fund_name: string
  eligible: boolean
  failing_constraints: ConstraintResult[]
}

export interface Claim {
  claim_id: string
  claim_text: string
  referenced_metric_ids: MetricId[]
  referenced_fund_names: string[]
}

export interface MemoOutput {
  memo_text: string
  claims: Claim[]
}

export interface FactPack {
  run_id: string
  shortlist: ScoredFund[]
  universe_summary: Record<string, unknown>
  mandate: MandateConfig
  benchmark_symbol: string
  analyst_notes: WarningResolution[]
  instructions: Record<string, unknown>
  group_name: string
  group_rationale: string
}

export interface FundGroup {
  group_name: string
  group_id: string
  fund_names: string[]
  benchmark_symbol: string | null
  benchmark: BenchmarkSeries | null
  grouping_rationale: string
}

export interface GroupRun {
  group: FundGroup
  fund_metrics: FundMetrics[]
  ranked_shortlist: ScoredFund[]
  run_candidates: RunCandidate[]
  memo: MemoOutput | null
  fact_pack: FactPack | null
}

export interface LLMExtractedFund {
  fund_name: string
  strategy: string | null
  liquidity_days: number | null
  management_fee: number | null
  performance_fee: number | null
  monthly_returns: Record<string, number>
  source_row_indices: number[]
}

export interface LLMIngestionResult {
  funds: LLMExtractedFund[]
  interpretation_notes: string
  ambiguities: string[]
}

export interface WarningResolution {
  category: string
  fund_name: string | null
  original_message: string
  action: string
  analyst_note: string
}

// ---------------------------------------------------------------------------
// Wizard state
// ---------------------------------------------------------------------------

export const STEPS = [
  "Mandate",
  "Upload & Review",
  "Metrics & Ranking",
  "Memo & Export",
] as const

interface WizardState {
  allocationActive: boolean
  step: number
  highestStepReached: number
  mandate: MandateConfig | null
  uploadedFileName: string | null

  rawContext: RawFileContext | null
  llmResult: LLMIngestionResult | null
  llmValidationErrors: string[]
  universe: NormalizedUniverse | null
  fundMetrics: FundMetrics[]
  eligibility: FundEligibility[]

  dismissedWarnings: Set<number>
  warningResolutions: WarningResolution[]

  benchmark: BenchmarkSeries | null
  benchmarkSymbol: string
  benchmarkMetrics: Record<string, number> | null
  groupRuns: GroupRun[]

  selectedClaimIdx: number
}

interface WizardActions {
  setStep: (step: number) => void
  goForward: () => void
  goBack: () => void
  setMandate: (mandate: MandateConfig) => void
  setUploadResult: (data: {
    rawContext: RawFileContext
    llmResult: LLMIngestionResult
    llmValidationErrors: string[]
    universe: NormalizedUniverse
    fundMetrics: FundMetrics[]
    eligibility: FundEligibility[]
    fileName: string
  }) => void
  setBenchmark: (benchmark: BenchmarkSeries, metrics: Record<string, number>) => void
  setBenchmarkSymbol: (symbol: string) => void
  clearBenchmark: () => void
  setGroupRuns: (runs: GroupRun[]) => void
  setDismissedWarnings: (warnings: Set<number>) => void
  setWarningResolutions: (resolutions: WarningResolution[]) => void
  setSelectedClaimIdx: (idx: number) => void
  resetFrom: (step: number) => void
  canNavigateTo: (targetStep: number) => boolean
  startAllocation: () => void
  cancelAllocation: () => void
}

type WizardContextType = WizardState & WizardActions

const WizardContext = createContext<WizardContextType | null>(null)

const DEFAULT_MANDATE: MandateConfig = {
  name: "Untitled Mandate",
  min_liquidity_days: null,
  max_drawdown_tolerance: null,
  target_volatility: null,
  min_annualized_return: null,
  min_sharpe_ratio: null,
  min_history_months: 12,
  weights: {
    annualized_return: 0.4,
    annualized_volatility: 0,
    sharpe_ratio: 0.4,
    max_drawdown: 0.2,
    benchmark_correlation: 0,
  },
  shortlist_top_k: 3,
  strategy_include: [],
  strategy_exclude: [],
}

function initialState(): WizardState {
  return {
    allocationActive: false,
    step: 0,
    highestStepReached: 0,
    mandate: null,
    uploadedFileName: null,
    rawContext: null,
    llmResult: null,
    llmValidationErrors: [],
    universe: null,
    fundMetrics: [],
    eligibility: [],
    dismissedWarnings: new Set(),
    warningResolutions: [],
    benchmark: null,
    benchmarkSymbol: "SPY",
    benchmarkMetrics: null,
    groupRuns: [],
    selectedClaimIdx: 0,
  }
}

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WizardState>(initialState)

  const resetFrom = useCallback((step: number) => {
    setState((prev) => {
      const next = { ...prev }
      if (step <= 0) {
        return { ...initialState(), step: 0 }
      }
      if (step <= 1) {
        next.benchmark = null
        next.benchmarkMetrics = null
        next.groupRuns = []
        next.warningResolutions = []
      }
      if (step <= 2) {
        next.groupRuns = next.groupRuns.map((gr) => ({
          ...gr,
          memo: null,
          fact_pack: null,
        }))
        next.selectedClaimIdx = 0
      }
      return next
    })
  }, [])

  const setStep = useCallback(
    (step: number) => setState((prev) => ({
      ...prev,
      step,
      highestStepReached: Math.max(prev.highestStepReached, step),
    })),
    [],
  )
  const goForward = useCallback(
    () => setState((prev) => {
      const newStep = Math.min(prev.step + 1, STEPS.length - 1)
      return {
        ...prev,
        step: newStep,
        highestStepReached: Math.max(prev.highestStepReached, newStep),
      }
    }),
    [],
  )
  const goBack = useCallback(() => {
    setState((prev) => {
      const newStep = Math.max(prev.step - 1, 0)
      return { ...prev, step: newStep }
    })
    // resetFrom uses functional setState so reading prev.step inside is fine
    setState((prev) => {
      const step = prev.step
      const next = { ...prev }
      if (step <= 0) return { ...initialState(), step: 0 }
      if (step <= 1) {
        next.benchmark = null
        next.benchmarkMetrics = null
        next.groupRuns = []
        next.warningResolutions = []
      }
      if (step <= 2) {
        next.groupRuns = next.groupRuns.map((gr) => ({
          ...gr,
          memo: null,
          fact_pack: null,
        }))
        next.selectedClaimIdx = 0
      }
      return next
    })
  }, [])
  const setMandate = useCallback(
    (mandate: MandateConfig) => setState((prev) => ({ ...prev, mandate })),
    [],
  )
  const setUploadResult = useCallback(
    (data: {
      rawContext: RawFileContext
      llmResult: LLMIngestionResult
      llmValidationErrors: string[]
      universe: NormalizedUniverse
      fundMetrics: FundMetrics[]
      eligibility: FundEligibility[]
      fileName: string
    }) =>
      setState((prev) => ({
        ...prev,
        rawContext: data.rawContext,
        llmResult: data.llmResult,
        llmValidationErrors: data.llmValidationErrors,
        universe: data.universe,
        fundMetrics: data.fundMetrics,
        eligibility: data.eligibility,
        uploadedFileName: data.fileName,
      })),
    [],
  )
  const setBenchmark = useCallback(
    (benchmark: BenchmarkSeries, metrics: Record<string, number>) =>
      setState((prev) => ({
        ...prev,
        benchmark,
        benchmarkMetrics: metrics,
        benchmarkSymbol: benchmark.symbol,
      })),
    [],
  )
  const setBenchmarkSymbol = useCallback(
    (symbol: string) => setState((prev) => ({ ...prev, benchmarkSymbol: symbol })),
    [],
  )
  const clearBenchmark = useCallback(
    () =>
      setState((prev) => ({
        ...prev,
        benchmark: null,
        benchmarkMetrics: null,
        groupRuns: [],
      })),
    [],
  )
  const setGroupRuns = useCallback(
    (runs: GroupRun[]) => setState((prev) => ({ ...prev, groupRuns: runs })),
    [],
  )
  const setDismissedWarnings = useCallback(
    (warnings: Set<number>) => setState((prev) => ({ ...prev, dismissedWarnings: warnings })),
    [],
  )
  const setWarningResolutions = useCallback(
    (resolutions: WarningResolution[]) =>
      setState((prev) => ({ ...prev, warningResolutions: resolutions })),
    [],
  )
  const setSelectedClaimIdx = useCallback(
    (idx: number) => setState((prev) => ({ ...prev, selectedClaimIdx: idx })),
    [],
  )
  const canNavigateTo = useCallback(
    (targetStep: number) => targetStep <= state.highestStepReached,
    [state.highestStepReached],
  )
  const startAllocation = useCallback(
    () => setState(() => ({ ...initialState(), allocationActive: true })),
    [],
  )
  const cancelAllocation = useCallback(
    () => setState(initialState),
    [],
  )

  const value = useMemo<WizardContextType>(
    () => ({
      ...state,
      setStep,
      goForward,
      goBack,
      setMandate,
      setUploadResult,
      setBenchmark,
      setBenchmarkSymbol,
      clearBenchmark,
      setGroupRuns,
      setDismissedWarnings,
      setWarningResolutions,
      setSelectedClaimIdx,
      resetFrom,
      canNavigateTo,
      startAllocation,
      cancelAllocation,
    }),
    [
      state,
      setStep,
      goForward,
      goBack,
      setMandate,
      setUploadResult,
      setBenchmark,
      setBenchmarkSymbol,
      clearBenchmark,
      setGroupRuns,
      setDismissedWarnings,
      setWarningResolutions,
      setSelectedClaimIdx,
      resetFrom,
      canNavigateTo,
      startAllocation,
      cancelAllocation,
    ],
  )

  return (
    <WizardContext.Provider value={value}>
      {children}
    </WizardContext.Provider>
  )
}

export function useWizard(): WizardContextType {
  const ctx = useContext(WizardContext)
  if (!ctx) throw new Error("useWizard must be used within WizardProvider")
  return ctx
}

export { DEFAULT_MANDATE }
