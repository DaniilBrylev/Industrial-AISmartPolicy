import type {
  AiAnalysisEnrichment,
  AnalysisLinkItem,
  AnalysisReport,
  ClassifiedAssetItem,
  NlpEntityItem,
  NlpRelationItem,
  RiskItem,
  TraceabilityMap,
} from "@/shared/api/types";

function asObj(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

function asStringRecord(v: unknown): Record<string, string> {
  if (!v || typeof v !== "object" || Array.isArray(v)) return {};
  const out: Record<string, string> = {};
  for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
    out[k] = String(val);
  }
  return out;
}

function parseEnrichment(raw: unknown): AiAnalysisEnrichment | null {
  const o = asObj(raw);
  if (!o) return null;
  const entitiesRaw = o.entities;
  const relationsRaw = o.relations;
  let entities: NlpEntityItem[] | null = null;
  if (Array.isArray(entitiesRaw)) {
    entities = entitiesRaw
      .map((x) => {
        const e = asObj(x);
        if (!e) return null;
        return {
          type: String(e.type ?? ""),
          value: String(e.value ?? ""),
          source_field: String(e.source_field ?? ""),
        };
      })
      .filter((x): x is NlpEntityItem => x != null);
  }
  let relations: NlpRelationItem[] | null = null;
  if (Array.isArray(relationsRaw)) {
    relations = relationsRaw
      .map((x) => {
        const e = asObj(x);
        if (!e) return null;
        return {
          subject: String(e.subject ?? ""),
          relation: String(e.relation ?? ""),
          object: String(e.object ?? ""),
          source_field: String(e.source_field ?? ""),
        };
      })
      .filter((x): x is NlpRelationItem => x != null);
  }
  const nt = o.normalized_text;
  return {
    risk_explanations: asStringRecord(o.risk_explanations),
    link_explanations: asStringRecord(o.link_explanations),
    notes_summary: o.notes_summary != null ? String(o.notes_summary) : null,
    normalized_text: nt && typeof nt === "object" && !Array.isArray(nt) ? (nt as Record<string, unknown>) : null,
    entities,
    relations,
    llm_used: o.llm_used === true,
    model: o.model != null ? String(o.model) : null,
    generated_at: o.generated_at != null ? String(o.generated_at) : null,
  };
}

function parseClassified(raw: unknown): ClassifiedAssetItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((x) => {
      const o = asObj(x);
      if (!o) return null;
      const notes = o.notes;
      return {
        asset_id: String(o.asset_id ?? ""),
        environment: String(o.environment ?? "IT"),
        original_criticality: String(o.original_criticality ?? ""),
        effective_criticality: String(o.effective_criticality ?? ""),
        usage_count: typeof o.usage_count === "number" ? o.usage_count : Number(o.usage_count) || 0,
        notes: Array.isArray(notes) ? notes.map((n) => String(n)) : [],
      };
    })
    .filter((x): x is ClassifiedAssetItem => x != null && x.asset_id !== "");
}

function parseRisks(raw: unknown): RiskItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((x) => {
      const o = asObj(x);
      if (!o) return null;
      const asset_id = String(o.asset_id ?? "");
      const risk_code = String(o.risk_code ?? "");
      if (!asset_id || !risk_code) return null;
      return {
        asset_id,
        risk_code,
        title: String(o.title ?? risk_code),
        severity: String(o.severity ?? "medium"),
      };
    })
    .filter((x): x is RiskItem => x != null);
}

function parseLinks(raw: unknown): AnalysisLinkItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((x) => {
      const o = asObj(x);
      if (!o) return null;
      return {
        asset_id: String(o.asset_id ?? ""),
        risk: String(o.risk ?? ""),
        requirement: String(o.requirement ?? ""),
        measure: String(o.measure ?? ""),
      };
    })
    .filter((x): x is AnalysisLinkItem => x != null);
}

function parseTraceability(raw: unknown): TraceabilityMap | null {
  const o = asObj(raw);
  if (!o || !Array.isArray(o.entries)) return null;
  return { entries: o.entries as TraceabilityMap["entries"] };
}

/** Безопасный разбор сохранённого analysis_result с сервера. */
export function parseAnalysisReportJson(json: string | null): AnalysisReport | null {
  if (!json?.trim()) return null;
  try {
    const data = JSON.parse(json) as unknown;
    const o = asObj(data);
    if (!o) return null;
    const meta = o.analysis_meta;
    const metaObj = asObj(meta);
    return {
      assets: Array.isArray(o.assets) ? (o.assets as Record<string, unknown>[]) : [],
      classified_assets: parseClassified(o.classified_assets),
      risks: parseRisks(o.risks),
      requirements: Array.isArray(o.requirements) ? o.requirements.map(String) : [],
      measures: Array.isArray(o.measures) ? o.measures.map(String) : [],
      links: parseLinks(o.links),
      warnings: Array.isArray(o.warnings) ? o.warnings.map(String) : [],
      ai_enrichment: parseEnrichment(o.ai_enrichment),
      traceability_map: parseTraceability(o.traceability_map),
      analysis_meta:
        metaObj && typeof metaObj.source_hash === "string"
          ? {
              source_hash: String(metaObj.source_hash),
              generated_at: String(metaObj.generated_at ?? ""),
              tracked_sections: Array.isArray(metaObj.tracked_sections)
                ? metaObj.tracked_sections.map(String)
                : [],
            }
          : undefined,
    };
  } catch {
    return null;
  }
}

export function mergeReportFromAnalyze(
  stored: AnalysisReport | null,
  fresh: AnalysisReport | null,
): AnalysisReport | null {
  return fresh ?? stored;
}

/** Нормализация объекта отчёта из POST /analyze (уже объект). */
export function coerceAnalysisReport(data: unknown): AnalysisReport | null {
  try {
    return parseAnalysisReportJson(JSON.stringify(data));
  } catch {
    return null;
  }
}
