interface SectionHeadingProps {
  eyebrow: string;
  title: string;
  description: string;
}

/**
 * Унифицированный заголовок секции.
 */
export function SectionHeading({
  eyebrow,
  title,
  description
}: SectionHeadingProps) {
  return (
    <header className="section-heading">
      <span className="section-heading__eyebrow">{eyebrow}</span>
      <h2 className="section-heading__title">{title}</h2>
      <p className="section-heading__description">{description}</p>
    </header>
  );
}
