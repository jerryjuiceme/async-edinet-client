class EdinetAPIError(Exception):
    """Base exception for Edinet API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class EdinetConnectionError(EdinetAPIError):
    """Network level errors."""

    pass


class EdinetAPIRateLimitError(EdinetAPIError):
    """429 errors."""

    pass


class EdinetAPIAuthError(EdinetAPIError):
    """401 errors."""

    pass


class EdinetClientError(EdinetAPIError):
    """400, 404 errors (Invalid ID, etc)."""

    pass


class EdinetServerError(EdinetAPIError):
    """500+ errors."""

    pass
