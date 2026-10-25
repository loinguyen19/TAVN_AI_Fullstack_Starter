"""Business logic.

Sits between the HTTP layer and the repository. Knows nothing about FastAPI,
request objects or status codes -- it raises domain errors and the router maps
those to HTTP responses. That keeps the orchestration testable without a web
client, and keeps `main.py` to routing.
"""

import csv
import io
from collections import Counter
from typing import Any

from .parser import TorqueDocument, parse_torque_xml
from .repository import ReportRepository
from .validators.registry import run_all_validators, validator_catalogue

CSV_COLUMNS = [
    "report_id",
    "filename",
    "created_at",
    "severity",
    "code",
    "validator",
    "message",
    "expected",
    "actual",
    "torque",
    "start_date",
    "end_date",
    "notes",
]


# ── domain errors ────────────────────────────────────────────────────────
# Deliberately not HTTPException: the service must not know about HTTP.


class ServiceError(Exception):
    """Base class for errors the router knows how to translate."""


class UnsupportedFileType(ServiceError):
    pass


class DocumentParseError(ServiceError):
    pass


class ReportNotFound(ServiceError):
    pass


# ── service ──────────────────────────────────────────────────────────────


class ReportService:
    """Creates and retrieves validation reports."""

    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def create_from_file(self, content: bytes, filename: str | None) -> dict[str, Any]:
        if not filename or not filename.endswith(".xml"):
            raise UnsupportedFileType("Only XML files are accepted")

        try:
            document = parse_torque_xml(content, filename)
        except Exception as exc:
            raise DocumentParseError(f"Failed to parse XML: {exc}") from exc

        payload = self._build_payload(document, filename)
        report_id, created_at = self._repository.add(payload)
        payload["report_id"] = report_id
        payload["created_at"] = created_at
        return payload

    def list_reports(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._repository.list(limit=limit)

    def get_report(self, report_id: int) -> dict[str, Any]:
        payload = self._repository.get(report_id)
        if payload is None:
            raise ReportNotFound(f"No report with id {report_id}")
        return payload

    def export_report_csv(self, report_id: int) -> tuple[bytes, str]:
        """Return (csv bytes, suggested filename)."""
        payload = self.get_report(report_id)
        return build_csv(payload), csv_filename(payload)

    @staticmethod
    def available_validators() -> dict[str, dict[str, str]]:
        return validator_catalogue()

    @staticmethod
    def _build_payload(document: TorqueDocument, filename: str) -> dict[str, Any]:
        validations = run_all_validators(document)
        counts = Counter(v.severity.value for v in validations)
        return {
            "filename": filename,
            "document_date": document.document_date,
            "notes": document.notes,
            "addresses": [
                {
                    "code": a.code,
                    "torque": a.torque,
                    "torque_raw": a.torque_raw,
                    "notes": a.notes,
                    "start_date": a.start_date,
                    "end_date": a.end_date,
                    "position": a.position,
                }
                for a in document.addresses
            ],
            "validations": [v.model_dump(mode="json") for v in validations],
            # Rationales live here, once per validator, rather than being
            # repeated on every finding. The UI joins on `validator`.
            "validators": validator_catalogue(),
            "summary": {
                "error": counts.get("error", 0),
                "warning": counts.get("warning", 0),
                "info": counts.get("info", 0),
                "total": len(validations),
                "addresses": len(document.addresses),
            },
        }


# ── CSV export ───────────────────────────────────────────────────────────
# A pure function of the payload, so it is testable without a repository.


def build_csv(payload: dict[str, Any]) -> bytes:
    by_code = {a["code"]: a for a in payload.get("addresses", [])}
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()

    for finding in payload.get("validations", []):
        address = by_code.get(finding.get("code")) or {}
        writer.writerow(
            {
                "report_id": payload.get("report_id"),
                "filename": payload.get("filename"),
                "created_at": payload.get("created_at"),
                "severity": finding.get("severity"),
                "code": finding.get("code"),
                "validator": finding.get("validator"),
                "message": finding.get("message"),
                "expected": finding.get("expected"),
                "actual": finding.get("actual"),
                "torque": address.get("torque_raw"),
                "start_date": address.get("start_date"),
                "end_date": address.get("end_date"),
                "notes": address.get("notes"),
            }
        )

    # utf-8-sig so Excel detects the encoding instead of mangling it.
    return buffer.getvalue().encode("utf-8-sig")


def csv_filename(payload: dict[str, Any]) -> str:
    stem = (payload.get("filename") or "report").rsplit(".", 1)[0]
    return f"{stem}-validations.csv"
