"""
Session Memory — SQLite-backed persistent session storage.

Stores audit sessions, claims, evidence, and verdicts so users
can review past analyses and the system maintains context across runs.

Demonstrates the 'Session Memory' capstone concept.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default DB path relative to project root
_DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "sessions.db"


class SessionMemory:
    """
    SQLite-backed session memory.

    Stores:
      - Sessions: session_id, timestamp, input text preview, status
      - Claim results: per-claim data (claim, evidence, verdict) as JSON

    The database and tables are auto-created on first use.
    """

    def __init__(self, db_path: str | Path | None = None):
        """
        Args:
            db_path: Path to SQLite database file.
                     Defaults to data/sessions.db in the project root.
        """
        self._db_path = str(db_path or _DEFAULT_DB_PATH)

        # Ensure parent directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        logger.info("SessionMemory initialized at %s", self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    input_preview TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    total_claims INTEGER DEFAULT 0,
                    extraction_mode TEXT DEFAULT 'rule-based'
                );

                CREATE TABLE IF NOT EXISTS session_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    claim_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    verdict_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_session_claims_session
                    ON session_claims(session_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def create_session(self, input_text: str, extraction_mode: str = "rule-based") -> str:
        """
        Create a new audit session.

        Args:
            input_text: The full input text being analyzed.
            extraction_mode: 'rule-based' or 'gemini-llm'.

        Returns:
            The generated session_id (12-char hex string).
        """
        session_id = uuid.uuid4().hex[:12]
        created_at = datetime.now().isoformat()
        preview = input_text[:200].replace("\n", " ").strip()

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO sessions (session_id, created_at, input_text, input_preview, status, extraction_mode)
                   VALUES (?, ?, ?, ?, 'in_progress', ?)""",
                (session_id, created_at, input_text, preview, extraction_mode),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info("Created session %s", session_id)
        return session_id

    def store_claim_result(
        self,
        session_id: str,
        claim_id: str,
        claim: Any,
        evidence: Any,
        verdict: Any,
    ) -> None:
        """
        Store a processed claim result.

        Args:
            session_id: The session this claim belongs to.
            claim_id: Unique claim identifier.
            claim: Claim object or dict (will be JSON-serialized).
            evidence: List of evidence objects/dicts.
            verdict: Verdict object or dict.
        """
        # Serialize to JSON
        claim_json = self._to_json(claim)
        evidence_json = self._to_json(evidence)
        verdict_json = self._to_json(verdict)

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO session_claims (session_id, claim_id, claim_json, evidence_json, verdict_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, claim_id, claim_json, evidence_json, verdict_json),
            )
            conn.commit()
        finally:
            conn.close()

    def complete_session(self, session_id: str, total_claims: int) -> None:
        """Mark a session as completed."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE sessions SET status = 'completed', total_claims = ? WHERE session_id = ?""",
                (total_claims, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve a session and all its claim results.

        Returns:
            Dict with session metadata and list of claim results,
            or None if session not found.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

            if not row:
                return None

            claims = conn.execute(
                "SELECT * FROM session_claims WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()

            return {
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "input_preview": row["input_preview"],
                "status": row["status"],
                "total_claims": row["total_claims"],
                "extraction_mode": row["extraction_mode"],
                "claims": [
                    {
                        "claim_id": c["claim_id"],
                        "claim": json.loads(c["claim_json"]),
                        "evidence": json.loads(c["evidence_json"]),
                        "verdict": json.loads(c["verdict_json"]),
                    }
                    for c in claims
                ],
            }
        finally:
            conn.close()

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        List recent sessions, most recent first.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of session summary dicts.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT session_id, created_at, input_preview, status, total_claims, extraction_mode
                   FROM sessions ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()

            return [
                {
                    "session_id": r["session_id"],
                    "created_at": r["created_at"],
                    "input_preview": r["input_preview"],
                    "status": r["status"],
                    "total_claims": r["total_claims"],
                    "extraction_mode": r["extraction_mode"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def _to_json(obj: Any) -> str:
        """Serialize an object to JSON string."""
        if hasattr(obj, "model_dump"):
            # Pydantic model
            return json.dumps(obj.model_dump(), default=str)
        elif isinstance(obj, list):
            return json.dumps(
                [item.model_dump() if hasattr(item, "model_dump") else item for item in obj],
                default=str,
            )
        elif isinstance(obj, dict):
            return json.dumps(obj, default=str)
        else:
            return json.dumps(str(obj))
