import { apiJson } from "@/shared/api/http";

/** Список версий (для счётчика на dashboard; опционально с фильтром по документу). */
export function listAllPolicyVersions(params?: { limit?: number }): Promise<unknown[]> {
  const limit = params?.limit ?? 500;
  return apiJson<unknown[]>(`/api/policy-versions?limit=${limit}`);
}
