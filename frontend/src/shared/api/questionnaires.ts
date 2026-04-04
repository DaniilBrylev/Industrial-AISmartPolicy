import { ApiError, apiJson } from "@/shared/api/http";
import type {
  ExplanationPayload,
  ExplanationRequestBody,
  QuestionnaireAnalysisDiffResponse,
  QuestionnaireAnalyzeResponse,
  QuestionnaireCreate,
  QuestionnairePolicyGenerateResponse,
  QuestionnaireRead,
  QuestionnaireResponseRead,
  QuestionnaireResponseSaveBody,
  QuestionnaireStatusChangeResponse,
  QuestionnaireUpdate,
  QuestionnaireWorkflowStateRead,
  ValidationResult,
  WorkflowActionRequestBody,
  WorkflowActionResponse,
  WorkflowRole,
} from "@/shared/api/types";

const base = "/api/questionnaires";

export type ListQuestionnairesParams = {
  department_id?: number;
  status?: string;
};

export function listQuestionnaires(
  params?: ListQuestionnairesParams,
): Promise<QuestionnaireRead[]> {
  const q = new URLSearchParams();
  if (params?.department_id != null) q.set("department_id", String(params.department_id));
  if (params?.status) q.set("status", params.status);
  const s = q.toString();
  return apiJson<QuestionnaireRead[]>(s ? `${base}?${s}` : base);
}

export function getQuestionnaire(id: number): Promise<QuestionnaireRead> {
  return apiJson<QuestionnaireRead>(`${base}/${id}`);
}

export function createQuestionnaire(body: QuestionnaireCreate): Promise<QuestionnaireRead> {
  return apiJson<QuestionnaireRead>(base, { method: "POST", json: body });
}

export function updateQuestionnaire(
  id: number,
  body: QuestionnaireUpdate,
): Promise<QuestionnaireRead> {
  return apiJson<QuestionnaireRead>(`${base}/${id}`, { method: "PUT", json: body });
}

export function deleteQuestionnaire(id: number): Promise<{ message: string }> {
  return apiJson<{ message: string }>(`${base}/${id}`, { method: "DELETE" });
}

export async function getQuestionnaireResponse(
  id: number,
): Promise<QuestionnaireResponseRead | null> {
  try {
    return await apiJson<QuestionnaireResponseRead>(`${base}/${id}/response`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export function saveQuestionnaireResponse(
  id: number,
  body: QuestionnaireResponseSaveBody,
): Promise<QuestionnaireResponseRead> {
  return apiJson<QuestionnaireResponseRead>(`${base}/${id}/response`, {
    method: "PUT",
    json: body,
  });
}

export function validateQuestionnaire(id: number): Promise<ValidationResult> {
  return apiJson<ValidationResult>(`${base}/${id}/validate`, { method: "POST" });
}

export function analyzeQuestionnaire(id: number): Promise<QuestionnaireAnalyzeResponse> {
  return apiJson<QuestionnaireAnalyzeResponse>(`${base}/${id}/analyze`, {
    method: "POST",
  });
}

export function getQuestionnaireAnalysisDiff(
  id: number,
): Promise<QuestionnaireAnalysisDiffResponse> {
  return apiJson<QuestionnaireAnalysisDiffResponse>(`${base}/${id}/analysis-diff`);
}

export function postQuestionnaireExplanation(
  id: number,
  body: ExplanationRequestBody,
): Promise<ExplanationPayload> {
  return apiJson<ExplanationPayload>(`${base}/${id}/explanation`, {
    method: "POST",
    json: body,
  });
}

export function getQuestionnaireWorkflow(
  id: number,
  role?: WorkflowRole | null,
): Promise<QuestionnaireWorkflowStateRead> {
  const q = role != null ? `?role=${encodeURIComponent(role)}` : "";
  return apiJson<QuestionnaireWorkflowStateRead>(`${base}/${id}/workflow${q}`);
}

export function postQuestionnaireWorkflowAction(
  id: number,
  body: WorkflowActionRequestBody,
): Promise<WorkflowActionResponse> {
  return apiJson<WorkflowActionResponse>(`${base}/${id}/workflow/action`, {
    method: "POST",
    json: body,
  });
}

export function submitQuestionnaire(id: number): Promise<QuestionnaireStatusChangeResponse> {
  return apiJson<QuestionnaireStatusChangeResponse>(`${base}/${id}/submit`, {
    method: "POST",
  });
}

export function returnQuestionnaireForRevision(
  id: number,
  reason: string,
): Promise<QuestionnaireStatusChangeResponse> {
  return apiJson<QuestionnaireStatusChangeResponse>(
    `${base}/${id}/return-for-revision`,
    { method: "POST", json: { reason } },
  );
}

export function approveQuestionnaire(id: number): Promise<QuestionnaireStatusChangeResponse> {
  return apiJson<QuestionnaireStatusChangeResponse>(`${base}/${id}/approve`, {
    method: "POST",
  });
}

export function reopenQuestionnaireDraft(
  id: number,
): Promise<QuestionnaireStatusChangeResponse> {
  return apiJson<QuestionnaireStatusChangeResponse>(`${base}/${id}/reopen-draft`, {
    method: "POST",
  });
}

export function generateQuestionnairePolicy(
  id: number,
  policyDocumentId?: number | null,
): Promise<QuestionnairePolicyGenerateResponse> {
  const q =
    policyDocumentId != null && policyDocumentId > 0
      ? `?policy_document_id=${policyDocumentId}`
      : "";
  return apiJson<QuestionnairePolicyGenerateResponse>(
    `${base}/${id}/generate-policy${q}`,
    { method: "POST" },
  );
}
