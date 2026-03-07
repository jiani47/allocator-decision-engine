"""Hard-coded synthetic fund-of-funds portfolio for diversification analysis."""

from __future__ import annotations

from app.core.schemas import ExistingPortfolio, PortfolioHolding

# 36 months: 2022-01 through 2024-12
_MONTHS = [f"{y}-{m:02d}" for y in range(2022, 2025) for m in range(1, 13)]


def _returns(values: list[float]) -> dict[str, float]:
    """Zip month labels with return values."""
    return dict(zip(_MONTHS, values))


def get_default_portfolio() -> ExistingPortfolio:
    """Return a synthetic existing portfolio with 6 fictional funds.

    Each fund has 36 months of fabricated monthly returns with distinct
    correlation profiles to test diversification scoring meaningfully.
    """
    return ExistingPortfolio(
        name="Sample FoF Portfolio",
        holdings=[
            PortfolioHolding(
                fund_name="Apex Equity L/S",
                weight=0.18,
                monthly_returns=_returns([
                    # 2022
                    -0.02, 0.03, 0.01, -0.04, -0.03, 0.02,
                    0.04, 0.01, -0.05, 0.03, 0.02, 0.01,
                    # 2023
                    0.03, 0.02, -0.01, 0.04, 0.01, 0.03,
                    -0.02, 0.05, 0.01, 0.02, 0.04, 0.03,
                    # 2024
                    0.02, 0.03, 0.01, 0.02, -0.01, 0.04,
                    0.03, -0.02, 0.01, 0.03, 0.02, 0.04,
                ]),
            ),
            PortfolioHolding(
                fund_name="Meridian Global Macro",
                weight=0.18,
                monthly_returns=_returns([
                    # 2022
                    0.01, -0.01, 0.03, 0.02, 0.04, -0.02,
                    0.01, 0.03, 0.02, -0.03, 0.01, 0.04,
                    # 2023
                    -0.01, 0.02, 0.03, -0.02, 0.01, 0.02,
                    0.03, -0.01, 0.04, 0.01, -0.02, 0.03,
                    # 2024
                    0.01, 0.02, -0.01, 0.03, 0.02, -0.02,
                    0.04, 0.01, 0.03, -0.01, 0.02, 0.01,
                ]),
            ),
            PortfolioHolding(
                fund_name="Ironbridge Credit",
                weight=0.18,
                monthly_returns=_returns([
                    # 2022
                    0.005, 0.006, 0.004, 0.003, 0.005, 0.004,
                    0.006, 0.005, 0.003, 0.007, 0.005, 0.006,
                    # 2023
                    0.005, 0.004, 0.006, 0.005, 0.007, 0.004,
                    0.005, 0.006, 0.004, 0.005, 0.006, 0.005,
                    # 2024
                    0.006, 0.005, 0.004, 0.006, 0.005, 0.007,
                    0.004, 0.005, 0.006, 0.005, 0.004, 0.006,
                ]),
            ),
            PortfolioHolding(
                fund_name="Quasar Market Neutral",
                weight=0.16,
                monthly_returns=_returns([
                    # 2022
                    0.003, 0.002, 0.004, 0.001, 0.003, 0.002,
                    0.004, 0.003, 0.001, 0.002, 0.003, 0.004,
                    # 2023
                    0.002, 0.003, 0.004, 0.002, 0.001, 0.003,
                    0.004, 0.002, 0.003, 0.001, 0.004, 0.003,
                    # 2024
                    0.003, 0.002, 0.004, 0.003, 0.002, 0.001,
                    0.003, 0.004, 0.002, 0.003, 0.001, 0.004,
                ]),
            ),
            PortfolioHolding(
                fund_name="Vortex CTA",
                weight=0.16,
                monthly_returns=_returns([
                    # 2022 (tends to do well when equity sells off)
                    0.04, -0.02, 0.01, 0.05, 0.03, -0.01,
                    -0.03, 0.02, 0.06, -0.01, -0.02, 0.03,
                    # 2023
                    -0.01, 0.03, -0.02, 0.01, 0.04, -0.03,
                    0.02, -0.01, 0.03, 0.01, -0.02, 0.01,
                    # 2024
                    0.03, -0.01, 0.02, -0.02, 0.04, 0.01,
                    -0.03, 0.02, -0.01, 0.03, 0.01, -0.02,
                ]),
            ),
            PortfolioHolding(
                fund_name="Terrastone Real Assets",
                weight=0.14,
                monthly_returns=_returns([
                    # 2022
                    0.01, 0.02, 0.03, 0.01, -0.01, 0.02,
                    0.01, 0.02, -0.02, 0.01, 0.02, 0.01,
                    # 2023
                    0.02, 0.01, 0.01, 0.02, 0.01, 0.02,
                    0.01, 0.02, 0.01, 0.01, 0.02, 0.01,
                    # 2024
                    0.01, 0.02, 0.01, 0.01, 0.02, 0.01,
                    0.02, 0.01, 0.01, 0.02, 0.01, 0.02,
                ]),
            ),
        ],
    )
