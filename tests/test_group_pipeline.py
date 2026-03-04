"""Tests for per-group ranking and memo pipeline."""

from __future__ import annotations

from datetime import datetime

from app.core.schemas import (
    FundGroup,
    GroupRun,
    MandateConfig,
    MetricId,
    NormalizedFund,
    NormalizedUniverse,
    ValidationWarning,
)
from app.services import build_group_universe, step_rank_group


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fund(name: str, strategy: str, base_return: float) -> NormalizedFund:
    """Create a test fund with 24 months of synthetic returns."""
    returns = {}
    for y in (2022, 2023):
        for m in range(1, 13):
            # Vary returns slightly per month so metrics differ between funds
            returns[f"{y}-{m:02d}"] = base_return + 0.001 * (m % 5 - 2)
    return NormalizedFund(
        fund_name=name,
        strategy=strategy,
        liquidity_days=45,
        monthly_returns=returns,
        date_range_start="2022-01",
        date_range_end="2023-12",
        month_count=24,
    )


def _make_universe(funds: list[NormalizedFund]) -> NormalizedUniverse:
    """Build a NormalizedUniverse from a list of funds."""
    return NormalizedUniverse(
        funds=funds,
        warnings=[
            ValidationWarning(
                category="outlier",
                fund_name="Alpha Equity",
                message="Outlier return in 2022-03",
            ),
            ValidationWarning(
                category="missing_month",
                fund_name=None,
                message="Global: some months may be missing",
            ),
        ],
        source_file_hash="testhash123",
        normalization_timestamp=datetime.utcnow().isoformat(),
        ingestion_method="deterministic",
    )


def _make_groups() -> tuple[FundGroup, FundGroup]:
    """Create two groups splitting the 4-fund universe."""
    group_equity = FundGroup(
        group_name="Equity Strategies",
        group_id="group_1",
        fund_names=["Alpha Equity", "Beta Equity"],
        benchmark_symbol=None,
        grouping_rationale="Both are equity strategies.",
    )
    group_macro = FundGroup(
        group_name="Macro Strategies",
        group_id="group_2",
        fund_names=["Gamma Macro", "Delta Macro"],
        benchmark_symbol=None,
        grouping_rationale="Both are macro strategies.",
    )
    return group_equity, group_macro


# ---------------------------------------------------------------------------
# Tests: build_group_universe
# ---------------------------------------------------------------------------


class TestBuildGroupUniverse:
    def test_filters_to_group_funds(self):
        """Sub-universe should only contain the group's funds."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
            _make_fund("Gamma Macro", "Macro", 0.012),
            _make_fund("Delta Macro", "Macro", 0.006),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()

        sub = build_group_universe(universe, group_eq)

        assert len(sub.funds) == 2
        names = {f.fund_name for f in sub.funds}
        assert names == {"Alpha Equity", "Beta Equity"}

    def test_preserves_global_warnings(self):
        """Warnings with fund_name=None should be included in sub-universe."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
            _make_fund("Gamma Macro", "Macro", 0.012),
            _make_fund("Delta Macro", "Macro", 0.006),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()

        sub = build_group_universe(universe, group_eq)

        # Should include: the Alpha Equity warning + the global (fund_name=None) warning
        assert len(sub.warnings) == 2
        categories = {w.category for w in sub.warnings}
        assert "outlier" in categories
        assert "missing_month" in categories

    def test_excludes_other_group_warnings(self):
        """Warnings for funds not in the group should be excluded."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Gamma Macro", "Macro", 0.012),
        ]
        universe = NormalizedUniverse(
            funds=funds,
            warnings=[
                ValidationWarning(
                    category="outlier",
                    fund_name="Gamma Macro",
                    message="Outlier in Gamma",
                ),
            ],
            source_file_hash="testhash",
            normalization_timestamp=datetime.utcnow().isoformat(),
        )
        group = FundGroup(
            group_name="Equity Only",
            group_id="g1",
            fund_names=["Alpha Equity"],
        )

        sub = build_group_universe(universe, group)

        assert len(sub.warnings) == 0

    def test_preserves_metadata(self):
        """Sub-universe should carry over source_file_hash, ingestion_method, etc."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()

        sub = build_group_universe(universe, group_eq)

        assert sub.source_file_hash == universe.source_file_hash
        assert sub.normalization_timestamp == universe.normalization_timestamp
        assert sub.ingestion_method == universe.ingestion_method


