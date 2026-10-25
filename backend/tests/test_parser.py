"""Parser: happy path, and the resilience the validators depend on."""

import pytest

from app.parser import parse_torque_xml
from tests.conftest import address, build_xml


def test_parses_sample_file(sample_document):
    assert len(sample_document.addresses) == 137
    assert sample_document.document_date == "2024-09-15"
    assert sample_document.manufacturer == "AZD"
    assert sample_document.series == "F01"
    assert (sample_document.main_group, sample_document.sub_group) == ("41", "61")


def test_parses_european_decimal():
    doc = parse_torque_xml(build_xml(address(torque="18,5")), "t.xml")
    assert doc.addresses[0].torque == 18.5
    assert doc.addresses[0].torque_raw == "18,5"


def test_keeps_raw_text_alongside_float():
    """float() erases formatting; decimal_format needs the original string."""
    doc = parse_torque_xml(build_xml(address(torque="8500")), "t.xml")
    assert doc.addresses[0].torque == 8500.0
    assert doc.addresses[0].torque_raw == "8500"


def test_unparseable_torque_does_not_raise():
    """A bad value must become a finding, not fail the whole upload."""
    doc = parse_torque_xml(build_xml(address(torque="n/a")), "t.xml")
    entry = doc.addresses[0]
    assert entry.torque is None
    assert entry.torque_raw == "n/a"
    assert entry.torque_parse_failed is True


def test_absent_torque_is_distinguishable_from_unparseable():
    doc = parse_torque_xml(build_xml(address(torque=None)), "t.xml")
    entry = doc.addresses[0]
    assert entry.torque is None and entry.torque_raw is None
    assert entry.torque_parse_failed is False


def test_document_without_notes_does_not_raise():
    """Regression: a debug print used to dereference <Notes> unconditionally."""
    xml = build_xml(address()).replace(b"<Notes>Test document.</Notes>", b"")
    doc = parse_torque_xml(xml, "t.xml")
    assert doc.notes is None
    assert len(doc.addresses) == 1


def test_positions_are_assigned_in_document_order():
    xml = build_xml("\n".join(address(code=f"{i}AZ") for i in range(1, 4)))
    doc = parse_torque_xml(xml, "t.xml")
    assert [a.position for a in doc.addresses] == [0, 1, 2]


def test_malformed_xml_raises():
    with pytest.raises(Exception):
        parse_torque_xml(b"<TorqueDocument><Addresses>", "broken.xml")
