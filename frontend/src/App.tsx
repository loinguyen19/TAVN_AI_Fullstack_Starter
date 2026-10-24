import { useState } from "react";
import type { UploadResponse } from "./types";

export default function App() {
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Upload failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 960, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Torque Specification Validator</h1>

      <input type="file" accept=".xml" onChange={handleUpload} disabled={loading} />
      {loading && <p>Processing…</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && (
        <>
          <h2>{result.filename}</h2>
          <p>Document date: {result.document_date ?? "—"}</p>

          {/* ── Validation Results ── */}
          <h3>Validation Results ({result.validations.length})</h3>
          {result.validations.length === 0 ? (
            <p style={{ color: "green" }}>No issues found.</p>
          ) : (
            <table border={1} cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Code</th>
                  <th>Message</th>
                  <th>Validator</th>
                </tr>
              </thead>
              <tbody>
                {result.validations.map((v, i) => (
                  <tr key={i} style={{
                    background: v.severity === "error" ? "#fee" : v.severity === "warning" ? "#ffe" : "#eef",
                  }}>
                    <td>{v.severity.toUpperCase()}</td>
                    <td>{v.code ?? "—"}</td>
                    <td>{v.message}</td>
                    <td><code>{v.validator}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* ── Data Table ── */}
          <h3>Extracted Data ({result.addresses.length} entries)</h3>
          <table border={1} cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th>Code</th>
                <th>Torque (Nm)</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {result.addresses.map((a, i) => (
                <tr key={i}>
                  <td>{a.code}</td>
                  <td>{a.torque ?? "—"}</td>
                  <td>{a.start_date ?? "—"}</td>
                  <td>{a.end_date ?? "—"}</td>
                  <td>{a.notes ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
