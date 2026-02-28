class DecisionEngineError(Exception):
    """Base exception for core decision engine errors."""


class InvalidUniverseError(DecisionEngineError):
    """Raised when the normalized universe is invalid."""


class InsufficientDataError(DecisionEngineError):
    """Raised when a fund has insufficient history for metric computation."""


class SchemaInferenceError(DecisionEngineError):
    """Raised when column mapping cannot be inferred."""


class BenchmarkAlignmentError(DecisionEngineError):
    """Raised when benchmark cannot be aligned to fund date range."""


class MemoGenerationError(DecisionEngineError):
    """Raised when LLM memo generation fails."""


class LLMIngestionError(DecisionEngineError):
    """Raised when LLM-based ingestion fails."""
