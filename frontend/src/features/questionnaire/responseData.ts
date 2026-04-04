/**
 * Нормализация response_data с сервера и подготовка тела для PUT /response.
 */

export type AssetRow = {
  id: string;
  name: string;
  asset_type: string;
  owner: string;
  criticality: string;
};

export type ProcessRow = {
  name: string;
  used_asset_ids: string;
};

/** Два текстовых поля на строку (матрица доступа, подрядчики, инциденты). */
export type PairRow = {
  field_a: string;
  field_b: string;
};

export type FormResponseData = {
  department_profile: {
    description: string;
    manager_name: string;
    contact_info: string;
  };
  assets: AssetRow[];
  business_processes: ProcessRow[];
  access_matrix: PairRow[];
  contractors: PairRow[];
  incidents: PairRow[];
  additional_notes: string;
};

export function emptyFormResponseData(): FormResponseData {
  return {
    department_profile: { description: "", manager_name: "", contact_info: "" },
    assets: [],
    business_processes: [],
    access_matrix: [],
    contractors: [],
    incidents: [],
    additional_notes: "",
  };
}

function pairRows(raw: unknown, keyA: string, keyB: string): PairRow[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const o = item as Record<string, unknown>;
      return {
        field_a: String(o[keyA] ?? o.name ?? o.resource ?? o.summary ?? ""),
        field_b: String(o[keyB] ?? o.details ?? o.note ?? o.description ?? ""),
      };
    }
    return { field_a: String(item ?? ""), field_b: "" };
  });
}

export function parseResponseDataFromServer(
  raw: Record<string, unknown> | undefined | null,
): FormResponseData {
  if (!raw || typeof raw !== "object") return emptyFormResponseData();

  const dp = raw.department_profile;
  const profile =
    dp && typeof dp === "object" && !Array.isArray(dp)
      ? {
          description: String((dp as Record<string, unknown>).description ?? ""),
          manager_name: String((dp as Record<string, unknown>).manager_name ?? ""),
          contact_info: String((dp as Record<string, unknown>).contact_info ?? ""),
        }
      : { description: "", manager_name: "", contact_info: "" };

  const assets: AssetRow[] = [];
  const assetsRaw = raw.assets;
  if (Array.isArray(assetsRaw)) {
    for (const item of assetsRaw) {
      if (item && typeof item === "object" && !Array.isArray(item)) {
        const o = item as Record<string, unknown>;
        const owner = o.owner ?? o.owner_name;
        assets.push({
          id: String(o.id ?? ""),
          name: String(o.name ?? ""),
          asset_type: String(o.asset_type ?? ""),
          owner: typeof owner === "string" ? owner : String(owner ?? ""),
          criticality: String(o.criticality ?? "").toLowerCase(),
        });
      }
    }
  }

  const business_processes: ProcessRow[] = [];
  const procRaw = raw.business_processes;
  if (Array.isArray(procRaw)) {
    for (const item of procRaw) {
      if (item && typeof item === "object" && !Array.isArray(item)) {
        const o = item as Record<string, unknown>;
        const used = o.used_asset_ids ?? o.asset_ids;
        let idsStr = "";
        if (Array.isArray(used)) {
          idsStr = used.map((x) => String(x)).join(", ");
        }
        business_processes.push({
          name: String(o.name ?? ""),
          used_asset_ids: idsStr,
        });
      }
    }
  }

  return {
    department_profile: profile,
    assets,
    business_processes,
    access_matrix: pairRows(raw.access_matrix, "resource", "note"),
    contractors: pairRows(raw.contractors, "name", "details"),
    incidents: pairRows(raw.incidents, "summary", "details"),
    additional_notes: typeof raw.additional_notes === "string" ? raw.additional_notes : "",
  };
}

export function formToSavePayload(form: FormResponseData): Record<string, unknown> {
  const usedIds = (s: string) =>
    s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

  return {
    department_profile: form.department_profile,
    assets: form.assets.map((a) => ({
      id: a.id.trim(),
      name: a.name,
      asset_type: a.asset_type,
      owner: a.owner,
      criticality: a.criticality,
    })),
    business_processes: form.business_processes.map((p) => ({
      name: p.name,
      used_asset_ids: usedIds(p.used_asset_ids),
    })),
    access_matrix: form.access_matrix.map((r) => ({
      resource: r.field_a,
      note: r.field_b,
    })),
    contractors: form.contractors.map((r) => ({
      name: r.field_a,
      details: r.field_b,
    })),
    incidents: form.incidents.map((r) => ({
      summary: r.field_a,
      details: r.field_b,
    })),
    additional_notes: form.additional_notes,
  };
}
