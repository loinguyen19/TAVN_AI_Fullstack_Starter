import re

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# Instructions buried in free text that change how the job must be done.
# A correct torque applied without these is still a failed repair.
HANDLING_PATTERNS = (
    (
        re.compile(r"left[- ]hand thread", re.IGNORECASE),
        "Left-hand thread: this fastener tightens anticlockwise.",
    ),
    (
        re.compile(r"replace .*after each removal|single[- ]use|renew", re.IGNORECASE),
        "Single-use fastener: it must be replaced, not refitted.",
    ),
    (
        re.compile(r"thread lock|threadlock|loctite", re.IGNORECASE),
        "Thread-locking compound is required.",
    ),
    (
        re.compile(r"anti[- ]seize", re.IGNORECASE),
        "Anti-seize compound is required; it also changes the friction the "
        "torque figure assumes.",
    ),
    (
        re.compile(r"hand[- ]tight|[\d/]+\s*turn", re.IGNORECASE),
        "Procedural tightening (hand-tight plus a turn) rather than a pure "
        "torque figure.",
    ),
    (
        re.compile(r"tighten in sequence|in sequence", re.IGNORECASE),
        "Must be tightened in a specified sequence.",
    ),
)


class SpecialHandlingValidator(BaseValidator):
    """Surfaces handling instructions hidden in the notes column.

    These are not data errors. They are advisories that a reviewer scanning a
    table of numbers would otherwise miss, so they are reported at INFO.
    """

    rationale = (
        "These instructions live in free text where a reader scanning torque figures "
        "will miss them, yet ignoring one ruins the repair even when the torque is "
        "correct."
    )

    @property
    def name(self) -> str:
        return "special_handling"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            notes = addr.notes or ""
            for pattern, explanation in HANDLING_PATTERNS:
                if not pattern.search(notes):
                    continue
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.INFO,
                        message=f"Address {addr.code!r}: {explanation}",
                        validator=self.name,
                        expected=None,
                        actual=notes,
                    )
                )
        return issues
