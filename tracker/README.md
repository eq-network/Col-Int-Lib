# Prediction Tracker

A robust, well-tested prediction tracking system for monitoring agent calibration.

## Quick Start

### Basic Usage

```python
from tracker.database import TrackerDB

# Use context manager (recommended)
with TrackerDB("tracker.db") as db:
    # Register a prediction
    pred_id = db.register_prediction(
        agent_name="claude-sonnet",
        probability=0.85,
        horizon_minutes=15,
        condition="task_complete",
        context={"task": "implement feature X"}
    )

    # Later: resolve the prediction
    db.resolve_prediction(pred_id, outcome=True)

    # View calibration
    stats = db.get_agent_stats("claude-sonnet")
    print(f"Calibration: {stats['calibration']:.4f}")
```

### Error Handling

```python
from tracker.database import (
    TrackerDB,
    InvalidPredictionError,
    PredictionNotFoundError,
    DatabaseError
)

with TrackerDB("tracker.db") as db:
    try:
        pred_id = db.register_prediction("agent", 0.5, 10)
    except InvalidPredictionError as e:
        print(f"Invalid input: {e}")
    except DatabaseError as e:
        print(f"Database error: {e}")
```

### Using Pure Metrics

```python
from tracker.metrics import compute_brier_score, compute_calibration

# Compute Brier score
brier = compute_brier_score(probability=0.8, outcome=True)
print(f"Brier score: {brier:.4f}")  # 0.0400

# Compute calibration from multiple Brier scores
brier_scores = [0.04, 0.16, 0.09]
calibration = compute_calibration(brier_scores)
print(f"Calibration: {calibration:.4f}")  # 0.0967
```

## API Reference

### TrackerDB

#### Context Manager (Recommended)

```python
with TrackerDB(db_path="tracker.db") as db:
    # Use db here
    pass
# Connection automatically closed
```

#### Methods

**`register_prediction(agent_name, probability, horizon_minutes, condition, context)`**

Register a new prediction.

- **agent_name** (str): Name of agent making prediction
- **probability** (float): Predicted probability in [0, 1]
- **horizon_minutes** (int): Time horizon in minutes (positive)
- **condition** (str): Condition being predicted (default: "task_complete")
- **context** (dict, optional): JSON-serializable context

Returns: Prediction ID (int)

Raises:
- `InvalidPredictionError`: If validation fails
- `DatabaseError`: If database operation fails

**`resolve_prediction(prediction_id, outcome)`**

Resolve a prediction with an outcome.

- **prediction_id** (int): ID of prediction to resolve
- **outcome** (bool): Actual outcome (True/False)

Raises:
- `PredictionNotFoundError`: If prediction doesn't exist
- `DatabaseError`: If database operation fails

**`get_agent_stats(agent_name)`**

Get statistics for an agent.

- **agent_name** (str): Agent name to query

Returns: Dict with `name`, `calibration`, `prediction_count`, `last_updated`

**`get_leaderboard()`**

Get all agents sorted by calibration (lower is better).

Returns: List of agent dicts

**`get_predictions(agent_name=None, resolved=None, limit=100)`**

Get predictions with optional filters.

- **agent_name** (str, optional): Filter by agent
- **resolved** (bool, optional): Filter by resolution status (None = all)
- **limit** (int): Maximum results (default: 100)

Returns: List of prediction dicts

**`get_pending_resolutions()`**

Get predictions past their horizon but not resolved.

Returns: List of prediction dicts

### Exceptions

```python
TrackerDBError (base)
├── InvalidPredictionError - Invalid input data
├── PredictionNotFoundError - Missing prediction ID
└── DatabaseError - SQLite operation failure
```

### Pure Functions (tracker.metrics)

**`compute_brier_score(probability, outcome)`**

Compute Brier score = (p - outcome)²

- Lower is better (0.0 = perfect)
- Raises `ValueError` if probability not in [0, 1]

**`compute_calibration(brier_scores)`**

Compute average of Brier scores.

- Raises `ValueError` if list is empty

**`compute_incremental_calibration(current_calibration, current_count, new_brier_score)`**

Update calibration with a new Brier score using running average.

## Bridge Integration

Connect functional predictions (core/predictions.py) to database:

