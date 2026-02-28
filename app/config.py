from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EQUI_",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.2
    log_level: str = "INFO"
    min_history_months: int = 12
    outlier_return_threshold: float = 0.25
    default_benchmark_symbol: str = "SPY"
    ingestion_max_rows: int = 2000
