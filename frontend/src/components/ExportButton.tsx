interface Props {
  reportId?: number;
}

/**
 * A plain anchor, so the browser handles the download and the
 * Content-Disposition filename from the API is respected.
 */
export default function ExportButton({ reportId }: Props) {
  if (reportId === undefined) return null;
  return (
    <a
      href={`/api/reports/${reportId}/export.csv`}
      download
      style={{
        display: "inline-block",
        padding: "6px 12px",
        borderRadius: 6,
        border: "1px solid #1a73e8",
        background: "#1a73e8",
        color: "#fff",
        textDecoration: "none",
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      Download CSV
    </a>
  );
}
