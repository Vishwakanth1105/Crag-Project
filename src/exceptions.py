"""Application-specific exceptions with safe user-facing messages."""


class AppError(Exception):
    """Base class for controlled application errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AppError):
    """Raised when required runtime configuration is missing or invalid."""


class IngestionError(AppError):
    """Raised when document ingestion fails."""


class ParsingError(IngestionError):
    """Raised when a document cannot be parsed safely."""


class IndexingError(IngestionError):
    """Raised when vector or graph indexing fails."""


class RetrievalError(AppError):
    """Raised when retrieval from vector or graph stores fails."""


class RerankError(AppError):
    """Raised when reranking fails."""


class EvaluationError(AppError):
    """Raised when document evaluation fails."""


class GenerationError(AppError):
    """Raised when answer generation fails."""


class StorageError(AppError):
    """Raised when object storage operations fail."""


class GraphWorkflowError(AppError):
    """Raised when the agent workflow fails."""


class ExternalServiceError(AppError):
    """Raised when an external provider call fails."""
