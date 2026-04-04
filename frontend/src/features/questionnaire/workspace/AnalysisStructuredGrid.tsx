import type { AnalysisAssetSnapshot, AnalysisReport } from "@/shared/api/types";

function severityPill(sev: string) {
  const s = sev.toLowerCase();
  if (s === "critical") return "sevPill sev-critical";
  if (s === "high") return "sevPill sev-high";
  if (s === "low") return "sevPill sev-low";
  return "sevPill sev-medium";
}

export function AnalysisStructuredGrid({ report }: { report: AnalysisReport }) {
  const assets = (report.assets ?? []) as AnalysisAssetSnapshot[];
  const classified = report.classified_assets ?? [];
  const risks = report.risks ?? [];
  const req = report.requirements ?? [];
  const meas = report.measures ?? [];
  const links = report.links ?? [];
  const warnings = report.warnings ?? [];

  return (
    <>
      {warnings.length > 0 && (
        <div className="callout calloutError" style={{ marginBottom: 16 }}>
          <strong>Предупреждения анализа</strong>
          <ul className="diffList" style={{ marginTop: 8 }}>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h3 className="cardTitle">Классификация активов</h3>
        {classified.length === 0 ? (
          <div className="emptyState">Нет записей классификации.</div>
        ) : (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Актив</th>
                  <th>Среда</th>
                  <th>Критичность</th>
                  <th>Эффективная</th>
                  <th>Процессов</th>
                  <th>Заметки</th>
                </tr>
              </thead>
              <tbody>
                {classified.map((c) => (
                  <tr key={c.asset_id}>
                    <td>
                      <code>{c.asset_id}</code>
                    </td>
                    <td>
                      {c.environment === "OT" ? (
                        <span className="badge badgeOtStrong">OT</span>
                      ) : (
                        <span className="badge badgeNeutral">IT</span>
                      )}
                    </td>
                    <td>{c.original_criticality}</td>
                    <td>{c.effective_criticality}</td>
                    <td>{c.usage_count}</td>
                    <td style={{ fontSize: 12 }}>
                      {c.notes?.length ? c.notes.join("; ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="cardTitle">Снимок активов (вход анализа)</h3>
        {assets.length === 0 ? (
          <div className="emptyState">Нет активов в отчёте.</div>
        ) : (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя</th>
                  <th>Тип</th>
                  <th>Критичность</th>
                  <th>Зона</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((a, i) => (
                  <tr key={String(a.id ?? i)}>
                    <td>
                      <code>{String(a.id ?? "")}</code>
                    </td>
                    <td>{String(a.name ?? "")}</td>
                    <td>{String(a.asset_type ?? "")}</td>
                    <td>{String(a.criticality ?? "")}</td>
                    <td>{a.network_zone != null ? String(a.network_zone) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="cardTitle">Риски</h3>
        {risks.length === 0 ? (
          <div className="emptyState">Риски не сформированы.</div>
        ) : (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Актив</th>
                  <th>Код</th>
                  <th>Название</th>
                  <th>Критичность</th>
                </tr>
              </thead>
              <tbody>
                {risks.map((r, i) => (
                  <tr key={`${r.asset_id}-${r.risk_code}-${i}`}>
                    <td>
                      <code>{r.asset_id}</code>
                    </td>
                    <td>
                      <code>{r.risk_code}</code>
                    </td>
                    <td>{r.title}</td>
                    <td>
                      <span className={severityPill(r.severity)}>{r.severity}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="cardTitle">Требования и меры (каталог)</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 13 }}>Требования ({req.length})</h4>
            {req.length === 0 ? (
              <p className="muted" style={{ margin: 0 }}>
                —
              </p>
            ) : (
              <ul className="diffList" style={{ maxHeight: 200, overflow: "auto" }}>
                {req.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 13 }}>Меры ({meas.length})</h4>
            {meas.length === 0 ? (
              <p className="muted" style={{ margin: 0 }}>
                —
              </p>
            ) : (
              <ul className="diffList" style={{ maxHeight: 200, overflow: "auto" }}>
                {meas.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="cardTitle">Связи (актив → риск → требование → мера)</h3>
        {links.length === 0 ? (
          <div className="emptyState">Нет связей links[].</div>
        ) : (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Актив</th>
                  <th>Риск</th>
                  <th>Требование</th>
                  <th>Мера</th>
                </tr>
              </thead>
              <tbody>
                {links.map((L, i) => (
                  <tr key={i}>
                    <td>
                      <code>{L.asset_id}</code>
                    </td>
                    <td style={{ fontSize: 12 }}>{L.risk}</td>
                    <td style={{ fontSize: 12 }}>{L.requirement}</td>
                    <td style={{ fontSize: 12 }}>{L.measure}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
