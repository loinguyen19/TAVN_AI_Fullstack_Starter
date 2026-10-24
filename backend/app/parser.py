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


@dataclass
class TorqueDocument:
    filename: str
    document_date: Optional[str]
    notes: Optional[str]
    addresses: list[Address] = field(default_factory=list)


def parse_torque_xml(content: bytes, filename: str) -> TorqueDocument:
    """Parse a torque specification XML file into a structured document."""
    root = ET.fromstring(content)

    doc = TorqueDocument(
        filename=filename,
        document_date=_text(root, "DocumentDate"),
        notes=_text(root, "Notes"),
    )

    for addr_el in root.findall(".//Address"):
        torque_text = _text(addr_el, "Torque")
        torque = _parse_european_decimal(torque_text) if torque_text else None

        doc.addresses.append(
            Address(
                code=_text(addr_el, "Code") or "",
                torque=torque,
                notes=_text(addr_el, "Notes"),
                start_date=_text(addr_el, "StartDate"),
                end_date=_text(addr_el, "EndDate"),
            )
        )

    return doc


def _text(el: ET.Element, tag: str) -> Optional[str]:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_european_decimal(value: str) -> float:
    """Parse European decimal format (comma as separator)."""
    return float(value.replace(",", "."))


if __name__ == "__main__":
    with open("././data/AZD-AZD-AZDMUC4161-F01_RBU.xml", "rb") as f:
        document = parse_torque_xml(f.read(), f.name)
        # print(document)
    # parse_torque_xml(b"""<?xml version="1.0" encoding="UTF-8"?>)
    print(Address(
            code=None, 
            torque=None, 
            notes=None, 
            start_date=None, 
            end_date=None).__dict__)
    