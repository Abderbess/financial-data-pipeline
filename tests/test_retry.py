import sqlite3

import pytest

from txpipe.retry import is_retryable, retry


def test_is_retryable_classification() -> None:
    assert is_retryable(sqlite3.OperationalError("database is locked"))
    assert is_retryable(sqlite3.OperationalError("database table is locked"))
    # Même famille mais pas transitoire : inutile de réessayer
    assert not is_retryable(sqlite3.OperationalError("no such table: transactions"))
    # Contraintes violées : jamais de retry
    assert not is_retryable(sqlite3.IntegrityError("UNIQUE constraint failed"))
    assert not is_retryable(ValueError("autre chose"))


def test_retry_succeeds_after_transient_errors() -> None:
    calls: list[int] = []
    sleeps: list[float] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert retry(flaky, attempts=3, base_delay=0.1, sleep=sleeps.append) == "ok"
    assert len(calls) == 3
    assert sleeps == [0.1, 0.2]  # attente doublée


def test_retry_gives_up_after_max_attempts() -> None:
    calls: list[int] = []

    def always_locked() -> None:
        calls.append(1)
        raise sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError):
        retry(always_locked, attempts=3, sleep=lambda _s: None)
    assert len(calls) == 3


def test_integrity_error_is_never_retried() -> None:
    calls: list[int] = []

    def violates_constraint() -> None:
        calls.append(1)
        raise sqlite3.IntegrityError("UNIQUE constraint failed: fichiers.sha256")

    with pytest.raises(sqlite3.IntegrityError):
        retry(violates_constraint, attempts=5, sleep=lambda _s: None)
    assert len(calls) == 1  # un seul essai, pas cinq


def test_non_transient_operational_error_is_not_retried() -> None:
    calls: list[int] = []

    def no_table() -> None:
        calls.append(1)
        raise sqlite3.OperationalError("no such table: foo")

    with pytest.raises(sqlite3.OperationalError):
        retry(no_table, attempts=5, sleep=lambda _s: None)
    assert len(calls) == 1