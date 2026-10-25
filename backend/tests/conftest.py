"""Shared fixtures.

Tests run both inside the backend container (where the sample data is mounted
at /data) and from the repo root, so the sample file is located rather than
hardcoded.
"""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SAMPLE_NAME = "AZD-AZD-AZDMUC4161-F01_RBU.xml"


def _find_sample() -> Path:
    candidates = [
        Path("/data") / SAMPLE_NAME,                       # container mount
        BACKEND_ROOT.parent / "data" / SAMPLE_NAME,        # repo checkout
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"sample data not found; looked in {candidates}")


@pytest.fixture(scope="session")
def sample_path() -> Path:
    return _find_sample()


@pytest.fixture(scope="session")
def sample_bytes(sample_path: Path) -> bytes:
    return sample_path.read_bytes()


@pytest.fixture(scope="session")
def sample_document(sample_bytes: bytes):
    from app.parser import parse_torque_xml

    return parse_torque_xml(sample_bytes, SAMPLE_NAME)


@pytest.fixture
def repository(tmp_path):
    """A real SQLite repository on a throwaway file."""
    from app.repository import SqliteReportRepository

    repo = SqliteReportRepository(str(tmp_path / "test.db"))
    repo.initialise()
    return repo


@pytest.fixture
def service(repository):
    """Service under test, with no HTTP layer involved."""
    from app.services import ReportService

    return ReportService(repository)


@pytest.fixture
def client(repository):
    """TestClient with the repository swapped via dependency_overrides.

    This is the payoff of injecting the repository rather than importing it:
    the test substitutes persistence without monkeypatching module globals.
    """
    from fastapi.testclient import TestClient

    from app.dependencies import get_repository
    from app.main import app

    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def build_xml(addresses: str, document_fields: str = "") -> bytes:
    """Minimal valid document wrapping the given <Address> entries."""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<TorqueDocument>
  <DocumentDate>2024-09-15</DocumentDate>
  <Manufacturer>AZD</Manufacturer>
  <Series>F01</Series>
  <MainGroup>41</MainGroup>
  <SubGroup>61</SubGroup>
  <Notes>Test document.</Notes>
  {document_fields}
  <Addresses>
{addresses}
  </Addresses>
</TorqueDocument>""".encode("utf-8")


def address(
    code="1AZ",
    torque="20,0",
    notes="Test fastener",
    start="2008-01-01",
    end="2030-12-31",
) -> str:
    parts = [f"      <Code>{code}</Code>"]
    if torque is not None:
        parts.append(f"      <Torque>{torque}</Torque>")
    if notes is not None:
        parts.append(f"      <Notes>{notes}</Notes>")
    if start is not None:
        parts.append(f"      <StartDate>{start}</StartDate>")
    if end is not None:
        parts.append(f"      <EndDate>{end}</EndDate>")
    return "    <Address>\n" + "\n".join(parts) + "\n    </Address>"
