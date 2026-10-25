from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# (attribute, XML element name, severity when absent)
REQUIRED_ADDRESS_FIELDS = (
    ("code", "Code", Severity.ERROR),
    ("notes", "Notes", Severity.WARNING),
    ("start_date", "StartDate", Severity.ERROR),
    ("end_date", "EndDate", Severity.ERROR),
)


class RequiredFieldsValidator(BaseValidator):
    """Checks that every address carries the fields a lookup depends on.

    Finds nothing in the current sample file -- every entry is complete -- but
    these are the fields a torque lookup is keyed on, so their absence must be
    caught rather than assumed impossible.
    """

    rationale = (
        "A lookup is keyed on code and date and presented with its notes; an entry "
        "missing any of them cannot be found, or is found without the context needed "
        "to apply it."
    )

    @property
    def name(self) -> str:
        return "required_fields"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            for attribute, element, severity in REQUIRED_ADDRESS_FIELDS:
                if getattr(addr, attribute):
                    continue
                label = addr.code or f"entry #{addr.position + 1}"
                issues.append(
                    ValidationResult(
                        code=addr.code or None,
                        severity=severity,
                        message=(
                            f"Address {label!r} is missing its <{element}> value."
                        ),
                        validator=self.name,
                        expected=f"a non-empty <{element}>",
                        actual="empty or absent",
                    )
                )
        return issues
