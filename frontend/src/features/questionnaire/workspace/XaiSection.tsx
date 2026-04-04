import type { AnalysisRiskRow, ExplanationRequestBody, TraceabilityEntry } from "@/shared/api/types";

const COMPENSATING_PREFIX = "(компенсирующая мера)";

function traceRowIsCompensating(e: TraceabilityEntry): boolean {
  const m = (e.measure_title ?? "").trim();
  return Boolean((e.compensating_measure ?? "").trim()) || m.startsWith(COMPENSATING_PREFIX);
}

type Props = {
  analysisRiskRows: AnalysisRiskRow[];
  traceabilityRows: TraceabilityEntry[];
  busy: boolean;
  onExplain: (body: ExplanationRequestBody) => void;
};

export function XaiSection({ analysisRiskRows, traceabilityRows, busy, onExplain }: Props) {
  if (analysisRiskRows.length === 0 && traceabilityRows.length === 0) {
    return (
      <div className="card">
        <h3 className="cardTitle">Объяснимость (XAI)</h3>
        <div className="emptyState">
          Выполните анализ и сохраните отчёт — появятся риски и карта соответствия для запроса обоснований.
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="cardTitle">Объяснимость (XAI)</h3>
      <p className="cardHint">
        Запрос к <code>POST /explanation</code>: rule-based факты + при наличии текст из <code>ai_enrichment</code>.
        Решения не пересчитываются.
      </p>
      {analysisRiskRows.length > 0 && (
        <>
          <h4 style={{ margin: "16px 0 8px", fontSize: 14 }}>По рискам</h4>
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Актив</th>
                  <th>Код</th>
                  <th>Название</th>
                  <th>Severity</th>
                  <th style={{ width: 200 }}>Обоснование</th>
                </tr>
              </thead>
              <tbody>
                {analysisRiskRows.map((r) => {
                  const riskKey = `asset:${r.asset_id}|risk:${r.risk_code}`;
                  return (
                    <tr key={riskKey}>
                      <td>
                        <code>{r.asset_id}</code>
                      </td>
                      <td>
                        <code>{r.risk_code}</code>
                      </td>
                      <td>{r.title}</td>
                      <td>{r.severity ?? "—"}</td>
                      <td>
                        <button
                          type="button"
                          className="btnXai"
                          disabled={busy}
                          onClick={() => onExplain({ kind: "risk", risk_key: riskKey })}
                        >
                          Показать обоснование
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
      {traceabilityRows.length > 0 && (
        <>
          <h4 style={{ margin: "20px 0 8px", fontSize: 14 }}>По карте соответствия</h4>
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Актив</th>
                  <th>Риск</th>
                  <th>Требование</th>
                  <th>Мера</th>
                  <th style={{ width: 200 }}>Обоснование</th>
                </tr>
              </thead>
              <tbody>
                {traceabilityRows.map((row, idx) => {
                  const comp = traceRowIsCompensating(row);
                  return (
                    <tr key={`${idx}-${row.asset_id}-${row.measure_title ?? ""}`}>
                      <td>{idx}</td>
                      <td>
                        <code>{row.asset_id}</code>
                        {String(row.environment ?? "").toUpperCase() === "OT" ? (
                          <span className="badge badgeOtStrong" style={{ marginLeft: 6 }}>
                            OT
                          </span>
                        ) : null}
                      </td>
                      <td>
                        {row.risk_title || row.risk_code || "—"}
                        {row.risk_code ? (
                          <div>
                            <code style={{ fontSize: 11 }}>{row.risk_code}</code>
                          </div>
                        ) : null}
                      </td>
                      <td>{row.requirement_title || row.requirement_key || "—"}</td>
                      <td>
                        {row.measure_title || "—"}
                        {comp ? (
                          <div style={{ marginTop: 4 }}>
                            <span className="badge badgeOtStrong" title="Компенсирующая мера">
                              компенс.
                            </span>
                          </div>
                        ) : null}
                        {row.ot_constraints ? (
                          <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                            {row.ot_constraints}
                          </div>
                        ) : null}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btnXai"
                          disabled={busy}
                          onClick={() => onExplain({ kind: "traceability", traceability_index: idx })}
                        >
                          Показать обоснование
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
