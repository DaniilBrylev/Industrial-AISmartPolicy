import { apiJson } from "@/shared/api/http";
import type { DepartmentCreate, DepartmentRead, DepartmentUpdate } from "@/shared/api/types";

const base = "/api/departments";

export function listDepartments(): Promise<DepartmentRead[]> {
  return apiJson<DepartmentRead[]>(base);
}

export function getDepartment(id: number): Promise<DepartmentRead> {
  return apiJson<DepartmentRead>(`${base}/${id}`);
}

export function createDepartment(body: DepartmentCreate): Promise<DepartmentRead> {
  return apiJson<DepartmentRead>(base, { method: "POST", json: body });
}

export function updateDepartment(
  id: number,
  body: DepartmentUpdate,
): Promise<DepartmentRead> {
  return apiJson<DepartmentRead>(`${base}/${id}`, { method: "PUT", json: body });
}

export function deleteDepartment(id: number): Promise<{ message: string }> {
  return apiJson<{ message: string }>(`${base}/${id}`, { method: "DELETE" });
}
