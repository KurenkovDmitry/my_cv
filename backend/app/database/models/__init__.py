"""Импортирует ORM-модели для регистрации в metadata."""

from app.database.models.analytics_models import (
    SectionClickDaily,
    SectionClickTotal,
    SectionViewDaily,
    SectionViewTotal,
    SessionDaily,
    SessionTotal,
)
from app.database.models.audit_models import AdminActionLog
from app.database.models.public_models import MediaAsset, PortfolioSnapshot
from app.database.models.system_models import (
    AdminContentState,
    BackupArtifact,
    ImportCandidate,
    RuntimeHealthSnapshot,
)

__all__ = [
    "AdminActionLog",
    "AdminContentState",
    "BackupArtifact",
    "ImportCandidate",
    "MediaAsset",
    "PortfolioSnapshot",
    "RuntimeHealthSnapshot",
    "SectionClickDaily",
    "SectionClickTotal",
    "SectionViewDaily",
    "SectionViewTotal",
    "SessionDaily",
    "SessionTotal",
]
