"""Validators: one focused case each, plus a golden test on the real file."""

import pytest

from app.parser import parse_torque_xml
from app.validators.base import Severity
from app.validators.registry import (
    VALIDATORS,
    run_all_validators,
    validator_catalogue,
)
from tests.conftest import address, build_xml


def findings(xml: bytes, validator_name: str, filename: str = "AZD-AZD-AZDMUC4161-F01_RBU.xml"):
    doc = parse_torque_xml(xml, filename)
    return [r for r in run_all_validators(doc) if r.validator == validator_name]


# ── missing / unusable values ────────────────────────────────────────────

def test_missing_torque_flagged():
    results = findings(build_xml(address(code="9AZ", torque=None)), "missing_torque")
    assert [r.code for r in results] == ["9AZ"]
    assert results[0].severity is Severity.ERROR


def test_unreadable_torque_is_not_reported_as_missing():
    """One defect, one owner: "n/a" is unreadable, not absent."""
    xml = build_xml(address(code="9AZ", torque="n/a"))
    assert findings(xml, "missing_torque") == []
    assert len(findings(xml, "torque_value")) == 1


def test_negative_torque_flagged():
    results = findings(build_xml(address(code="9AZ", torque="-8,5")), "torque_value")
    assert [r.code for r in results] == ["9AZ"]
    assert results[0].severity is Severity.ERROR


def test_zero_torque_flagged():
    """'Tighten to 0 Nm' specifies nothing, so the check is <= 0, not < 0."""
    results = findings(build_xml(address(torque="0,0")), "torque_value")
    assert len(results) == 1


def test_unparseable_torque_flagged():
    results = findings(build_xml(address(torque="n/a")), "torque_value")
    assert len(results) == 1 and results[0].actual == "n/a"


def test_normal_torque_not_flagged():
    assert findings(build_xml(address(torque="20,0")), "torque_value") == []


# ── plausibility ─────────────────────────────────────────────────────────

def test_torque_above_thread_band_flagged():
    results = findings(
        build_xml(address(torque="350,0", notes="Main bearing cap, M12")),
        "torque_plausibility",
    )
    assert len(results) == 1 and results[0].severity is Severity.WARNING


def test_torque_below_thread_band_flagged():
    results = findings(
        build_xml(address(torque="45,0", notes="Steering wheel to column, M16")),
        "torque_plausibility",
    )
    assert len(results) == 1 and results[0].severity is Severity.WARNING


def test_torque_inside_thread_band_not_flagged():
    assert (
        findings(build_xml(address(torque="150,0", notes="Subframe, M12")),
                 "torque_plausibility")
        == []
    )


def test_absolute_ceiling_flagged_without_thread_size():
    """The ceiling needs no M-size, which is why 8500 is an ERROR not a WARNING."""
    results = findings(
        build_xml(address(torque="8500", notes="No thread size here")),
        "torque_plausibility",
    )
    assert len(results) == 1 and results[0].severity is Severity.ERROR


def test_no_thread_size_means_no_band_check():
    assert findings(build_xml(address(torque="350,0", notes="Unspecified")),
                    "torque_plausibility") == []


# ── formatting ───────────────────────────────────────────────────────────

def test_integer_among_eu_decimals_flagged():
    entries = [address(code=f"{i}AZ", torque="20,0") for i in range(1, 20)]
    entries.append(address(code="99AZ", torque="8500"))
    results = findings(build_xml("\n".join(entries)), "decimal_format")
    assert [r.code for r in results] == ["99AZ"]


def test_negative_value_is_not_a_format_finding():
    """Regression: an unsigned pattern would duplicate the torque_value finding."""
    entries = [address(code=f"{i}AZ", torque="20,0") for i in range(1, 20)]
    entries.append(address(code="99AZ", torque="-8,5"))
    assert findings(build_xml("\n".join(entries)), "decimal_format") == []


def test_small_sample_infers_no_convention():
    assert findings(build_xml(address(torque="8500")), "decimal_format") == []


# ── validity periods ─────────────────────────────────────────────────────

def test_overlapping_periods_with_different_torque_is_error():
    xml = build_xml(
        address(code="7AZ", torque="18,5", start="2008-01-01", end="2025-12-31")
        + "\n"
        + address(code="7AZ", torque="22,0", start="2022-06-01", end="2030-12-31")
    )
    results = findings(xml, "validity_overlap")
    assert len(results) == 1 and results[0].severity is Severity.ERROR


def test_overlapping_periods_with_same_torque_is_warning():
    xml = build_xml(
        address(code="7AZ", torque="18,5", start="2008-01-01", end="2025-12-31")
        + "\n"
        + address(code="7AZ", torque="18,5", start="2022-06-01", end="2030-12-31")
    )
    results = findings(xml, "validity_overlap")
    assert len(results) == 1 and results[0].severity is Severity.WARNING


def test_adjacent_periods_are_not_an_overlap():
    """The common, correct supersession pattern must stay silent."""
    xml = build_xml(
        address(code="7AZ", torque="20,0", start="2008-01-01", end="2010-09-30")
        + "\n"
        + address(code="7AZ", torque="28,0", start="2010-10-01", end="2030-12-31")
    )
    assert findings(xml, "validity_overlap") == []


# ── notes vs dates ───────────────────────────────────────────────────────

def test_notes_period_contradicting_start_date_flagged():
    xml = build_xml(
        address(notes="Window regulator, from 07/2015", start="2014-01-01")
    )
    results = findings(xml, "notes_date_consistency")
    assert len(results) == 1
    assert results[0].expected == "2015-07-01" and results[0].actual == "2014-01-01"


