import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { formatApiError } from "@/shared/api/http";
import { comparePolicyVersions, getPolicyDocument, listPolicyVersions } from "@/shared/api/policies";
import type { PolicyDocumentRead, PolicySnapshotDiff, PolicyVersionSummaryRead } from "@/shared/api/types";
import { PageStatus } from "@/shared/ui/PageStatus";

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function shortHash(h: string | null | undefined) {
  if (!h) return "—";
  return h.length <= 14 ? h : `${h.slice(0, 10)}…`;
}

function DiffChunkView({ title, chunk }: { title: string; chunk: PolicySnapshotDiff["assets"] }) {
  const has =
    chunk.added.length > 0 || chunk.removed.length > 0 || chunk.changed.length > 0;
  if (!has) {
    return (
      <div className="diffBlock">
        <h4>{title}</h4>
        <p className="muted" style={{ margin: 0 }}>
          без изменений
        </p>
      </div>
    );
  }
  return (
    <div className="diffBlock">
      <h4>{title}</h4>
      {chunk.added.length > 0 && (
        <p>
          <strong>Добавлено:</strong>
        </p>
      )}
      {chunk.added.length > 0 && (
        <ul className="diffList">
          {chunk.added.map((s, i) => (
            <li key={`a-${i}`}>{s}</li>
          ))}
        </ul>
      )}
      {chunk.removed.length > 0 && (
        <p>
          <strong>Удалено:</strong>
        </p>
      )}
      {chunk.removed.length > 0 && (
        <ul className="diffList">
          {chunk.removed.map((s, i) => (
            <li key={`r-${i}`}>{s}</li>
          ))}
        </ul>
      )}
      {chunk.changed.length > 0 && (
        <>
          <p>
            <strong>Изменено:</strong>
          </p>
          <ul className="diffList">
            {chunk.changed.map((s, i) => (
              <li key={`c-${i}`}>{s}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function VersionsHistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [policyIdInput, setPolicyIdInput] = useState(() => searchParams.get("policy_id") ?? "");
  const [policyMeta, setPolicyMeta] = useState<PolicyDocumentRead | null>(null);
  const [versions, setVersions] = useState<PolicyVersionSummaryRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromV, setFromV] = useState<string>("");
  const [toV, setToV] = useState<string>("");
  const [diff, setDiff] = useState<PolicySnapshotDiff | null>(null);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const loadVersions = useCallback(
    async (pidStr?: string) => {
      const raw = (pidStr ?? policyIdInput).trim();
      const pid = Number(raw);
      if (!Number.isFinite(pid) || pid < 1) {
        setError("Введите корректный числовой ID документа политики.");
        return;
      }
      setPolicyIdInput(String(pid));
      setLoading(true);
      setError(null);
      setDiff(null);
      setDiffError(null);
      setVersions([]);
      setPolicyMeta(null);
      setFromV("");
      setToV("");
      try {
        const [doc, vers] = await Promise.all([getPolicyDocument(pid), listPolicyVersions(pid)]);
        setPolicyMeta(doc);
        setVersions(vers);
        setSearchParams({ policy_id: String(pid) });
        if (vers.length >= 2) {
          const sorted = [...vers].sort((a, b) => a.version_number - b.version_number);
          setFromV(String(sorted[0].version_number));
          setToV(String(sorted[sorted.length - 1].version_number));
        } else if (vers.length === 1) {
          setFromV(String(vers[0].version_number));
          setToV(String(vers[0].version_number));
        }
      } catch (e) {
        setError(formatApiError(e));
      } finally {
        setLoading(false);
      }
    },
    [policyIdInput, setSearchParams],
  );

  useEffect(() => {
    const q = searchParams.get("policy_id")?.trim();
    if (!q) return;
    const pid = Number(q);
    if (!Number.isFinite(pid) || pid < 1) return;
    void loadVersions(q);
    // только searchParams — иначе цикл при смене identity loadVersions
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  async function onCompare() {
    const pid = Number(policyIdInput.trim());
    const f = Number(fromV);
    const t = Number(toV);
    if (!Number.isFinite(pid) || !Number.isFinite(f) || !Number.isFinite(t)) {
      setDiffError("Укажите версии «с» и «по».");
      return;
    }
    setDiffLoading(true);
    setDiffError(null);
    setDiff(null);
    try {
      const d = await comparePolicyVersions(pid, f, t);
      setDiff(d);
    } catch (e) {
      setDiffError(formatApiError(e));
    } finally {
      setDiffLoading(false);
    }
  }

  const latest =
    versions.length === 0
      ? null
      : [...versions].sort((a, b) => b.version_number - a.version_number)[0];

  return (
    <>
      <h1 className="pageTitle">История версий политики</h1>
      <p className="pageSubtitle">
        Укажите ID документа политики (из раздела «Политики»), загрузите список версий и при необходимости сравните две
        версии.
      </p>

      <div className="panel">
        <h2 className="panelTitle">Выбор документа</h2>
        <div className="inlineForm">
          <div className="field" style={{ width: 200 }}>
            <label className="fieldLabel" htmlFor="pid">
              policy_id
            </label>
            <input
              id="pid"
              className="input"
              value={policyIdInput}
              onChange={(e) => setPolicyIdInput(e.target.value)}
            />
          </div>
          <button type="button" className="btn btnPrimary" disabled={loading} onClick={() => void loadVersions()}>
            Загрузить версии
          </button>
        </div>
      </div>

      <PageStatus loading={loading} error={error} empty={false}>
        {policyMeta && (
          <div className="panel">
            <h2 className="panelTitle">Документ</h2>
            <p style={{ margin: "0 0 8px" }}>
              <strong>{policyMeta.title}</strong> (id {policyMeta.id}, статус {policyMeta.status})
            </p>
            <p className="muted" style={{ margin: 0 }}>
              Текущая версия (ссылка в БД): {policyMeta.current_version_id ?? "—"}
            </p>
          </div>
        )}

        {latest && (
          <div className="callout calloutOk">
            Последняя по номеру версия: <strong>v{latest.version_number}</strong>, хеш источника:{" "}
            <code>{shortHash(latest.source_hash)}</code>, {fmtDate(latest.created_at)}
          </div>
        )}

        {versions.length > 0 && (
          <div className="tableWrap">
            <table className="dataTable">
              <thead>
                <tr>
                  <th>Версия</th>
                  <th>ID записи</th>
                  <th>source_hash</th>
                  <th>Создана</th>
                </tr>
              </thead>
              <tbody>
                {versions
                  .slice()
                  .sort((a, b) => b.version_number - a.version_number)
                  .map((v) => (
                    <tr key={v.id}>
                      <td>{v.version_number}</td>
                      <td>{v.id}</td>
                      <td>
                        <code>{shortHash(v.source_hash)}</code>
                      </td>
                      <td>{fmtDate(v.created_at)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && policyMeta && versions.length === 0 && (
          <p className="muted">Для этого документа версий пока нет (сгенерируйте политику с указанием policy_document_id).</p>
        )}

        {versions.length >= 1 && (
          <div className="panel">
            <h2 className="panelTitle">Сравнение снимков</h2>
            <div className="filtersRow">
              <div className="field">
                <label className="fieldLabel" htmlFor="v-from">
                  Версия «с»
                </label>
                <select id="v-from" className="input" value={fromV} onChange={(e) => setFromV(e.target.value)}>
                  <option value="">—</option>
                  {versions.map((v) => (
                    <option key={v.id} value={String(v.version_number)}>
                      {v.version_number}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label className="fieldLabel" htmlFor="v-to">
                  Версия «по»
                </label>
                <select id="v-to" className="input" value={toV} onChange={(e) => setToV(e.target.value)}>
                  <option value="">—</option>
                  {versions.map((v) => (
                    <option key={`t-${v.id}`} value={String(v.version_number)}>
                      {v.version_number}
                    </option>
                  ))}
                </select>
              </div>
              <button type="button" className="btn btnSecondary" disabled={diffLoading} onClick={() => void onCompare()}>
                Сравнить
              </button>
            </div>
            {diffLoading && <p className="muted">Считаем diff…</p>}
            {diffError && (
              <div className="callout calloutError" role="alert">
                {diffError}
              </div>
            )}
            {diff && (
              <>
                <DiffChunkView title="Активы (assets)" chunk={diff.assets} />
                <DiffChunkView title="Риски (risks)" chunk={diff.risks} />
                <DiffChunkView title="Меры (measures)" chunk={diff.measures} />
              </>
            )}
          </div>
        )}
      </PageStatus>
    </>
  );
}
