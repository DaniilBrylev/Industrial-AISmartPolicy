import { apiJson } from "@/shared/api/http";
import type {
  PolicyDocumentCreate,
  PolicyDocumentRead,
  PolicySnapshotDiff,
  PolicyVersionSummaryRead,
} from "@/shared/api/types";

const base = "/api/policies";

export function listPolicyDocuments(): Promise<PolicyDocumentRead[]> {
  return apiJson<PolicyDocumentRead[]>(base);
}

export function createPolicyDocument(body: PolicyDocumentCreate): Promise<PolicyDocumentRead> {
  return apiJson<PolicyDocumentRead>(base, { method: "POST", json: body });
}

export function getPolicyDocument(id: number): Promise<PolicyDocumentRead> {
  return apiJson<PolicyDocumentRead>(`${base}/${id}`);
}

export function listPolicyVersions(policyId: number): Promise<PolicyVersionSummaryRead[]> {
  return apiJson<PolicyVersionSummaryRead[]>(`${base}/${policyId}/versions`);
}

export function comparePolicyVersions(
  policyId: number,
  fromVersion: number,
  toVersion: number,
): Promise<PolicySnapshotDiff> {
  const q = new URLSearchParams({
    from: String(fromVersion),
    to: String(toVersion),
  });
  return apiJson<PolicySnapshotDiff>(`${base}/${policyId}/diff?${q}`);
}
