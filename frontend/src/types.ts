export type SeverityLevel = "info" | "warning" | "error";

export interface Address {
  code: string;
  torque: number | null;
  torque_raw: string | null;
  notes: string | null;
  start_date: string | null;
  end_date: string | null;
  position: number;
}

export interface Validation {
  code: string | null;
  severity: SeverityLevel;
  message: string;
  validator: string;
  expected: string | null;
  actual: string | null;
}

export interface ValidatorInfo {
  name: string;
  rationale: string;
}

export interface Summary {
  error: number;
  warning: number;
  info: number;
  total: number;
  addresses: number;
}

export interface ValidationReport {
  report_id?: number;
  created_at?: string;
  filename: string;
  document_date: string | null;
  notes: string | null;
  addresses: Address[];
  validations: Validation[];
  /** Rationale per validator, sent once rather than on every finding. */
  validators: Record<string, ValidatorInfo>;
  summary: Summary;
}

export interface ReportSummaryRow {
  id: number;
  filename: string;
  created_at: string;
  document_date: string | null;
  address_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
}

export const SEVERITY_ORDER: Record<SeverityLevel, number> = {
  error: 0,
  warning: 1,
  info: 2,
};

export const SEVERITY_COLORS: Record<
  SeverityLevel,
  { bg: string; border: string; text: string }
> = {
  error: { bg: "#fdecea", border: "#d93025", text: "#a50e0e" },
  warning: { bg: "#fef7e0", border: "#f9ab00", text: "#8a6400" },
  info: { bg: "#e8f0fe", border: "#1a73e8", text: "#174ea6" },
};
