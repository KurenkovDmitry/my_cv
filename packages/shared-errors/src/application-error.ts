/**
 * Базовая ошибка приложения.
 *
 * Используется как единый формат для frontend-слоя до момента,
 * пока backend не начнёт отдавать полноценные error DTO.
 */
export class ApplicationError extends Error {
  public constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, string | number | boolean>,
  ) {
    super(message);
    this.name = "ApplicationError";
  }
}

