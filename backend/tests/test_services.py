"""Service layer, exercised without FastAPI.

These tests are the reason the orchestration was lifted out of the router:
they drive the real logic through a plain object and a fake repository, with
no TestClient, no routes and no database.
"""

import pytest

from app.services import (
    DocumentParseError,
    ReportNotFound,
    ReportService,
    UnsupportedFileType,
    build_csv,
    csv_filename,
)
from tests.conftest import SAMPLE_NAME, address, build_xml


class FakeRepository:
    """In-memory stand-in. Satisfies the ReportRepository protocol
    structurally -- no base class, no mocking library."""

    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.initialised = False

    def initialise(self):
        self.initialised = True

    def add(self, payload):
        report_id = len(self.rows) + 1
        created_at = "2026-01-01T00:00:00+00:00"
        self.rows[report_id] = {**payload, "report_id": report_id,
                                "created_at": created_at}
        return report_id, created_at

    def list(self, limit=50):
        return list(self.rows.values())[:limit]

    def get(self, report_id):
        return self.rows.get(report_id)


@pytest.fixture
def fake_service():
    return ReportService(FakeRepository())


def test_create_report_returns_id_and_timestamp(fake_service, sample_bytes):
    payload = fake_service.create_from_file(sample_bytes, SAMPLE_NAME)
    assert payload["report_id"] == 1
    assert payload["created_at"].startswith("2026-")
    assert payload["summary"]["total"] == 20


def test_rejects_non_xml_filename(fake_service):
    with pytest.raises(UnsupportedFileType):
        fake_service.create_from_file(b"hello", "notes.txt")


def test_rejects_missing_filename(fake_service):
    with pytest.raises(UnsupportedFileType):
        fake_service.create_from_file(b"<a/>", None)


def test_malformed_xml_raises_parse_error(fake_service):
    with pytest.raises(DocumentParseError):
        fake_service.create_from_file(b"<TorqueDocument><Addresses>", "x.xml")


def test_service_errors_are_not_http_errors():
    """The service must stay ignorant of the web layer."""
    from fastapi import HTTPException

    assert not issubclass(UnsupportedFileType, HTTPException)
    assert not issubclass(ReportNotFound, HTTPException)


def test_get_missing_report_raises(fake_service):
    with pytest.raises(ReportNotFound):
        fake_service.get_report(404)


def test_reports_round_trip_through_the_repository(fake_service, sample_bytes):
    created = fake_service.create_from_file(sample_bytes, SAMPLE_NAME)
    fetched = fake_service.get_report(created["report_id"])
    assert fetched["validations"] == created["validations"]


def test_service_works_against_real_sqlite(service, sample_bytes):
    """Same orchestration, real repository -- proves the Protocol holds."""
    payload = service.create_from_file(sample_bytes, SAMPLE_NAME)
    assert service.get_report(payload["report_id"])["summary"] == payload["summary"]
    assert len(service.list_reports()) == 1


# ── CSV is a pure function of the payload ────────────────────────────────

def test_build_csv_emits_one_row_per_finding(fake_service, sample_bytes):
    payload = fake_service.create_from_file(sample_bytes, SAMPLE_NAME)
    lines = build_csv(payload).decode("utf-8-sig").strip().splitlines()
    assert len(lines) == 21  # header + 20 findings
    assert lines[0].startswith("report_id,filename,created_at")


def test_build_csv_on_a_clean_report_is_header_only():
    payload = {"filename": "x.xml", "addresses": [], "validations": []}
    assert len(build_csv(payload).decode("utf-8-sig").strip().splitlines()) == 1


def test_csv_filename_derives_from_the_document():
    assert csv_filename({"filename": "AZD-F01.xml"}) == "AZD-F01-validations.csv"
    assert csv_filename({}) == "report-validations.csv"
