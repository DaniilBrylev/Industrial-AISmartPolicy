import type { AnalysisReport } from "@/shared/api/types";

function shortHash(h: string | null | undefined) {
  if (!h) return "—";
  return h.length <= 20 ? h : `${h.slice(0, 16)}…`;
}

type Props = {
  report: AnalysisReport | null;
  analysisStale: boolean;
};

export function AnalysisMetaCard({ report, analysisStale }: Props) {
  const meta = report?.analysis_meta;

  return (
    <div className="card">
      <h3 className="cardTitle">Метаданные анализа</h3>
      <p className="cardHint">
        Отпечаток отслеживаемых секций анкеты и момент фиксации отчёта на сервере.
      </p>
      {analysisStale && (
        <div className="callout calloutError" style={{ marginBottom: 12 }}>
          <strong>Анализ не соответствует текущим данным анкеты.</strong> Выполните пересчёт, чтобы
          обновить <code>source_hash</code> и отчёт.
        </div>
      )}
      {!meta ? (
        <div className="emptyState">Нет сохранённого анализа или метаданных (выполните «Анализировать»).</div>
      ) : (
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(140px, auto) 1fr",
            gap: "8px 16px",
            fontSize: 13,
            margin: 0,
          }}
        >
          <dt className="muted" style={{ margin: 0 }}>
            Время анализа
          </dt>
          <dd style={{ margin: 0 }}>{meta.generated_at || "—"}</dd>
          <dt className="muted" style={{ margin: 0 }}>
            source_hash
          </dt>
          <dd style={{ margin: 0 }}>
            <code>{shortHash(meta.source_hash)}</code>
          </dd>
          <dt className="muted" style={{ margin: 0 }}>
            Отслеживаемые секции
          </dt>
          <dd style={{ margin: 0 }}>
            {meta.tracked_sections?.length ? (
              <span style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {meta.tracked_sections.map((s) => (
                  <span key={s} className="badge badgeNeutral">
                    {s}
                  </span>
                ))}
              </span>
            ) : (
              "—"
            )}
          </dd>
        </dl>
      )}
    </div>
  );
}
