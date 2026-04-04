import type { ExplanationPayload } from "@/shared/api/types";

type Props = {
  open: boolean;
  onClose: () => void;
  payload: ExplanationPayload | null;
  error: string | null;
  loading: boolean;
};

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 12 }}>
      <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>{title}</h4>
      <ul className="diffList" style={{ marginBottom: 0 }}>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  );
}

export function ExplainabilityModal({ open, onClose, payload, error, loading }: Props) {
  if (!open) return null;

  return (
    <div
      className="modalBackdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modalPanel xaiModal" role="dialog" aria-modal="true" aria-labelledby="xai-modal-title">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <h3 id="xai-modal-title" style={{ margin: 0, fontSize: "1.05rem", lineHeight: 1.35, flex: 1 }}>
            {payload?.title ?? "Обоснование решения"}
          </h3>
          <button type="button" className="btn btnSmall" onClick={onClose} aria-label="Закрыть">
            ✕
          </button>
        </div>
        {payload && !loading && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
            <span
              className={
                payload.source === "rule_based"
                  ? "badge badgeNeutral"
                  : payload.source === "hybrid"
                    ? "badge badgeAi"
                    : "badge badgeOk"
              }
            >
              Источник: {payload.source}
            </span>
            {payload.method ? (
              <span className="badge badgeNeutral" style={{ textTransform: "none" }}>
                {payload.method}
              </span>
            ) : null}
            {payload.confidence != null ? (
              <span className="badge badgeNeutral">Уверенность: {payload.confidence}</span>
            ) : null}
          </div>
        )}

        {loading && <p className="muted" style={{ marginTop: 12 }}>Загрузка…</p>}
        {error && (
          <div className="callout calloutError" style={{ marginTop: 12 }}>
            {error}
          </div>
        )}

        {payload && !loading && (
          <div style={{ marginTop: 14, fontSize: 13 }}>
            {payload.asset && (
              <div className="callout" style={{ marginBottom: 12 }}>
                <p style={{ margin: "0 0 6px" }}>
                  <strong>Актив:</strong> {payload.asset.name || payload.asset.id}{" "}
                  <code style={{ fontSize: 12 }}>(id: {payload.asset.id})</code>
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Среда:</strong> {payload.asset.environment || "—"}
                  {payload.network_zone ? (
                    <>
                      {" "}
                      · <strong>Зона сети:</strong> {payload.network_zone}
                    </>
                  ) : null}
                </p>
              </div>
            )}

            {(payload.risk_code || payload.risk_title) && (
              <p style={{ margin: "0 0 8px" }}>
                <strong>Риск:</strong>{" "}
                {payload.risk_title ? (
                  <>
                    {payload.risk_title}{" "}
                    {payload.risk_code ? <code style={{ fontSize: 12 }}>({payload.risk_code})</code> : null}
                  </>
                ) : (
                  payload.risk_code && <code>{payload.risk_code}</code>
                )}
              </p>
            )}

            {(payload.requirement_title || payload.measure_title) && (
              <p style={{ margin: "0 0 8px" }}>
                {payload.requirement_title ? (
                  <>
                    <strong>Требование:</strong> {payload.requirement_title}
                    <br />
                  </>
                ) : null}
                {payload.measure_title ? (
                  <>
                    <strong>Мера:</strong> {payload.measure_title}
                  </>
                ) : null}
              </p>
            )}

            {payload.compensating_measure?.trim() ? (
              <div className="callout calloutOk" style={{ marginBottom: 12 }}>
                <strong>Компенсирующая мера (OT):</strong>
                <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{payload.compensating_measure}</div>
                <p className="hint" style={{ marginTop: 8, marginBottom: 0 }}>
                  Вместо прямой IT-меры (MFA, онлайн-патчинг и т.д.) применена мера, учитывающая ограничения
                  промышленного контура.
                </p>
              </div>
            ) : null}

            {payload.ot_constraints ? (
              <div className="callout" style={{ marginBottom: 12 }}>
                <strong>Ограничения OT:</strong>
                <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{payload.ot_constraints}</div>
              </div>
            ) : null}

            <ListBlock title="Связанные процессы" items={payload.processes} />
            <ListBlock title="Связанные инциденты" items={payload.incidents} />
            <ListBlock title="Матрица доступа (упоминания)" items={payload.access_matrix_hints} />
            <ListBlock title="Правила и причины (rule-based)" items={payload.rules} />

            {payload.llm_explanation ? (
              <div style={{ marginTop: 14 }}>
                <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Краткое объяснение (LLM / обогащение)</h4>
                <div
                  style={{
                    padding: 10,
                    background: "#f7f9fc",
                    border: "1px solid #c5d4e8",
                    whiteSpace: "pre-wrap",
                    fontSize: 13,
                    lineHeight: 1.45,
                  }}
                >
                  {payload.llm_explanation}
                </div>
                <p className="hint" style={{ marginTop: 6, marginBottom: 0 }}>
                  Текст не меняет факты анализа; формулирует уже зафиксированное решение.
                </p>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
