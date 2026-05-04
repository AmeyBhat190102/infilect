class IngestionError(Exception):
    """Raised when file ingestion fails at a structural level."""
    pass


class ValidationError(Exception):
    """Raised when a row fails business-rule validation."""
    pass


class DependencyError(Exception):
    """Raised when a dependency (store / user) is missing for PJP."""
    pass
