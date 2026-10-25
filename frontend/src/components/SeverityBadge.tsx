import type { SeverityLevel } from "../types";
import { SEVERITY_COLORS } from "../types";

export default function SeverityBadge({ severity }: { severity: SeverityLevel }) {
  const c = SEVERITY_COLORS[severity];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 10,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: 0.4,
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        whiteSpace: "nowrap",
      }}
    >
      {severity.toUpperCase()}
    </span>
  );
}
