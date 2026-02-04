# Mycorrhiza: Prediction Tracking for Claude Code

A pure functional system for tracking real predictions from Claude Code instances, computing calibration metrics, and enabling learning through feedback.

**Core Principle**: Track reality, don't simulate it.

## What Is This?

Mycorrhiza is a **prediction tracker** for Claude Code. When Claude makes predictions about tasks ("I'll complete this in 15 minutes, 80% confident"), Mycorrhiza:

1. Records the prediction
2. Tracks the actual outcome
3. Computes accuracy (Brier score)
4. Maintains calibration metrics
5. Displays performance over time

**Not a simulator.** A tracker for real events.

## Quick Start

```python
from core.time import run_n_ticks
from core.predictions import register_prediction, mark_task_complete
from core.stats import get_calibration, get_leaderboard
from engine.environments.code_tracker import create_code_tracker

# Initialize tracker
world = create_code_tracker(agent_names=["claude"])

# Claude makes a prediction
world = register_prediction(
    world,
    agent_id=1,
    probability=0.8,
    horizon=10,
    condition="task_complete"
)

# Task actually completes (real event)
world = mark_task_complete(world, agent_id=1)

# Time passes
world = run_n_ticks(world, 10)

# Check calibration
calibration = get_calibration(world, agent_id=1)
print(f"Calibration: {calibration:.4f}")  # 0.04 (good!)
```

## Architecture

```
core/
├── time.py         - Discrete time, events, World = (tick, state, log)
├── graph.py        - GraphState (immutable graph structure)
├── predictions.py  - Pure prediction tracking (register, resolve, Brier)
└── stats.py        - Pure analysis functions (calibration, leaderboard)

engine/environments/
└── code_tracker.py - MCP adapter for Claude Code

experiments/
└── synthetic_agents.py - Simulation (for testing only)

tests/
└── test_tracker_known_outcomes.py - Tests with explicit outcomes
```

## Philosophy

### Pure Core, Effects at Edges

All core functions are **pure**: `World → World`

- No I/O in core
- No randomness in core
- No simulation in core
- Just: prediction + outcome → Brier score → calibration

Effects (persistence, MCP integration, UI) live at the edges.

### Track Reality, Don't Simulate It

The core tracker does NOT:
- Simulate agent personalities ❌
- Generate synthetic outcomes ❌
- Adjust probabilities ❌
- Assume behaviors ❌

The core tracker DOES:
- Record real predictions ✅
- Log real outcomes ✅
- Compute exact Brier scores ✅
- Maintain running averages ✅

### Simulation is for Testing, Not Production

The `experiments/` directory contains simulation code for **testing the tracker**, not as part of the system itself.

One-way dependency:
```
experiments/ → core/   (experiments USE core)
core/ ↛ experiments/   (core doesn't know about experiments)
```

## Key Concepts

### 1. Discrete Time (Ticks)

Time advances in discrete ticks. Events happen at specific ticks.

```python
world = World(tick=0, state=..., log=...)
world = tick_world(world)  # Advances to tick 1
```

### 2. Events

Events are immutable records of things that happened:

```python
Event(
    tick=0,
    source=agent_id,
    target=agent_id,
    event_type="prediction",
    payload={"probability": 0.8, "horizon": 10},
    duration=0
)
```

### 3. Predictions & Resolutions

Predictions resolve at their horizon:

```python
# At tick 0: Register prediction
world = register_prediction(world, agent_id=1, prob=0.8, horizon=10)

# At tick 5: Task completes
world = mark_task_complete(world, agent_id=1)

# At tick 10: Prediction auto-resolves
world = run_n_ticks(world, 10)
# → Brier = (0.8 - 1.0)² = 0.04
# → Calibration updates
```

### 4. Brier Score

Measures prediction accuracy:

```
Brier = (probability - outcome)²

Perfect prediction: 0.0
Worst prediction: 1.0
```

### 5. Calibration

Running average of Brier scores. Lower is better.