# ---------------------------------------------------------------------------
# Tests: step_rank_group
# ---------------------------------------------------------------------------


class TestStepRankGroup:
    def test_ranks_within_group(self):
        """Each group should have its own independent ranking."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
            _make_fund("Gamma Macro", "Macro", 0.012),
            _make_fund("Delta Macro", "Macro", 0.006),
        ]
        universe = _make_universe(funds)
        group_eq, group_macro = _make_groups()
        mandate = MandateConfig()

        run_eq = step_rank_group(universe, group_eq, mandate)
        run_macro = step_rank_group(universe, group_macro, mandate)

        # Each group should have 2 funds ranked
        assert isinstance(run_eq, GroupRun)
        assert isinstance(run_macro, GroupRun)
        assert len(run_eq.ranked_shortlist) == 2
        assert len(run_macro.ranked_shortlist) == 2

        # Ranks should be 1, 2 within each group
        eq_ranks = sorted(sf.rank for sf in run_eq.ranked_shortlist)
        macro_ranks = sorted(sf.rank for sf in run_macro.ranked_shortlist)
        assert eq_ranks == [1, 2]
        assert macro_ranks == [1, 2]

    def test_fund_metrics_match_group(self):
        """Fund metrics should only be computed for funds in the group."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
            _make_fund("Gamma Macro", "Macro", 0.012),
            _make_fund("Delta Macro", "Macro", 0.006),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()
        mandate = MandateConfig()

        run_eq = step_rank_group(universe, group_eq, mandate)

        metric_names = {fm.fund_name for fm in run_eq.fund_metrics}
        assert metric_names == {"Alpha Equity", "Beta Equity"}

    def test_run_candidates_match_group(self):
        """Run candidates should reflect only the group's funds."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
            _make_fund("Gamma Macro", "Macro", 0.012),
            _make_fund("Delta Macro", "Macro", 0.006),
        ]
        universe = _make_universe(funds)
        _, group_macro = _make_groups()
        mandate = MandateConfig()

        run_macro = step_rank_group(universe, group_macro, mandate)

        candidate_names = {rc.fund_name for rc in run_macro.run_candidates}
        assert candidate_names == {"Gamma Macro", "Delta Macro"}

    def test_group_preserves_reference(self):
        """The GroupRun should reference the original FundGroup."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()
        mandate = MandateConfig()

        run_eq = step_rank_group(universe, group_eq, mandate)

        assert run_eq.group.group_name == "Equity Strategies"
        assert run_eq.group.group_id == "group_1"

    def test_no_benchmark_by_default(self):
        """When benchmark_symbol is None, benchmark should not be fetched."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()
        mandate = MandateConfig()

        run_eq = step_rank_group(universe, group_eq, mandate)

        # benchmark should remain None
        assert run_eq.group.benchmark is None

    def test_memo_initially_none(self):
        """GroupRun from step_rank_group should not have a memo yet."""
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.01),
            _make_fund("Beta Equity", "Equity", 0.008),
        ]
        universe = _make_universe(funds)
        group_eq, _ = _make_groups()
        mandate = MandateConfig()

        run_eq = step_rank_group(universe, group_eq, mandate)

        assert run_eq.memo is None
        assert run_eq.fact_pack is None

    def test_different_groups_rank_independently(self):
        """Ranking within one group should not be affected by the other group."""
        # Create funds where Gamma would rank differently
        # if ranked globally vs within-group
        funds = [
            _make_fund("Alpha Equity", "Equity", 0.015),  # highest equity
            _make_fund("Beta Equity", "Equity", 0.005),  # lowest equity
            _make_fund("Gamma Macro", "Macro", 0.012),  # highest macro
            _make_fund("Delta Macro", "Macro", 0.003),  # lowest macro
        ]
        universe = _make_universe(funds)
        group_eq, group_macro = _make_groups()
        mandate = MandateConfig()

        run_eq = step_rank_group(universe, group_eq, mandate)
        run_macro = step_rank_group(universe, group_macro, mandate)

        # In equity group, Alpha should rank #1 (higher returns)
        eq_rank1 = next(sf for sf in run_eq.ranked_shortlist if sf.rank == 1)
        assert eq_rank1.fund_name == "Alpha Equity"

        # In macro group, Gamma should rank #1 (higher returns)
        macro_rank1 = next(sf for sf in run_macro.ranked_shortlist if sf.rank == 1)
        assert macro_rank1.fund_name == "Gamma Macro"
