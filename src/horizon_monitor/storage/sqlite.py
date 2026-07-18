"""SQLite-backed persistent dynamics store for cross-session continuity.

Stores per-user/per-agent fidelity profiles, epsilon baselines, and
conversation summaries — enabling Horizon to detect behavioral drift
across sessions, not just within a single session.

Uses stdlib sqlite3 — no external dependencies.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    user_id         TEXT,
    agent_name      TEXT,
    domain          TEXT DEFAULT 'general',
    started_at      TEXT NOT NULL,
    last_turn_at    TEXT,
    turn_count      INTEGER DEFAULT 0,
    final_fidelity  REAL,
    health_status   TEXT,
    metadata        TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS turn_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    turn_number     INTEGER NOT NULL,
    timestamp       TEXT,
    fidelity_score  REAL,
    igt_value       REAL,
    divergence_score REAL,
    twr_value       REAL,
    consistency_score REAL,
    epsilon_t       REAL,
    health_status   TEXT,
    events          TEXT DEFAULT '[]',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id             TEXT PRIMARY KEY,
    avg_fidelity        REAL DEFAULT 0.5,
    avg_epsilon         REAL DEFAULT 0.3,
    session_count       INTEGER DEFAULT 0,
    preferred_domains   TEXT DEFAULT '[]',
    last_session_at     TEXT,
    updated_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_turn_session ON turn_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


class PersistentDynamicsStore:
    """SQLite persistence for cross-session fidelity dynamics.

    Thread-safe via per-connection threading.local() pattern.
    All operations are synchronous; the write path is fast (< 1ms typical).
    """

    def __init__(self, db_path: str | Path = "data/horizon.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._get_conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Session operations ──────────────────────────────────────────────────

    def save_session(
        self,
        session_id: str,
        user_id: str | None = None,
        agent_name: str | None = None,
        domain: str = "general",
        metadata: dict | None = None,
    ) -> None:
        """Upsert a session record."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, agent_name, domain, started_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    agent_name = excluded.agent_name,
                    domain = excluded.domain
                """,
                (
                    session_id,
                    user_id,
                    agent_name,
                    domain,
                    now,
                    json.dumps(metadata or {}),
                ),
            )

    def record_turn(
        self,
        session_id: str,
        turn_number: int,
        timestamp: str | None,
        fidelity_score: float,
        igt_value: float,
        divergence_score: float,
        twr_value: float,
        consistency_score: float,
        epsilon_t: float,
        health_status: str,
        events: list[dict],
    ) -> None:
        """Append a turn snapshot and update the parent session summary."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO turn_snapshots
                (session_id, turn_number, timestamp, fidelity_score, igt_value,
                 divergence_score, twr_value, consistency_score, epsilon_t, health_status, events)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    turn_number,
                    timestamp,
                    fidelity_score,
                    igt_value,
                    divergence_score,
                    twr_value,
                    consistency_score,
                    epsilon_t,
                    health_status,
                    json.dumps(events),
                ),
            )
            conn.execute(
                """
                UPDATE sessions SET
                    last_turn_at = ?,
                    turn_count = turn_count + 1,
                    final_fidelity = ?,
                    health_status = ?
                WHERE session_id = ?
                """,
                (now, fidelity_score, health_status, session_id),
            )

    def get_session_history(self, session_id: str) -> list[dict]:
        """Return all turn snapshots for a session, ordered by turn number."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM turn_snapshots WHERE session_id = ? ORDER BY turn_number",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── User profile operations ─────────────────────────────────────────────

    def update_user_profile(
        self,
        user_id: str,
        fidelity_score: float,
        epsilon_t: float,
        domain: str,
    ) -> None:
        """Exponentially update the user's long-term fidelity profile."""
        now = datetime.now(timezone.utc).isoformat()
        decay = 0.9
        with self._lock, self._get_conn() as conn:
            existing = conn.execute(
                "SELECT avg_fidelity, avg_epsilon, session_count, preferred_domains "
                "FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if existing:
                new_fidelity = decay * existing["avg_fidelity"] + (1 - decay) * fidelity_score
                new_epsilon = decay * existing["avg_epsilon"] + (1 - decay) * epsilon_t
                domains: list[str] = json.loads(existing["preferred_domains"])
                if domain not in domains:
                    domains.append(domain)
                conn.execute(
                    """
                    UPDATE user_profiles SET
                        avg_fidelity = ?,
                        avg_epsilon = ?,
                        session_count = session_count + 1,
                        preferred_domains = ?,
                        last_session_at = ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        new_fidelity,
                        new_epsilon,
                        json.dumps(domains),
                        now,
                        now,
                        user_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_profiles
                    (user_id, avg_fidelity, avg_epsilon, session_count,
                     preferred_domains, last_session_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?, ?)
                    """,
                    (user_id, fidelity_score, epsilon_t, json.dumps([domain]), now, now),
                )

    def get_user_profile(self, user_id: str) -> dict | None:
        """Return user's long-term fidelity profile, or None if new user."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_recent_sessions(self, user_id: str, limit: int = 5) -> list[dict]:
        """Return the user's most recent session records."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE user_id = ? ORDER BY started_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Data subject rights (GDPR Art. 17 / CCPA § 1798.105) ────────────────

    def delete_user_data(self, user_id: str) -> int:
        """Delete all data linked to a user_id.

        Satisfies GDPR Art. 17 (Right to Erasure) and CCPA § 1798.105.
        Removes sessions, turn snapshots, and the user profile in one
        atomic transaction.

        Returns the number of sessions (and their turn snapshots) deleted.
        """
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            session_ids = [r["session_id"] for r in rows]
            if session_ids:
                placeholders = ",".join("?" * len(session_ids))
                conn.execute(
                    "DELETE FROM turn_snapshots"
                    f" WHERE session_id IN ({placeholders})",
                    session_ids,
                )
                conn.execute(
                    "DELETE FROM sessions"
                    f" WHERE session_id IN ({placeholders})",
                    session_ids,
                )
            conn.execute(
                "DELETE FROM user_profiles WHERE user_id = ?",
                (user_id,),
            )
        return len(session_ids)

    def anonymize_session(self, session_id: str) -> bool:
        """Anonymize a session by nullifying its user_id (GDPR Art. 89).

        The session record and turn snapshots are retained but the link
        to the data subject is severed. Use when you need to keep aggregate
        analytics while honoring a specific user erasure request.

        For full erasure of all data for a user, call delete_user_data().

        Returns True if the session was found, False if not found.
        """
        with self._lock, self._get_conn() as conn:
            result = conn.execute(
                "UPDATE sessions SET user_id = NULL WHERE session_id = ?",
                (session_id,),
            )
            anonymized = result.rowcount > 0
        return anonymized
