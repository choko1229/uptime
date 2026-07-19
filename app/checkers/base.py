from dataclasses import dataclass, field

from app.models import CheckStatus


@dataclass
class CheckOutcome:
    status: CheckStatus
    response_time_ms: int | None = None
    detail: dict = field(default_factory=dict)


class CheckerError(Exception):
    """Raised when a checker cannot complete a check due to bad config."""
