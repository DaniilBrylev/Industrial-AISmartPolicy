/** Типы ответов API (согласованы с backend Pydantic-схемами). */

export type QuestionnaireStatus = "draft" | "submitted" | "needs_revision" | "approved";

export type DepartmentRead = {
  id: number;
  name: string;
  manager_name: string;
  contact_info: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type DepartmentCreate = {
  name: string;
  manager_name: string;
  contact_info: string;
  description?: string | null;
};

export type DepartmentUpdate = Partial<DepartmentCreate>;

export type QuestionnaireRead = {
  id: number;
  title: string;
  status: QuestionnaireStatus;
  department_id: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
};

export type QuestionnaireCreate = {
  title: string;
  status?: QuestionnaireStatus;
  department_id: number;
};

export type QuestionnaireUpdate = {
  title?: string;
};

export type ValidationIssue = {
  code: string;
  field: string;
  message: string;
};

export type ValidationResult = {
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
};

export type QuestionnaireResponseRead = {
  id: number;
  questionnaire_id: number;
  response_data: Record<string, unknown>;
  validation_status: string;
  validation_errors: unknown;
  created_at: string;
  updated_at: string;
};

export type QuestionnaireResponseSaveBody = {
  response_data: Record<string, unknown>;
};

export type QuestionnaireStatusChangeResponse = {
  questionnaire_id: number;
  status: QuestionnaireStatus;
  message: string;
};

export type AnalysisReport = {
  assets: Record<string, unknown>[];
  classified_assets: unknown[];
  risks: unknown[];
  requirements: string[];
  measures: string[];
  links: unknown[];
  warnings: string[];
};

export type QuestionnaireAnalyzeResponse = {
  validation: ValidationResult | null;
  report: AnalysisReport | null;
};

export type QuestionnairePolicyVersioningInfo = {
  status: string;
  version_id: number | null;
  version_number: number | null;
  source_hash: string | null;
};

export type QuestionnairePolicyGenerateResponse = {
  html_preview: string;
  download_url: string;
  versioning: QuestionnairePolicyVersioningInfo | null;
};

export type PolicyDocumentRead = {
  id: number;
  title: string;
  status: string;
  current_version_id: number | null;
  created_at: string;
  updated_at: string;
};

export type PolicyDocumentCreate = {
  title: string;
  status?: string;
};

export type PolicyVersionSummaryRead = {
  id: number;
  policy_document_id: number;
  version_number: number;
  source_hash: string | null;
  change_summary: string | null;
  created_at: string;
};

export type DiffChunk = {
  added: string[];
  removed: string[];
  changed: string[];
};

export type PolicySnapshotDiff = {
  assets: DiffChunk;
  risks: DiffChunk;
  measures: DiffChunk;
};
