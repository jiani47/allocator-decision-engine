export interface PortfolioHolding {
  fund_name: string
  strategy: string
  weight: number
  annualized_return: number | null
  annualized_volatility: number | null
}

export interface PortfolioGovernance {
  max_drawdown_tolerance: number
  target_volatility: number
  min_liquidity_days: number
  min_sharpe_ratio: number | null
  min_annualized_return: number | null
  min_history_months: number
}

export interface PortfolioMetrics {
  annualized_return: number
  annualized_volatility: number
  sharpe_ratio: number
  max_drawdown: number
  ytd_return: number
}

export interface Portfolio {
  id: string
  name: string
  strategy: string
  aum: number
  targetReturn: number
  targetVolatility: number
  inceptionDate: string
  governance: PortfolioGovernance
  holdings: PortfolioHolding[]
  metrics: PortfolioMetrics
}

export const SAMPLE_PORTFOLIOS: Portfolio[] = [
  {
    id: "growth-alt-fof",
    name: "Growth Alternatives FoF",
    strategy: "Multi-Strategy FoF",
    aum: 250_000_000,
    targetReturn: 0.10,
    targetVolatility: 0.18,
    inceptionDate: "2019-03-01",
    governance: {
      max_drawdown_tolerance: -0.40,
      target_volatility: 0.30,
      min_liquidity_days: 90,
      min_sharpe_ratio: null,
      min_annualized_return: null,
      min_history_months: 6,
    },
    holdings: [
      { fund_name: "Apex Equity L/S", strategy: "Long/Short Equity", weight: 0.18, annualized_return: 0.112, annualized_volatility: 0.098 },
      { fund_name: "Meridian Global Macro", strategy: "Global Macro", weight: 0.18, annualized_return: 0.087, annualized_volatility: 0.072 },
      { fund_name: "Ironbridge Credit", strategy: "Credit", weight: 0.18, annualized_return: 0.062, annualized_volatility: 0.015 },
      { fund_name: "Quasar Market Neutral", strategy: "Market Neutral", weight: 0.16, annualized_return: 0.034, annualized_volatility: 0.009 },
      { fund_name: "Vortex CTA", strategy: "Managed Futures", weight: 0.16, annualized_return: 0.075, annualized_volatility: 0.085 },
      { fund_name: "Terrastone Real Assets", strategy: "Real Assets", weight: 0.14, annualized_return: 0.058, annualized_volatility: 0.032 },
    ],
    metrics: {
      annualized_return: 0.074,
      annualized_volatility: 0.061,
      sharpe_ratio: 1.21,
      max_drawdown: -0.089,
      ytd_return: 0.032,
    },
  },
  {
    id: "conservative-income-fof",
    name: "Conservative Income FoF",
    strategy: "Income-Oriented FoF",
    aum: 180_000_000,
    targetReturn: 0.06,
    targetVolatility: 0.08,
    inceptionDate: "2020-07-01",
    governance: {
      max_drawdown_tolerance: -0.25,
      target_volatility: 0.20,
      min_liquidity_days: 90,
      min_sharpe_ratio: null,
      min_annualized_return: null,
      min_history_months: 12,
    },
    holdings: [
      { fund_name: "Ironbridge Credit", strategy: "Credit", weight: 0.25, annualized_return: 0.062, annualized_volatility: 0.015 },
      { fund_name: "Quasar Market Neutral", strategy: "Market Neutral", weight: 0.25, annualized_return: 0.034, annualized_volatility: 0.009 },
      { fund_name: "Terrastone Real Assets", strategy: "Real Assets", weight: 0.20, annualized_return: 0.058, annualized_volatility: 0.032 },
      { fund_name: "Meridian Global Macro", strategy: "Global Macro", weight: 0.15, annualized_return: 0.087, annualized_volatility: 0.072 },
      { fund_name: "Vortex CTA", strategy: "Managed Futures", weight: 0.15, annualized_return: 0.075, annualized_volatility: 0.085 },
    ],
    metrics: {
      annualized_return: 0.056,
      annualized_volatility: 0.031,
      sharpe_ratio: 1.81,
      max_drawdown: -0.042,
      ytd_return: 0.021,
    },
  },
]
