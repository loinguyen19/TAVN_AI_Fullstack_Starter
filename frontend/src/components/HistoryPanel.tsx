import type { ReportSummaryRow } from "../types";

interface Props {
  rows: ReportSummaryRow[];
  currentId?: number;
  onOpen: (id: number) => void;
  onRefresh: () => void;
}

const cell: React.CSSProperties = {
  padding: "6px 9px",
  borderBottom: "1px solid #eee",
  fontSize: 13,
};

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default function HistoryPanel({
  rows,
  currentId,
  onOpen,
  onRefresh,
}: Props) {
  return (
    <section style={{ marginTop: 28 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h3 style={{ margin: 0 }}>Upload history ({rows.length})</h3>
        <button
          onClick={onRefresh}
          style={{
            cursor: "pointer",
            fontSize: 12,
            padding: "3px 9px",
            borderRadius: 5,
            border: "1px solid #ccc",
            background: "#fff",
          }}
        >
          refresh
        </button>
      </div>

      {rows.length === 0 ? (
        <p style={{ color: "#666", fontSize: 13 }}>
          No previous uploads yet. Upload a file to start the history.
        </p>
      ) : (
        <table
          style={{
            borderCollapse: "collapse",
            width: "100%",
            border: "1px solid #ddd",
            background: "#fff",
            marginTop: 8,
          }}
        >
          <thead>
            <tr style={{ background: "#fafafa", textAlign: "left" }}>
              <th style={{ ...cell, width: 45 }}>#</th>
              <th style={cell}>File</th>
              <th style={{ ...cell, width: 165 }}>Uploaded</th>
              <th style={{ ...cell, width: 70 }}>Entries</th>
              <th style={{ ...cell, width: 150 }}>Findings</th>
              <th style={{ ...cell, width: 130 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                style={{ background: row.id === currentId ? "#e8f0fe" : undefined }}
              >
                <td style={cell}>{row.id}</td>
                <td style={{ ...cell, fontFamily: "monospace", fontSize: 12 }}>
                  {row.filename}
                </td>
                <td style={cell}>{formatTimestamp(row.created_at)}</td>
                <td style={cell}>{row.address_count}</td>
                <td style={cell}>
                  <span style={{ color: "#a50e0e" }}>{row.error_count}E</span>{" "}
                  <span style={{ color: "#8a6400" }}>{row.warning_count}W</span>{" "}
                  <span style={{ color: "#174ea6" }}>{row.info_count}I</span>
                </td>
                <td style={cell}>
                  <button
                    onClick={() => onOpen(row.id)}
                    style={{
                      cursor: "pointer",
                      fontSize: 12,
                      padding: "3px 8px",
                      marginRight: 6,
                      borderRadius: 5,
                      border: "1px solid #ccc",
                      background: "#fff",
                    }}
                  >
                    view
                  </button>
                  <a
                    href={`/api/reports/${row.id}/export.csv`}
                    download
                    style={{ fontSize: 12 }}
                  >
                    CSV
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
