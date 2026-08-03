import type { ConsentModalProps } from "../../types/consent";

/**
 * Блокирующая модалка согласия на полностью обезличенную аналитику.
 */
export function ConsentModal({
  localeCode,
  content,
  onAccept,
  onReject,
}: ConsentModalProps) {
  const modalBody = content.modalBodyMarkdown[localeCode]
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <div className="consent-modal" role="dialog" aria-modal="true" aria-labelledby="consent-modal-title">
      <div className="consent-modal__backdrop" aria-hidden="true" />
      <div className="consent-modal__card">
        <p className="consent-modal__eyebrow">
          {localeCode === "ru" ? "Пользовательское соглашение" : "User agreement"}
        </p>
        <h2 id="consent-modal-title" className="consent-modal__title">
          {content.modalTitle[localeCode]}
        </h2>
        <div className="consent-modal__body">
          {modalBody.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
        <div className="consent-modal__actions">
          <button className="consent-modal__button consent-modal__button--primary" type="button" onClick={onAccept}>
            {content.acceptButtonLabel[localeCode]}
          </button>
          <button className="consent-modal__button consent-modal__button--secondary" type="button" onClick={onReject}>
            {content.rejectButtonLabel[localeCode]}
          </button>
        </div>
      </div>
    </div>
  );
}
