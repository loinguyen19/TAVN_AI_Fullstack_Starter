from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel
from ..parser import TorqueDocument


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


class ValidationResult(BaseModel):
    code: str | None = None  # address code, None for document-level issues
    severity: Severity
    message: str
    validator: str  # name of the validator that produced this
    # Machine-readable detail, mainly for the CSV export: a reviewer filtering
    # in a spreadsheet needs sortable columns, not a prose sentence to parse.
    # Optional because several validators have no meaningful expected value.
    expected: str | None = None
    actual: str | None = None


class BaseValidator(ABC):
    """Base class for all validators.

    To add a new validator:
    1. Create a new file in this directory
    2. Subclass BaseValidator
    3. Implement the validate() method
    4. Register it in registry.py

    `rationale` is declared once per validator class and is NOT copied onto
    each ValidationResult -- the API returns it in a separate `validators` map
    so the sentence is transmitted once rather than per finding. `message` is
    per-row and instance-specific; `rationale` is per-class and domain-level.
    """

    #: One sentence on why this class of issue is dangerous in a workshop.
    rationale: str = ""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this validator."""
        ...

    @abstractmethod
    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        """Run validation on the document. Return a list of issues found."""
        ...
