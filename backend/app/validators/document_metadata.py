import re

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# {Manufacturer}-{Manufacturer}-{ManufacturerCode}{MainGroup}{SubGroup}-{Series}_{Variant}.xml
# e.g. AZD-AZD-AZDMUC4161-F01_RBU.xml
FILENAME_RE = re.compile(
    r"^(?P<mfr>[A-Z0-9]+)-(?P<mfr2>[A-Z0-9]+)-"
    r"(?P<code>[A-Z]+)(?P<main>\d{2})(?P<sub>\d{2})-"
    r"(?P<series>[A-Z0-9]+)_(?P<variant>[A-Z0-9]+)\.xml$",
    re.IGNORECASE,
)

REQUIRED_DOC_FIELDS = (
    ("document_date", "DocumentDate"),
    ("manufacturer", "Manufacturer"),
    ("series", "Series"),
    ("main_group", "MainGroup"),
    ("sub_group", "SubGroup"),
)


class DocumentMetadataValidator(BaseValidator):
    """Cross-checks the filename against the metadata inside the document.

    Filenames encode the manufacturer, group and series, and downstream systems
    route on them. A mismatch means the file is filed under the wrong part of
    the catalogue even though its contents are correct.
    """

    rationale = (
        "Workshop systems locate a torque sheet by its filename; if that disagrees "
        "with the metadata inside, the correct data is served for the wrong vehicle."
    )

    @property
    def name(self) -> str:
        return "document_metadata"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []

        for attribute, element in REQUIRED_DOC_FIELDS:
            if not getattr(document, attribute):
                issues.append(
                    ValidationResult(
                        code=None,
                        severity=Severity.WARNING,
                        message=f"Document is missing its <{element}> value.",
                        validator=self.name,
                        expected=f"a non-empty <{element}>",
                        actual="empty or absent",
                    )
                )

        match = FILENAME_RE.match(document.filename)
        if not match:
            issues.append(
                ValidationResult(
                    code=None,
                    severity=Severity.INFO,
                    message=(
                        f"Filename {document.filename!r} does not follow the "
                        f"convention "
                        f"{{Manufacturer}}-{{Manufacturer}}-{{Code}}{{MainGroup}}"
                        f"{{SubGroup}}-{{Series}}_{{Variant}}.xml, so filename and "
                        f"content could not be cross-checked."
                    ),
                    validator=self.name,
                    expected="MFR-MFR-CODEmmss-SERIES_VARIANT.xml",
                    actual=document.filename,
                )
            )
            return issues

        for group, attribute, label in (
            ("mfr", "manufacturer", "Manufacturer"),
            ("main", "main_group", "MainGroup"),
            ("sub", "sub_group", "SubGroup"),
            ("series", "series", "Series"),
        ):
            from_name = match.group(group)
            from_doc = getattr(document, attribute)
            if from_doc is None:
                continue
            if from_name.upper() != str(from_doc).upper():
                issues.append(
                    ValidationResult(
                        code=None,
                        severity=Severity.WARNING,
                        message=(
                            f"Filename encodes {label} {from_name!r} but the document "
                            f"declares {from_doc!r}."
                        ),
                        validator=self.name,
                        expected=f"{label} {from_name!r} (from filename)",
                        actual=f"{from_doc!r} (from document)",
                    )
                )
        return issues
