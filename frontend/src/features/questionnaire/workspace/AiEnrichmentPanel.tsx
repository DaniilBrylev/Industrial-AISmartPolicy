import type { AiAnalysisEnrichment } from "@/shared/api/types";

type Props = {
  enrichment: AiAnalysisEnrichment | null | undefined;
};

export function AiEnrichmentPanel({ enrichment }: Props) {
  if (!enrichment) {
    return (
      <div className="card">
        <h3 className="cardTitle">ИИ и NLP (обогащение)</h3>
        <div className="emptyState">
          Блок появится, если при анализе выполнялось LLM-обогащение (сущности, связи, резюме заметок).
        </div>
      </div>
    );
  }

  const hasNlp =
    (enrichment.entities && enrichment.entities.length > 0) ||
    (enrichment.relations && enrichment.relations.length > 0);
  const hasNotes = Boolean(enrichment.notes_summary?.trim());
  const hasNorm = enrichment.normalized_text && Object.keys(enrichment.normalized_text).length > 0;

  return (
    <div className="card">
      <h3 className="cardTitle">ИИ и NLP (обогащение)</h3>
      <p className="cardHint">
        Данные из <code>ai_enrichment</code>: не меняют rule-based выводы, дополняют объяснимость и текстовый
        анализ.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <span className={enrichment.llm_used ? "badge badgeAi" : "badge badgeNeutral"}>
          LLM: {enrichment.llm_used ? "использовался" : "не вызывался"}
        </span>
        {enrichment.model ? (
          <span className="badge badgeNeutral">Модель: {enrichment.model}</span>
        ) : null}
        {enrichment.generated_at ? (
          <span className="badge badgeNeutral">{enrichment.generated_at}</span>
        ) : null}
      </div>
      {hasNotes && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Резюме заметок</h4>
          <div
            style={{
              padding: 12,
              background: "var(--color-surface-muted)",
              borderRadius: "var(--radius-sm)",
              fontSize: 13,
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
            }}
          >
            {enrichment.notes_summary}
          </div>
        </div>
      )}
      {enrichment.entities && enrichment.entities.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 8px", fontSize: 13 }}>Сущности (NER)</h4>
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Тип</th>
                  <th>Значение</th>
                  <th>Источник</th>
                </tr>
              </thead>
              <tbody>
                {enrichment.entities.map((e, i) => (
                  <tr key={i}>
                    <td>
                      <code>{e.type}</code>
                    </td>
                    <td>{e.value}</td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {e.source_field || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {enrichment.relations && enrichment.relations.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 8px", fontSize: 13 }}>Связи (RE)</h4>
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Субъект</th>
                  <th>Связь</th>
                  <th>Объект</th>
                  <th>Источник</th>
                </tr>
              </thead>
              <tbody>
                {enrichment.relations.map((r, i) => (
                  <tr key={i}>
                    <td>{r.subject}</td>
                    <td>
                      <code>{r.relation}</code>
                    </td>
                    <td>{r.object}</td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {r.source_field || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {!hasNlp && !hasNotes && (
        <p className="muted" style={{ margin: 0 }}>
          В этом отчёте нет текста резюме и таблиц NER/RE (возможно, LLM отключён или ответ пустой).
        </p>
      )}
      {hasNorm && (
        <details className="debugDisclosure" style={{ marginTop: 12 }}>
          <summary>Нормализованные фрагменты (normalized_text)</summary>
          <pre className="debugPre">{JSON.stringify(enrichment.normalized_text, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
