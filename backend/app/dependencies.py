"""Dependency wiring.

FastAPI's `Depends` is the inversion-of-control mechanism here -- no container
library needed. Routers declare what they need; this module decides which
concrete implementation satisfies it. Tests swap implementations with
`app.dependency_overrides[...]`.
"""

from functools import lru_cache

from fastapi import Depends

from .repository import DEFAULT_DB_PATH, ReportRepository, SqliteReportRepository
from .services import ReportService


@lru_cache(maxsize=1)
def get_repository() -> ReportRepository:
    """Single repository instance per process (it holds only a path)."""
    return SqliteReportRepository(DEFAULT_DB_PATH)


def get_report_service(
    repository: ReportRepository = Depends(get_repository),
) -> ReportService:
    return ReportService(repository)
