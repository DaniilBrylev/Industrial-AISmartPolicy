/**
 * Нормализация response_data с сервера и подготовка тела для PUT /response.
 */

export type AssetRow = {
  id: string;
  name: string;
  asset_type: string;
  owner: string;
  criticality: string;
  /** OT: зона (VLAN / сегмент) */
  network_zone?: string;
  vendor?: string;
  protocols?: string;
  supports_mfa?: boolean;
  supports_patching?: boolean;
  availability_class?: string;
  safety_critical?: boolean;
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
        const parseOptBool = (v: unknown): boolean | undefined => {
          if (v === true || v === false) return v;
          const s = typeof v === "string" ? v.trim().toLowerCase() : "";
          if (s === "true" || s === "yes" || s === "1") return true;
          if (s === "false" || s === "no" || s === "0") return false;
          return undefined;
        };
        assets.push({
          id: String(o.id ?? ""),
          name: String(o.name ?? ""),
          asset_type: String(o.asset_type ?? ""),
          owner: typeof owner === "string" ? owner : String(owner ?? ""),
          criticality: String(o.criticality ?? "").toLowerCase(),
          network_zone: o.network_zone != null ? String(o.network_zone) : "",
          vendor: o.vendor != null ? String(o.vendor) : "",
          protocols: o.protocols != null ? String(o.protocols) : "",
          supports_mfa: parseOptBool(o.supports_mfa),
          supports_patching: parseOptBool(o.supports_patching),
          availability_class:
            o.availability_class != null ? String(o.availability_class) : "",
          safety_critical: parseOptBool(o.safety_critical),
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
    assets: form.assets.map((a) => {
      const row: Record<string, unknown> = {
        id: a.id.trim(),
        name: a.name,
        asset_type: a.asset_type,
        owner: a.owner,
        criticality: a.criticality,
      };
      if (a.network_zone?.trim()) row.network_zone = a.network_zone.trim();
      if (a.vendor?.trim()) row.vendor = a.vendor.trim();
      if (a.protocols?.trim()) row.protocols = a.protocols.trim();
      if (a.supports_mfa !== undefined) row.supports_mfa = a.supports_mfa;
      if (a.supports_patching !== undefined) row.supports_patching = a.supports_patching;
      if (a.availability_class?.trim()) row.availability_class = a.availability_class.trim();
      if (a.safety_critical !== undefined) row.safety_critical = a.safety_critical;
      return row;
    }),
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
