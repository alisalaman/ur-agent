"""Custom exceptions for MCP stakeholder views functionality."""


class StakeholderViewsError(Exception):
    """Base exception for stakeholder views functionality."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class TranscriptStoreError(StakeholderViewsError):
    """Exception raised when transcript store operations fail."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, "TRANSCRIPT_STORE_ERROR")
        self.original_error = original_error


class SearchError(StakeholderViewsError):
    """Exception raised when search operations fail."""

    def __init__(self, message: str, topic: str | None = None):
        super().__init__(message, "SEARCH_ERROR")
        self.topic = topic


class ValidationError(StakeholderViewsError):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class ConfigurationError(StakeholderViewsError):
    """Exception raised when configuration is invalid."""

    def __init__(self, message: str, config_key: str | None = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key


class ServerRegistrationError(StakeholderViewsError):
    """Exception raised when server registration fails."""

    def __init__(self, message: str, server_name: str | None = None):
        super().__init__(message, "SERVER_REGISTRATION_ERROR")
        self.server_name = server_name
