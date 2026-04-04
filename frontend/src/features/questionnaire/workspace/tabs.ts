export type WorkspaceTabId = "data" | "analysis" | "diff" | "xai" | "workflow" | "policy";

export const WORKSPACE_TABS: { id: WorkspaceTabId; label: string }[] = [
  { id: "data", label: "Данные анкеты" },
  { id: "analysis", label: "Результаты анализа" },
  { id: "diff", label: "Актуализация" },
  { id: "xai", label: "Объяснимость" },
  { id: "workflow", label: "Согласование" },
  { id: "policy", label: "Политика" },
];
