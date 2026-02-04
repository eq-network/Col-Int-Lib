"""
Database layer for prediction tracking.

Uses SQLite for simplicity and portability.

## Concurrency Model

**Single-threaded assumptions:**
- This class assumes single-threaded access within a process
- SQLite serializes all writes automatically (prevents corruption)
- However, reads during writes may see incomplete data

**Multi-threaded safety:**
- SQLite connection is NOT thread-safe by default
- To use from multiple threads:
  1. Create separate TrackerDB instance per thread, OR
  2. Enable check_same_thread=False and add locking, OR
  3. Use connection pooling (not implemented)

**Multi-process safety:**
- SQLite file locking prevents corruption across processes
- However, long transactions can block other processes
- For production multi-process: enable WAL mode

  ```python
  conn.execute("PRAGMA journal_mode=WAL")
  ```

**MCP Server:**
- Async functions call synchronous database methods
- This is safe because MCP event loop is single-threaded
- For concurrent requests, would need async SQLite library (aiosqlite)

## Transaction Boundaries

Currently commits after every operation (autocommit style).
This is simple but prevents batching for performance.

Future: Add explicit transaction control with begin/commit/rollback.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json


class TrackerDBError(Exception):
    """Base exception for TrackerDB errors."""
    pass


class PredictionNotFoundError(TrackerDBError):
    """Raised when prediction ID doesn't exist."""
    pass


class InvalidPredictionError(TrackerDBError):
    """Raised when prediction data is invalid."""
    pass


class DatabaseError(TrackerDBError):
    """Raised when database operation fails."""
    pass


