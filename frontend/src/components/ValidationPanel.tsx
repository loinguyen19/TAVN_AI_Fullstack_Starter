import { useMemo, useState } from "react";
import type { SeverityLevel, ValidationReport, Validation } from "../types";
import { SEVERITY_COLORS, SEVERITY_ORDER } from "../types";
import SeverityBadge from "./SeverityBadge";

type GroupMode = "flat" | "code" | "validator";

interface Props {
  result: ValidationReport;
  activeSeverities: Set<SeverityLevel>;
  onSelectCode: (code: string | null) => void;
}

const cell: React.CSSProperties = {
  padding: "7px 9px",
  borderBottom: "1px solid #eee",
  verticalAlign: "top",
  fontSize: 13,
};

export default function ValidationPanel({
  result,
  activeSeverities,
  onSelectCode,
}: Props) {
  const [groupMode, setGroupMode] = useState<GroupMode>("flat");
  const [validatorFilter, setValidatorFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const validatorNames = useMemo(
    () => Object.keys(result.validators ?? {}).sort(),
    [result.validators]
  );

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return result.validations
      .filter((v) => activeSeverities.has(v.severity))
      .filter((v) => validatorFilter === "all" || v.validator === validatorFilter)
      .filter(
        (v) =>
          !needle ||
          (v.code ?? "").toLowerCase().includes(needle) ||
          v.message.toLowerCase().includes(needle) ||
          v.validator.toLowerCase().includes(needle)
      )
      .sort(
        (a, b) =>
          SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] ||
          (a.code ?? "").localeCompare(b.code ?? "", undefined, { numeric: true })
      );
  }, [result.validations, activeSeverities, validatorFilter, search]);

  const groups = useMemo(() => {
    if (groupMode === "flat") return [{ key: "", items: filtered }];
    const map = new Map<string, Validation[]>();
    for (const v of filtered) {
      const key = groupMode === "code" ? v.code ?? "(document)" : v.validator;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(v);
    }
    return [...map.entries()]
      .sort((a, b) =>
        groupMode === "code"
          ? a[0].localeCompare(b[0], undefined, { numeric: true })
          : b[1].length - a[1].length
      )
      .map(([key, items]) => ({ key, items }));
  }, [filtered, groupMode]);

  return (
    <section style={{ marginTop: 18 }}>
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          flexWrap: "wrap",
          marginBottom: 10,
        }}
      >
        <strong style={{ fontSize: 14 }}>Group by</strong>
        {(["flat", "code", "validator"] as GroupMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setGroupMode(mode)}
            style={{
              cursor: "pointer",
              padding: "5px 10px",
              borderRadius: 6,
              fontSize: 13,
              border: "1px solid #ccc",
              background: groupMode === mode ? "#1a73e8" : "#fff",
              color: groupMode === mode ? "#fff" : "#333",
            }}
          >
            {mode === "flat" ? "none" : mode}
          </button>
        ))}

        <select
          value={validatorFilter}
          onChange={(e) => setValidatorFilter(e.target.value)}
          style={{ padding: "5px 8px", fontSize: 13, marginLeft: 6 }}
        >
          <option value="all">all validators</option>
          {validatorNames.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>

        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="search code or message…"
          style={{ padding: "5px 8px", fontSize: 13, flex: "1 1 200px", minWidth: 160 }}
        />
        <span style={{ fontSize: 13, color: "#666" }}>
          {filtered.length} shown
        </span>
      </div>

      {filtered.length === 0 ? (
        <p style={{ color: "#666" }}>No findings match the current filters.</p>
      ) : (
        groups.map((group) => (
          <div key={group.key} style={{ marginBottom: 16 }}>
            {groupMode !== "flat" && (
              <div
                style={{
                  background: "#f1f3f4",
                  padding: "7px 10px",
                  borderRadius: "6px 6px 0 0",
                  border: "1px solid #ddd",
                  borderBottom: "none",
                }}
              >
                <strong style={{ fontSize: 13 }}>
                  {group.key} — {group.items.length} finding
                  {group.items.length === 1 ? "" : "s"}
                </strong>
                {groupMode === "validator" &&
                  result.validators?.[group.key]?.rationale && (
                    /* Rationale renders once per validator group, never per row. */
                    <div style={{ fontSize: 12, color: "#555", marginTop: 3 }}>
                      Why this matters: {result.validators[group.key].rationale}
                    </div>
                  )}
              </div>
            )}
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
                  <th style={{ ...cell, width: 85 }}>Severity</th>
                  <th style={{ ...cell, width: 70 }}>Code</th>
                  <th style={cell}>Message</th>
                  <th style={{ ...cell, width: 150 }}>Expected / Actual</th>
                  <th style={{ ...cell, width: 150 }}>Validator</th>
                </tr>
              </thead>
              <tbody>
                {group.items.map((v, i) => (
                  <tr
                    key={`${v.validator}-${v.code}-${i}`}
                    onClick={() => onSelectCode(v.code)}
                    style={{
                      cursor: v.code ? "pointer" : "default",
                      background: SEVERITY_COLORS[v.severity].bg,
                    }}
                    title={v.code ? "Click to highlight this entry below" : undefined}
                  >
                    <td style={cell}>
                      <SeverityBadge severity={v.severity} />
                    </td>
                    <td style={{ ...cell, fontFamily: "monospace" }}>
                      {v.code ?? "—"}
                    </td>
                    <td style={cell}>{v.message}</td>
                    <td style={{ ...cell, fontSize: 12, color: "#444" }}>
                      {v.expected || v.actual ? (
                        <>
                          <div>
                            <em>exp:</em> {v.expected ?? "—"}
                          </div>
                          <div>
                            <em>act:</em> {v.actual ?? "—"}
                          </div>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td style={{ ...cell, fontSize: 12 }}>
                      <code>{v.validator}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </section>
  );
}
