import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ResponseDataForm } from "@/features/questionnaire/ResponseDataForm";
import {
  emptyFormResponseData,
  formToSavePayload,
  parseResponseDataFromServer,
  type FormResponseData,
} from "@/features/questionnaire/responseData";
import { downloadPolicyDocx } from "@/shared/api/files";
import { formatApiError } from "@/shared/api/http";
import {
  analyzeQuestionnaire,
  approveQuestionnaire,
  generateQuestionnairePolicy,
  getQuestionnaire,
  getQuestionnaireResponse,
  reopenQuestionnaireDraft,
  returnQuestionnaireForRevision,
  saveQuestionnaireResponse,
  submitQuestionnaire,
  validateQuestionnaire,
} from "@/shared/api/questionnaires";
import type {
  QuestionnaireAnalyzeResponse,
  QuestionnairePolicyGenerateResponse,
  QuestionnaireRead,
  ValidationResult,
} from "@/shared/api/types";
import { PageStatus } from "@/shared/ui/PageStatus";

function shortHash(h: string | null | undefined) {
  if (!h) return "—";
  return h.length <= 18 ? h : `${h.slice(0, 14)}…`;
}

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
  const [formData, setFormData] = useState<FormResponseData>(emptyFormResponseData);
  const [revisionFeedback, setRevisionFeedback] = useState<string | null>(null);
  const [analysisJson, setAnalysisJson] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<QuestionnaireAnalyzeResponse | null>(null);

  const [policyHtml, setPolicyHtml] = useState<string | null>(null);
  const [policyGen, setPolicyGen] = useState<QuestionnairePolicyGenerateResponse | null>(null);
  const [policyDocId, setPolicyDocId] = useState("");
  const [revisionReason, setRevisionReason] = useState("");

  const canEditResponses = q?.status === "draft" || q?.status === "needs_revision";

  const reload = useCallback(async () => {
    if (!Number.isFinite(id) || id < 1) return;
    setLoading(true);
    setError(null);
    try {
      const [meta, respRow] = await Promise.all([getQuestionnaire(id), getQuestionnaireResponse(id)]);
      setQ(meta);
      if (respRow) {
        const rd = respRow.response_data as Record<string, unknown>;
        setFormData(parseResponseDataFromServer(rd));
        setRevisionFeedback(typeof rd.revision_feedback === "string" ? rd.revision_feedback : null);
        const ar = rd.analysis_result;
        setAnalysisJson(ar !== undefined ? JSON.stringify(ar, null, 2) : null);
      } else {
        setFormData(emptyFormResponseData());
        setRevisionFeedback(null);
        setAnalysisJson(null);
      }
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onSave() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      await saveQuestionnaireResponse(id, { response_data: formToSavePayload(formData) });
      setActionMsg("Ответы сохранены.");
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
      setActionMsg(r.is_valid ? "Проверка: ошибок не найдено." : "Проверка: есть ошибки (см. блок ниже).");
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onAnalyze() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const r = await analyzeQuestionnaire(id);
      setAnalyzeResult(r);
      if (r.report) {
        setActionMsg("Анализ выполнен, отчёт записан в ответ анкеты.");
        await reload();
      } else {
        setActionMsg("Анализ не выполнен: данные не прошли валидацию.");
      }
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
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
      setActionMsg("Укажите причину возврата на доработку.");
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
    setActionMsg(null);
    try {
      const pid = policyDocId.trim() ? Number(policyDocId.trim()) : undefined;
      const out = await generateQuestionnairePolicy(
        id,
        pid !== undefined && Number.isFinite(pid) && pid > 0 ? pid : null,
      );
      setPolicyGen(out);
      setPolicyHtml(out.html_preview);
      setActionMsg("Политика сгенерирована (предпросмотр ниже).");
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onDownloadDocx() {
    if (!Number.isFinite(id) || id < 1) return;
    setBusy(true);
    setActionMsg(null);
    try {
      const blob = await downloadPolicyDocx(id);
      triggerBlobDownload(blob, `policy_questionnaire_${id}.docx`);
      setActionMsg("Файл DOCX загружен.");
    } catch (e) {
      setActionMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  if (!Number.isFinite(id) || id < 1) {
    return <p className="muted">Некорректный идентификатор анкеты.</p>;
  }

  return (
    <>
      <p style={{ margin: "0 0 8px" }}>
        <Link to="/questionnaires">← К списку анкет</Link>
      </p>
      <h1 className="pageTitle">Анкета #{id}</h1>

      <PageStatus loading={loading} error={error} empty={false}>
        {q && (
          <>
            <div className="panel">
              <h2 className="panelTitle">Метаданные</h2>
              <table className="dataTable" style={{ maxWidth: 560 }}>
                <tbody>
                  <tr>
                    <th scope="row">Название</th>
                    <td>{q.title}</td>
                  </tr>
                  <tr>
                    <th scope="row">Статус</th>
                    <td>{q.status}</td>
                  </tr>
                  <tr>
                    <th scope="row">Подразделение (id)</th>
                    <td>{q.department_id}</td>
                  </tr>
                  <tr>
                    <th scope="row">Обновлена</th>
                    <td>{q.updated_at}</td>
                  </tr>
                </tbody>
              </table>
              {revisionFeedback && (
                <div className="callout" style={{ marginTop: 12 }}>
                  <strong>Комментарий при возврате на доработку:</strong>
                  <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{revisionFeedback}</div>
                </div>
              )}
              <p className="hint" style={{ marginTop: 12, marginBottom: 0 }}>
                Редактирование ответов доступно в статусах <code>draft</code> и <code>needs_revision</code>. После
                сохранения формы при необходимости повторите анализ (результат анализа хранится в ответе на сервере).
              </p>
            </div>

            <div className="panel">
              <h2 className="panelTitle">Действия</h2>
              {actionMsg && (
                <div
                  className={
                    actionMsg.includes("HTTP") || actionMsg.includes("Ошибка") || actionMsg.includes("detail")
                      ? "callout calloutError"
                      : "callout"
                  }
                >
                  {actionMsg}
                </div>
              )}
              <div className="toolbar">
                <button type="button" className="btn btnPrimary" disabled={busy || !canEditResponses} onClick={() => void onSave()}>
                  Сохранить ответы
                </button>
                <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onValidate()}>
                  Проверить
                </button>
                <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onAnalyze()}>
                  Анализировать
                </button>
                <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onSubmit()}>
                  Отправить
                </button>
                <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onReopenDraft()}>
                  Вернуть в черновик
                </button>
                <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onApprove()}>
                  Утвердить
                </button>
              </div>
              <div className="field" style={{ marginTop: 12 }}>
                <label className="fieldLabel" htmlFor="rev-reason">
                  Возврат на доработку (причина)
                </label>
                <div className="inlineForm" style={{ marginTop: 4 }}>
                  <input
                    id="rev-reason"
                    className="input"
                    style={{ flex: "1 1 240px" }}
                    value={revisionReason}
                    onChange={(e) => setRevisionReason(e.target.value)}
                    disabled={busy}
                  />
                  <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onReturnRevision()}>
                    Вернуть на доработку
                  </button>
                </div>
              </div>
              <div className="field" style={{ marginTop: 12 }}>
                <label className="fieldLabel" htmlFor="pol-doc">
                  ID документа политики (для версионирования при генерации, необязательно)
                </label>
                <input
                  id="pol-doc"
                  className="input"
                  style={{ maxWidth: 200 }}
                  value={policyDocId}
                  onChange={(e) => setPolicyDocId(e.target.value)}
                  disabled={busy}
                  placeholder="например, 1"
                />
              </div>
              <div className="toolbar" style={{ marginTop: 8 }}>
                <button type="button" className="btn btnPrimary" disabled={busy} onClick={() => void onGeneratePolicy()}>
                  Сгенерировать политику
                </button>
                <button type="button" className="btn btnSecondary" disabled={busy} onClick={() => void onDownloadDocx()}>
                  Скачать DOCX
                </button>
              </div>
            </div>

            {validationResult && (
              <div className="panel">
                <h2 className="panelTitle">Результат проверки (validate)</h2>
                <p>
                  Статус:{" "}
                  <strong>{validationResult.is_valid ? "допустимо" : "есть ошибки"}</strong>
                </p>
                {validationResult.errors.length > 0 && (
                  <>
                    <p style={{ marginBottom: 4 }}>
                      <strong>Ошибки</strong>
                    </p>
                    <ul className="diffList">
                      {validationResult.errors.map((e, i) => (
                        <li key={i}>
                          <code>{e.field}</code> — {e.message} ({e.code})
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {validationResult.warnings.length > 0 && (
                  <>
                    <p style={{ marginBottom: 4 }}>
                      <strong>Предупреждения</strong>
                    </p>
                    <ul className="diffList">
                      {validationResult.warnings.map((e, i) => (
                        <li key={i}>
                          <code>{e.field}</code> — {e.message}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {analyzeResult && (
              <div className="panel">
                <h2 className="panelTitle">Результат анализа (последний запрос)</h2>
                {analyzeResult.validation && (
                  <>
                    <p>Анализ не выполнен — валидация:</p>
                    <ul className="diffList">
                      {analyzeResult.validation.errors.map((e, i) => (
                        <li key={i}>
                          <code>{e.field}</code> — {e.message}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {analyzeResult.report && (
                  <p>
                    Отчёт получен (классификация активов, риски, меры). Детали см. в JSON ниже и на сервере в{" "}
                    <code>response_data.analysis_result</code>.
                  </p>
                )}
              </div>
            )}

            {(analysisJson || analyzeResult?.report) && (
              <div className="panel">
                <h2 className="panelTitle">Сохранённый результат анализа (JSON)</h2>
                <pre
                  style={{
                    margin: 0,
                    padding: 10,
                    background: "#f5f5f5",
                    border: "1px solid #ccc",
                    fontSize: 12,
                    overflow: "auto",
                    maxHeight: 320,
                  }}
                >
                  {analysisJson ?? JSON.stringify(analyzeResult?.report, null, 2)}
                </pre>
              </div>
            )}

            {(policyHtml || policyGen) && (
              <div className="panel">
                <h2 className="panelTitle">Политика ИБ — предпросмотр</h2>
                {policyGen?.versioning && (
                  <div className="callout" style={{ marginBottom: 12 }}>
                    <p style={{ margin: "0 0 6px" }}>
                      <strong>Версионирование:</strong> статус <code>{policyGen.versioning.status}</code>
                      {policyGen.versioning.version_number != null && (
                        <>
                          , номер версии <strong>{policyGen.versioning.version_number}</strong>
                        </>
                      )}
                    </p>
                    <p style={{ margin: "0 0 6px" }}>
                      <strong>source_hash:</strong> <code>{shortHash(policyGen.versioning.source_hash)}</code>
                    </p>
                    <p style={{ margin: 0 }} className="hint">
                      Поле «reason» в ответе версионирования API не предусмотрено; причина возврата анкеты показывается в
                      блоке комментария выше.
                    </p>
                  </div>
                )}
                {policyHtml && (
                  <iframe
                    title="Предпросмотр политики"
                    className="policyPreview"
                    style={{ width: "100%", minHeight: 380, border: "1px solid #ccc" }}
                    srcDoc={policyHtml}
                  />
                )}
              </div>
            )}

            <div className="panel">
              <h2 className="panelTitle">Данные анкеты (секции)</h2>
              <ResponseDataForm data={formData} setData={setFormData} disabled={!canEditResponses || busy} />
            </div>
          </>
        )}
      </PageStatus>
    </>
  );
}
