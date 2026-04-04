import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDepartments } from "@/shared/api/departments";
import { formatApiError } from "@/shared/api/http";
import { createQuestionnaire, listQuestionnaires } from "@/shared/api/questionnaires";
import type { DepartmentRead, QuestionnaireRead } from "@/shared/api/types";
import { PageStatus } from "@/shared/ui/PageStatus";

const STATUSES = ["draft", "submitted", "needs_revision", "approved"] as const;

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export function QuestionnairesPage() {
  const [depts, setDepts] = useState<DepartmentRead[]>([]);
  const [rows, setRows] = useState<QuestionnaireRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDept, setFilterDept] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [newTitle, setNewTitle] = useState("");
  const [newDeptId, setNewDeptId] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const loadLists = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [d, q] = await Promise.all([
        listDepartments(),
        listQuestionnaires({
          department_id: filterDept ? Number(filterDept) : undefined,
          status: filterStatus || undefined,
        }),
      ]);
      setDepts(d);
      setRows(q);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [filterDept, filterStatus]);

  useEffect(() => {
    void loadLists();
  }, [loadLists]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    const did = Number(newDeptId);
    if (!newTitle.trim() || !Number.isFinite(did) || did < 1) {
      setMsg("Укажите название и корректный ID подразделения.");
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const q = await createQuestionnaire({ title: newTitle.trim(), department_id: did });
      setMsg(`Создана анкета #${q.id}`);
      setNewTitle("");
      await loadLists();
    } catch (e) {
      setMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="pageTitle">Анкеты</h1>
      <p className="pageSubtitle">Список анкет и фильтры.</p>

      <div className="panel">
        <h2 className="panelTitle">Фильтры</h2>
        <div className="filtersRow">
          <div className="field">
            <label className="fieldLabel" htmlFor="f-dept">
              Подразделение (id)
            </label>
            <select
              id="f-dept"
              className="input"
              value={filterDept}
              onChange={(e) => setFilterDept(e.target.value)}
            >
              <option value="">Все</option>
              {depts.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.id} — {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="fieldLabel" htmlFor="f-st">
              Статус
            </label>
            <select
              id="f-st"
              className="input"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">Все</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="btn btnSecondary" onClick={() => void loadLists()} disabled={loading}>
            Обновить
          </button>
        </div>
      </div>

      <PageStatus
        loading={loading}
        error={error}
        empty={!loading && !error && rows.length === 0}
        emptyText="Анкет нет — создайте новую формой ниже."
      >
        {rows.length > 0 && (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Название</th>
                  <th>Статус</th>
                  <th>Подразделение</th>
                  <th>Создана</th>
                  <th>Обновлена</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.title}</td>
                    <td>{r.status}</td>
                    <td>{r.department_id}</td>
                    <td>{fmtDate(r.created_at)}</td>
                    <td>{fmtDate(r.updated_at)}</td>
                    <td>
                      <Link to={`/questionnaires/${r.id}`}>Открыть</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageStatus>

      <div className="panel">
        <h2 className="panelTitle">Новая анкета</h2>
        {msg && <div className="callout">{msg}</div>}
        <form onSubmit={(e) => void onCreate(e)} className="inlineForm">
          <div className="field" style={{ flex: "1 1 220px" }}>
            <label className="fieldLabel" htmlFor="q-title">
              Название
            </label>
            <input
              id="q-title"
              className="input"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              disabled={busy}
            />
          </div>
          <div className="field" style={{ width: 200 }}>
            <label className="fieldLabel" htmlFor="q-dept">
              Подразделение
            </label>
            <select
              id="q-dept"
              className="input"
              value={newDeptId}
              onChange={(e) => setNewDeptId(e.target.value)}
              disabled={busy}
            >
              <option value="">—</option>
              {depts.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.id} — {d.name}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn btnPrimary" disabled={busy}>
            Создать
          </button>
        </form>
      </div>
    </>
  );
}
