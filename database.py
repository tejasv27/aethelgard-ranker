"""
Aethelgard Database — Persistent RLRF & Compliance Layer
=========================================================

Production-grade SQLite persistence for recruiter feedback adjustments,
dynamic job profile caching, and compliance audit logging. Survives
application reboots and session token expirations.

Author: Team Aethelgard
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("aethelgard.database")

# ---------------------------------------------------------------------------
# Database path (stored alongside the application)
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "aethelgard_data.db"


class AethelgardDB:
    """
    Thread-safe SQLite manager for persistent RLRF state, job profile
    caching, and compliance audit trails.
    """

    _local = threading.local()

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DB_PATH)
        self._init_schema()

    # ── Connection pool (thread-local) ────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=10)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    # ── Schema initialization ─────────────────────────────────────────

    def _init_schema(self) -> None:
        """Create all tables and indices if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS recruiter_feedback (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id    TEXT    NOT NULL,
                role_context     TEXT    NOT NULL DEFAULT 'default',
                adjustment      REAL    NOT NULL,
                feedback_type   TEXT    NOT NULL CHECK(feedback_type IN ('upvote', 'downvote')),
                timestamp       TEXT    NOT NULL,
                UNIQUE(candidate_id, role_context)
            );

            CREATE INDEX IF NOT EXISTS idx_feedback_candidate
                ON recruiter_feedback(candidate_id);

            CREATE INDEX IF NOT EXISTS idx_feedback_role
                ON recruiter_feedback(role_context);

            CREATE TABLE IF NOT EXISTS job_profiles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                role_hash       TEXT    NOT NULL UNIQUE,
                jd_text         TEXT    NOT NULL,
                computed_weights TEXT   NOT NULL,
                weight_source   TEXT    NOT NULL DEFAULT 'default',
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_profiles_hash
                ON job_profiles(role_hash);

            CREATE TABLE IF NOT EXISTS compliance_audit (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type      TEXT    NOT NULL,
                details         TEXT    NOT NULL,
                timestamp       TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_audit_type
                ON compliance_audit(event_type);

            CREATE INDEX IF NOT EXISTS idx_audit_time
                ON compliance_audit(timestamp);
        """)
        conn.commit()
        log.info(f"Database initialized: {self.db_path}")

    # ── Recruiter Feedback (RLRF) ─────────────────────────────────────

    def record_feedback(
        self,
        candidate_id: str,
        feedback_type: str,
        adjustment: float,
        role_context: str = "default",
    ) -> None:
        """
        Record or update recruiter feedback for a candidate.
        Uses UPSERT to handle repeated clicks on the same candidate.
        """
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()

        conn.execute("""
            INSERT INTO recruiter_feedback (candidate_id, role_context, adjustment, feedback_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(candidate_id, role_context)
            DO UPDATE SET
                adjustment = excluded.adjustment,
                feedback_type = excluded.feedback_type,
                timestamp = excluded.timestamp
        """, (candidate_id, role_context, adjustment, feedback_type, now))
        conn.commit()

        # Audit trail
        self._log_audit("feedback_recorded", json.dumps({
            "candidate_id": candidate_id,
            "feedback_type": feedback_type,
            "adjustment": adjustment,
            "role_context": role_context,
        }))

    def get_all_feedback(self, role_context: str = "default") -> dict[str, float]:
        """
        Load all historical feedback adjustments for a role context.
        Returns {candidate_id: cumulative_adjustment}.
        """
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT candidate_id, adjustment
            FROM recruiter_feedback
            WHERE role_context = ?
        """, (role_context,)).fetchall()

        return {row["candidate_id"]: row["adjustment"] for row in rows}

    def get_feedback_counts(self, role_context: str = "default") -> dict[str, int]:
        """Get counts of upvotes and downvotes for a role context."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN feedback_type = 'upvote' THEN 1 ELSE 0 END), 0) as upvotes,
                COALESCE(SUM(CASE WHEN feedback_type = 'downvote' THEN 1 ELSE 0 END), 0) as downvotes
            FROM recruiter_feedback
            WHERE role_context = ?
        """, (role_context,)).fetchone()

        return {"upvotes": row["upvotes"], "downvotes": row["downvotes"]}

    def get_feedback_type(self, candidate_id: str, role_context: str = "default") -> str | None:
        """Get the feedback type for a specific candidate."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT feedback_type FROM recruiter_feedback
            WHERE candidate_id = ? AND role_context = ?
        """, (candidate_id, role_context)).fetchone()

        return row["feedback_type"] if row else None

    def clear_feedback(self, candidate_id: str, role_context: str = "default") -> None:
        """Remove feedback for a specific candidate."""
        conn = self._get_conn()
        conn.execute("""
            DELETE FROM recruiter_feedback
            WHERE candidate_id = ? AND role_context = ?
        """, (candidate_id, role_context))
        conn.commit()

    # ── Job Profile Caching ───────────────────────────────────────────

    @staticmethod
    def _hash_jd(jd_text: str) -> str:
        """Generate a deterministic hash for a JD text."""
        return hashlib.sha256(jd_text.strip().lower().encode("utf-8")).hexdigest()[:16]

    def cache_job_profile(
        self,
        jd_text: str,
        weights: dict[str, float],
        weight_source: str = "default",
    ) -> str:
        """
        Cache a computed weight profile for a JD. Returns the role_hash.
        """
        conn = self._get_conn()
        role_hash = self._hash_jd(jd_text)
        now = datetime.utcnow().isoformat()
        weights_json = json.dumps(weights)

        conn.execute("""
            INSERT INTO job_profiles (role_hash, jd_text, computed_weights, weight_source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(role_hash)
            DO UPDATE SET
                computed_weights = excluded.computed_weights,
                weight_source = excluded.weight_source,
                updated_at = excluded.updated_at
        """, (role_hash, jd_text[:5000], weights_json, weight_source, now, now))
        conn.commit()

        return role_hash

    def get_cached_weights(self, jd_text: str) -> tuple[dict[str, float] | None, str | None]:
        """
        Retrieve cached weights for a JD text.
        Returns (weights_dict, weight_source) or (None, None) if not cached.
        """
        conn = self._get_conn()
        role_hash = self._hash_jd(jd_text)

        row = conn.execute("""
            SELECT computed_weights, weight_source
            FROM job_profiles
            WHERE role_hash = ?
        """, (role_hash,)).fetchone()

        if row:
            try:
                weights = json.loads(row["computed_weights"])
                return weights, row["weight_source"]
            except json.JSONDecodeError:
                return None, None

        return None, None

    # ── Compliance Audit ──────────────────────────────────────────────

    def _log_audit(self, event_type: str, details: str) -> None:
        """Log an audit event."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT INTO compliance_audit (event_type, details, timestamp)
            VALUES (?, ?, ?)
        """, (event_type, details[:2000], now))
        conn.commit()

    def log_pipeline_run(self, details: dict[str, Any]) -> None:
        """Log a pipeline execution event."""
        self._log_audit("pipeline_run", json.dumps(details))

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent audit log entries."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT event_type, details, timestamp
            FROM compliance_audit
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "event_type": row["event_type"],
                "details": row["details"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    # ── Cleanup ───────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
