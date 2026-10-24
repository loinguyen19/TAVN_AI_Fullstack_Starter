from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity


class MissingTorqueValidator(BaseValidator):
    """Example validator: flags address entries that have no torque value."""

    @property
    def name(self) -> str:
        return "missing_torque"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            if addr.torque is None:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.ERROR,
                        message=f"Address {addr.code!r} has no torque value.",
                        validator=self.name,
                    )
                )
        return issues