class TrackerDB:
    """
    Database layer for prediction tracking.

    Usage:
        with TrackerDB("tracker.db") as db:
            pred_id = db.register_prediction(...)
            # Connection automatically closed

    Backward compatible usage:
        db = TrackerDB("tracker.db")
        db.register_prediction(...)
        db.close()  # Must remember to close!

    Concurrency assumptions:
        - Single-threaded access assumed
        - SQLite serializes writes automatically
        - Not safe for multi-process access without WAL mode
    """

    def __init__(self, db_path: str = "tracker.db"):
        """
        Initialize database connection.

        Note: Does not create connection yet. Use as context manager
        or call open() explicitly.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._opened_by_context_manager = False

    def open(self):
        """
        Open database connection explicitly.

        Returns:
            self for chaining
        """
        if self.conn is not None:
            return self

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        self._init_schema()
        return self

    def __enter__(self):
        """Context manager entry."""
        self._opened_by_context_manager = True
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - always closes connection."""
        self.close()
        return False  # Don't suppress exceptions

    def _ensure_open(self):
        """
        Ensure connection is open before operations.

        Raises:
            RuntimeError: If connection is not open
        """
        if self.conn is None:
            # For backward compatibility, auto-open if not using context manager
            if not self._opened_by_context_manager:
                self.open()
            else:
                raise RuntimeError(
                    "Database not open. Use 'with TrackerDB(...) as db:' or call db.open()"
                )

    def _init_schema(self):
        """Create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                calibration REAL,
                prediction_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                probability REAL NOT NULL CHECK(probability >= 0 AND probability <= 1),
                horizon_minutes INTEGER NOT NULL,
                condition TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                outcome BOOLEAN,
                brier_score REAL,
                FOREIGN KEY (agent_name) REFERENCES agents(name)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                agent_name TEXT,
                prediction_id INTEGER,
                data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_agent ON predictions(agent_name);
            CREATE INDEX IF NOT EXISTS idx_predictions_resolved ON predictions(resolved_at);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        """)
        self.conn.commit()

    def register_agent(self, name: str) -> int:
        """
        Register a new agent. Returns agent ID.

        Args:
            name: Agent name (must be non-empty)

        Returns:
            Database agent ID

        Raises:
            InvalidPredictionError: If name is empty
            DatabaseError: If database operation fails
        """
        self._ensure_open()

        if not name or not name.strip():
            raise InvalidPredictionError("Agent name cannot be empty")

        try:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO agents (name) VALUES (?)",
                (name,)
            )
            self.conn.commit()
            return cursor.lastrowid or self.conn.execute(
                "SELECT id FROM agents WHERE name = ?", (name,)
            ).fetchone()[0]
        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to register agent: {e}") from e

    def register_prediction(
        self,
        agent_name: str,
        probability: float,
        horizon_minutes: int,
        condition: str = "task_complete",
        context: Optional[Dict] = None
    ) -> int:
        """
        Register a new prediction. Returns prediction ID.

        Args:
            agent_name: Name of agent making prediction
            probability: Predicted probability in [0, 1]
            horizon_minutes: Time horizon in minutes (must be positive)
            condition: Condition being predicted
            context: Optional context dict (must be JSON-serializable)

        Returns:
            Database prediction ID

        Raises:
            InvalidPredictionError: If validation fails
            DatabaseError: If database operation fails

        Concurrency:
            Safe for concurrent calls (SQLite serializes writes)
        """
        self._ensure_open()

        # Validate inputs
        if not agent_name or not agent_name.strip():
            raise InvalidPredictionError("agent_name cannot be empty")

        if not 0 <= probability <= 1:
            raise InvalidPredictionError(
                f"probability must be in [0, 1], got {probability}"
            )

        if horizon_minutes <= 0:
            raise InvalidPredictionError(
                f"horizon_minutes must be positive, got {horizon_minutes}"
            )

        # Validate context is JSON-serializable
        if context is not None:
            try:
                json.dumps(context)
            except (TypeError, ValueError) as e:
                raise InvalidPredictionError(
                    f"context must be JSON-serializable: {e}"
                )

        try:
            self.register_agent(agent_name)

            cursor = self.conn.execute("""
                INSERT INTO predictions (agent_name, probability, horizon_minutes, condition, context)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_name, probability, horizon_minutes, condition, json.dumps(context or {})))

            pred_id = cursor.lastrowid

            # Log event
            self.conn.execute("""
                INSERT INTO events (event_type, agent_name, prediction_id, data)
                VALUES (?, ?, ?, ?)
            """, ("prediction_registered", agent_name, pred_id, json.dumps({
                "probability": probability,
                "horizon_minutes": horizon_minutes
            })))

            self.conn.commit()
            return pred_id

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to register prediction: {e}") from e

    def resolve_prediction(self, prediction_id: int, outcome: bool):
        """
        Resolve a prediction with an outcome.

        Args:
            prediction_id: ID of prediction to resolve
            outcome: Actual outcome (True/False)

        Raises:
            PredictionNotFoundError: If prediction doesn't exist
            DatabaseError: If database operation fails
        """
        self._ensure_open()

        try:
            # Get prediction
            pred = self.conn.execute(
                "SELECT * FROM predictions WHERE id = ?", (prediction_id,)
            ).fetchone()

            if not pred:
                raise PredictionNotFoundError(f"Prediction {prediction_id} not found")

            # Compute Brier score using pure function
            from tracker.metrics import compute_brier_score
            brier = compute_brier_score(pred["probability"], outcome)

            # Update prediction
            self.conn.execute("""
                UPDATE predictions
                SET resolved_at = CURRENT_TIMESTAMP, outcome = ?, brier_score = ?
                WHERE id = ?
            """, (outcome, brier, prediction_id))

            # Update agent calibration
            self._update_agent_calibration(pred["agent_name"])

            # Log event
            self.conn.execute("""
                INSERT INTO events (event_type, agent_name, prediction_id, data)
                VALUES (?, ?, ?, ?)
            """, ("prediction_resolved", pred["agent_name"], prediction_id, json.dumps({
                "outcome": outcome,
                "brier_score": brier
            })))

            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to resolve prediction: {e}") from e

    def _update_agent_calibration(self, agent_name: str):
        """
        Recalculate agent's calibration (running average of Brier scores).

        Note: Uses SQL AVG() which is efficient for this operation.
        For incremental updates, see tracker.metrics.compute_incremental_calibration.

        Args:
            agent_name: Agent to update
        """
        # Get all resolved predictions for this agent
        result = self.conn.execute("""
            SELECT AVG(brier_score) as avg_brier, COUNT(*) as count
            FROM predictions
            WHERE agent_name = ? AND resolved_at IS NOT NULL
        """, (agent_name,)).fetchone()

        avg_brier = result["avg_brier"] or 0.0
        count = result["count"]

        # Update agent
        self.conn.execute("""
            UPDATE agents
            SET calibration = ?, prediction_count = ?, last_updated = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (avg_brier, count, agent_name))

        self.conn.commit()

    def get_agent_stats(self, agent_name: str) -> Optional[Dict]:
        """
        Get statistics for an agent.

        Args:
            agent_name: Agent name to query

        Returns:
            Dict with agent stats, or None if not found
        """
        self._ensure_open()
        row = self.conn.execute(
            "SELECT * FROM agents WHERE name = ?", (agent_name,)
        ).fetchone()

        if not row:
            return None

        return dict(row)

    def get_leaderboard(self) -> List[Dict]:
        """
        Get all agents sorted by calibration (lower is better).

        Returns:
            List of agent dicts sorted by calibration
        """
        self._ensure_open()
        rows = self.conn.execute("""
            SELECT * FROM agents
            WHERE prediction_count > 0
            ORDER BY calibration ASC
        """).fetchall()

        return [dict(row) for row in rows]

    def get_predictions(
        self,
        agent_name: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get predictions with optional filters.

        Args:
            agent_name: Filter by agent name
            resolved: Filter by resolution status (None = all)
            limit: Maximum number of results

        Returns:
            List of prediction dicts
        """
        self._ensure_open()
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []

        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)

        if resolved is not None:
            if resolved:
                query += " AND resolved_at IS NOT NULL"
            else:
                query += " AND resolved_at IS NULL"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_pending_resolutions(self) -> List[Dict]:
        """
        Get predictions that are past their horizon but not resolved.

        Returns:
            List of prediction dicts needing resolution
        """
        self._ensure_open()
        rows = self.conn.execute("""
            SELECT * FROM predictions
            WHERE resolved_at IS NULL
            AND datetime(created_at, '+' || horizon_minutes || ' minutes') < datetime('now')
            ORDER BY created_at DESC
        """).fetchall()

        return [dict(row) for row in rows]

    def close(self):
        """Close database connection."""
        if self.conn is not None:
            self.conn.close()
            self.conn = None
