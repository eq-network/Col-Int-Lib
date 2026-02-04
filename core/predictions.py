"""
Pure prediction tracking logic.

This module provides the core functions for:
- Registering predictions from real agents
- Resolving predictions with real outcomes
- Computing Brier scores
- Updating calibration

NO simulation. NO personalities. Just track reality.

All functions are pure: World → World
"""

from typing import Optional, List
from .time import World, Event, EventLog, Tick, NodeID


# =============================================================================
# CORE PREDICTION FUNCTIONS
# =============================================================================

def register_prediction(
    world: World,
    agent_id: NodeID,
    probability: float,
    horizon: Tick,
    condition: str,
    context: Optional[dict] = None
) -> World:
    """
    Register a REAL prediction from a REAL agent.

    No adjustment. No simulation. Just record it.

    Args:
        world: Current world state
        agent_id: Which agent made the prediction
        probability: Agent's predicted probability (0.0 to 1.0)
        horizon: Tick at which prediction should resolve
        condition: What is being predicted (e.g., "task_complete")
        context: Optional real context (task description, code context, etc.)

    Returns:
        World with prediction recorded
    """
    if context is None:
        context = {}

    prediction_id = f"pred_{world.tick}_{agent_id}"

    event = Event(
        tick=world.tick,
        source=agent_id,
        target=agent_id,
        event_type="prediction",
        payload={
            "prediction_id": prediction_id,
            "condition": condition,
            "probability": probability,
            "horizon": horizon,
            "context": context
        },
        duration=0  # Predictions register instantly
    )

    new_log = world.log.append(event)
    return World(tick=world.tick, state=world.state, log=new_log)


def resolve_prediction(
    world: World,
    prediction_id: str,
    outcome: bool
) -> World:
    """
    Resolve a prediction with REAL outcome.

    No simulation. Outcome actually happened (or didn't).

    Args:
        world: Current world state
        prediction_id: ID of prediction to resolve
        outcome: What actually happened (True/False)

    Returns:
        World with resolution recorded and calibration updated
    """
    # Find the prediction
    pred = find_prediction(world.log, prediction_id)
    if pred is None:
        # Prediction not found - just return world unchanged
        return world

    # Check if already resolved
    if is_resolved(world.log, prediction_id):
        return world

    # Compute Brier score
    probability = pred.payload["probability"]
    brier = compute_brier(probability, outcome)

    # Create resolution event
    resolution = Event(
        tick=world.tick,
        source=pred.source,
        target=pred.source,
        event_type="resolution",
        payload={
            "prediction_id": prediction_id,
            "outcome": outcome,
            "brier_score": brier
        },
        duration=0
    )

    new_log = world.log.append(resolution)

    # Update agent calibration
    new_state = update_agent_calibration(world.state, pred.source, brier)

    return World(tick=world.tick, state=new_state, log=new_log)


def compute_brier(probability: float, outcome: bool) -> float:
    """
    Pure: Compute Brier score.

    Brier score = (p - outcome)²

    Lower is better:
    - Perfect prediction: 0.0
    - Worst prediction: 1.0

    Args:
        probability: Predicted probability
        outcome: Actual outcome (True/False)

    Returns:
        Brier score in [0.0, 1.0]
    """
    return (probability - float(outcome)) ** 2


def update_agent_calibration(state, agent_id: NodeID, brier_score: float):
    """
    Update agent's calibration with new Brier score.

    Calibration is the running average of all Brier scores.

    Args:
        state: GraphState
        agent_id: Which agent
        brier_score: New Brier score to incorporate

    Returns:
        Updated GraphState
    """
    current_calibration = float(state.node_attrs["calibration"][agent_id])
    current_count = int(state.node_attrs["prediction_count"][agent_id])

    if current_calibration < 0:  # -1.0 = no calibration yet
        # First prediction
        new_calibration = brier_score
    else:
        # Running average
        total = current_calibration * current_count
        new_calibration = (total + brier_score) / (current_count + 1)

    # Update state (using JAX immutable arrays)
    new_calibration_array = state.node_attrs["calibration"].at[agent_id].set(new_calibration)
    new_count = state.node_attrs["prediction_count"].at[agent_id].add(1)

    return state.replace(
        node_attrs={
            **state.node_attrs,
            "calibration": new_calibration_array,
            "prediction_count": new_count
        }
    )


def check_and_resolve_predictions(world: World) -> World:
    """
    Check if any predictions should resolve at current tick.

    For each prediction where horizon == current_tick:
    1. Check if the condition is met
    2. Resolve the prediction

    This is called automatically during tick_pipeline.

    Args:
        world: Current world state

    Returns:
        World with any due predictions resolved
    """
    current_tick = world.tick

    # Find predictions that resolve at this tick
    predictions = [
        e for e in world.log.completed
        if e.event_type == "prediction"
        and e.payload["horizon"] == current_tick
    ]

    if not predictions:
        return world  # No predictions to resolve

    new_world = world

    for pred in predictions:
        pred_id = pred.payload["prediction_id"]

        # Skip if already resolved
        if is_resolved(new_world.log, pred_id):
            continue

        # Check condition
        condition = pred.payload["condition"]
        agent_id = pred.source

        # Determine outcome based on condition
        if condition == "task_complete":
            # Look for task completion events
            outcome = any(
                e.event_type == "task_complete"
                and e.source == agent_id
                and e.tick <= current_tick
                for e in new_world.log.completed
            )
        else:
            # Unknown condition type - default to False
            outcome = False

        # Resolve the prediction
        new_world = resolve_prediction(new_world, pred_id, outcome)

    return new_world


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def find_prediction(log: EventLog, prediction_id: str) -> Optional[Event]:
    """Find a prediction event by ID."""
    for event in log.completed:
        if (event.event_type == "prediction"
            and event.payload.get("prediction_id") == prediction_id):
            return event
    return None


def is_resolved(log: EventLog, prediction_id: str) -> bool:
    """Check if a prediction has been resolved."""
    return any(
        e.event_type == "resolution"
        and e.payload.get("prediction_id") == prediction_id
        for e in log.completed
    )


def get_prediction_history(world: World, agent_id: NodeID) -> List[Event]:
    """
    Get all predictions and resolutions for an agent.

    Returns:
        List of events (predictions + resolutions) for this agent
    """
    return [
        e for e in world.log.completed
        if e.source == agent_id
        and e.event_type in ["prediction", "resolution"]
    ]


def mark_task_complete(world: World, agent_id: NodeID, task_id: str = "default") -> World:
    """
    Mark a task as complete.

    This records a REAL completion event.

    Args:
        world: Current world state
        agent_id: Which agent completed the task
        task_id: Task identifier

    Returns:
        World with completion recorded
    """
    event = Event(
        tick=world.tick,
        source=agent_id,
        target=agent_id,
        event_type="task_complete",
        payload={"task_id": task_id},
        duration=0
    )

    # Update task count in state if it exists
    if "task_count" in world.state.node_attrs:
        new_task_count = world.state.node_attrs["task_count"].at[agent_id].add(1)
        new_state = world.state.replace(
            node_attrs={**world.state.node_attrs, "task_count": new_task_count}
        )
    else:
        new_state = world.state

    new_log = world.log.append(event)
    return World(tick=world.tick, state=new_state, log=new_log)
