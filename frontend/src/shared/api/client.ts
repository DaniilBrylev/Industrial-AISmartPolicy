/** Пустое значение: относительные пути /api/... (удобно с proxy Vite → backend). */
const baseUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${p}`;
}
