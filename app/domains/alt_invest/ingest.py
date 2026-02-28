"""CSV ingestion, schema inference, normalization, and anomaly detection."""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone

import pandas as pd

from app.core.exceptions import InvalidUniverseError, SchemaInferenceError
from app.core.schemas import (
    ColumnMapping,
    LLMIngestionResult,
    NormalizedFund,
    NormalizedUniverse,
    RawFileContext,
    ValidationWarning,
)

logger = logging.getLogger("equi.ingest")

# Fuzzy matching patterns for column inference
_COLUMN_PATTERNS: dict[str, list[str]] = {
    "fund_name": ["fund_name", "fund name", "fund", "manager", "manager_name", "name"],
    "date": ["date", "period", "month", "as_of_date", "as of date", "reporting_date"],
    "monthly_return": [
        "monthly_return",
        "monthly return",
        "return",
        "return (%)",
        "return(%)",
        "returns",
        "mo_return",
        "pnl",
    ],
    "strategy": ["strategy", "strategy_type", "type", "style"],
    "liquidity_days": [
        "liquidity_days",
        "liquidity (days)",
        "liquidity",
        "redemption_days",
        "lock_up",
    ],
    "management_fee": ["management_fee", "mgmt_fee", "mgmt fee", "management fee"],
    "performance_fee": [
        "performance_fee",
        "perf_fee",
        "perf fee",
        "performance fee",
        "incentive_fee",
    ],
}


def read_csv(file_content: bytes, filename: str) -> pd.DataFrame:
    """Read raw CSV bytes into a DataFrame."""
    logger.info("Reading CSV: %s (%d bytes)", filename, len(file_content))
    try:
        df = pd.read_csv(io.BytesIO(file_content))
    except Exception as exc:
        raise InvalidUniverseError(f"Failed to parse CSV '{filename}': {exc}") from exc

    if df.empty:
        raise InvalidUniverseError(f"CSV '{filename}' is empty")

    logger.info("Parsed %d rows, %d columns", len(df), len(df.columns))
    return df


def infer_column_mapping(df: pd.DataFrame) -> ColumnMapping:
    """Infer likely mapping from CSV columns to canonical fields."""
    columns_lower = {col: col.strip().lower() for col in df.columns}
    mapping: dict[str, str | None] = {}

    for canonical, patterns in _COLUMN_PATTERNS.items():
        matched = None
        for col, col_lower in columns_lower.items():
            if col_lower in patterns:
                matched = col
                break
        mapping[canonical] = matched

    # Validate required fields
    for required in ("fund_name", "date", "monthly_return"):
        if mapping.get(required) is None:
            raise SchemaInferenceError(
                f"Could not infer required column '{required}' from headers: "
                f"{list(df.columns)}"
            )

    return ColumnMapping(
        fund_name=mapping["fund_name"],  # type: ignore[arg-type]
        date=mapping["date"],  # type: ignore[arg-type]
        monthly_return=mapping["monthly_return"],  # type: ignore[arg-type]
        strategy=mapping.get("strategy"),
        liquidity_days=mapping.get("liquidity_days"),
        management_fee=mapping.get("management_fee"),
        performance_fee=mapping.get("performance_fee"),
    )


def normalize_dates(series: pd.Series) -> pd.Series:
    """Parse mixed date formats and normalize to YYYY-MM period strings."""
    parsed = pd.to_datetime(series, format="mixed", dayfirst=False)
    return parsed.dt.to_period("M").astype(str)


def normalize_returns(series: pd.Series) -> pd.Series:
    """Convert returns to float decimals. Handles '1.23%' -> 0.0123."""

    def _parse_return(val: object) -> float:
        if pd.isna(val):
            return float("nan")
        s = str(val).strip()
        if s.endswith("%"):
            return float(s[:-1]) / 100.0
        return float(s)

    return series.apply(_parse_return)


def normalize_fund_names(series: pd.Series) -> pd.Series:
    """Trim whitespace, normalize to title case."""
    return series.str.strip().str.title()


