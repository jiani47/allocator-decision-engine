"""Calculation spreadsheet widget — step-by-step metric computation display."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app.core.schemas import (
    BenchmarkSeries,
    FundMetrics,
    MetricId,
    NormalizedFund,
    RawFileContext,
)


def render_calc_sheet(
    fund: NormalizedFund,
    metric_id: MetricId,
    fund_metrics: FundMetrics,
    raw_context: RawFileContext | None,
    benchmark: BenchmarkSeries | None = None,
) -> None:
    """Render a step-by-step calculation spreadsheet for a single metric."""
    returns = _sorted_returns(fund)
    r = np.array([v for _, v in returns])
    periods = [p for p, _ in returns]

    builders = {
        MetricId.ANNUALIZED_RETURN: _render_annualized_return,
        MetricId.ANNUALIZED_VOLATILITY: _render_annualized_volatility,
        MetricId.SHARPE_RATIO: _render_sharpe_ratio,
        MetricId.MAX_DRAWDOWN: _render_max_drawdown,
        MetricId.BENCHMARK_CORRELATION: _render_benchmark_correlation,
    }

    builder = builders.get(metric_id)
    if builder is None:
        st.write(f"No calculation sheet available for {metric_id.value}")
        return

    if metric_id == MetricId.BENCHMARK_CORRELATION:
        builder(periods, r, fund, benchmark)
    elif metric_id == MetricId.SHARPE_RATIO:
        builder(periods, r, fund_metrics)
    else:
        builder(periods, r)

    # Source data from uploaded CSV
    if raw_context and fund.source_row_indices:
        _render_source_data(fund, raw_context)


def _sorted_returns(fund: NormalizedFund) -> list[tuple[str, float]]:
    """Return (period, value) pairs sorted by period."""
    return sorted(fund.monthly_returns.items(), key=lambda x: x[0])


def _render_annualized_return(periods: list[str], r: np.ndarray) -> None:
    """Annualized return: (product(1 + r_i))^(12/n) - 1."""
    growth_factors = 1.0 + r
    cum_product = np.cumprod(growth_factors)

    df = pd.DataFrame({
        "Period": periods,
        "Monthly Return": r,
        "1 + r": growth_factors,
        "Cumulative Product": cum_product,
    })
    st.dataframe(
        df.style.format({
            "Monthly Return": "{:.6f}",
            "1 + r": "{:.6f}",
            "Cumulative Product": "{:.6f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    n = len(r)
    years = n / 12.0
    growth = cum_product[-1]
    ann_ret = growth ** (1.0 / years) - 1.0
    st.caption(
        f"n = {n}, years = {years:.2f}, "
        f"growth = {growth:.6f}, "
        f"ann. return = ({growth:.6f})^(1/{years:.2f}) - 1 = **{ann_ret:.4%}**"
    )


def _render_annualized_volatility(periods: list[str], r: np.ndarray) -> None:
    """Annualized volatility: std(r_i) * sqrt(12)."""
    mean_r = np.mean(r)
    deviations = r - mean_r
    sq_deviations = deviations ** 2

    df = pd.DataFrame({
        "Period": periods,
        "Monthly Return": r,
        "Deviation from Mean": deviations,
        "Squared Deviation": sq_deviations,
    })
    st.dataframe(
        df.style.format({
            "Monthly Return": "{:.6f}",
            "Deviation from Mean": "{:.6f}",
            "Squared Deviation": "{:.8f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    n = len(r)
    std_dev = np.std(r, ddof=1)
    ann_vol = std_dev * np.sqrt(12)
    st.caption(
        f"mean = {mean_r:.6f}, "
        f"variance = {np.sum(sq_deviations) / (n - 1):.8f}, "
        f"std = {std_dev:.6f}, "
        f"ann. vol = {std_dev:.6f} x sqrt(12) = **{ann_vol:.4%}**"
    )


def _render_sharpe_ratio(
    periods: list[str],
    r: np.ndarray,
    fund_metrics: FundMetrics,
) -> None:
    """Sharpe ratio: ann_return / ann_volatility (rf = 0)."""
    ann_ret_result = fund_metrics.get_result(MetricId.ANNUALIZED_RETURN)
    ann_vol_result = fund_metrics.get_result(MetricId.ANNUALIZED_VOLATILITY)
    sharpe_result = fund_metrics.get_result(MetricId.SHARPE_RATIO)

    ann_ret = ann_ret_result.value if ann_ret_result else 0.0
    ann_vol = ann_vol_result.value if ann_vol_result else 0.0
    sharpe = sharpe_result.value if sharpe_result else 0.0

    st.markdown(
        f"- Annualized Return = **{ann_ret:.4%}**\n"
        f"- Annualized Volatility = **{ann_vol:.4%}**\n"
        f"- Risk-Free Rate = **0%**\n"
        f"- Sharpe = {ann_ret:.4%} / {ann_vol:.4%} = **{sharpe:.4f}**"
    )


def _render_max_drawdown(periods: list[str], r: np.ndarray) -> None:
    """Max drawdown: min(cumulative_wealth / running_max - 1)."""
    cumulative = np.cumprod(1.0 + r)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative / running_max - 1.0

    df = pd.DataFrame({
        "Period": periods,
        "Monthly Return": r,
        "Cumulative Wealth": cumulative,
        "Running Max": running_max,
        "Drawdown": drawdowns,
    })
    st.dataframe(
        df.style.format({
            "Monthly Return": "{:.6f}",
            "Cumulative Wealth": "{:.6f}",
            "Running Max": "{:.6f}",
            "Drawdown": "{:.4%}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    worst_idx = int(np.argmin(drawdowns))
    st.caption(
        f"Max drawdown = **{drawdowns[worst_idx]:.4%}** "
        f"at {periods[worst_idx]}"
    )


def _render_benchmark_correlation(
    periods: list[str],
    r: np.ndarray,
    fund: NormalizedFund,
    benchmark: BenchmarkSeries | None,
) -> None:
    """Benchmark correlation: pearson_corr(fund, benchmark)."""
    if benchmark is None:
        st.write("No benchmark available for correlation calculation.")
        return

    # Align by overlapping periods
    bm_returns = benchmark.monthly_returns
    rows = []
    for period in periods:
        if period in bm_returns:
            rows.append({
                "Period": period,
                "Fund Return": fund.monthly_returns[period],
                "Benchmark Return": bm_returns[period],
            })

    if len(rows) < 3:
        st.write(f"Only {len(rows)} overlapping periods (need at least 3).")
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.format({
            "Fund Return": "{:.6f}",
            "Benchmark Return": "{:.6f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    fund_vals = df["Fund Return"].to_numpy()
    bench_vals = df["Benchmark Return"].to_numpy()
    corr = float(np.corrcoef(fund_vals, bench_vals)[0, 1])
    st.caption(
        f"N = {len(rows)} overlapping periods, "
        f"Pearson r = **{corr:.4f}**"
    )


def _render_source_data(
    fund: NormalizedFund,
    raw_context: RawFileContext,
) -> None:
    """Show the original CSV rows for this fund."""
    row_lookup = {row.row_index: row.cells for row in raw_context.data_rows}
    source_rows = []
    for idx in sorted(fund.source_row_indices):
        cells = row_lookup.get(idx)
        if cells:
            source_rows.append(cells)

    if not source_rows:
        return

    st.caption("Source data (original CSV rows)")
    df = pd.DataFrame(source_rows, columns=raw_context.headers)
    st.dataframe(df, use_container_width=True, hide_index=True)
