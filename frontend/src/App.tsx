import { useCallback, useEffect, useState } from "react";
import type {
  SeverityLevel,
  ReportSummaryRow,
  ValidationReport,
} from "./types";
import SummaryBar from "./components/SummaryBar";
import ValidationPanel from "./components/ValidationPanel";
import DataTable from "./components/DataTable";
import HistoryPanel from "./components/HistoryPanel";
import ExportButton from "./components/ExportButton";

const ALL_SEVERITIES: SeverityLevel[] = ["error", "warning", "info"];

export default function App() {
  const [result, setResult] = useState<ValidationReport | null>(null);
  const [history, setHistory] = useState<ReportSummaryRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeSeverities, setActiveSeverities] = useState<Set<SeverityLevel>>(
    new Set(ALL_SEVERITIES)
  );
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch("/api/reports");
      if (res.ok) setHistory(await res.json());
    } catch {
      /* history is non-critical; leave the previous list in place */
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedCode(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/api/reports", { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Upload failed (${res.status})`);
      }
      setResult(await res.json());
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
      e.target.value = ""; // allow re-uploading the same file
    }
  };

  const openUpload = async (id: number) => {
    setError(null);
    setSelectedCode(null);
    try {
      const res = await fetch(`/api/reports/${id}`);
      if (!res.ok) throw new Error(`Could not load report ${id}`);
      setResult(await res.json());
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  const toggleSeverity = (severity: SeverityLevel) => {
    setActiveSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(severity)) next.delete(severity);
      else next.add(severity);
      return next;
    });
  };

  const selectCode = (code: string | null) => {
    setSelectedCode(code);
    if (code) {
      document
        .getElementById(`entry-${code}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div
      style={{
        maxWidth: 1100,
        margin: "2rem auto",
        padding: "0 1rem",
        fontFamily: "system-ui, sans-serif",
        color: "#202124",
      }}
    >
      <h1 style={{ marginBottom: 4 }}>Torque Specification Validator</h1>
      <p style={{ marginTop: 0, color: "#666", fontSize: 14 }}>
        Upload a torque specification XML file to check it for data quality
        issues a workshop technician should be warned about.
      </p>

      <input
        type="file"
        accept=".xml"
        onChange={handleUpload}
        disabled={loading}
      />
      {loading && <p>Processing…</p>}
      {error && (
        <p
          style={{
            color: "#a50e0e",
            background: "#fdecea",
            border: "1px solid #d93025",
            borderRadius: 6,
            padding: "8px 12px",
          }}
        >
          {error}
        </p>
      )}

      {result && (
        <>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 12,
              flexWrap: "wrap",
              marginTop: 20,
            }}
          >
            <h2 style={{ margin: 0, fontSize: 20 }}>{result.filename}</h2>
            <span style={{ color: "#666", fontSize: 13 }}>
              document date: {result.document_date ?? "—"}
              {result.report_id !== undefined && ` · upload #${result.report_id}`}
            </span>
            <span style={{ marginLeft: "auto" }}>
              <ExportButton reportId={result.report_id} />
            </span>
          </div>

          <h3 style={{ marginBottom: 8 }}>
            Validation results ({result.summary.total})
          </h3>
          {result.summary.total === 0 ? (
            <p style={{ color: "#137333" }}>No issues found.</p>
          ) : (
            <>
              <SummaryBar
                summary={result.summary}
                active={activeSeverities}
                onToggle={toggleSeverity}
              />
              <ValidationPanel
                result={result}
                activeSeverities={activeSeverities}
                onSelectCode={selectCode}
              />
            </>
          )}

          <h3 style={{ marginTop: 28, marginBottom: 8 }}>
            Extracted data ({result.addresses.length} entries)
          </h3>
          <DataTable result={result} selectedCode={selectedCode} />
        </>
      )}

      <HistoryPanel
        rows={history}
        currentId={result?.report_id}
        onOpen={openUpload}
        onRefresh={loadHistory}
      />
    </div>
  );
}
