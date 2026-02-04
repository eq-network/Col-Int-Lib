"""
Prediction Tracker Dashboard

Real-time visualization reading from SQLite database.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Dict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.studio.screens.base import Screen
from apps.prediction_tracker.legacy.database import TrackerDB


class PredictionDashboardScreen(Screen):
    """
    Real-time prediction tracking dashboard.

    Polls database every second for updates.
    """

    def __init__(self, manager, app_state):
        super().__init__(manager, app_state)
        self.db: Optional[TrackerDB] = None
        self.refresh_interval = 1000  # ms

    def on_enter(self, prev_screen: Optional[Screen] = None) -> None:
        self._create_base_frame()
        nav = self._create_nav_bar(title="Prediction Tracker", show_back=True)

        # Connect to database (open explicitly, will close in on_exit)
        self.db = TrackerDB("tracker.db").open()

        # Header
        header = ttk.Frame(self.frame)
        header.pack(fill=tk.X, padx=20, pady=(10, 0))

        self._status_var = tk.StringVar(value="Connected to tracker.db")
        status_lbl = ttk.Label(header, textvariable=self._status_var, font=("Arial", 12))
        status_lbl.pack(side=tk.LEFT)

        # Main content
        content = ttk.Frame(self.frame)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Left panel: Leaderboard
        left_frame = ttk.LabelFrame(content, text="Agent Leaderboard", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.leaderboard_tree = ttk.Treeview(
            left_frame,
            columns=("agent", "calibration", "predictions"),
            show="headings",
            height=10
        )
        self.leaderboard_tree.heading("agent", text="Agent")
        self.leaderboard_tree.heading("calibration", text="Calibration")
        self.leaderboard_tree.heading("predictions", text="Predictions")
        self.leaderboard_tree.column("agent", width=150)
        self.leaderboard_tree.column("calibration", width=100)
        self.leaderboard_tree.column("predictions", width=100)
        self.leaderboard_tree.pack(fill=tk.BOTH, expand=True)

        # Calibration gauges
        gauges_frame = ttk.LabelFrame(left_frame, text="Calibration Gauges", padding=10)
        gauges_frame.pack(fill=tk.BOTH, pady=(10, 0))

        self.gauges_canvas = tk.Canvas(gauges_frame, bg="white", height=150)
        self.gauges_canvas.pack(fill=tk.BOTH, expand=True)

        # Right panel: Recent predictions
        right_frame = ttk.LabelFrame(content, text="Recent Predictions", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.predictions_tree = ttk.Treeview(
            right_frame,
            columns=("agent", "probability", "horizon", "status"),
            show="headings",
            height=20
        )
        self.predictions_tree.heading("agent", text="Agent")
        self.predictions_tree.heading("probability", text="Probability")
        self.predictions_tree.heading("horizon", text="Horizon (min)")
        self.predictions_tree.heading("status", text="Status")
        self.predictions_tree.column("agent", width=100)
        self.predictions_tree.column("probability", width=100)
        self.predictions_tree.column("horizon", width=100)
        self.predictions_tree.column("status", width=150)
        self.predictions_tree.pack(fill=tk.BOTH, expand=True)

        # Start auto-refresh
        self._schedule_refresh()

    def _update_display(self):
        """Update all visualizations from database."""
        if not self.db:
            return

        self._update_leaderboard()
        self._update_gauges()
        self._update_predictions()

    def _update_leaderboard(self):
        """Update leaderboard from database."""
        # Clear existing
        for item in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(item)

        # Get leaderboard
        leaderboard = self.db.get_leaderboard()

        # Populate
        for agent in leaderboard:
            calibration = agent["calibration"] or 0.0
            self.leaderboard_tree.insert("", "end", values=(
                agent["name"],
                f"{calibration:.4f}",
                agent["prediction_count"]
            ))

    def _update_gauges(self):
        """Draw calibration gauges."""
        self.gauges_canvas.delete("all")

        leaderboard = self.db.get_leaderboard()
        if not leaderboard:
            return

        width = self.gauges_canvas.winfo_width() or 400
        height = self.gauges_canvas.winfo_height() or 150

        # Draw gauge for each agent (max 4)
        num_gauges = min(len(leaderboard), 4)
        gauge_width = width // num_gauges

        for i, agent in enumerate(leaderboard[:4]):
            x = i * gauge_width + gauge_width // 2
            y = height // 2
            radius = min(gauge_width, height) // 3

            calibration = agent["calibration"] or 0.0
            self._draw_gauge(x, y, radius, calibration, agent["name"])

    def _draw_gauge(self, x: int, y: int, radius: int, calibration: float, agent_name: str):
        """Draw a circular gauge."""
        # Background arc
        self.gauges_canvas.create_arc(
            x - radius, y - radius, x + radius, y + radius,
            start=0, extent=180, outline="#ddd", width=8, style="arc"
        )

        # Color-coded arc
        if calibration < 0.1:
            color = "#4CAF50"  # Green
        elif calibration < 0.2:
            color = "#FFC107"  # Yellow
        else:
            color = "#F44336"  # Red

        # Arc extent (0.0 = full, 1.0 = none)
        extent = 180 * (1 - min(calibration, 1.0))

        self.gauges_canvas.create_arc(
            x - radius, y - radius, x + radius, y + radius,
            start=0, extent=extent, outline=color, width=8, style="arc"
        )

        # Label
        self.gauges_canvas.create_text(
            x, y + radius + 15,
            text=agent_name,
            font=("Arial", 9, "bold")
        )

        # Value
        self.gauges_canvas.create_text(
            x, y,
            text=f"{calibration:.3f}",
            font=("Arial", 11)
        )

    def _update_predictions(self):
        """Update predictions list from database."""
        # Clear existing
        for item in self.predictions_tree.get_children():
            self.predictions_tree.delete(item)

        # Get recent predictions
        predictions = self.db.get_predictions(limit=50)

        # Populate
        for pred in predictions:
            if pred["resolved_at"]:
                outcome = "✓" if pred["outcome"] else "✗"
                brier = pred["brier_score"]
                status = f"{outcome} Brier: {brier:.4f}"
            else:
                status = "Pending..."

            self.predictions_tree.insert("", "end", values=(
                pred["agent_name"],
                f"{pred['probability']:.2f}",
                pred["horizon_minutes"],
                status
            ))

    def _schedule_refresh(self):
        """Schedule periodic refresh."""
        self._update_display()
        if self.frame and self.frame.winfo_exists():
            self.frame.after(self.refresh_interval, self._schedule_refresh)

    def on_exit(self, next_screen: Optional[Screen] = None) -> None:
        """Clean up database connection."""
        if self.db:
            self.db.close()
