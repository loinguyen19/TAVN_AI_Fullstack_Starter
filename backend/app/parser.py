from dataclasses import dataclass, field
from typing import Optional
import xml.etree.ElementTree as ET


@dataclass
class Address:
    code: str
    torque: Optional[float]
    notes: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    # Original Torque text, kept verbatim. Needed because float() erases the
    # source formatting: "8500", "8500,0" and "8500.00" all parse to 8500.0,
    # and only the raw string reveals a dropped decimal separator. It also
    # distinguishes "no Torque element" from "Torque element we could not read".
    torque_raw: Optional[str] = None
    # True when torque_raw was present but could not be parsed as a number.
    torque_parse_failed: bool = False
    # 0-based index within the document, so the UI can point at a specific row
    # (ElementTree does not expose line numbers).
    position: int = 0


@dataclass
class TorqueDocument:
    filename: str
    document_date: Optional[str]
    notes: Optional[str]
    addresses: list[Address] = field(default_factory=list)
    manufacturer: Optional[str] = None
    series: Optional[str] = None
    main_group: Optional[str] = None
    sub_group: Optional[str] = None


def parse_torque_xml(content: bytes, filename: str) -> TorqueDocument:
    """Parse a torque specification XML file into a structured document.

    Field-level problems never raise: an unreadable torque value is recorded on
    the Address so a validator can report it. Only genuinely malformed XML
    raises, which the caller turns into a 400.
    """
    root = ET.fromstring(content)

    doc = TorqueDocument(
        filename=filename,
        document_date=_text(root, "DocumentDate"),
        notes=_text(root, "Notes"),
        manufacturer=_text(root, "Manufacturer"),
        series=_text(root, "Series"),
        main_group=_text(root, "MainGroup"),
        sub_group=_text(root, "SubGroup"),
    )

    for index, addr_el in enumerate(root.findall(".//Address")):
        torque_raw = _text(addr_el, "Torque")
        torque = _parse_european_decimal(torque_raw) if torque_raw else None

        doc.addresses.append(
            Address(
                code=_text(addr_el, "Code") or "",
                torque=torque,
                notes=_text(addr_el, "Notes"),
                start_date=_text(addr_el, "StartDate"),
                end_date=_text(addr_el, "EndDate"),
                torque_raw=torque_raw,
                torque_parse_failed=torque_raw is not None and torque is None,
                position=index,
            )
        )

    return doc


def _text(el: ET.Element, tag: str) -> Optional[str]:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_european_decimal(value: str) -> Optional[float]:
    """Parse European decimal format (comma as separator).

    Returns None rather than raising: a single bad value must not fail the
    whole upload, or the validator meant to report it never runs.
    """
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None