def detect_duplicates(df: pd.DataFrame) -> list[ValidationWarning]:
    """Find duplicate (fund_name, date) rows."""
    dupes = df[df.duplicated(subset=["fund_name", "date"], keep="first")]
    warnings: list[ValidationWarning] = []
    if len(dupes) > 0:
        for fund_name in dupes["fund_name"].unique():
            fund_dupes = dupes[dupes["fund_name"] == fund_name]
            warnings.append(
                ValidationWarning(
                    category="duplicate",
                    fund_name=fund_name,
                    message=f"{len(fund_dupes)} duplicate row(s) found for {fund_name}, keeping first occurrence",
                    row_indices=fund_dupes.index.tolist(),
                )
            )
    return warnings


def detect_missing_months(df: pd.DataFrame) -> list[ValidationWarning]:
    """For each fund, find gaps in monthly coverage."""
    warnings: list[ValidationWarning] = []
    for fund_name, group in df.groupby("fund_name"):
        periods = pd.PeriodIndex(group["date"], freq="M")
        full_range = pd.period_range(periods.min(), periods.max(), freq="M")
        missing = full_range.difference(periods)
        if len(missing) > 0:
            warnings.append(
                ValidationWarning(
                    category="missing_month",
                    fund_name=str(fund_name),
                    message=f"{len(missing)} missing month(s): {', '.join(str(m) for m in missing[:5])}{'...' if len(missing) > 5 else ''}",
                )
            )
    return warnings


def detect_outliers(
    df: pd.DataFrame, threshold: float = 0.25
) -> list[ValidationWarning]:
    """Flag returns where |value| > threshold."""
    warnings: list[ValidationWarning] = []
    outlier_mask = df["monthly_return"].abs() > threshold
    outliers = df[outlier_mask]
    for _, row in outliers.iterrows():
        warnings.append(
            ValidationWarning(
                category="outlier",
                fund_name=row["fund_name"],
                message=f"Extreme return {row['monthly_return']:.4f} ({row['monthly_return']*100:.1f}%) in {row['date']}",
                row_indices=[int(row.name)],  # type: ignore[arg-type]
            )
        )
    return warnings


