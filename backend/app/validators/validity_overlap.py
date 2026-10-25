from collections import defaultdict
from datetime import date

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity


def _parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class ValidityOverlapValidator(BaseValidator):
    """Flags address codes whose validity periods overlap.

    Pure interval arithmetic -- no text is consulted. A torque lookup is keyed
    on (code, date); if two entries for one code cover the same date, the
    lookup is ambiguous. When the overlapping entries also disagree on the
    torque value, the data actively yields two different answers.
    """

    rationale = (
        "A technician looks up a torque by part code and date; overlapping validity "
        "periods return two different answers for the same date, so which torque gets "
        "applied is arbitrary."
    )

    @property
    def name(self) -> str:
        return "validity_overlap"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        by_code = defaultdict(list)
        for addr in document.addresses:
            start, end = _parse_iso(addr.start_date), _parse_iso(addr.end_date)
            if start and end:
                by_code[addr.code].append((start, end, addr))

        issues = []
        for code, entries in sorted(by_code.items()):
            if len(entries) < 2:
                continue
            entries.sort(key=lambda e: e[0])

            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    a_start, a_end, a = entries[i]
                    b_start, b_end, b = entries[j]
                    if not (a_start <= b_end and b_start <= a_end):
                        continue

                    overlap_from = max(a_start, b_start)
                    overlap_to = min(a_end, b_end)
                    conflicting = a.torque != b.torque

                    if conflicting:
                        message = (
                            f"Address {code!r} has two overlapping validity periods "
                            f"with different torques: {a.torque_raw} Nm "
                            f"({a.start_date} to {a.end_date}) and {b.torque_raw} Nm "
                            f"({b.start_date} to {b.end_date}). Any lookup between "
                            f"{overlap_from} and {overlap_to} returns two conflicting "
                            f"values."
                        )
                        severity = Severity.ERROR
                    else:
                        message = (
                            f"Address {code!r} has two overlapping validity periods "
                            f"({a.start_date} to {a.end_date} and {b.start_date} to "
                            f"{b.end_date}) carrying the same torque "
                            f"{a.torque_raw} Nm. The duplicate entry is redundant."
                        )
                        severity = Severity.WARNING

                    issues.append(
                        ValidationResult(
                            code=code,
                            severity=severity,
                            message=message,
                            validator=self.name,
                            expected="non-overlapping validity periods per code",
                            actual=f"overlap {overlap_from} to {overlap_to}",
                        )
                    )
        return issues
