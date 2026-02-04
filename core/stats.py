"""
Pure analysis functions for prediction tracking.

All functions are read-only queries that compute statistics
from the World state and event log.

No side effects. No caching. Just pure queries.
"""

from typing import Optional, List, Dict
from .time import World, NodeID


# =============================================================================
# AGENT STATISTICS
# =============================================================================

def get_calibration(world: World, agent_id: NodeID) -> Optional[float]:
    """
    Get agent's current calibration score.

    Calibration is the running average of Brier scores.
    Lower is better (0.0 = perfect, 1.0 = worst).

    Args:
        world: Current world state
        agent_id: Which agent

    Returns:
        Calibration score, or None if no predictions yet
    """
    if "calibration" not in world.state.node_attrs:
        return None

    cal = float(world.state.node_attrs["calibration"][agent_id])
    return None if cal < 0 else cal


def get_prediction_count(world: World, agent_id: NodeID) -> int:
    """
    Get number of predictions agent has made.

    Args:
        world: Current world state
        agent_id: Which agent

    Returns:
        Number of predictions (resolved)
    """
    if "prediction_count" not in world.state.node_attrs:
        return 0

    return int(world.state.node_attrs["prediction_count"][agent_id])


def get_agent_stats(world: World, agent_id: NodeID) -> Dict:
    """
    Get comprehensive statistics for an agent.

    Args:
        world: Current world state
        agent_id: Which agent

    Returns:
        Dictionary with:
        - agent_id
        - calibration (or None)
        - prediction_count
        - task_count (if tracked)
    """
    calibration = get_calibration(world, agent_id)
    prediction_count = get_prediction_count(world, agent_id)

    task_count = 0
    if "task_count" in world.state.node_attrs:
        task_count = int(world.state.node_attrs["task_count"][agent_id])

    return {
        "agent_id": agent_id,
        "calibration": calibration,
        "prediction_count": prediction_count,
        "task_count": task_count
    }


# =============================================================================
# LEADERBOARD
# =============================================================================

def get_leaderboard(world: World) -> List[Dict]:
    """
    Get agent leaderboard sorted by calibration.

    Lower calibration = better predictions.

    Args:
        world: Current world state

    Returns:
        List of agent stats, sorted by calibration (best first)
    """
    n_agents = len(world.state.node_types)
    agents = []

    for agent_id in range(1, n_agents):  # Skip user (0)
        stats = get_agent_stats(world, agent_id)
        if stats["calibration"] is not None:
            agents.append(stats)

    # Sort by calibration (lower is better)
    return sorted(agents, key=lambda x: x["calibration"])


# =============================================================================
# ANALYSIS
# =============================================================================

def compute_correction_strength(world: World, agent_id: NodeID) -> Optional[float]:
    """
    Compute correction strength: does agent learn from errors?

    Measures if agent's predictions improve over time.

    Args:
        world: Current world state
        agent_id: Which agent

    Returns:
        Correction strength in [0, 1] or None if insufficient data
        - 1.0 = strong learning
        - 0.5 = moderate learning
        - 0.0 = no learning
    """
    # Get all resolutions
    resolutions = [
        e for e in world.log.completed
        if e.event_type == "resolution" and e.source == agent_id
    ]

    if len(resolutions) < 3:
        return None  # Need at least 3 to measure trend

    # Get Brier scores
    brier_scores = [r.payload["brier_score"] for r in resolutions]

    # Compare recent vs early performance
    early_avg = sum(brier_scores[:-1]) / len(brier_scores[:-1])
    recent = brier_scores[-1]

    # Measure improvement
    if recent < early_avg * 0.8:  # 20% improvement
        return 1.0
    elif recent < early_avg:  # Some improvement
        return 0.5
    else:  # No improvement
        return 0.0


def get_all_predictions(world: World) -> List[Dict]:
    """
    Get all predictions with their resolutions.

    Args:
        world: Current world state

    Returns:
        List of prediction dictionaries with:
        - prediction_id
        - agent_id
        - probability
        - horizon
        - outcome (if resolved)
        - brier_score (if resolved)
    """
    predictions = []

    for event in world.log.completed:
        if event.event_type == "prediction":
            pred_id = event.payload["prediction_id"]

            # Find resolution if exists
            resolution = None
            for res in world.log.completed:
                if (res.event_type == "resolution"
                    and res.payload.get("prediction_id") == pred_id):
                    resolution = res
                    break

            pred_dict = {
                "prediction_id": pred_id,
                "agent_id": event.source,
                "tick": event.tick,
                "probability": event.payload["probability"],
                "horizon": event.payload["horizon"],
                "condition": event.payload["condition"]
            }

            if resolution:
                pred_dict["outcome"] = resolution.payload["outcome"]
                pred_dict["brier_score"] = resolution.payload["brier_score"]
                pred_dict["resolved"] = True
            else:
                pred_dict["resolved"] = False

            predictions.append(pred_dict)

    return predictions
