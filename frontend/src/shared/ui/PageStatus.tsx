import type { ReactNode } from "react";

type Props = {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyText?: string;
  children: ReactNode;
};

/** Простые состояния страницы: загрузка, ошибка, пусто. */
export function PageStatus({
  loading,
  error,
  empty,
  emptyText = "Нет данных",
  children,
}: Props) {
  if (loading) {
    return <p className="muted">Загрузка…</p>;
  }
  if (error) {
    return (
      <div className="callout calloutError" role="alert">
        {error}
      </div>
    );
  }
  if (empty) {
    return <p className="muted">{emptyText}</p>;
  }
  return <>{children}</>;
}
