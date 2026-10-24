from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult

# ──────────────────────────────────────────────────────────────
# Validator Registry
#
# Register your validators here. Each validator must subclass
# BaseValidator and implement validate().
#
# The example MissingTorqueValidator is provided to show the
# pattern. Add your own validators below.
# ──────────────────────────────────────────────────────────────

from .missing_torque import MissingTorqueValidator

VALIDATORS: list[BaseValidator] = [
    MissingTorqueValidator(),
    # TODO: Add your validators here
]


def run_all_validators(document: TorqueDocument) -> list[ValidationResult]:
    """Run all registered validators and collect results."""
    results = []
    for validator in VALIDATORS:
        results.extend(validator.validate(document))
    return results
