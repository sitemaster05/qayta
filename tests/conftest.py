# Shared pytest configuration and fixtures for the Qayta test suite.
# asyncio_mode = "auto" is set in pyproject.toml [tool.pytest.ini_options];
# this file provides fixtures reused across multiple test modules.

from collections.abc import Iterator

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests that hit real external services (deselect with -m 'not integration')",
    )


@pytest.fixture
def in_memory_db() -> Iterator[str]:
    """Yield the SQLite in-memory DSN for tests that need a throwaway database."""
    yield ":memory:"
