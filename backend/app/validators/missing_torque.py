from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity


class MissingTorqueValidator(BaseValidator):
    """Example validator: flags address entries that have no torque value."""

    rationale = (
        "An entry with no torque at all gives the technician nothing to work to, so "
        "the fastener is tightened by feel or the job stalls."
    )

    @property
    def name(self) -> str:
        return "missing_torque"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            # Absent only. A present-but-unreadable value (e.g. "n/a") is
            # owned by TorqueValueValidator -- reporting it here as well
            # would emit two errors for one defect, and "has no torque
            # value" would be the wrong description of it.
            if addr.torque is None and addr.torque_raw is None:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.ERROR,
                        message=f"Address {addr.code!r} has no torque value.",
                        validator=self.name,
                    )
                )
        return issues
