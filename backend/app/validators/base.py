from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel
from ..parser import TorqueDocument


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationResult(BaseModel):
    code: str | None = None  # address code, None for document-level issues
    severity: Severity
    message: str
    validator: str  # name of the validator that produced this


class BaseValidator(ABC):
    """Base class for all validators.

    To add a new validator:
    1. Create a new file in this directory
    2. Subclass BaseValidator
    3. Implement the validate() method
    4. Register it in registry.py
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this validator."""
        ...

    @abstractmethod
    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        """Run validation on the document. Return a list of issues found."""
        ...
