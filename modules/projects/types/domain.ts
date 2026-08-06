export interface ProjectCardViewModel {
  id: string;
  slug: string;
  featured: boolean;
  title: string;
  summary: string;
  coverAsset?: string;
  category?: "commercial" | "academic" | "hackathon";
  period?: string;
  role?: string;
  teamSize?: number;
  responsibilities: string[];
  achievements: string[];
  technologies: string[];
  links: Array<{
    kind: string;
    label: string;
    href: string;
  }>;
}
