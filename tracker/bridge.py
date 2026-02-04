"""
Bridge between functional prediction system and database tracker.

This module connects:
- core/predictions.py (functional World/Event system)
- tracker/database.py (SQLite persistence)

Use this to:
1. Sync simulation predictions to database for visualization
2. Track real Claude Code predictions alongside simulations
3. Visualize both in studio dashboard
"""
from typing import Optional
from core.time import World, Event
from .database import TrackerDB


class PredictionBridge:
    """
    Bridge between functional predictions and database tracker.

    Usage:
        # Recommended: Use as context manager
        with PredictionBridge("tracker.db") as bridge:
            bridge.sync_prediction(world, agent_id)
            bridge.sync_resolution(world, pred_id)

        # Backward compatible:
        bridge = PredictionBridge("tracker.db")
        bridge.sync_prediction(world, agent_id)
        bridge.close()  # Must remember to close!
    """

    def __init__(self, db_path: str = "tracker.db"):
        """Initialize bridge with database connection."""
        self.db = TrackerDB(db_path).open()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - always closes connection."""
        self.close()
        return False  # Don't suppress exceptions

    def sync_prediction(self, world: World, agent_id: int) -> Optional[int]:
        """
        Sync the most recent prediction from World to database.

        Args:
            world: Current world state
            agent_id: Agent who made the prediction

        Returns:
            Database prediction ID, or None if no new prediction found
        """
        # Find most recent prediction event for this agent
        prediction_events = [
            e for e in world.log.completed
            if e.event_type == "prediction"
            and e.source == agent_id
        ]

        if not prediction_events:
            return None

        # Get the most recent one
        pred_event = prediction_events[-1]

        # Get agent name from world metadata
        agent_meta = world.state.global_attrs.get("agents", {}).get(str(agent_id), {})
        agent_name = agent_meta.get("name", f"agent_{agent_id}")

        # Extract prediction details
        probability = pred_event.payload["probability"]
        horizon = pred_event.payload["horizon"]
        condition = pred_event.payload["condition"]
        context = {
            "prediction_id": pred_event.payload.get("prediction_id"),
            "task_id": pred_event.payload.get("task_id"),
            "true_probability": pred_event.payload.get("true_probability"),
            "tick": pred_event.tick
        }

        # Calculate horizon in minutes (assume 1 tick = 1 minute, adjust as needed)
        horizon_minutes = max(1, horizon - pred_event.tick)

        # Register in database
        db_pred_id = self.db.register_prediction(
            agent_name=agent_name,
            probability=probability,
            horizon_minutes=horizon_minutes,
            condition=condition,
            context=context
        )

        return db_pred_id

    def sync_resolution(self, world: World, prediction_id: str) -> bool:
        """
        Sync a prediction resolution from World to database.

        Args:
            world: Current world state
            prediction_id: Prediction ID from World system

        Returns:
            True if resolution was synced, False otherwise
        """
        # Find resolution event
        resolution_events = [
            e for e in world.log.completed
            if e.event_type == "resolution"
            and e.payload.get("prediction_id") == prediction_id
        ]

        if not resolution_events:
            return False

        resolution = resolution_events[-1]
        outcome = resolution.payload["outcome"]

        # Find corresponding database prediction
        # We stored the world prediction_id in context
        predictions = self.db.get_predictions(resolved=False)

        for pred in predictions:
            import json
            context = json.loads(pred["context"])
            if context.get("prediction_id") == prediction_id:
                # Found it - resolve in database
                self.db.resolve_prediction(pred["id"], outcome)
                return True

        return False

    def sync_world(self, world: World) -> dict:
        """
        Sync entire world state to database efficiently.

        This is useful for batch syncing after a simulation run.

        Performance: O(n) where n = number of events
        (Previously O(n²) due to repeated searches through event log)

        Args:
            world: Current world state

        Returns:
            Dict with sync statistics
        """
        synced_predictions = 0
        synced_resolutions = 0

        # Build index of prediction events by agent_id for O(1) lookup
        # This eliminates the O(n²) behavior from sync_prediction searching the log
        prediction_by_agent = {}
        resolution_by_pred_id = {}

        for event in world.log.completed:
            if event.event_type == "prediction":
                agent_id = event.source
                pred_id = event.payload.get("prediction_id")
                # Keep most recent prediction per agent (overwrite previous)
                prediction_by_agent[agent_id] = (pred_id, event)

            elif event.event_type == "resolution":
                pred_id = event.payload.get("prediction_id")
                # Keep most recent resolution per prediction
                resolution_by_pred_id[pred_id] = event

        # Track which predictions we've already synced
        synced_pred_ids = set()

        # Sync predictions (now O(n) instead of O(n²))
        for agent_id, (pred_id, event) in prediction_by_agent.items():
            if pred_id not in synced_pred_ids:
                db_id = self.sync_prediction(world, agent_id)
                if db_id:
                    synced_predictions += 1
                    synced_pred_ids.add(pred_id)

        # Sync resolutions
        for pred_id, event in resolution_by_pred_id.items():
            if self.sync_resolution(world, pred_id):
                synced_resolutions += 1

        return {
            "predictions_synced": synced_predictions,
            "resolutions_synced": synced_resolutions,
            "total_events": len(world.log.completed)
        }

    def close(self):
        """Close database connection."""
        self.db.close()


def sync_agent_to_db(world: World, agent_id: int, db: TrackerDB):
    """
    Helper function: Sync single agent's latest prediction to database.

    Args:
        world: Current world state
        agent_id: Agent to sync
        db: Database connection

    Returns:
        Database prediction ID or None
    """
    bridge = PredictionBridge()
    bridge.db = db  # Reuse connection
    return bridge.sync_prediction(world, agent_id)


def watch_simulation(world_generator, db_path: str = "tracker.db"):
    """
    Watch a simulation and sync predictions to database in real-time.

    Args:
        world_generator: Iterator that yields World states
        db_path: Database path

    Usage:
        for world in watch_simulation(run_simulation(), "tracker.db"):
            # Your simulation logic here
            print(f"Tick {world.tick}")
    """
    with PredictionBridge(db_path) as bridge:
        for world in world_generator:
            # Sync any new predictions/resolutions
            bridge.sync_world(world)
            yield world
