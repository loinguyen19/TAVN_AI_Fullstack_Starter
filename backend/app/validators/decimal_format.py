import re
from collections import Counter

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# Optional sign is deliberate. Using an unsigned pattern would also reject the
# negative-torque entry, duplicating the torque_value finding as spurious
# "format" noise. This validator owns the separator convention only.
EU_DECIMAL = re.compile(r"-?\d+,\d+")
US_DECIMAL = re.compile(r"-?\d+\.\d+")
INTEGER = re.compile(r"-?\d+")

# Share of values one shape must reach before deviations are worth reporting.
DOMINANCE_THRESHOLD = 0.9


def _shape(raw: str) -> str:
    if EU_DECIMAL.fullmatch(raw):
        return "european decimal (comma)"
    if US_DECIMAL.fullmatch(raw):
        return "point decimal"
    if INTEGER.fullmatch(raw):
        return "integer, no decimal separator"
    return "non-numeric"


class DecimalFormatValidator(BaseValidator):
    """Flags torque values written inconsistently with the rest of the file.

    Self-calibrating: it learns the dominant notation from the document rather
    than assuming which one a given manufacturer uses. A lone integer in a file
    that otherwise uses comma decimals is the signature of a dropped separator.
    """

    rationale = (
        "A value written in a different notation from the rest of the file usually "
        "means a lost decimal separator, which silently multiplies the torque by ten "
        "or a hundred."
    )

    @property
    def name(self) -> str:
        return "decimal_format"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        raws = [(a, a.torque_raw) for a in document.addresses if a.torque_raw]
        if len(raws) < 10:
            return []  # too small a sample to infer a convention

        counts = Counter(_shape(raw) for _, raw in raws)
        dominant, dominant_count = counts.most_common(1)[0]
        if dominant == "non-numeric":
            return []
        if dominant_count / len(raws) < DOMINANCE_THRESHOLD:
            return []  # no single convention to deviate from

        issues = []
        for addr, raw in raws:
            shape = _shape(raw)
            if shape == dominant or shape == "non-numeric":
                continue

            hint = ""
            if shape == "integer, no decimal separator" and dominant.startswith(
                "european"
            ):
                hint = (
                    f" If a separator was lost, the intended value may have been "
                    f"{raw[:-2]},{raw[-2:]} Nm."
                    if len(raw.lstrip("-")) > 2
                    else ""
                )

            issues.append(
                ValidationResult(
                    code=addr.code,
                    severity=Severity.WARNING,
                    message=(
                        f"Address {addr.code!r} writes its torque as {raw!r} "
                        f"({shape}), while {dominant_count} of {len(raws)} values in "
                        f"this file use {dominant}.{hint}"
                    ),
                    validator=self.name,
                    expected=dominant,
                    actual=f"{raw!r} ({shape})",
                )
            )
        return issues