def test_notes_period_matching_dates_not_flagged():
    xml = build_xml(address(notes="Hinge, to 09/2010", end="2010-09-30"))
    assert findings(xml, "notes_date_consistency") == []


# ── dates ────────────────────────────────────────────────────────────────

def test_reversed_date_range_flagged():
    xml = build_xml(address(start="2020-01-01", end="2015-01-01"))
    results = findings(xml, "date_sanity")
    assert any(r.severity is Severity.ERROR for r in results)


def test_non_iso_date_flagged():
    results = findings(build_xml(address(start="01/01/2008")), "date_sanity")
    assert any(r.severity is Severity.ERROR for r in results)


def test_expired_entry_is_info_only():
    xml = build_xml(address(start="2008-01-01", end="2012-03-31"))
    results = findings(xml, "date_sanity")
    assert [r.severity for r in results] == [Severity.INFO]


# ── required fields ──────────────────────────────────────────────────────

def test_missing_notes_flagged():
    results = findings(build_xml(address(notes=None)), "required_fields")
    assert len(results) == 1 and results[0].severity is Severity.WARNING


def test_complete_entry_not_flagged():
    assert findings(build_xml(address()), "required_fields") == []


# ── procedures and advisories ────────────────────────────────────────────

def test_step_one_without_step_two_flagged():
    xml = build_xml(address(code="81AZ", notes="Connecting rod bearing cap, step 1"))
    results = findings(xml, "incomplete_procedure")
    assert [r.code for r in results] == ["81AZ"]


def test_gap_in_step_sequence_flagged():
    """Steps 1 and 3 present, 2 missing."""
    xml = build_xml(
        address(code="81AZ", notes="Rod cap, step 1")
        + "\n"
        + address(code="83AZ", notes="Rod cap, step 3")
    )
    results = findings(xml, "incomplete_procedure")
    assert [r.code for r in results] == ["81AZ"]


def test_complete_step_sequence_not_flagged():
    xml = build_xml(
        address(code="81AZ", notes="Rod cap, step 1")
        + "\n"
        + address(code="82AZ", notes="Rod cap, step 2, 90 degrees")
    )
    assert findings(xml, "incomplete_procedure") == []


@pytest.mark.parametrize(
    "notes",
    [
        "Lever to hinge. Attention! Left-hand threads.",
        "Axle nut. Replace nut after each removal.",
        "Strut mount. Apply thread lock medium-strength.",
        "Towing eye. Apply anti-seize compound to threads.",
        "Lambda sensor (hand-tight, then 1/2 turn)",
    ],
)
def test_special_handling_detected(notes):
    assert len(findings(build_xml(address(notes=notes)), "special_handling")) >= 1


def test_ordinary_notes_produce_no_advisory():
    assert findings(build_xml(address(notes="Bonnet to hinge")), "special_handling") == []


# ── document metadata ────────────────────────────────────────────────────

def test_filename_mismatch_flagged():
    results = findings(build_xml(address()), "document_metadata",
                       filename="XXX-XXX-XXXMUC4161-F01_RBU.xml")
    assert any("Manufacturer" in r.message for r in results)


def test_matching_filename_not_flagged():
    assert findings(build_xml(address()), "document_metadata") == []


# ── registry contract ────────────────────────────────────────────────────

def test_every_validator_declares_a_rationale():
    missing = [v.name for v in VALIDATORS if not v.rationale]
    assert missing == [], f"validators without a rationale: {missing}"


def test_validator_names_are_unique():
    names = [v.name for v in VALIDATORS]
    assert len(names) == len(set(names))


def test_catalogue_covers_every_validator():
    assert set(validator_catalogue()) == {v.name for v in VALIDATORS}


def test_a_failing_validator_does_not_break_the_run(monkeypatch, sample_document):
    """One bad validator must not take down the whole upload."""
    class Exploding:
        name = "exploding"
        rationale = "test"

        def validate(self, document):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.validators.registry.VALIDATORS", [*VALIDATORS, Exploding()]
    )
    results = run_all_validators(sample_document)
    boom = [r for r in results if r.validator == "exploding"]
    assert len(boom) == 1 and "boom" in boom[0].message
    assert len(results) > 20  # the real findings still came through


# ── golden test against the real sample file ─────────────────────────────

EXPECTED_BY_VALIDATOR = {
    "missing_torque": {"103AZ"},
    "torque_value": {"90AZ"},
    "torque_plausibility": {"80AZ", "111AZ", "116AZ"},
    "decimal_format": {"111AZ"},
    "validity_overlap": {"87AZ", "126AZ"},
    "notes_date_consistency": {"126AZ"},
    "date_sanity": {"3AZ", "61AZ", "77AZ", "126AZ"},
    "required_fields": set(),
    "incomplete_procedure": {"81AZ"},
    "special_handling": {"10AZ", "53AZ", "80AZ", "97AZ", "103AZ", "130AZ"},
    "document_metadata": set(),
}


@pytest.mark.parametrize("validator_name", sorted(EXPECTED_BY_VALIDATOR))
def test_golden_findings_per_validator(sample_document, validator_name):
    """Pins the exact codes each validator reports on the real file.

    This is the regression net for the headline claim: 20 findings, no false
    positives. A change that adds or drops a finding fails here loudly.
    """
    results = run_all_validators(sample_document)
    actual = {r.code for r in results if r.validator == validator_name}
    assert actual == EXPECTED_BY_VALIDATOR[validator_name]


def test_golden_severity_counts(sample_document):
    results = run_all_validators(sample_document)
    counts = {level: 0 for level in ("error", "warning", "info")}
    for r in results:
        counts[r.severity.value] += 1
    assert counts == {"error": 5, "warning": 5, "info": 10}
    assert len(results) == 20
