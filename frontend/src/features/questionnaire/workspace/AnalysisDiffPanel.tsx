import type { QuestionnaireAnalysisDiffResponse } from "@/shared/api/types";

type Props = {
  data: QuestionnaireAnalysisDiffResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  disabled?: boolean;
};

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 14 }}>
      <h4 style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 700 }}>{title}</h4>
      <ul className="diffList" style={{ margin: 0 }}>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  );
}

function ObjListBlock({ title, items }: { title: string; items: Record<string, unknown>[] }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 14 }}>
      <h4 style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 700 }}>{title}</h4>
      <ul className="diffList" style={{ margin: 0 }}>
        {items.map((x, i) => (
          <li key={i}>
            <code style={{ fontSize: 11 }}>{JSON.stringify(x)}</code>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AnalysisDiffPanel({ data, loading, error, onRefresh, disabled }: Props) {
  return (
    <div className="card">
      <h3 className="cardTitle">Актуализация и изменения</h3>
      <p className="cardHint">
        Сравнение <strong>сохранённого</strong> анализа с rule-based пересчётом по текущему ответу анкеты (без
        записи в БД и без вызова LLM). Источник: <code>GET /analysis-diff</code>.
      </p>
      <div className="workspaceToolbar" style={{ border: "none", paddingTop: 0, marginBottom: 16 }}>
        <button type="button" className="btn btnPrimary" disabled={disabled || loading} onClick={() => onRefresh()}>
          {loading ? "Загрузка…" : "Обновить сравнение"}
        </button>
      </div>
      {error && <div className="callout calloutError">{error}</div>}
      {!data && !loading && !error && (
        <div className="emptyState">Нажмите «Обновить сравнение», чтобы загрузить diff с сервера.</div>
      )}
      {data && (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <span className={data.analysis_stale ? "badge badgeWarn" : "badge badgeOk"}>
              {data.analysis_stale ? "Анкета устарела относительно анализа" : "Отслеживаемые секции совпадают"}
            </span>
            {data.diff?.has_changes ? (
              <span className="badge badgeWarn">Есть отличия в пересчёте</span>
            ) : (
              <span className="badge badgeOk">Пересчёт совпадает с сохранённым</span>
            )}
          </div>
          <dl
            style={{
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              gap: "6px 12px",
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            <dt className="muted">Хеш в отчёте</dt>
            <dd style={{ margin: 0 }}>
              <code>{data.stored_source_hash ?? "—"}</code>
            </dd>
            <dt className="muted">Хеш по текущим данным</dt>
            <dd style={{ margin: 0 }}>
              <code>{data.projected_source_hash ?? "—"}</code>
            </dd>
          </dl>
          {data.diff?.summary && data.diff.summary.length > 0 && (
            <div className="callout" style={{ marginBottom: 16 }}>
              <strong>Сводка</strong>
              <ul className="diffList" style={{ marginTop: 8 }}>
                {data.diff.summary.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {data.diff?.policy_sections_changed && data.diff.policy_sections_changed.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ margin: "0 0 8px", fontSize: 13 }}>Затронутые разделы политики</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {data.diff.policy_sections_changed.map((s) => (
                  <span key={s} className="badge badgeWarn">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          <ObjListBlock title="Добавленные риски" items={data.diff?.added_risks ?? []} />
          <ObjListBlock title="Удалённые риски" items={data.diff?.removed_risks ?? []} />
          <ListBlock title="Добавленные меры" items={data.diff?.added_measures ?? []} />
          <ListBlock title="Удалённые меры" items={data.diff?.removed_measures ?? []} />
          <ObjListBlock title="Добавленные записи traceability" items={data.diff?.added_traceability_entries ?? []} />
          <ObjListBlock title="Удалённые записи traceability" items={data.diff?.removed_traceability_entries ?? []} />
        </>
      )}
    </div>
  );
}
