"""
Code Tracker Environment

Minimal MCP adapter for tracking real Claude Code predictions.

NO simulation. NO personalities. Just adapters for real usage.

This bridges Claude Code's string-based interaction with the core tracker.
"""

import jax.numpy as jnp
from typing import List, Optional, Dict
from core.time import World, Event, EventLog
from core.graph import GraphState
from core.predictions import register_prediction, mark_task_complete
from core.stats import get_agent_stats, get_leaderboard


# =============================================================================
# ENVIRONMENT INITIALIZATION
# =============================================================================

def create_code_tracker(agent_names: Optional[List[str]] = None) -> World:
    """
    Initialize tracker for Claude Code.

    Nodes:
    - 0: User (human)
    - 1+: Claude instances

    Args:
        agent_names: Optional list of agent identifiers

    Returns:
        World ready for tracking
    """
    if agent_names is None:
        agent_names = ["claude"]

    n_agents = len(agent_names) + 1  # +1 for user

    # Node types: user (0), then agents (1, 1, 1, ...)
    node_types = jnp.array([0] + [1] * len(agent_names), dtype=jnp.int32)

    state = GraphState(
        node_types=node_types,
        node_attrs={
            "calibration": jnp.full(n_agents, -1.0),  # -1.0 = no calibration yet
            "prediction_count": jnp.zeros(n_agents, dtype=jnp.int32),
            "task_count": jnp.zeros(n_agents, dtype=jnp.int32),
        },
        adj_matrices={},
        edge_attrs={},
        global_attrs={
            "tick": 0,
            "agents": {
                "0": {"name": "user", "type": "user"},
                **{str(i): {"name": name, "type": "agent"}
                   for i, name in enumerate(agent_names, start=1)}
            }
        }
    )

    return World(
        tick=0,
        state=state,
        log=EventLog(completed=[], pending=[])
    )


# =============================================================================
# MESSAGE TRACKING
# =============================================================================

def track_message(
    world: World,
    from_id: int,
    to_id: int,
    text: str
) -> World:
    """
    Track a message in the code environment.

    Messages are actual strings (code, responses, etc.)

    Args:
        world: Current world state
        from_id: Sender node ID
        to_id: Receiver node ID
        text: Message content

    Returns:
        World with message logged
    """
    event = Event(
        tick=world.tick,
        source=from_id,
        target=to_id,
        event_type="message",
        payload={"text": text},
        duration=1  # Messages take 1 tick to deliver
    )

    new_log = world.log.append(event)
    return World(tick=world.tick, state=world.state, log=new_log)


# =============================================================================
# PREDICTION EXTRACTION (Simple heuristics)
# =============================================================================

def extract_prediction_from_text(text: str) -> Optional[Dict]:
    """
    Extract prediction from Claude's response.

    Looks for patterns like:
    - "I predict this will take 10 minutes"
    - "I'm 80% confident this will work"
    - "This should be done in ~15 minutes, about 70% sure"

    Args:
        text: Claude's response text

    Returns:
        {probability, horizon_minutes, condition} or None
    """
    import re

    text_lower = text.lower()

    # Look for probability (e.g., "80%", "0.8 confident")
    prob_patterns = [
        r'(\d+)%\s+(?:confident|sure|certain)',
        r'(?:confident|sure|certain)\s+(\d+)%',
        r'probability.*?(\d+)%',
        r'(\d+)%.*?probability',
    ]

    probability = None
    for pattern in prob_patterns:
        match = re.search(pattern, text_lower)
        if match:
            probability = float(match.group(1)) / 100
            break

    # Look for time horizon (e.g., "15 minutes", "~10 minutes")
    time_patterns = [
        r'(?:take|done in|complete in).*?~?\s*(\d+)\s*minutes?',
        r'~?\s*(\d+)\s*minutes?.*?(?:take|done|complete)',
        r'(?:approximately|about|around)\s+(\d+)\s*minutes?',
    ]

    horizon_minutes = None
    for pattern in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            horizon_minutes = int(match.group(1))
            break

    # If we found both, return prediction
    if probability is not None and horizon_minutes is not None:
        return {
            "probability": probability,
            "horizon_minutes": horizon_minutes,
            "condition": "task_complete"
        }

    return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def register_prediction_from_text(
    world: World,
    agent_id: int,
    text: str,
    ticks_per_minute: int = 1
) -> Optional[World]:
    """
    Extract and register a prediction from Claude's text.

    Args:
        world: Current world state
        agent_id: Which agent
        text: Claude's response
        ticks_per_minute: How many ticks = 1 minute (default: 1)

    Returns:
        World with prediction registered, or None if no prediction found
    """
    pred = extract_prediction_from_text(text)
    if pred is None:
        return None

    horizon_ticks = pred["horizon_minutes"] * ticks_per_minute

    return register_prediction(
        world,
        agent_id=agent_id,
        probability=pred["probability"],
        horizon=world.tick + horizon_ticks,
        condition=pred["condition"],
        context={"original_text": text}
    )


def log_task_completion(
    world: World,
    agent_id: int,
    task_id: str = "default"
) -> World:
    """
    Log a task completion (real event).

    Args:
        world: Current world state
        agent_id: Which agent completed it
        task_id: Task identifier

    Returns:
        World with completion logged
    """
    return mark_task_complete(world, agent_id, task_id)


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def print_agent_stats(world: World, agent_id: int):
    """Pretty print an agent's statistics."""
    stats = get_agent_stats(world, agent_id)

    agent_meta = world.state.global_attrs.get("agents", {}).get(str(agent_id), {})
    name = agent_meta.get("name", f"agent_{agent_id}")

    print(f"\nAgent: {name} (ID: {agent_id})")
    if stats["calibration"] is not None:
        print(f"  Calibration: {stats['calibration']:.4f}")
    else:
        print("  Calibration: None (no predictions yet)")
    print(f"  Predictions: {stats['prediction_count']}")
    print(f"  Tasks: {stats['task_count']}")


def print_leaderboard(world: World):
    """Pretty print the agent leaderboard."""
    leaderboard = get_leaderboard(world)

    print("\n" + "="*60)
    print("AGENT LEADERBOARD (by calibration)")
    print("="*60)

    for i, stats in enumerate(leaderboard, 1):
        agent_meta = world.state.global_attrs.get("agents", {}).get(str(stats["agent_id"]), {})
        name = agent_meta.get("name", f"agent_{stats['agent_id']}")

        medal = {1: "[1st]", 2: "[2nd]", 3: "[3rd]"}.get(i, f"[{i}th]")
        print(f"\n{medal} {name}")
        print(f"    Calibration: {stats['calibration']:.4f}")
        print(f"    Predictions: {stats['prediction_count']}")

    print("\n" + "="*60)
