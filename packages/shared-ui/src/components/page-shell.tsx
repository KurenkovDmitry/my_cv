import type { PropsWithChildren } from "react";

/**
 * Общая оболочка страницы.
 *
 * Ограничивает ширину контента и позволяет сохранить единый rhythm между экранами.
 */
export function PageShell({ children }: PropsWithChildren) {
  return <div className="page-shell">{children}</div>;
}
