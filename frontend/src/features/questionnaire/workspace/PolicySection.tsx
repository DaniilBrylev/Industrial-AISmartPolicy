import type { QuestionnairePolicyGenerateResponse } from "@/shared/api/types";

function shortHash(h: string | null | undefined) {
  if (!h) return "—";
  return h.length <= 18 ? h : `${h.slice(0, 14)}…`;
}

type Props = {
  analysisStale: boolean;
  policyDocId: string;
  setPolicyDocId: (s: string) => void;
  policyHtml: string | null;
  policyGen: QuestionnairePolicyGenerateResponse | null;
  busy: boolean;
};

export function PolicySection({
  analysisStale,
  policyDocId,
  setPolicyDocId,
  policyHtml,
  policyGen,
  busy,
}: Props) {
  return (
    <div className="card">
      <h3 className="cardTitle">Политика ИБ</h3>
      <p className="cardHint">
        Генерация текста и DOCX на основе ответа анкеты и сохранённого анализа. Версионирование — при указании ID
        документа политики.
      </p>
      {analysisStale && (
        <div className="callout calloutError" style={{ marginBottom: 16 }}>
          <strong>Внимание:</strong> анализ помечен как устаревший. Перед генерацией рекомендуется выполнить
          «Анализировать», иначе политика может не отражать текущие данные.
        </div>
      )}
      {!analysisStale && policyHtml && (
        <div className="callout calloutOk" style={{ marginBottom: 16 }}>
          Предпросмотр ниже соответствует последней успешной генерации в этой сессии. При изменении анкеты обновите
          анализ и сгенерируйте политику снова.
        </div>
      )}
      <p className="cardHint" style={{ marginTop: -8 }}>
        Генерация и выгрузка DOCX — кнопки в шапке страницы.
      </p>
      <div className="field" style={{ maxWidth: 320, marginBottom: 16 }}>
        <label className="fieldLabel" htmlFor="pol-doc-w">
          ID документа политики (версионирование, необязательно)
        </label>
        <input
          id="pol-doc-w"
          className="input"
          value={policyDocId}
          onChange={(e) => setPolicyDocId(e.target.value)}
          disabled={busy}
          placeholder="например, 1"
        />
      </div>
      {policyGen?.versioning && (
        <div className="callout" style={{ marginBottom: 16 }}>
          <p style={{ margin: "0 0 6px" }}>
            <strong>Версионирование:</strong> <code>{policyGen.versioning.status}</code>
            {policyGen.versioning.version_number != null && (
              <> · версия #{policyGen.versioning.version_number}</>
            )}
          </p>
          <p style={{ margin: 0 }} className="muted">
            source_hash: <code>{shortHash(policyGen.versioning.source_hash)}</code>
          </p>
        </div>
      )}
      {policyHtml ? (
        <div className="policyFrameWrap">
          <iframe title="Предпросмотр политики" className="policyPreview" srcDoc={policyHtml} />
        </div>
      ) : (
        <div className="emptyState">Сгенерируйте политику — здесь появится HTML-предпросмотр.</div>
      )}
    </div>
  );
}
