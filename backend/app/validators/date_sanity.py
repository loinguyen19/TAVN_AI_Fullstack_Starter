from datetime import date

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

MIN_PLAUSIBLE_YEAR = 1950
MAX_PLAUSIBLE_YEAR = 2100


def _parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class DateSanityValidator(BaseValidator):
    """Checks that validity dates are well-formed, ordered and plausible."""

    rationale = (
        "Validity dates decide which torque a technician is shown for a given vehicle; "
        "a malformed or reversed range silently excludes the entry from lookups."
    )

    @property
    def name(self) -> str:
        return "date_sanity"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        doc_date = _parse_iso(document.document_date)

        for addr in document.addresses:
            parsed = {}
            for field, raw in (("StartDate", addr.start_date), ("EndDate", addr.end_date)):
                if raw is None:
                    continue
                value = _parse_iso(raw)
                if value is None:
                    issues.append(
                        ValidationResult(
                            code=addr.code,
                            severity=Severity.ERROR,
                            message=(
                                f"Address {addr.code!r} has a {field} of {raw!r}, "
                                f"which is not a valid ISO date (YYYY-MM-DD)."
                            ),
                            validator=self.name,
                            expected="YYYY-MM-DD",
                            actual=raw,
                        )
                    )
                    continue
                if not MIN_PLAUSIBLE_YEAR <= value.year <= MAX_PLAUSIBLE_YEAR:
                    issues.append(
                        ValidationResult(
                            code=addr.code,
                            severity=Severity.WARNING,
                            message=(
                                f"Address {addr.code!r} has a {field} of {raw}, "
                                f"outside the plausible range "
                                f"{MIN_PLAUSIBLE_YEAR}-{MAX_PLAUSIBLE_YEAR}."
                            ),
                            validator=self.name,
                            expected=f"year {MIN_PLAUSIBLE_YEAR}-{MAX_PLAUSIBLE_YEAR}",
                            actual=raw,
                        )
                    )
                parsed[field] = value

            start, end = parsed.get("StartDate"), parsed.get("EndDate")
            if start and end and start > end:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.ERROR,
                        message=(
                            f"Address {addr.code!r} starts on {addr.start_date} but "
                            f"ends on {addr.end_date}; the validity period is "
                            f"reversed and matches no date at all."
                        ),
                        validator=self.name,
                        expected="StartDate <= EndDate",
                        actual=f"{addr.start_date} to {addr.end_date}",
                    )
                )

            if doc_date and end and end < doc_date:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.INFO,
                        message=(
                            f"Address {addr.code!r} expired on {addr.end_date}, before "
                            f"this document was issued ({document.document_date}). "
                            f"Confirm a superseding entry exists."
                        ),
                        validator=self.name,
                        expected=f"EndDate >= {document.document_date}",
                        actual=addr.end_date,
                    )
                )
        return issues
