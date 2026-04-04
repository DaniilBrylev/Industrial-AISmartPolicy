import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDepartments } from "@/shared/api/departments";
import { formatApiError } from "@/shared/api/http";
import { listPolicyDocuments } from "@/shared/api/policies";
import { listAllPolicyVersions } from "@/shared/api/policyVersions";
import { listQuestionnaires } from "@/shared/api/questionnaires";
import { fetchHealth } from "@/shared/api/health";
import { PageStatus } from "@/shared/ui/PageStatus";

type Counts = {
  departments: number;
  questionnaires: number;
  policies: number;
  versions: number;
};

export function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [counts, setCounts] = useState<Counts | null>(null);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [h, depts, quests, pols, vers] = await Promise.all([
          fetchHealth().catch(() => null),
          listDepartments(),
          listQuestionnaires(),
          listPolicyDocuments(),
          listAllPolicyVersions({ limit: 500 }),
        ]);
        if (cancelled) return;
        setHealthOk(h?.status === "ok");
        setCounts({
          departments: depts.length,
          questionnaires: quests.length,
          policies: pols.length,
          versions: vers.length,
        });
      } catch (e) {
        if (!cancelled) setError(formatApiError(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <h1 className="pageTitle">Сводка</h1>
      <p className="pageSubtitle">
        Учебный прототип: формирование политики ИБ промышленного предприятия (с использованием ИИ).
      </p>

      <PageStatus loading={loading} error={error} empty={false}>
        {counts && (
          <>
            <div className="panel">
              <h2 className="panelTitle">Состояние API</h2>
              <p className="muted" style={{ marginBottom: 8 }}>
                {healthOk === true && "Сервис доступен."}
                {healthOk === false && (
                  <span className="calloutError" style={{ display: "inline-block", padding: "4px 8px" }}>
                    Нет ответа /health — проверьте backend и proxy.
                  </span>
                )}
              </p>
              <p className="hint" style={{ margin: 0 }}>
                Базовый URL:{" "}
                <code>{import.meta.env.VITE_API_URL || "(относительно dev-сервера → proxy /api)"}</code>
              </p>
            </div>

            <div className="panel">
              <h2 className="panelTitle">Количество записей</h2>
              <table className="dataTable" style={{ maxWidth: 360 }}>
                <tbody>
                  <tr>
                    <th scope="row">Подразделения</th>
                    <td>{counts.departments}</td>
                  </tr>
                  <tr>
                    <th scope="row">Анкеты</th>
                    <td>{counts.questionnaires}</td>
                  </tr>
                  <tr>
                    <th scope="row">Документы политики</th>
                    <td>{counts.policies}</td>
                  </tr>
                  <tr>
                    <th scope="row">Версии политик (всего)</th>
                    <td>{counts.versions}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="panel">
              <h2 className="panelTitle">Быстрые действия</h2>
              <div className="toolbar">
                <Link to="/departments" className="btn btnPrimary" style={{ textDecoration: "none" }}>
                  Создать подразделение
                </Link>
                <Link to="/questionnaires" className="btn btnPrimary" style={{ textDecoration: "none" }}>
                  Создать анкету
                </Link>
                <Link to="/questionnaires" className="btn btnSecondary" style={{ textDecoration: "none" }}>
                  Список анкет
                </Link>
              </div>
            </div>
          </>
        )}
      </PageStatus>
    </>
  );
}
