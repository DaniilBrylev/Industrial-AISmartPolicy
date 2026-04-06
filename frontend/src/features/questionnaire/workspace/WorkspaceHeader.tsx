import type { QuestionnaireRead, QuestionnaireWorkflowStateRead } from "@/shared/api/types";
import type { LongRunningQuestionnaireOp } from "./longRunning";

const WF_LABEL: Record<string, string> = {
  draft: "Черновик",
  analyzed: "Проанализировано",
  under_review: "На согласовании",
  approved: "Утверждено",
  needs_revision: "Доработка",
};

type Props = {
  questionnaire: QuestionnaireRead;
  departmentLabel: string;
  workflowState: QuestionnaireWorkflowStateRead | null;
  analysisStale: boolean;
  llmEnabledGlobally: boolean | null;
  lastAnalysisUsedLlm: boolean;
  busy: boolean;
  canEditResponses: boolean;
  onSave: () => void;
  onValidate: () => void;
  onAnalyze: () => void;
  onOpenDiff: () => void;
  onGeneratePolicy: () => void;
  onDownloadDocx: () => void;
  diffLoading: boolean;
  longRunningOp: LongRunningQuestionnaireOp | null;
};

export function WorkspaceHeader({
  questionnaire: q,
  departmentLabel,
  workflowState,
  analysisStale,
  llmEnabledGlobally,
  lastAnalysisUsedLlm,
  busy,
  canEditResponses,
  onSave,
  onValidate,
  onAnalyze,
  onOpenDiff,
  onGeneratePolicy,
  onDownloadDocx,
  diffLoading,
  longRunningOp,
}: Props) {
  const wf = workflowState?.workflow_status;
  const analyzing = longRunningOp === "analyze";
  const generatingPolicy = longRunningOp === "generate_policy";

  return (
    <header className="workspaceHeader" aria-busy={Boolean(longRunningOp)}>
      <div className="workspaceHeaderTop">
        <div className="workspaceTitleBlock">
          <h1>{q.title}</h1>
          <p className="workspaceTitleMeta">
            Анкета #{q.id}
            {departmentLabel ? <> · {departmentLabel}</> : null} · статус: <code>{q.status}</code>
            {q.submitted_at ? <> · отправлена: {q.submitted_at}</> : null}
          </p>
        </div>
        <div className="workspaceBadges">
          {wf ? (
            <span className="badge badgeNeutral" title="workflow_status">
              Процесс: {WF_LABEL[wf] ?? wf}
            </span>
          ) : null}
          <span className={analysisStale ? "badge badgeWarn" : "badge badgeOk"}>
            {analysisStale ? "Анализ устарел" : "Анализ актуален"}
          </span>
          {llmEnabledGlobally === true && (
            <span className="badge badgeAi">LLM в API включён</span>
          )}
          {llmEnabledGlobally === false && (
            <span className="badge badgeNeutral">LLM в API выкл.</span>
          )}
          {lastAnalysisUsedLlm && <span className="badge badgeAi">Последний отчёт: LLM</span>}
        </div>
      </div>
      <div className="workspaceToolbar">
        <button type="button" className="btn btnPrimary" disabled={busy || !canEditResponses} onClick={onSave}>
          Сохранить
        </button>
        <button type="button" className="btn btnSecondary" disabled={busy} onClick={onValidate}>
          Проверить
        </button>
        <button type="button" className="btn btnSecondary" disabled={busy} onClick={onAnalyze}>
          {analyzing ? (
            <>
              <span className="btnSpinner" aria-hidden />
              Анализ…
            </>
          ) : (
            "Анализировать"
          )}
        </button>
        <button
          type="button"
          className="btn btnSecondary"
          disabled={busy || diffLoading}
          onClick={() => onOpenDiff()}
        >
          {diffLoading ? "Diff…" : "Показать diff"}
        </button>
        <button type="button" className="btn btnPrimary" disabled={busy} onClick={onGeneratePolicy}>
          {generatingPolicy ? (
            <>
              <span className="btnSpinner" aria-hidden />
              Генерация…
            </>
          ) : (
            "Сгенерировать политику"
          )}
        </button>
        <button type="button" className="btn btnSecondary" disabled={busy} onClick={onDownloadDocx}>
          Скачать DOCX
        </button>
      </div>
      {longRunningOp && (
        <div className="workspaceActivityStrip" role="status" aria-live="polite" aria-atomic="true">
          <span className="activitySpinner" aria-hidden />
          <div>
            {longRunningOp === "analyze" ? (
              <>
                <strong>Выполняется анализ</strong>
                Идёт обработка данных (риски, связи и анализ с помощью ИИ). Это может занять от нескольких секунд до 60 минут.
                Страница не зависла: дождитесь завершения.
                Не обновляйте страницу.
              </>
            ) : (
              <>
                <strong>Генерируется политика</strong>
                Сервер формирует текст и DOCX. При использовании ИИ это может занять до 10 минут.
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
