import type { QuestionnaireWorkflowStateRead, WorkflowAction, WorkflowRole } from "@/shared/api/types";

const WORKFLOW_STATUS_LABEL: Record<string, string> = {
  draft: "Черновик",
  analyzed: "Проанализировано",
  under_review: "На согласовании",
  approved: "Утверждено",
  needs_revision: "На доработке",
};

function workflowActionLabel(a: WorkflowAction): string {
  switch (a) {
    case "submit_for_review":
      return "Отправить на согласование";
    case "approve":
      return "Утвердить";
    case "reject":
      return "Вернуть на доработку";
    case "revise":
      return "В черновик для правок";
    default:
      return a;
  }
}

type Props = {
  workflowState: QuestionnaireWorkflowStateRead | null;
  workflowRole: WorkflowRole;
  setWorkflowRole: (r: WorkflowRole) => void;
  workflowActor: string;
  setWorkflowActor: (s: string) => void;
  workflowComment: string;
  setWorkflowComment: (s: string) => void;
  busy: boolean;
  onWorkflowAction: (a: WorkflowAction) => void;
};

export function WorkflowSection({
  workflowState,
  workflowRole,
  setWorkflowRole,
  workflowActor,
  setWorkflowActor,
  workflowComment,
  setWorkflowComment,
  busy,
  onWorkflowAction,
}: Props) {
  if (!workflowState) {
    return (
      <div className="card">
        <h3 className="cardTitle">Согласование политики</h3>
        <div className="emptyState">Сохраните ответ анкеты — станет доступен workflow и история.</div>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="cardTitle">Согласование политики</h3>
      <p className="cardHint">
        Роль и участник передаются в запросе (MVP без JWT). История — <code>workflow_log</code> в ответе анкеты.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 16 }}>
        <span className="badge badgeNeutral" style={{ fontSize: 12, textTransform: "none" }}>
          {WORKFLOW_STATUS_LABEL[workflowState.workflow_status] ?? workflowState.workflow_status}
        </span>
        <span className="muted" style={{ fontSize: 13 }}>
          Анкета: <code>{workflowState.questionnaire_status}</code>
        </span>
      </div>
      {workflowState.workflow_status === "approved" && (
        <div className="callout calloutOk" style={{ marginBottom: 16 }}>
          Утверждено — редактирование ответов заблокировано.
        </div>
      )}
      {workflowState.workflow_status === "needs_revision" && workflowState.revision_feedback && (
        <div className="callout calloutError" style={{ marginBottom: 16 }}>
          <strong>Комментарий согласующего</strong>
          <div style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{workflowState.revision_feedback}</div>
        </div>
      )}
      {workflowState.analysis_stale && workflowState.workflow_status === "analyzed" && (
        <div className="callout calloutError" style={{ marginBottom: 16 }}>
          Анализ устарел — отправка на согласование недоступна до пересчёта.
        </div>
      )}
      <div className="fieldGrid fieldGridTight" style={{ marginBottom: 16 }}>
        <div className="field">
          <label className="fieldLabel" htmlFor="wf-role">
            Роль
          </label>
          <select
            id="wf-role"
            className="input"
            value={workflowRole}
            onChange={(e) => setWorkflowRole(e.target.value as WorkflowRole)}
            disabled={busy}
          >
            <option value="security_analyst">Аналитик ИБ</option>
            <option value="department_head">Руководитель (наблюдатель)</option>
            <option value="approver">Утверждающий</option>
          </select>
        </div>
        <div className="field">
          <label className="fieldLabel" htmlFor="wf-actor">
            Участник (actor)
          </label>
          <input
            id="wf-actor"
            className="input"
            value={workflowActor}
            onChange={(e) => setWorkflowActor(e.target.value)}
            disabled={busy}
          />
        </div>
        <div className="field fieldSpan2">
          <label className="fieldLabel" htmlFor="wf-comment">
            Комментарий к действию
          </label>
          <input
            id="wf-comment"
            className="input"
            value={workflowComment}
            onChange={(e) => setWorkflowComment(e.target.value)}
            disabled={busy}
            placeholder="Для отклонения укажите причину"
          />
        </div>
      </div>
      <div className="workspaceToolbar" style={{ border: "none", paddingTop: 0, marginBottom: 20 }}>
        {workflowState.allowed_actions.map((a) => (
          <button
            key={a}
            type="button"
            className={a === "approve" ? "btn btnPrimary" : "btn btnSecondary"}
            disabled={busy}
            onClick={() => void onWorkflowAction(a)}
          >
            {workflowActionLabel(a)}
          </button>
        ))}
        {workflowState.allowed_actions.length === 0 && (
          <span className="muted">Нет действий для выбранной роли в текущем статусе.</span>
        )}
      </div>
      <h4 style={{ margin: "0 0 12px", fontSize: 14 }}>История</h4>
      {workflowState.workflow_log.length === 0 ? (
        <p className="muted">Пока пусто.</p>
      ) : (
        <ul className="timeline">
          {[...workflowState.workflow_log].reverse().map((e, i) => (
            <li key={`${e.timestamp}-${i}`} className="timelineItem">
              <div style={{ fontWeight: 700, fontSize: 13 }}>
                {e.action} · {e.from_status} → {e.to_status}
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                {e.timestamp} · {e.actor}
                {e.role ? ` · ${e.role}` : ""}
              </div>
              {e.comment ? (
                <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.45 }}>{e.comment}</div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
