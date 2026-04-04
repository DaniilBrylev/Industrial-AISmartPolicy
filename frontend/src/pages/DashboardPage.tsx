import { useEffect, useState } from "react";
import { fetchHealth } from "@/shared/api/health";

type Status = "loading" | "ok" | "error";

export function DashboardPage() {
  const [status, setStatus] = useState<Status>("loading");
  const [detail, setDetail] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchHealth();
        if (cancelled) return;
        if (data.status === "ok") {
          setStatus("ok");
          setDetail(`${data.service}: ${data.status}`);
        } else {
          setStatus("error");
          setDetail("Неожиданный ответ API");
        }
      } catch {
        if (!cancelled) {
          setStatus("error");
          setDetail("Не удалось выполнить запрос");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "2.5rem 1.25rem",
      }}
    >
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ margin: "0 0 0.5rem", fontSize: "1.75rem" }}>
          Политика ИБ промышленного предприятия
        </h1>
        <p style={{ margin: 0, color: "#475569" }}>
          Демонстрационный прототип (Этап 1: каркас системы)
        </p>
      </header>

      <section
        style={{
          background: "#fff",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "1.25rem 1.5rem",
          boxShadow: "0 1px 2px rgb(15 23 42 / 6%)",
        }}
      >
        <h2 style={{ margin: "0 0 1rem", fontSize: "1.1rem" }}>Состояние backend</h2>
        {status === "loading" && <p style={{ margin: 0 }}>Проверка…</p>}
        {status === "ok" && (
          <p style={{ margin: 0, color: "#15803d", fontWeight: 600 }}>
            Backend доступен
            {detail ? ` (${detail})` : ""}
          </p>
        )}
        {status === "error" && (
          <p style={{ margin: 0, color: "#b91c1c", fontWeight: 600 }}>
            Backend недоступен
            {detail ? ` — ${detail}` : ""}
          </p>
        )}
        <p style={{ margin: "1rem 0 0", fontSize: "0.9rem", color: "#64748b" }}>
          Запрос: <code>{import.meta.env.VITE_API_URL || "(не задан VITE_API_URL)"}/api/health</code>
        </p>
      </section>
    </main>
  );
}
