export interface ProjectCardViewModel {
  id: string;
  title: string;
  summary: string;
  technologies: string[];
  links: Array<{
    kind: string;
    label: string;
    href: string;
  }>;
}

