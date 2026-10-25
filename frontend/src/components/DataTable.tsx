import { useMemo } from "react";
import type { SeverityLevel, ValidationReport } from "../types";
import { SEVERITY_COLORS, SEVERITY_ORDER } from "../types";

interface Props {
  result: ValidationReport;
  selectedCode: string | null;
}

const cell: React.CSSProperties = {
  padding: "6px 9px",
  borderBottom: "1px solid #eee",
  fontSize: 13,
  verticalAlign: "top",
};

export default function DataTable({ result, selectedCode }: Props) {
  // Worst severity per code, so a row can show a dot without re-scanning.
  const worstByCode = useMemo(() => {
    const map = new Map<string, SeverityLevel>();
    for (const v of result.validations) {
      if (!v.code) continue;
      const current = map.get(v.code);
      if (!current || SEVERITY_ORDER[v.severity] < SEVERITY_ORDER[current]) {
        map.set(v.code, v.severity);
      }
    }
    return map;
  }, [result.validations]);

  return (
    <table
      style={{
        borderCollapse: "collapse",
        width: "100%",
        border: "1px solid #ddd",
        background: "#fff",
      }}
    >
      <thead>
        <tr style={{ background: "#fafafa", textAlign: "left" }}>
          <th style={{ ...cell, width: 28 }} />
          <th style={{ ...cell, width: 70 }}>Code</th>
          <th style={{ ...cell, width: 95 }}>Torque (Nm)</th>
          <th style={{ ...cell, width: 100 }}>Start Date</th>
          <th style={{ ...cell, width: 100 }}>End Date</th>
          <th style={cell}>Notes</th>
        </tr>
      </thead>
      <tbody>
        {result.addresses.map((a, i) => {
          const worst = worstByCode.get(a.code);
          const selected = selectedCode !== null && a.code === selectedCode;
          return (
            <tr
              key={`${a.code}-${i}`}
              id={`entry-${a.code}`}
              style={{
                background: selected
                  ? "#fff8c4"
                  : worst
                  ? SEVERITY_COLORS[worst].bg
                  : undefined,
                outline: selected ? "2px solid #f9ab00" : undefined,
              }}
            >
              <td style={{ ...cell, textAlign: "center" }}>
                {worst && (
                  <span
                    title={`${worst} finding(s) on this entry`}
                    style={{
                      display: "inline-block",
                      width: 9,
                      height: 9,
                      borderRadius: "50%",
                      background: SEVERITY_COLORS[worst].border,
                    }}
                  />
                )}
              </td>
              <td style={{ ...cell, fontFamily: "monospace" }}>{a.code}</td>
              <td style={{ ...cell, fontFamily: "monospace" }}>
                {a.torque_raw ?? "—"}
              </td>
              <td style={cell}>{a.start_date ?? "—"}</td>
              <td style={cell}>{a.end_date ?? "—"}</td>
              <td style={cell}>{a.notes ?? ""}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
