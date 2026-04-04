import { apiBlob } from "@/shared/api/http";

export function downloadPolicyDocx(questionnaireId: number): Promise<Blob> {
  return apiBlob(`/api/files/policies/${questionnaireId}`);
}
