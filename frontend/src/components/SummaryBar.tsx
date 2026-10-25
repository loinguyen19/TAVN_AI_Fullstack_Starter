import type { SeverityLevel, Summary } from "../types";
import { SEVERITY_COLORS } from "../types";

interface Props {
  summary: Summary;
  active: Set<SeverityLevel>;
  onToggle: (severity: SeverityLevel) => void;
}

const LEVELS: SeverityLevel[] = ["error", "warning", "info"];

export default function SummaryBar({ summary, active, onToggle }: Props) {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      {LEVELS.map((level) => {
        const c = SEVERITY_COLORS[level];
        const on = active.has(level);
        return (
          <button
            key={level}
            onClick={() => onToggle(level)}
            title={`Click to ${on ? "hide" : "show"} ${level} findings`}
            style={{
              cursor: "pointer",
              padding: "6px 12px",
              borderRadius: 16,
              border: `1px solid ${on ? c.border : "#ccc"}`,
              background: on ? c.bg : "#f5f5f5",
              color: on ? c.text : "#888",
              fontWeight: 600,
              fontSize: 13,
              opacity: on ? 1 : 0.65,
            }}
          >
            {summary[level]} {level}
            {summary[level] === 1 ? "" : "s"}
          </button>
        );
      })}
      <span style={{ color: "#555", fontSize: 13, marginLeft: 4 }}>
        {summary.total} finding{summary.total === 1 ? "" : "s"} across{" "}
        {summary.addresses} entries
      </span>
    </div>
  );
}
