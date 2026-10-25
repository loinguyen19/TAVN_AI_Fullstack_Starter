from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# ──────────────────────────────────────────────────────────────
# Validator Registry
#
# Register your validators here. Each validator must subclass
# BaseValidator and implement validate().
#
# Each validator covers one *class* of data quality issue and
# declares a `rationale` explaining why that class matters to a
# workshop technician. The API returns those rationales in a
# separate map so the UI can show them once per validator.
# ──────────────────────────────────────────────────────────────

from .missing_torque import MissingTorqueValidator
from .torque_value import TorqueValueValidator
from .torque_plausibility import TorquePlausibilityValidator
from .decimal_format import DecimalFormatValidator
from .validity_overlap import ValidityOverlapValidator
from .notes_date_consistency import NotesDateConsistencyValidator
from .date_sanity import DateSanityValidator
from .required_fields import RequiredFieldsValidator
from .special_handling import SpecialHandlingValidator
from .incomplete_procedure import IncompleteProcedureValidator
from .document_metadata import DocumentMetadataValidator

VALIDATORS: list[BaseValidator] = [
    MissingTorqueValidator(),
    TorqueValueValidator(),
    TorquePlausibilityValidator(),
    DecimalFormatValidator(),
    ValidityOverlapValidator(),
    NotesDateConsistencyValidator(),
    DateSanityValidator(),
    RequiredFieldsValidator(),
    IncompleteProcedureValidator(),
    SpecialHandlingValidator(),
    DocumentMetadataValidator(),
]


def run_all_validators(document: TorqueDocument) -> list[ValidationResult]:
    """Run all registered validators and collect results.

    Each validator is isolated: one that raises is reported as a finding
    against itself rather than failing the whole upload.
    """
    results: list[ValidationResult] = []
    for validator in VALIDATORS:
        try:
            results.extend(validator.validate(document))
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            results.append(
                ValidationResult(
                    code=None,
                    severity=Severity.ERROR,
                    message=(
                        f"Validator {validator.name!r} failed to run: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    validator=validator.name,
                )
            )
    return results


def validator_catalogue() -> dict[str, dict[str, str]]:
    """Name and rationale for every registered validator."""
    return {
        v.name: {"name": v.name, "rationale": v.rationale} for v in VALIDATORS
    }
