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

function OptBoolSelect({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: boolean | undefined;
  onChange: (v: boolean | undefined) => void;
  disabled?: boolean;
}) {
  const s = value === true ? "true" : value === false ? "false" : "";
  return (
    <div className="field">
      <FieldLabel>{label}</FieldLabel>
      <select
        className="input"
        value={s}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v === "" ? undefined : v === "true");
        }}
        disabled={disabled}
      >
        <option value="">— не задано</option>
        <option value="true">да</option>
        <option value="false">нет</option>
      </select>
    </div>
  );
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
      <section className="formSubSection">
        <h3 className="cardTitle">Профиль подразделения</h3>
        <p className="cardHint" style={{ marginTop: -6 }}>
          Юридический контекст подразделения для политики и маршрутов согласования.
        </p>
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

      <section className="formSubSection">
        <h3 className="cardTitle">Активы</h3>
        <p className="cardHint" style={{ marginTop: -6 }}>
          IT и OT активы. Для промышленного контура заполните зону, протоколы, MFA/патчинг и safety-critical — это
          влияет на OT-ограничения и компенсирующие меры в анализе.
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
              <div className="field">
                <FieldLabel>Сетевая зона (OT)</FieldLabel>
                <input
                  className="input"
                  placeholder="напр. ot_production_vlan20"
                  value={row.network_zone ?? ""}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], network_zone: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Производитель</FieldLabel>
                <input
                  className="input"
                  value={row.vendor ?? ""}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], vendor: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Протоколы</FieldLabel>
                <input
                  className="input"
                  placeholder="Modbus, OPC UA, Profinet…"
                  value={row.protocols ?? ""}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], protocols: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <div className="field">
                <FieldLabel>Класс доступности</FieldLabel>
                <input
                  className="input"
                  placeholder="low / medium / high / critical"
                  value={row.availability_class ?? ""}
                  onChange={(e) =>
                    setData((d) => {
                      const next = [...d.assets];
                      next[idx] = { ...next[idx], availability_class: e.target.value };
                      return { ...d, assets: next };
                    })
                  }
                  disabled={disabled}
                />
              </div>
              <OptBoolSelect
                label="Поддержка MFA на устройстве"
                value={row.supports_mfa}
                disabled={disabled}
                onChange={(v) =>
                  setData((d) => {
                    const next = [...d.assets];
                    next[idx] = { ...next[idx], supports_mfa: v };
                    return { ...d, assets: next };
                  })
                }
              />
              <OptBoolSelect
                label="Возможен регулярный патчинг"
                value={row.supports_patching}
                disabled={disabled}
                onChange={(v) =>
                  setData((d) => {
                    const next = [...d.assets];
                    next[idx] = { ...next[idx], supports_patching: v };
                    return { ...d, assets: next };
                  })
                }
              />
              <OptBoolSelect
                label="Safety-critical (АСУ ТП)"
                value={row.safety_critical}
                disabled={disabled}
                onChange={(v) =>
                  setData((d) => {
                    const next = [...d.assets];
                    next[idx] = { ...next[idx], safety_critical: v };
                    return { ...d, assets: next };
                  })
                }
              />
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
                    network_zone: "",
                    vendor: "",
                    protocols: "",
                    availability_class: "",
                  },
                ],
              }))
            }
          >
            Добавить актив
          </button>
        )}
      </section>

      <section className="formSubSection">
        <h3 className="cardTitle">Бизнес-процессы</h3>
        <p className="cardHint" style={{ marginTop: -6 }}>
          Связь процессов с активами: укажите id активов через запятую — это влияет на классификацию и explainability.
        </p>
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

      <section className="formSubSection">
        <h3 className="cardTitle">Дополнительные заметки</h3>
        <p className="cardHint" style={{ marginTop: -6 }}>
          Свободный текст; может учитываться NLP и резюме в AI enrichment.
        </p>
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
    <section className="formSubSection">
      <h3 className="cardTitle">{title}</h3>
      <p className="cardHint" style={{ marginTop: -6 }}>
        {hint}
      </p>
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
