import sqlite3
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

# SQLite signale un verrou par "database is locked" ou "database table is locked"
_TRANSIENT_MARKERS = ("locked", "busy")


def is_retryable(exc: BaseException) -> bool:
    """True uniquement pour une OperationalError de type verrou / base occupée."""
    if not isinstance(exc, sqlite3.OperationalError):
        # IntegrityError, ProgrammingError... : déterministes, jamais de retry
        return False
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_MARKERS)


def retry(
    func: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Appelle func ; si l'erreur est retryable, attend puis réessaie (attente doublée à chaque fois)."""
    if attempts < 1:
        raise ValueError("attempts doit être >= 1")
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            if attempt == attempts or not is_retryable(exc):
                raise
            sleep(base_delay * 2 ** (attempt - 1))
    raise AssertionError("inatteignable")  # pour mypy