def build_normalized_universe(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    file_hash: str,
) -> NormalizedUniverse:
    """Main orchestrator: apply all normalizations, produce NormalizedUniverse."""
    logger.info("Building normalized universe from %d rows", len(df))

    # Step 1: Apply column mapping (rename to canonical names)
    rename_map: dict[str, str] = {
        mapping.fund_name: "fund_name",
        mapping.date: "date",
        mapping.monthly_return: "monthly_return",
    }
    optional_mappings = {
        "strategy": mapping.strategy,
        "liquidity_days": mapping.liquidity_days,
        "management_fee": mapping.management_fee,
        "performance_fee": mapping.performance_fee,
    }
    for canonical, source in optional_mappings.items():
        if source is not None:
            rename_map[source] = canonical

    work = df.rename(columns=rename_map).copy()

    # Step 2: Normalize fund names
    work["fund_name"] = normalize_fund_names(work["fund_name"])

    # Step 3: Normalize dates
    work["date"] = normalize_dates(work["date"])

    # Step 4: Normalize returns
    work["monthly_return"] = normalize_returns(work["monthly_return"])

    # Step 5: Detect duplicates -> dedupe
    warnings = detect_duplicates(work)
    work = work.drop_duplicates(subset=["fund_name", "date"], keep="first").reset_index(
        drop=True
    )

    # Step 6: Detect missing months
    warnings.extend(detect_missing_months(work))

    # Step 7: Detect outliers
    warnings.extend(detect_outliers(work))

    # Step 8: Validate we have a time series
    if work["date"].nunique() <= 1:
        raise InvalidUniverseError(
            "Data appears to be a summary, not a time series (only 1 unique date found)"
        )

    # Step 9: Build NormalizedFund objects
    funds: list[NormalizedFund] = []
    for fund_name, group in work.groupby("fund_name"):
        sorted_group = group.sort_values("date")
        monthly_returns = dict(
            zip(sorted_group["date"], sorted_group["monthly_return"])
        )
        periods = sorted(monthly_returns.keys())

        fund = NormalizedFund(
            fund_name=str(fund_name),
            strategy=sorted_group["strategy"].iloc[0]
            if "strategy" in sorted_group.columns
            and pd.notna(sorted_group["strategy"].iloc[0])
            else None,
            liquidity_days=int(sorted_group["liquidity_days"].iloc[0])
            if "liquidity_days" in sorted_group.columns
            and pd.notna(sorted_group["liquidity_days"].iloc[0])
            else None,
            management_fee=float(sorted_group["management_fee"].iloc[0])
            if "management_fee" in sorted_group.columns
            and pd.notna(sorted_group["management_fee"].iloc[0])
            else None,
            performance_fee=float(sorted_group["performance_fee"].iloc[0])
            if "performance_fee" in sorted_group.columns
            and pd.notna(sorted_group["performance_fee"].iloc[0])
            else None,
            monthly_returns=monthly_returns,
            date_range_start=periods[0],
            date_range_end=periods[-1],
            month_count=len(periods),
        )
        funds.append(fund)

    if not funds:
        raise InvalidUniverseError("No funds found after normalization")

    logger.info("Normalized %d funds with %d warnings", len(funds), len(warnings))
    return NormalizedUniverse(
        funds=funds,
        warnings=warnings,
        source_file_hash=file_hash,
        column_mapping=mapping,
        normalization_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def build_normalized_universe_from_llm(
    llm_result: LLMIngestionResult,
    raw_context: RawFileContext,
) -> NormalizedUniverse:
    """Build NormalizedUniverse from LLM-extracted fund data.

    Converts LLMExtractedFund objects into a DataFrame, then runs the
    existing deterministic validation (duplicates, missing months, outliers).
    """
    logger.info(
        "Building normalized universe from LLM extraction: %d funds",
        len(llm_result.funds),
    )

    # Convert LLM-extracted funds to a DataFrame for validation
    rows = []
    for fund in llm_result.funds:
        for date_key, ret_val in fund.monthly_returns.items():
            row: dict = {
                "fund_name": fund.fund_name,
                "date": date_key,
                "monthly_return": ret_val,
            }
            if fund.strategy is not None:
                row["strategy"] = fund.strategy
            if fund.liquidity_days is not None:
                row["liquidity_days"] = fund.liquidity_days
            if fund.management_fee is not None:
                row["management_fee"] = fund.management_fee
            if fund.performance_fee is not None:
                row["performance_fee"] = fund.performance_fee
            rows.append(row)

    if not rows:
        raise InvalidUniverseError("LLM extraction produced no data rows")

    work = pd.DataFrame(rows)

    # Run existing validation pipeline
    warnings = detect_duplicates(work)
    work = work.drop_duplicates(subset=["fund_name", "date"], keep="first").reset_index(
        drop=True
    )
    warnings.extend(detect_missing_months(work))
    warnings.extend(detect_outliers(work))

    if work["date"].nunique() <= 1:
        raise InvalidUniverseError(
            "LLM extraction produced data with only 1 unique date"
        )

    # Build NormalizedFund objects
    funds: list[NormalizedFund] = []
    for fund_name, group in work.groupby("fund_name"):
        sorted_group = group.sort_values("date")
        monthly_returns = dict(
            zip(sorted_group["date"], sorted_group["monthly_return"])
        )
        periods = sorted(monthly_returns.keys())

        fund = NormalizedFund(
            fund_name=str(fund_name),
            strategy=sorted_group["strategy"].iloc[0]
            if "strategy" in sorted_group.columns
            and pd.notna(sorted_group["strategy"].iloc[0])
            else None,
            liquidity_days=int(sorted_group["liquidity_days"].iloc[0])
            if "liquidity_days" in sorted_group.columns
            and pd.notna(sorted_group["liquidity_days"].iloc[0])
            else None,
            management_fee=float(sorted_group["management_fee"].iloc[0])
            if "management_fee" in sorted_group.columns
            and pd.notna(sorted_group["management_fee"].iloc[0])
            else None,
            performance_fee=float(sorted_group["performance_fee"].iloc[0])
            if "performance_fee" in sorted_group.columns
            and pd.notna(sorted_group["performance_fee"].iloc[0])
            else None,
            monthly_returns=monthly_returns,
            date_range_start=periods[0],
            date_range_end=periods[-1],
            month_count=len(periods),
        )
        funds.append(fund)

    if not funds:
        raise InvalidUniverseError("No funds found after LLM normalization")

    logger.info("Normalized %d funds from LLM with %d warnings", len(funds), len(warnings))
    return NormalizedUniverse(
        funds=funds,
        warnings=warnings,
        source_file_hash=raw_context.file_hash,
        column_mapping=None,
        normalization_timestamp=datetime.now(timezone.utc).isoformat(),
        ingestion_method="llm",
        raw_context=raw_context,
        llm_interpretation_notes=llm_result.interpretation_notes,
    )
