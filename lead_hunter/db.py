from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from lead_hunter.config import settings
from lead_hunter.models import AnalyzedLead


class LeadDatabase:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    url TEXT NOT NULL,
                    author TEXT DEFAULT '',
                    published_at TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    matched_ai_skills TEXT NOT NULL,
                    matched_dev_skills TEXT NOT NULL,
                    buying_signals TEXT NOT NULL,
                    budget_detected TEXT DEFAULT '',
                    language TEXT DEFAULT 'en',
                    summary TEXT DEFAULT '',
                    pitch TEXT DEFAULT '',
                    status TEXT DEFAULT 'nuevo',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)"
            )

    def exists(self, external_id: str, url: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM leads WHERE external_id = ? OR url = ? LIMIT 1",
                (external_id, url),
            ).fetchone()
            return row is not None

    def save_leads(self, leads: Iterable[AnalyzedLead]) -> list[AnalyzedLead]:
        inserted: list[AnalyzedLead] = []
        seen_ids: set[str] = set()
        seen_urls: set[str] = set()
        with self._connect() as conn:
            for lead in leads:
                if lead.external_id in seen_ids or lead.url in seen_urls:
                    continue
                row = conn.execute(
                    "SELECT 1 FROM leads WHERE external_id = ? OR url = ? LIMIT 1",
                    (lead.external_id, lead.url),
                ).fetchone()
                if row is not None:
                    continue
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO leads (
                        external_id, source, category, title, description, url,
                        author, published_at, score, matched_ai_skills,
                        matched_dev_skills, buying_signals, budget_detected,
                        language, summary, pitch, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead.external_id,
                        lead.source,
                        lead.category,
                        lead.title,
                        lead.description,
                        lead.url,
                        lead.author,
                        lead.published_at,
                        lead.score,
                        json.dumps(lead.matched_ai_skills, ensure_ascii=False),
                        json.dumps(lead.matched_dev_skills, ensure_ascii=False),
                        json.dumps(lead.buying_signals, ensure_ascii=False),
                        lead.budget_detected,
                        lead.language,
                        lead.summary,
                        lead.pitch,
                        lead.status,
                    ),
                )
                if cur.rowcount > 0:
                    lead.id = cur.lastrowid
                    inserted.append(lead)
                    seen_ids.add(lead.external_id)
                    seen_urls.add(lead.url)
        return inserted

    def list_leads(
        self,
        min_score: int = 0,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[AnalyzedLead]:
        query = "SELECT * FROM leads WHERE score >= ?"
        params: list[object] = [min_score]
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY score DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_lead(r) for r in rows]

    def get_lead(self, lead_id: int) -> AnalyzedLead | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM leads WHERE id = ?", (lead_id,)
            ).fetchone()
            return self._row_to_lead(row) if row else None

    def update_status(self, lead_id: int, status: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE leads SET status = ? WHERE id = ?", (status, lead_id)
            )
            return cur.rowcount > 0

    @staticmethod
    def _row_to_lead(row: sqlite3.Row) -> AnalyzedLead:
        return AnalyzedLead(
            id=row["id"],
            external_id=row["external_id"],
            source=row["source"],
            category=row["category"],
            title=row["title"],
            description=row["description"],
            url=row["url"],
            author=row["author"],
            published_at=row["published_at"],
            score=row["score"],
            matched_ai_skills=json.loads(row["matched_ai_skills"]),
            matched_dev_skills=json.loads(row["matched_dev_skills"]),
            buying_signals=json.loads(row["buying_signals"]),
            budget_detected=row["budget_detected"],
            language=row["language"],
            summary=row["summary"],
            pitch=row["pitch"],
            status=row["status"],
        )
