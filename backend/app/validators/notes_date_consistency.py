import calendar
import re

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# The sample file uses a consistent convention in its free text:
#   "... , to 09/2010"    pairs with EndDate   = last day of that month
#   "... (from 04/2011)"  pairs with StartDate = first day of that month
# This was verified against the data before being encoded: 7 notes match the
# pattern and 6 of them conform exactly. That conformance ratio is what makes
# the 7th a defect rather than noise.
PERIOD_RE = re.compile(r"\b(from|to)\s+(\d{2})/(\d{4})\b", re.IGNORECASE)


class NotesDateConsistencyValidator(BaseValidator):
    """Flags entries whose notes state a period that contradicts their dates."""

    rationale = (
        "When the prose and the date fields disagree, there is no way to tell which is "
        "authoritative, so the entry may be applied to vehicles it was never meant for."
    )

    @property
    def name(self) -> str:
        return "notes_date_consistency"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            for keyword, month_text, year_text in PERIOD_RE.findall(addr.notes or ""):
                month, year = int(month_text), int(year_text)
                if not 1 <= month <= 12:
                    continue

                if keyword.lower() == "from":
                    expected = f"{year:04d}-{month:02d}-01"
                    actual, field = addr.start_date, "StartDate"
                else:
                    last_day = calendar.monthrange(year, month)[1]
                    expected = f"{year:04d}-{month:02d}-{last_day:02d}"
                    actual, field = addr.end_date, "EndDate"

                if actual == expected:
                    continue

                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.WARNING,
                        message=(
                            f"Address {addr.code!r} says {keyword.lower()} "
                            f"{month_text}/{year_text} in its notes, which implies "
                            f"{field} {expected}, but {field} is {actual!r}."
                        ),
                        validator=self.name,
                        expected=expected,
                        actual=actual,
                    )
                )
        return issues
