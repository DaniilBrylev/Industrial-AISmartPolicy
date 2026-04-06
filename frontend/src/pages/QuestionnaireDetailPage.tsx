import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ExplainabilityModal } from "@/features/questionnaire/ExplainabilityModal";
import { ResponseDataForm } from "@/features/questionnaire/ResponseDataForm";
import { coerceAnalysisReport, parseAnalysisReportJson } from "@/features/questionnaire/parseAnalysisReport";
import { AnalysisDiffPanel } from "@/features/questionnaire/workspace/AnalysisDiffPanel";
import { AnalysisMetaCard } from "@/features/questionnaire/workspace/AnalysisMetaCard";
import { AiEnrichmentPanel } from "@/features/questionnaire/workspace/AiEnrichmentPanel";
import { AnalysisStructuredGrid } from "@/features/questionnaire/workspace/AnalysisStructuredGrid";
import { OtSummaryCard } from "@/features/questionnaire/workspace/OtSummaryCard";
import { PolicySection } from "@/features/questionnaire/workspace/PolicySection";
import { QuestionnaireWorkspace } from "@/features/questionnaire/workspace/QuestionnaireWorkspace";
import { WorkflowSection } from "@/features/questionnaire/workspace/WorkflowSection";
import { XaiSection } from "@/features/questionnaire/workspace/XaiSection";
import type { LongRunningQuestionnaireOp } from "@/features/questionnaire/workspace/longRunning";
import type { WorkspaceTabId } from "@/features/questionnaire/workspace/tabs";
import {
  emptyFormResponseData,
  formToSavePayload,
  parseResponseDataFromServer,
  type FormResponseData,
} from "@/features/questionnaire/responseData";
import { getOtIndustrialDemoData } from "@/features/questionnaire/otDemoScenario";
import { getDepartment } from "@/shared/api/departments";
import { downloadPolicyDocx } from "@/shared/api/files";
import { fetchHealth } from "@/shared/api/health";
import { formatApiError } from "@/shared/api/http";
import {
  analyzeQuestionnaire,
  approveQuestionnaire,
  generateQuestionnairePolicy,
  getQuestionnaire,
  getQuestionnaireAnalysisDiff,
  getQuestionnaireResponse,
  getQuestionnaireWorkflow,
  postQuestionnaireExplanation,
  postQuestionnaireWorkflowAction,
  reopenQuestionnaireDraft,
  returnQuestionnaireForRevision,
  saveQuestionnaireResponse,
  submitQuestionnaire,
  validateQuestionnaire,
} from "@/shared/api/questionnaires";
import type {
  AnalysisReport,
  AnalysisRiskRow,
  ExplanationPayload,
  ExplanationRequestBody,
  QuestionnaireAnalysisDiffResponse,
  QuestionnaireAnalyzeResponse,
  QuestionnairePolicyGenerateResponse,
  QuestionnaireRead,
  QuestionnaireWorkflowStateRead,
  ValidationResult,
  WorkflowAction,
  WorkflowRole,
} from "@/shared/api/types";
import { PageStatus } from "@/shared/ui/PageStatus";

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function QuestionnaireDetailPage() {
  const { id: idParam } = useParams();
  const id = Number(idParam);

  const [q, setQ] = useState<QuestionnaireRead | null>(null);
  const [deptLabel, setDeptLabel] = useState<string>("");
  const [formData, setFormData] = useState<FormResponseData>(emptyFormResponseData);
  const [revisionFeedback, setRevisionFeedback] = useState<string | null>(null);
  const [analysisJson, setAnalysisJson] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [longRunOp, setLongRunOp] = useState<LongRunningQuestionnaireOp | null>(null);

  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<QuestionnaireAnalyzeResponse | null>(null);

  const [policyHtml, setPolicyHtml] = useState<string | null>(null);
  const [policyGen, setPolicyGen] = useState<QuestionnairePolicyGenerateResponse | null>(null);
  const [policyDocId, setPolicyDocId] = useState("");
  const [revisionReason, setRevisionReason] = useState("");
  const [analysisStale, setAnalysisStale] = useState(false);

  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTabId>("data");
  const [diffData, setDiffData] = useState<QuestionnaireAnalysisDiffResponse | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);

  const [llmGlobal, setLlmGlobal] = useState<boolean | null>(null);

  const [workflowRole, setWorkflowRole] = useState<WorkflowRole>("security_analyst");
  const [workflowActor, setWorkflowActor] = useState("user_1");
  const [workflowComment, setWorkflowComment] = useState("");
  const [workflowState, setWorkflowState] = useState<QuestionnaireWorkflowStateRead | null>(null);

  const canEditResponses = q?.status === "draft" || q?.status === "needs_revision";

  const report = useMemo((): AnalysisReport | null => {
    if (analyzeResult?.report) return coerceAnalysisReport(analyzeResult.report);
    return parseAnalysisReportJson(analysisJson);
  }, [analyzeResult?.report, analysisJson]);

  const analysisRiskRows = useMemo((): AnalysisRiskRow[] => {
    if (!report?.risks) return [];
    return report.risks.map((r) => ({
      asset_id: r.asset_id,
      risk_code: r.risk_code,
      title: r.title,
      severity: r.severity,
    }));
  }, [report]);

  const traceabilityRows = useMemo(() => report?.traceability_map?.entries ?? [], [report]);

  const lastAnalysisUsedLlm = Boolean(report?.ai_enrichment?.llm_used);

  const [xaiOpen, setXaiOpen] = useState(false);
  const [xaiPayload, setXaiPayload] = useState<ExplanationPayload | null>(null);
  const [xaiError, setXaiError] = useState<string | null>(null);
  const [xaiLoading, setXaiLoading] = useState(false);

  const requestExplanation = useCallback(
    async (body: ExplanationRequestBody) => {
      if (!Number.isFinite(id) || id < 1) return;
      setXaiOpen(true);
      setXaiPayload(null);
      setXaiError(null);
      setXaiLoading(true);
      try {
        const p = await postQuestionnaireExplanation(id, body);
        setXaiPayload(p);
      } catch (e) {
        setXaiError(formatApiError(e));
      } finally {
        setXaiLoading(false);
      }
    },
    [id],
  );

  const loadDiff = useCallback(async () => {
    if (!Number.isFinite(id) || id < 1) return;
    setDiffLoading(true);
    setDiffError(null);
    try {
      const d = await getQuestionnaireAnalysisDiff(id);
      setDiffData(d);
    } catch (e) {
      setDiffError(formatApiError(e));
    } finally {
      setDiffLoading(false);
    }
  }, [id]);

  const openDiffTab = useCallback(() => {
    setWorkspaceTab("diff");
    void loadDiff();
  }, [loadDiff]);

  const reload = useCallback(async () => {
    if (!Number.isFinite(id) || id < 1) return;
    setLoading(true);
    setError(null);
    try {
      const h = await fetchHealth().catch(() => null);
      setLlmGlobal(h?.llm_enabled ?? null);

      const [meta, respRow] = await Promise.all([getQuestionnaire(id), getQuestionnaireResponse(id)]);
      setQ(meta);
      try {
        const d = await getDepartment(meta.department_id);
        setDeptLabel(d.name);
      } catch {
        setDeptLabel(`подразделение #${meta.department_id}`);
      }
      if (respRow) {
        const rd = respRow.response_data as Record<string, unknown>;
        setFormData(parseResponseDataFromServer(rd));
        setRevisionFeedback(typeof rd.revision_feedback === "string" ? rd.revision_feedback : null);
        const ar = rd.analysis_result;
        setAnalysisJson(ar !== undefined ? JSON.stringify(ar, null, 2) : null);
        setAnalysisStale(rd.analysis_stale === true);
        try {
          const w = await getQuestionnaireWorkflow(id, workflowRole);
          setWorkflowState(w);
        } catch {
          setWorkflowState(null);
        }
      } else {
        setFormData(emptyFormResponseData());
        setRevisionFeedback(null);
        setAnalysisJson(null);
        setAnalysisStale(false);
        setWorkflowState(null);
      }
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [id, workflowRole]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onSave() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      await saveQuestionnaireResponse(id, { response_data: formToSavePayload(formData) });
      setActionMsg("Сохранено.");
      await reload();
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onValidate() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const r = await validateQuestionnaire(id);
      setValidationResult(r);
      setActionMsg(r.is_valid ? "Проверка пройдена." : "Есть ошибки валидации.");
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onAnalyze() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setLongRunOp("analyze");
    setActionMsg(null);
    try {
      const r = await analyzeQuestionnaire(id);
      setAnalyzeResult(r);
      if (r.report) {
        setActionMsg("Анализ выполнен.");
        await reload();
        setWorkspaceTab("analysis");
      } else {
        setActionMsg("Анализ не выполнен: проверьте данные анкеты.");
      }
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
      setLongRunOp(null);
    }
  }

  async function onSubmit() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const r = await submitQuestionnaire(id);
      setActionMsg(r.message);
      await reload();
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onReopenDraft() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const r = await reopenQuestionnaireDraft(id);
      setActionMsg(r.message);
      await reload();
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onApprove() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const r = await approveQuestionnaire(id);
      setActionMsg(r.message);
      await reload();
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onReturnRevision() {
    if (!Number.isFinite(id) || id < 1) return;
    if (!revisionReason.trim()) {
      setActionMsg("Укажите причину возврата.");
      return;
    }
    setBusy(true);
    setActionMsg(null);
    try {
      const r = await returnQuestionnaireForRevision(id, revisionReason.trim());
      setActionMsg(r.message);
      setRevisionReason("");
      await reload();
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onGeneratePolicy() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setLongRunOp("generate_policy");
    setActionMsg(null);
    try {
      const pid = policyDocId.trim() ? Number(policyDocId.trim()) : undefined;
      const out = await generateQuestionnairePolicy(
        id,
        pid !== undefined && Number.isFinite(pid) && pid > 0 ? pid : null,
      );
      setPolicyGen(out);
      setPolicyHtml(out.html_preview);
      setActionMsg("Политика сгенерирована.");
      setWorkspaceTab("policy");
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
      setLongRunOp(null);
    }
  }

  async function onDownloadDocx() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const blob = await downloadPolicyDocx(id);
      triggerBlobDownload(blob, `policy_questionnaire_${id}.docx`);
      setActionMsg("DOCX загружен.");
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onWorkflowAction(action: WorkflowAction) {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      await postQuestionnaireWorkflowAction(id, {
        action,
        comment: workflowComment.trim(),
        actor: workflowActor.trim() || "anonymous",
        role: workflowRole,
      });
      setWorkflowComment("");
      setActionMsg("Действие workflow выполнено.");
      await reload();
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  if (!Number.isFinite(id) || id < 1) {
    return <p className="muted">Некорректный идентификатор анкеты.</p>;
  }

  const deptLine = deptLabel || "";

  return (
    <>
      <ExplainabilityModal
        open={xaiOpen}
        onClose={() => setXaiOpen(false)}
        payload={xaiPayload}
        error={xaiError}
        loading={xaiLoading}
      />
      <p className="workspaceBack">
        <Link to="/questionnaires">← К списку анкет</Link>
      </p>

      <PageStatus loading={loading} error={error} empty={false}>
        {q && (
          <QuestionnaireWorkspace
            tab={workspaceTab}
            onTabChange={setWorkspaceTab}
            questionnaire={q}
            departmentLabel={deptLine}
            workflowState={workflowState}
            analysisStale={analysisStale}
            llmEnabledGlobally={llmGlobal}
            lastAnalysisUsedLlm={lastAnalysisUsedLlm}
            busy={busy}
            canEditResponses={canEditResponses}
            onSave={() => void onSave()}
            onValidate={() => void onValidate()}
            onAnalyze={() => void onAnalyze()}
            onOpenDiff={openDiffTab}
            onGeneratePolicy={() => void onGeneratePolicy()}
            onDownloadDocx={() => void onDownloadDocx()}
            diffLoading={diffLoading}
            longRunningOp={longRunOp}
            panels={{
              data: (
                <>
                  {actionMsg && (
                    <div
                      className={
                        actionMsg.includes("HTTP") || actionMsg.includes("Ошибка") || actionMsg.includes("detail")
                          ? "callout calloutError"
                          : "callout calloutOk"
                      }
                      style={{ marginBottom: 16 }}
                    >
                      {actionMsg}
                    </div>
                  )}
                  {revisionFeedback && (
                    <div className="callout" style={{ marginBottom: 16 }}>
                      <strong>Комментарий при возврате</strong>
                      <div style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{revisionFeedback}</div>
                    </div>
                  )}
                  {validationResult && (
                    <div className="card formCard">
                      <h3 className="cardTitle">Результат проверки</h3>
                      <p>
                        <span className={validationResult.is_valid ? "badge badgeOk" : "badge badgeErr"}>
                          {validationResult.is_valid ? "Допустимо" : "Есть ошибки"}
                        </span>
                      </p>
                      {validationResult.errors.length > 0 && (
                        <ul className="diffList">
                          {validationResult.errors.map((e, i) => (
                            <li key={i}>
                              <code>{e.field}</code> — {e.message}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  <div className="card formCard">
                    <h3 className="cardTitle">Секции анкеты</h3>
                    <p className="cardHint">
                      Сохраните изменения перед анализом. Редактирование доступно в статусах черновика и доработки.
                    </p>
                    <ResponseDataForm data={formData} setData={setFormData} disabled={!canEditResponses || busy} />
                  </div>
                  <div className="card">
                    <h3 className="cardTitle">Дополнительные операции</h3>
                    <p className="cardHint">
                      Классический жизненный цикл анкеты (параллельно workflow): отправка, утверждение, возврат.
                    </p>
                    <div className="workspaceToolbar" style={{ border: "none", paddingTop: 0 }}>
                      <button
                        type="button"
                        className="btn btnSecondary"
                        disabled={busy || !canEditResponses}
                        onClick={() => {
                          setFormData(getOtIndustrialDemoData());
                          setActionMsg("Загружен демо-сценарий OT. Сохраните и выполните анализ.");
                        }}
                      >
                        Демо OT
                      </button>
                      <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onSubmit()}>
                        Отправить (legacy)
                      </button>
                      <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onReopenDraft()}>
                        В черновик
                      </button>
                      <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onApprove()}>
                        Утвердить (legacy)
                      </button>
                    </div>
                    <div className="inlineForm" style={{ marginTop: 12 }}>
                      <input
                        className="input"
                        style={{ flex: "1 1 220px" }}
                        value={revisionReason}
                        onChange={(e) => setRevisionReason(e.target.value)}
                        placeholder="Причина возврата"
                        disabled={busy}
                      />
                      <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onReturnRevision()}>
                        Вернуть на доработку
                      </button>
                    </div>
                  </div>
                </>
              ),
              analysis: report ? (
                <>
                  {analyzeResult?.validation && !analyzeResult.report && (
                    <div className="card">
                      <h3 className="cardTitle">Последний запуск анализа не сохранён</h3>
                      <p className="cardHint">Исправьте ошибки валидации и повторите анализ.</p>
                      <ul className="diffList">
                        {analyzeResult.validation.errors.map((e, i) => (
                          <li key={i}>
                            <code>{e.field}</code> — {e.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <AnalysisMetaCard report={report} analysisStale={analysisStale} />
                  <AnalysisStructuredGrid report={report} />
                  <OtSummaryCard report={report} />
                  <AiEnrichmentPanel enrichment={report.ai_enrichment} />
                  <details className="debugDisclosure card" style={{ padding: 16 }}>
                    <summary>Отладка: сырой JSON analysis_result</summary>
                    <pre className="debugPre" style={{ marginTop: 12 }}>
                      {analysisJson ?? JSON.stringify(analyzeResult?.report, null, 2)}
                    </pre>
                  </details>
                </>
              ) : (
                <div className="card">
                  <div className="emptyState">
                    Нет сохранённого анализа. Нажмите «Анализировать» в шапке — отчёт появится в этой вкладке.
                  </div>
                </div>
              ),
              diff: (
                <AnalysisDiffPanel
                  data={diffData}
                  loading={diffLoading}
                  error={diffError}
                  onRefresh={() => void loadDiff()}
                  disabled={busy}
                />
              ),
              xai: (
                <XaiSection
                  analysisRiskRows={analysisRiskRows}
                  traceabilityRows={traceabilityRows}
                  busy={busy}
                  onExplain={(b) => void requestExplanation(b)}
                />
              ),
              workflow: (
                <WorkflowSection
                  workflowState={workflowState}
                  workflowRole={workflowRole}
                  setWorkflowRole={setWorkflowRole}
                  workflowActor={workflowActor}
                  setWorkflowActor={setWorkflowActor}
                  workflowComment={workflowComment}
                  setWorkflowComment={setWorkflowComment}
                  busy={busy}
                  onWorkflowAction={(a) => void onWorkflowAction(a)}
                />
              ),
              policy: (
                <PolicySection
                  analysisStale={analysisStale}
                  policyDocId={policyDocId}
                  setPolicyDocId={setPolicyDocId}
                  policyHtml={policyHtml}
                  policyGen={policyGen}
                  busy={busy}
                />
              ),
            }}
          />
        )}
      </PageStatus>
    </>
  );
}
