import { useCallback, useEffect, useState } from "react";
import {
  createDepartment,
  deleteDepartment,
  listDepartments,
  updateDepartment,
} from "@/shared/api/departments";
import { formatApiError } from "@/shared/api/http";
import type { DepartmentRead } from "@/shared/api/types";
import { PageStatus } from "@/shared/ui/PageStatus";

const emptyForm = {
  name: "",
  manager_name: "",
  contact_info: "",
  description: "",
};

export function DepartmentsPage() {
  const [rows, setRows] = useState<DepartmentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await listDepartments());
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function startEdit(row: DepartmentRead) {
    setEditingId(row.id);
    setForm({
      name: row.name,
      manager_name: row.manager_name,
      contact_info: row.contact_info,
      description: row.description ?? "",
    });
    setMsg(null);
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      if (editingId != null) {
        await updateDepartment(editingId, {
          name: form.name,
          manager_name: form.manager_name,
          contact_info: form.contact_info,
          description: form.description || null,
        });
        setMsg("Запись обновлена.");
      } else {
        await createDepartment({
          name: form.name,
          manager_name: form.manager_name,
          contact_info: form.contact_info,
          description: form.description || null,
        });
        setMsg("Подразделение создано.");
      }
      resetForm();
      await load();
    } catch (e) {
      setMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm(`Удалить подразделение #${id}?`)) return;
    setBusy(true);
    setMsg(null);
    try {
      await deleteDepartment(id);
      if (editingId === id) resetForm();
      setMsg("Удалено.");
      await load();
    } catch (e) {
      setMsg(formatApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="pageTitle">Подразделения</h1>
      <p className="pageSubtitle">Справочник подразделений предприятия.</p>

      <PageStatus
        loading={loading}
        error={error}
        empty={!loading && !error && rows.length === 0}
        emptyText="Подразделений пока нет — добавьте первую запись формой ниже."
      >
        {rows.length > 0 && (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Название</th>
                  <th>Руководитель</th>
                  <th>Контакты</th>
                  <th>Описание</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.name}</td>
                    <td>{r.manager_name}</td>
                    <td>{r.contact_info}</td>
                    <td>{r.description ?? "—"}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btnSmall btnSecondary"
                        disabled={busy}
                        onClick={() => startEdit(r)}
                      >
                        Изменить
                      </button>{" "}
                      <button
                        type="button"
                        className="btn btnSmall btnSecondary"
                        disabled={busy}
                        onClick={() => void onDelete(r.id)}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageStatus>

      <div className="panel">
        <h2 className="panelTitle">{editingId != null ? `Редактирование #${editingId}` : "Новое подразделение"}</h2>
        {msg && (
          <div className={msg.startsWith("HTTP") || msg.includes("detail") ? "callout calloutError" : "callout"}>
            {msg}
          </div>
        )}
        <form onSubmit={(e) => void onSubmit(e)}>
          <div className="fieldGrid">
            <div className="field">
              <label className="fieldLabel" htmlFor="d-name">
                Название *
              </label>
              <input
                id="d-name"
                className="input"
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label className="fieldLabel" htmlFor="d-mgr">
                Руководитель *
              </label>
              <input
                id="d-mgr"
                className="input"
                required
                value={form.manager_name}
                onChange={(e) => setForm((f) => ({ ...f, manager_name: e.target.value }))}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label className="fieldLabel" htmlFor="d-contact">
                Контакты *
              </label>
              <input
                id="d-contact"
                className="input"
                required
                value={form.contact_info}
                onChange={(e) => setForm((f) => ({ ...f, contact_info: e.target.value }))}
                disabled={busy}
              />
            </div>
            <div className="field fieldSpan2">
              <label className="fieldLabel" htmlFor="d-desc">
                Описание
              </label>
              <textarea
                id="d-desc"
                className="input inputTextarea"
                rows={2}
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                disabled={busy}
              />
            </div>
          </div>
          <div className="toolbar" style={{ marginTop: 12 }}>
            <button type="submit" className="btn btnPrimary" disabled={busy}>
              {editingId != null ? "Сохранить" : "Создать"}
            </button>
            {editingId != null && (
              <button type="button" className="btn btnSecondary" disabled={busy} onClick={resetForm}>
                Отмена
              </button>
            )}
          </div>
        </form>
      </div>
    </>
  );
}
