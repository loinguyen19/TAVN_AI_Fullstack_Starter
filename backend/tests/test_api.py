"""API: success paths and the failure paths that matter."""

from tests.conftest import SAMPLE_NAME, address, build_xml


def upload(client, content: bytes, filename: str = "test.xml"):
    return client.post(
        "/api/reports",
        files={"file": (filename, content, "application/xml")},
    )


# ── success ──────────────────────────────────────────────────────────────

def test_upload_sample_returns_expected_shape(client, sample_bytes):
    response = upload(client, sample_bytes, SAMPLE_NAME)
    assert response.status_code == 201

    body = response.json()
    assert body["summary"] == {
        "error": 5,
        "warning": 5,
        "info": 10,
        "total": 20,
        "addresses": 137,
    }
    assert len(body["addresses"]) == 137
    assert body["report_id"] == 1
    assert body["document_date"] == "2024-09-15"


def test_rationales_are_sent_once_not_per_finding(client, sample_bytes):
    body = upload(client, sample_bytes, SAMPLE_NAME).json()
    assert body["validators"], "validators map should be populated"
    assert all(v["rationale"] for v in body["validators"].values())
    # The sentence must not be duplicated onto every finding.
    assert all("rationale" not in f for f in body["validations"])


def test_addresses_expose_raw_torque_text(client, sample_bytes):
    body = upload(client, sample_bytes, SAMPLE_NAME).json()
    entry = next(a for a in body["addresses"] if a["code"] == "111AZ")
    assert entry["torque_raw"] == "8500"
    assert entry["torque"] == 8500.0


def test_clean_file_reports_no_findings(client):
    # Filename must follow the convention, or document_metadata (correctly)
    # reports an INFO about it.
    xml = build_xml(address(code="1AZ", torque="20,0", notes="Bonnet to hinge"))
    body = upload(client, xml, SAMPLE_NAME).json()
    assert body["summary"]["error"] == 0
    assert body["summary"]["total"] == 0


# ── history ──────────────────────────────────────────────────────────────

def test_history_is_empty_before_any_upload(client):
    assert client.get("/api/reports").json() == []


def test_history_lists_uploads_newest_first(client, sample_bytes):
    upload(client, sample_bytes, "first.xml")
    upload(client, sample_bytes, "second.xml")

    rows = client.get("/api/reports").json()
    assert [r["filename"] for r in rows] == ["second.xml", "first.xml"]
    assert rows[0]["error_count"] == 5
    assert rows[0]["address_count"] == 137


def test_stored_upload_round_trips(client, sample_bytes):
    original = upload(client, sample_bytes, SAMPLE_NAME).json()
    fetched = client.get(f"/api/reports/{original['report_id']}").json()
    assert fetched["validations"] == original["validations"]
    assert fetched["summary"] == original["summary"]


def test_history_respects_limit(client, sample_bytes):
    for _ in range(3):
        upload(client, sample_bytes)
    assert len(client.get("/api/reports?limit=2").json()) == 2


# ── CSV export ───────────────────────────────────────────────────────────

def test_csv_export_has_a_row_per_finding(client, sample_bytes):
    report_id = upload(client, sample_bytes, SAMPLE_NAME).json()["report_id"]
    response = client.get(f"/api/reports/{report_id}/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert SAMPLE_NAME.replace(".xml", "") in response.headers["content-disposition"]

    lines = response.text.strip().splitlines()
    assert len(lines) == 21  # header + 20 findings


def test_csv_starts_with_bom_for_excel(client, sample_bytes):
    report_id = upload(client, sample_bytes).json()["report_id"]
    response = client.get(f"/api/reports/{report_id}/export.csv")
    assert response.content.startswith(b"\xef\xbb\xbf")


def test_csv_joins_address_data_onto_findings(client, sample_bytes):
    report_id = upload(client, sample_bytes).json()["report_id"]
    text = client.get(f"/api/reports/{report_id}/export.csv").text
    row = next(line for line in text.splitlines() if line.startswith(f"{report_id},") and "90AZ" in line)
    assert "-8,5" in row            # torque column populated
    assert "2008-01-01" in row      # date column populated


# ── validators endpoint ──────────────────────────────────────────────────

def test_validators_endpoint_lists_rationales(client):
    body = client.get("/api/validators").json()
    assert len(body) == 11
    assert all(entry["rationale"] for entry in body.values())


# ── failure paths ────────────────────────────────────────────────────────

def test_non_xml_filename_rejected(client):
    response = upload(client, b"hello", "notes.txt")
    assert response.status_code == 400
    assert "XML" in response.json()["detail"]


def test_malformed_xml_rejected(client):
    response = upload(client, b"<TorqueDocument><Addresses>")
    assert response.status_code == 400
    assert "Failed to parse XML" in response.json()["detail"]


def test_empty_file_rejected(client):
    assert upload(client, b"").status_code == 400


def test_unparseable_torque_is_a_finding_not_an_error(client):
    """Regression: float() used to raise and 400 the whole upload."""
    xml = build_xml(address(code="5AZ", torque="n/a"))
    response = upload(client, xml)

    assert response.status_code == 201
    messages = [
        f["message"] for f in response.json()["validations"]
        if f["validator"] == "torque_value"
    ]
    assert any("not a number" in m for m in messages)


def test_document_without_notes_accepted(client):
    """Regression: a debug print used to crash on a missing <Notes>."""
    xml = build_xml(address()).replace(b"<Notes>Test document.</Notes>", b"")
    assert upload(client, xml).status_code == 201


def test_unknown_report_id_returns_404(client):
    assert client.get("/api/reports/9999").status_code == 404


def test_csv_for_unknown_report_returns_404(client):
    assert client.get("/api/reports/9999/export.csv").status_code == 404