```python
from tracker.bridge import PredictionBridge

with PredictionBridge("tracker.db") as bridge:
    # Sync prediction from World to database
    db_pred_id = bridge.sync_prediction(world, agent_id)

    # Sync resolution from World to database
    bridge.sync_resolution(world, prediction_id)

    # Batch sync entire world
    stats = bridge.sync_world(world)
    print(f"Synced {stats['predictions_synced']} predictions")
```

## Concurrency Model

### Single-Threaded (Current)

TrackerDB assumes single-threaded access within a process:
- SQLite serializes writes automatically
- Reads during writes may see incomplete data

### Multi-Threaded

To use from multiple threads:
1. Create separate TrackerDB instance per thread, OR
2. Enable `check_same_thread=False` and add locking, OR
3. Use connection pooling (not implemented)

### Multi-Process

SQLite file locking prevents corruption across processes, but:
- Long transactions can block other processes
- For production: enable WAL mode

```python
with TrackerDB("tracker.db") as db:
    db.conn.execute("PRAGMA journal_mode=WAL")
```

### MCP Server

Async functions call synchronous database methods:
- Safe because MCP event loop is single-threaded
- For concurrent requests: would need `aiosqlite`

## Performance

### Bridge sync_world()

- **Time complexity:** O(n) where n = number of events
- **Previously:** O(n²) due to repeated searches
- **Improvement:** 10-100x faster for large event logs

### Database Operations

- Commits after every operation (autocommit style)
- Simple but prevents batching
- Future: explicit transaction control

## Backward Compatibility

Old API still works:

```python
# Old style (still works)
db = TrackerDB("tracker.db")
pred_id = db.register_prediction("agent", 0.5, 10)
db.close()

# New style (recommended)
with TrackerDB("tracker.db") as db:
    pred_id = db.register_prediction("agent", 0.5, 10)
```

## Migration Guide

### From Old API

Replace manual open/close with context manager:

```python
# Before
db = TrackerDB("tracker.db")
try:
    pred_id = db.register_prediction(...)
finally:
    db.close()

# After
with TrackerDB("tracker.db") as db:
    pred_id = db.register_prediction(...)
```

### Add Error Handling

```python
# Before
pred_id = db.register_prediction("agent", probability, horizon)

# After
try:
    pred_id = db.register_prediction("agent", probability, horizon)
except InvalidPredictionError as e:
    print(f"Invalid input: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")
```

## Examples

### Complete Example

```python
from tracker.database import TrackerDB, InvalidPredictionError

with TrackerDB("tracker.db") as db:
    # Register agents
    db.register_agent("claude-sonnet")
    db.register_agent("claude-opus")

    # Register predictions
    try:
        pred1 = db.register_prediction(
            "claude-sonnet",
            probability=0.85,
            horizon_minutes=15,
            context={"task": "write tests"}
        )

        pred2 = db.register_prediction(
            "claude-opus",
            probability=0.90,
            horizon_minutes=10,
            context={"task": "review code"}
        )
    except InvalidPredictionError as e:
        print(f"Invalid prediction: {e}")
        return

    # ... time passes ...

    # Resolve predictions
    db.resolve_prediction(pred1, outcome=True)
    db.resolve_prediction(pred2, outcome=False)

    # View leaderboard
    leaderboard = db.get_leaderboard()
    print("Leaderboard:")
    for i, agent in enumerate(leaderboard, 1):
        print(f"{i}. {agent['name']}: {agent['calibration']:.4f}")
```

### With Functional System

```python
from core.predictions import register_prediction, resolve_prediction
from tracker.bridge import PredictionBridge

with PredictionBridge("tracker.db") as bridge:
    # Register in functional system
    world = register_prediction(
        world,
        agent_id=1,
        probability=0.8,
        horizon=world.tick + 10,
        condition="task_complete"
    )

    # Sync to database
    db_pred_id = bridge.sync_prediction(world, agent_id=1)
    print(f"Synced to database: {db_pred_id}")

    # ... simulation runs ...

    # Resolve in functional system
    world = resolve_prediction(world, pred_id, outcome=True)

    # Sync resolution to database
    bridge.sync_resolution(world, pred_id)
```

## Testing

Run tests:

```bash
# Unit tests
python test_refactoring.py

# Integration tests
python test_tracker.py

# Full demo
python examples/integrated_prediction_demo.py
```

## See Also

- **TRACKER_README.md** - High-level overview
- **REFACTORING_SUMMARY.md** - Refactoring changes
- **core/predictions.py** - Functional prediction system
- **studio/screens/prediction_dashboard.py** - Visualization
