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

export type TraceabilityEntry = {
  asset_id: string;
  asset_name?: string;
  environment?: string;
  risk_code?: string;
  risk_title?: string;
  requirement_key?: string;
  requirement_title?: string;
  measure_title?: string;
  source?: string;
  method?: string;
  explanation?: string | null;
  confidence?: number | null;
  network_zone?: string | null;
  ot_constraints?: string | null;
  compensating_measure?: string | null;
};

export type TraceabilityMap = {
  entries: TraceabilityEntry[];
};

export type AnalysisMeta = {
  source_hash: string;
  generated_at: string;
  tracked_sections: string[];
};

/** Соответствует backend AiAnalysisEnrichment */
export type NlpEntityItem = {
  type: string;
  value: string;
  source_field: string;
};

export type NlpRelationItem = {
  subject: string;
  relation: string;
  object: string;
  source_field: string;
};

export type AiAnalysisEnrichment = {
  risk_explanations: Record<string, string>;
  link_explanations: Record<string, string>;
  notes_summary: string | null;
  normalized_text: Record<string, unknown> | null;
  entities: NlpEntityItem[] | null;
  relations: NlpRelationItem[] | null;
  llm_used: boolean;
  model: string | null;
  generated_at: string | null;
};

/** Соответствует backend ClassifiedAssetItem */
export type ClassifiedAssetItem = {
  asset_id: string;
  environment: string;
  original_criticality: string;
  effective_criticality: string;
  usage_count: number;
  notes: string[];
};

/** Соответствует backend RiskItem */
export type RiskItem = {
  asset_id: string;
  risk_code: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical" | string;
};

/** Соответствует backend AnalysisLinkItem */
export type AnalysisLinkItem = {
  asset_id: string;
  risk: string;
  requirement: string;
  measure: string;
};

export type AnalysisReport = {
  assets: Record<string, unknown>[];
  classified_assets: ClassifiedAssetItem[];
  risks: RiskItem[];
  requirements: string[];
  measures: string[];
  links: AnalysisLinkItem[];
  warnings: string[];
  ai_enrichment?: AiAnalysisEnrichment | null;
  traceability_map?: TraceabilityMap | null;
  analysis_meta?: AnalysisMeta | null;
};

export type AnalysisDiffPayload = {
  has_changes: boolean;
  summary: string[];
  added_risks: Record<string, unknown>[];
  removed_risks: Record<string, unknown>[];
  added_measures: string[];
  removed_measures: string[];
  added_traceability_entries: Record<string, unknown>[];
  removed_traceability_entries: Record<string, unknown>[];
  policy_sections_changed: string[];
};

export type QuestionnaireAnalysisDiffResponse = {
  analysis_stale: boolean;
  stored_source_hash: string | null;
  projected_source_hash: string | null;
  diff: AnalysisDiffPayload;
};

export type QuestionnaireAnalyzeResponse = {
  validation: ValidationResult | null;
  report: AnalysisReport | null;
};

export type WorkflowRole = "security_analyst" | "department_head" | "approver";

export type WorkflowAction = "submit_for_review" | "approve" | "reject" | "revise";

export type WorkflowStatusMvp =
  | "draft"
  | "analyzed"
  | "under_review"
  | "approved"
  | "needs_revision";

export type WorkflowLogEntry = {
  timestamp: string;
  action: string;
  from_status: string;
  to_status: string;
  actor: string;
  role: string;
  comment: string;
};

export type QuestionnaireWorkflowStateRead = {
  workflow_status: WorkflowStatusMvp;
  questionnaire_status: QuestionnaireStatus;
  workflow_log: WorkflowLogEntry[];
  analysis_stale: boolean;
  has_analysis: boolean;
  revision_feedback: string | null;
  allowed_actions: WorkflowAction[];
};

export type WorkflowActionRequestBody = {
  action: WorkflowAction;
  comment?: string;
  actor: string;
  role: WorkflowRole;
};

export type WorkflowActionResponse = {
  workflow_status: WorkflowStatusMvp;
  questionnaire_status: QuestionnaireStatus;
  workflow_log: WorkflowLogEntry[];
  message: string;
};

export type ExplanationAssetRef = {
  id: string;
  name?: string;
  environment?: string;
};

export type ExplanationPayload = {
  kind: "risk" | "traceability";
  target_key: string;
  title: string;
  asset: ExplanationAssetRef | null;
  processes: string[];
  incidents: string[];
  access_matrix_hints: string[];
  rules: string[];
  source: "rule_based" | "hybrid" | "ai_enrichment";
  method: string;
  llm_explanation: string | null;
  confidence: number | null;
  network_zone?: string | null;
  ot_constraints?: string | null;
  compensating_measure?: string | null;
  requirement_title?: string | null;
  measure_title?: string | null;
  risk_code?: string | null;
  risk_title?: string | null;
};

export type ExplanationRequestBody = {
  kind: "risk" | "traceability";
  risk_key?: string | null;
  traceability_index?: number | null;
};

export type AnalysisRiskRow = {
  asset_id: string;
  risk_code: string;
  title: string;
  severity?: string;
};

/** OT-поля актива в снимке analysis_result.assets (совместимо с анкетой) */
export type AnalysisAssetSnapshot = Record<string, unknown> & {
  id?: string;
  name?: string;
  asset_type?: string;
  criticality?: string;
  network_zone?: string;
  vendor?: string;
  protocols?: string;
  supports_mfa?: boolean;
  supports_patching?: boolean;
  availability_class?: string;
  safety_critical?: boolean;
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
