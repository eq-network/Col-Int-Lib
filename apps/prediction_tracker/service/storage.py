"""
Minimal SQLite storage for predictions.

Just data access - no business logic, no complex validation.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
from datetime import datetime


class PredictionStore:
    """Minimal SQLite storage for predictions."""

    def __init__(self, db_path: str = "tracker.db"):
        """Initialize storage with database path."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

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
                probability REAL NOT NULL,
                horizon_minutes INTEGER NOT NULL,
                condition TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                outcome BOOLEAN,
                brier_score REAL,
                FOREIGN KEY (agent_name) REFERENCES agents(name)
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_agent ON predictions(agent_name);
            CREATE INDEX IF NOT EXISTS idx_predictions_resolved ON predictions(resolved_at);
        """)
        self.conn.commit()

    def create_prediction(
        self,
        agent_name: str,
        probability: float,
        horizon_minutes: int,
        condition: str,
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a prediction. Returns prediction ID."""
        # Ensure agent exists
        self.conn.execute(
            "INSERT OR IGNORE INTO agents (name) VALUES (?)",
            (agent_name,)
        )

        cursor = self.conn.execute("""
            INSERT INTO predictions (agent_name, probability, horizon_minutes, condition, context)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, probability, horizon_minutes, condition, json.dumps(context or {})))

        self.conn.commit()
        return cursor.lastrowid

    def resolve_prediction(self, prediction_id: int, outcome: bool) -> float:
        """Resolve a prediction. Returns Brier score."""
        # Get prediction
        row = self.conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (prediction_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Prediction {prediction_id} not found")

        # Calculate Brier score
        from tracker.metrics import compute_brier_score
        brier = compute_brier_score(row["probability"], outcome)

        # Update prediction
        self.conn.execute("""
            UPDATE predictions
            SET resolved_at = CURRENT_TIMESTAMP, outcome = ?, brier_score = ?
            WHERE id = ?
        """, (outcome, brier, prediction_id))

        # Update agent calibration
        self._update_agent_calibration(row["agent_name"])

        self.conn.commit()
        return brier

    def _update_agent_calibration(self, agent_name: str):
        """Recalculate agent's calibration."""
        result = self.conn.execute("""
            SELECT AVG(brier_score) as avg_brier, COUNT(*) as count
            FROM predictions
            WHERE agent_name = ? AND resolved_at IS NOT NULL
        """, (agent_name,)).fetchone()

        avg_brier = result["avg_brier"] or 0.0
        count = result["count"]

        self.conn.execute("""
            UPDATE agents
            SET calibration = ?, prediction_count = ?, last_updated = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (avg_brier, count, agent_name))

        self.conn.commit()

    def get_predictions(
        self,
        agent_name: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get predictions with optional filters."""
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
        return [self._row_to_dict(row) for row in rows]

    def get_agent_stats(self, agent_name: str) -> Optional[Dict]:
        """Get statistics for an agent."""
        row = self.conn.execute(
            "SELECT * FROM agents WHERE name = ?", (agent_name,)
        ).fetchone()

        if not row:
            return None

        return dict(row)

    def get_leaderboard(self) -> List[Dict]:
        """Get all agents sorted by calibration."""
        rows = self.conn.execute("""
            SELECT * FROM agents
            WHERE prediction_count > 0
            ORDER BY calibration ASC
        """).fetchall()

        return [dict(row) for row in rows]

    def _row_to_dict(self, row) -> Dict:
        """Convert SQLite row to dict with parsed JSON."""
        d = dict(row)
        if 'context' in d and d['context']:
            d['context'] = json.loads(d['context'])
        return d

    def close(self):
        """Close database connection."""
        self.conn.close()
