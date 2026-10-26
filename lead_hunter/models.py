from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RawLead:
    external_id: str
    source: str
    category: str  # "foro", "freelance", "bounty", "remoto", "buscador"
    title: str
    description: str
    url: str
    author: str = ""
    published_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    budget_hint: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class AnalyzedLead:
    external_id: str
    source: str
    category: str
    title: str
    description: str
    url: str
    author: str
    published_at: str
    score: int
    matched_ai_skills: list[str]
    matched_dev_skills: list[str]
    buying_signals: list[str]
    budget_detected: str
    language: str
    summary: str
    pitch: str
    status: str = "nuevo"
    id: int | None = None
