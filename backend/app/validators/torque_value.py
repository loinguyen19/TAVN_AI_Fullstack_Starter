from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity


class TorqueValueValidator(BaseValidator):
    """Flags torque values that are present but unusable: non-positive, or text
    that is not a number at all.

    A torque *specification* is a magnitude -- the instruction is "tighten to
    X Nm", and a torque wrench is dialled to a magnitude. Thread direction is a
    property of the fastener, carried separately in the notes (see the
    left-hand-thread entry in the sample file, whose value is positive).

    Note this does NOT hold for torque *measurement* data (tool rundown traces,
    breakaway readings), where sign legitimately encodes rotation direction. If
    this system ever ingests measurement data, guard this check by document type.
    """

    rationale = (
        "A specification torque is a magnitude; zero or negative means the fastener "
        "has no usable spec and the technician cannot set a torque wrench from it."
    )

    @property
    def name(self) -> str:
        return "torque_value"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            if addr.torque_parse_failed:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.ERROR,
                        message=(
                            f"Address {addr.code!r} has a torque value that is not a "
                            f"number: {addr.torque_raw!r}."
                        ),
                        validator=self.name,
                        expected="a numeric value in Nm",
                        actual=addr.torque_raw,
                    )
                )
                continue

            # `torque is None` with no raw text is a missing value, owned by
            # MissingTorqueValidator. This validator owns present-but-unusable.
            if addr.torque is None:
                continue

            if addr.torque <= 0:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.ERROR,
                        message=(
                            f"Address {addr.code!r} has a non-positive torque of "
                            f"{addr.torque_raw} Nm. A tightening spec cannot be zero "
                            f"or negative."
                        ),
                        validator=self.name,
                        expected="> 0 Nm",
                        actual=addr.torque_raw,
                    )
                )
        return issues
