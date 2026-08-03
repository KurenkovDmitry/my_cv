import { describe, expect, it } from "vitest";
import { LocaleService } from "@portfolio/modules/localization";
import { ProjectViewModelFactory } from "../business/project-view-model-factory";

describe("ProjectViewModelFactory", () => {
  it("возвращает локализованную карточку проекта", () => {
    const localeService = new LocaleService(["en", "ru"], "en", { RU: "ru" });
    const factory = new ProjectViewModelFactory(localeService);

    const projectCard = factory.createCardViewModel(
      {
        id: "project-1",
        slug: "project-1",
        featured: true,
        status: "active",
        title: { ru: "Тест", en: "Test" },
        summary: { ru: "Описание", en: "Description" },
        technologies: ["TypeScript"],
        links: [
          {
            kind: "repository",
            label: { ru: "Код", en: "Code" },
            href: "#",
          },
        ],
      },
      "ru",
    );

    expect(projectCard.title).toBe("Тест");
    expect(projectCard.links[0]?.label).toBe("Код");
  });
});

