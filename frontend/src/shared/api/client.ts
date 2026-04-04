const baseUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${p}`;
}
