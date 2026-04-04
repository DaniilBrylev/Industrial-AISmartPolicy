import type { FormResponseData } from "@/features/questionnaire/responseData";
import type { Dispatch, SetStateAction } from "react";

const CRIT = ["low", "medium", "high", "critical"] as const;

type Props = {
  data: FormResponseData;
  setData: Dispatch<SetStateAction<FormResponseData>>;
  disabled?: boolean;
};

function FieldLabel({ children }: { children: string }) {
  return <label className="fieldLabel">{children}</label>;
}

export function ResponseDataForm({ data, setData, disabled }: Props) {
  const setProfile = (patch: Partial<FormResponseData["department_profile"]>) => {
    setData((d) => ({
      ...d,
      department_profile: { ...d.department_profile, ...patch },
    }));
  };

  return (
    <div className="formSections">
      <section className="panel">
        <h3 className="panelTitle">Профиль подразделения</h3>
        <div className="fieldGrid">
          <div className="field">
            <FieldLabel>Описание</FieldLabel>
            <textarea
              className="input inputTextarea"
              rows={3}
              value={data.department_profile.description}
              onChange={(e) => setProfile({ description: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="field">
            <FieldLabel>Руководитель</FieldLabel>
            <input
              className="input"
              value={data.department_profile.manager_name}
              onChange={(e) => setProfile({ manager_name: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="field">
            <FieldLabel>Контакты</FieldLabel>
            <input
              className="input"
              value={data.department_profile.contact_info}
              onChange={(e) => setProfile({ contact_info: e.target.value })}
              disabled={disabled}
            />
          </div>
        </div>
      </section>

      <section className="panel">
        <h3 className="panelTitle">Активы</h3>
        <p className="hint">
          Поля: id, наименование, тип, владелец, критичность (low / medium / high / critical).
        </p>
        {data.assets.map((row, idx) => (
          <div key={idx} className="repeatBlock">
            <div className="repeatBlockHead">
              <span>Актив #{idx + 1}</span>
              {!disabled && (
                <button
                  type="button"
                  className="btn btnSmall btnSecondary"
                  onClick={() =>
                    setData((d) => ({
                      ...d,
                      assets: d.assets.filter((_, i) => i !== idx),
                    }))
                  }
                >
                  Удалить
                </button>
              )}
            </div>
            <div className="fieldGrid fieldGridTight">
              <div className="field">
                <FieldLabel>id</FieldLabel>
                <input
                  className="input"
                  value={row.id}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], id: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Наименование</FieldLabel>
                <input
                  className="input"
                  value={row.name}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], name: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Тип актива</FieldLabel>
                <input
                  className="input"
                  value={row.asset_type}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], asset_type: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Владелец</FieldLabel>
                <input
                  className="input"
                  value={row.owner}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], owner: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Критичность</FieldLabel>
                <select
                  className="input"
                  value={row.criticality || "medium"}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], criticality: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                >
                  {CRIT.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        ))}
        {!disabled && (
          <button
            type="button"
            className="btn btnSecondary"
            onClick={() =>
              setData((d) => ({
                ...d,
                assets: [
                  ...d.assets,
                  {
                    id: "",
                    name: "",
                    asset_type: "",
                    owner: "",
                    criticality: "medium",
                  },
                ],
              }))
            }
          >
            Добавить актив
          </button>
        )}
      </section>

      <section className="panel">
        <h3 className="panelTitle">Бизнес-процессы</h3>
        <p className="hint">Используемые активы — id через запятую (used_asset_ids).</p>
        {data.business_processes.map((row, idx) => (
          <div key={idx} className="repeatBlock">
            <div className="repeatBlockHead">
              <span>Процесс #{idx + 1}</span>
              {!disabled && (
                <button
                  type="button"
                  className="btn btnSmall btnSecondary"
                  onClick={() =>
                    setData((d) => ({
                      ...d,
                      business_processes: d.business_processes.filter((_, i) => i !== idx),
                    }))
                  }
                >
                  Удалить
                </button>
              )}
            </div>
            <div className="fieldGrid fieldGridTight">
              <div className="field">
                <FieldLabel>Название процесса</FieldLabel>
                <input
                  className="input"
                  value={row.name}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.business_processes];
                      next[idx] = { ...next[idx], name: e.target.value };
                      return { ...d, business_processes: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field fieldSpan2">
                <FieldLabel>ID активов (через запятую)</FieldLabel>
                <input
                  className="input"
                  value={row.used_asset_ids}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.business_processes];
                      next[idx] = { ...next[idx], used_asset_ids: e.target.value };
                      return { ...d, business_processes: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
            </div>
          </div>
        ))}
        {!disabled && (
          <button
            type="button"
            className="btn btnSecondary"
            onClick={() =>
              setData((d) => ({
                ...d,
                business_processes: [...d.business_processes, { name: "", used_asset_ids: "" }],
              }))
            }
          >
            Добавить процесс
          </button>
        )}
      </section>

      <PairSection
        title="Матрица доступа"
        hint="Ресурс и примечание (упрощённо)."
        rows={data.access_matrix}
        disabled={disabled}
        onChange={(rows) => setData((d) => ({ ...d, access_matrix: rows }))}
      />

      <PairSection
        title="Подрядчики"
        hint="Название и детали."
        rows={data.contractors}
        disabled={disabled}
        onChange={(rows) => setData((d) => ({ ...d, contractors: rows }))}
      />

      <PairSection
        title="Инциденты"
        hint="Кратко и описание."
        rows={data.incidents}
        disabled={disabled}
        onChange={(rows) => setData((d) => ({ ...d, incidents: rows }))}
      />

      <section className="panel">
        <h3 className="panelTitle">Дополнительные заметки</h3>
        <textarea
          className="input inputTextarea"
          rows={4}
          value={data.additional_notes}
          onChange={(e) => setData((d) => ({ ...d, additional_notes: e.target.value }))}
          disabled={disabled}
        />
      </section>
    </div>
  );
}

type PairProps = {
  title: string;
  hint: string;
  rows: FormResponseData["access_matrix"];
  disabled?: boolean;
  onChange: (rows: FormResponseData["access_matrix"]) => void;
};

function PairSection({ title, hint, rows, disabled, onChange }: PairProps) {
  return (
    <section className="panel">
      <h3 className="panelTitle">{title}</h3>
      <p className="hint">{hint}</p>
      {rows.map((row, idx) => (
        <div key={idx} className="repeatBlock">
          <div className="repeatBlockHead">
            <span>Запись #{idx + 1}</span>
            {!disabled && (
              <button
                type="button"
                className="btn btnSmall btnSecondary"
                onClick={() => onChange(rows.filter((_, i) => i !== idx))}
              >
                Удалить
              </button>
            )}
          </div>
          <div className="fieldGrid fieldGridTight">
            <div className="field">
              <FieldLabel>Поле 1</FieldLabel>
              <input
                className="input"
                value={row.field_a}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], field_a: e.target.value };
                  onChange(next);
                }}
                disabled={disabled}
              />
            </div>
            <div className="field">
              <FieldLabel>Поле 2</FieldLabel>
              <input
                className="input"
                value={row.field_b}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], field_b: e.target.value };
                  onChange(next);
                }}
                disabled={disabled}
              />
            </div>
          </div>
        </div>
      ))}
      {!disabled && (
        <button
          type="button"
          className="btn btnSecondary"
          onClick={() => onChange([...rows, { field_a: "", field_b: "" }])}
        >
          Добавить строку
        </button>
      )}
    </section>
  );
}
