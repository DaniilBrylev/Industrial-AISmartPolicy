import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { formatApiError } from "@/shared/api/http";
import { createPolicyDocument, listPolicyDocuments } from "@/shared/api/policies";
import type { PolicyDocumentRead } from "@/shared/api/types";
import { PageStatus } from "@/shared/ui/PageStatus";

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export function PoliciesPage() {
  const [rows, setRows] = useState<PolicyDocumentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("Политика ИБ (черновик)");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await listPolicyDocuments());
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    setMsg(null);
    try {
      const p = await createPolicyDocument({ title: title.trim() });
      setMsg(`Создан документ #${p.id} — укажите этот ID при генерации политики в карточке анкеты.`);
      await load();
    } catch (e) {
      setMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="pageTitle">Документы политики ИБ</h1>
      <p className="pageSubtitle">
        Справочник документов для привязки версий. Идентификатор документа передаётся в запрос генерации политики.
      </p>

      <PageStatus
        loading={loading}
        error={error}
        empty={!loading && !error && rows.length === 0}
        emptyText="Документов нет — создайте запись формой ниже."
      >
        {rows.length > 0 && (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Название</th>
                  <th>Статус</th>
                  <th>Текущая версия (id)</th>
                  <th>Создан</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.title}</td>
                    <td>{r.status}</td>
                    <td>{r.current_version_id ?? "—"}</td>
                    <td>{fmtDate(r.created_at)}</td>
                    <td>
                      <Link to={`/versions?policy_id=${r.id}`}>История версий</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageStatus>

      <div className="panel">
        <h2 className="panelTitle">Новый документ</h2>
        {msg && <div className="callout">{msg}</div>}
        <form onSubmit={(e) => void onCreate(e)} className="inlineForm">
          <div className="field" style={{ flex: "1 1 280px" }}>
            <label className="fieldLabel" htmlFor="p-title">
              Название
            </label>
            <input
              id="p-title"
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={busy}
            />
          </div>
          <button type="submit" className="btn btnPrimary" disabled={busy}>
            Создать
          </button>
        </form>
      </div>
    </>
  );
}
