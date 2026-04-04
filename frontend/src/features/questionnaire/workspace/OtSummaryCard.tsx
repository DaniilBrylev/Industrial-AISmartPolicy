import type { AnalysisAssetSnapshot, AnalysisReport } from "@/shared/api/types";

export function OtSummaryCard({ report }: { report: AnalysisReport }) {
  const classified = report.classified_assets ?? [];
  const assets = (report.assets ?? []) as AnalysisAssetSnapshot[];
  const risks = report.risks ?? [];
  const otIds = new Set(classified.filter((c) => c.environment === "OT").map((c) => c.asset_id));
  const otRisks = risks.filter((r) => otIds.has(String(r.asset_id ?? "")));
  const riskCodes = [...new Set(otRisks.map((r) => String(r.risk_code ?? "")).filter(Boolean))].sort();

  const compEntries =
    report.traceability_map?.entries?.filter(
      (e) => e.compensating_measure != null && String(e.compensating_measure).length > 0,
    ) ?? [];

  if (otIds.size === 0) {
    return (
      <div className="card">
        <h3 className="cardTitle">Промышленный контур (OT)</h3>
        <div className="emptyState">
          В классификации нет активов среды OT. Заполните OT-поля и типы активов, затем выполните анализ.
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ borderLeft: "4px solid var(--color-accent-ot)" }}>
      <h3 className="cardTitle">Промышленный контур (OT)</h3>
      <p className="cardHint">
        Rule-based классификация IT/OT, учёт зон, MFA/патчинга, safety-critical и компенсирующих мер в карте
        соответствия.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
        <span className="badge badgeOtStrong">OT-активов: {otIds.size}</span>
        <span className="badge badgeNeutral">Уникальных OT risk_code: {riskCodes.length}</span>
        <span className="badge badgeNeutral">Компенсирующих записей в traceability: {compEntries.length}</span>
      </div>
      {riskCodes.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Коды OT-рисков</h4>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {riskCodes.map((c) => (
              <span key={c} className="badge badgeOtStrong">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="tableWrap">
        <table className="dataTable">
          <thead>
            <tr>
              <th>ID</th>
              <th>Среда</th>
              <th>Зона</th>
              <th>Производитель</th>
              <th>Протоколы</th>
              <th>MFA</th>
              <th>Патчинг</th>
              <th>Safety</th>
              <th>Класс доступности</th>
            </tr>
          </thead>
          <tbody>
            {classified
              .filter((c) => c.environment === "OT")
              .map((c) => {
                const a = assets.find((x) => String(x.id) === c.asset_id);
                return (
                  <tr key={c.asset_id}>
                    <td>
                      <code>{c.asset_id}</code>
                    </td>
                    <td>
                      <span className="badge badgeOtStrong">OT</span>
                    </td>
                    <td>{a?.network_zone != null ? String(a.network_zone) : "—"}</td>
                    <td>{a?.vendor != null ? String(a.vendor) : "—"}</td>
                    <td style={{ maxWidth: 160, fontSize: 12 }}>{a?.protocols != null ? String(a.protocols) : "—"}</td>
                    <td>{a?.supports_mfa === false ? "нет" : a?.supports_mfa === true ? "да" : "—"}</td>
                    <td>{a?.supports_patching === false ? "нет" : a?.supports_patching === true ? "да" : "—"}</td>
                    <td>{a?.safety_critical === true ? "да" : "—"}</td>
                    <td>{a?.availability_class != null ? String(a.availability_class) : "—"}</td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