```python
calibration = get_calibration(world, agent_id)
# 0.0-0.1: Excellent
# 0.1-0.2: Good
# 0.2-0.3: Fair
# 0.3+: Needs improvement
```

## Testing Strategy

Tests use **known outcomes**, not simulation:

```python
def test_exact_brier():
    world = create_code_tracker()

    # Known prediction: p=0.8
    world = register_prediction(world, agent_id=1, prob=0.8, horizon=10)

    # Known outcome: True
    world = mark_task_complete(world, agent_id=1)

    # Advance to resolution
    world = run_n_ticks(world, 10)

    # Verify EXACT Brier score
    cal = get_calibration(world, agent_id=1)
    assert cal == 0.04  # (0.8 - 1.0)² = 0.04
```

No randomness. No simulation. Just pure math on explicit outcomes.

## Integration with Claude Code (MCP)

Via MCP server (future):

```python
# MCP: Register prediction
mcp.call_tool("tracker.register_prediction", {
    "agent_id": "claude-1",
    "probability": 0.8,
    "horizon_ticks": 10
})

# MCP: Log completion
mcp.call_tool("tracker.log_completion", {
    "task_id": "fibonacci_function",
    "success": True
})

# MCP: Query stats
stats = mcp.call_resource("tracker://agents/claude-1")
# → {"calibration": 0.04, "prediction_count": 1}
```

## Example: Real Usage

```python
# Session start
world = create_code_tracker(agent_names=["claude-session-1"])

# User asks Claude to implement feature
# Claude responds: "I'll have this done in ~15 minutes, 80% confident"

# Extract and register prediction
world = register_prediction(
    world,
    agent_id=1,
    probability=0.8,
    horizon=15,  # 15 ticks (could be minutes)
    condition="task_complete",
    context={"task": "implement_feature_x"}
)

# Time passes... user interacts, code gets written
world = run_n_ticks(world, 10)

# Feature actually completes
world = mark_task_complete(world, agent_id=1, task_id="feature_x")

# Advance to resolution
world = run_n_ticks(world, 5)

# Check calibration
calibration = get_calibration(world, agent_id=1)
print(f"Claude's calibration: {calibration:.4f}")
# → Dashboard shows: "Claude calibration: 0.04 (excellent!)"
```

## Installation

```bash
git clone https://github.com/yourusername/mycorrhiza.git
cd mycorrhiza
pip install -r requirements.txt
```

Requirements: Python 3.10+, JAX, NumPy

## Running Tests

```bash
# Tests with known outcomes (preferred)
python tests/test_tracker_known_outcomes.py

# Original e2e tests (use new tracker functions)
python tests/test_e2e_prediction_cycle.py
```

All tests should pass with exact Brier score verification.

## Trade-offs & Decisions

**Decision: No Simulation in Core**
- ✅ Simpler, more focused, actually useful in production
- ✅ Can't confuse simulation with reality
- ✅ Forces tracking of real data
- ⚠️ Simulation moved to `experiments/` for testing

**Decision: String-based Messages (future)**
- ✅ Matches actual Claude Code interaction
- ✅ Can extract predictions from natural language
- ⚠️ Parsing is heuristic, might miss predictions
- ✅ Start simple, improve extraction over time

**Decision: Logical Time (Ticks)**
- ✅ Ticks when something happens (message, task completion)
- ✅ More flexible than wall-clock time
- ✅ Easier to test

## Extending the System

Open for extension, closed for modification:

1. **More metrics**: Add to `stats.py` without touching core
2. **Different environments**: Add new adapters in `engine/environments/`
3. **Persistence**: Swap save/load without changing core
4. **UI/Dashboard**: Query `stats.py`, doesn't need core changes
5. **MCP integration**: Another effect layer, core unchanged

## Contributing

This is research code exploring prediction tracking for AI agents. Contributions welcome:

- Improved prediction extraction from natural language
- MCP server implementation
- Dashboard/visualization
- Additional metrics and analysis

## License

MIT

---

**Remember**: This tracks reality, not simulations. All core functions are pure. Effects at edges. World → World all the way down.
