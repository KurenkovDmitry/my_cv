"""Application-сервис модуля profile."""

from app.modules.profile.domain.entities import PublicProfile


class ProfileService:
    """Возвращает публичный профиль из временного in-memory источника."""

    async def get_public_profile(self, locale_code: str) -> dict[str, str]:
        profile = PublicProfile(
            display_name_ru="Д. А. Куренков",
            display_name_en="D. A. Kurenkov",
            headline_ru=(
                "Инженер, который соединяет highload-мышление, инфраструктуру и аккуратный интерфейс."
            ),
            headline_en=(
                "An engineer connecting highload thinking, infrastructure, and refined interface design."
            ),
            summary_ru=(
                "Стартовый профиль подготовлен для дальнейшего импорта данных из резюме и редактирования через админку."
            ),
            summary_en=(
                "The starter profile is prepared for future CV import and admin-side editing."
            ),
        )

        return {
            "displayName": profile.display_name_ru if locale_code == "ru" else profile.display_name_en,
            "headline": profile.headline_ru if locale_code == "ru" else profile.headline_en,
            "summary": profile.summary_ru if locale_code == "ru" else profile.summary_en,
        }

