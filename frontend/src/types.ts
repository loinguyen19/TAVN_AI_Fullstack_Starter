export interface Address {
  code: string;
  torque: number | null;
  notes: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface Validation {
  code: string | null;
  severity: "info" | "warning" | "error";
  message: string;
  validator: string;
}

export interface UploadResponse {
  filename: string;
  document_date: string | null;
  notes: string | null;
  addresses: Address[];
  validations: Validation[];
}
