# Prediction Tracker

A service-first prediction tracking system for measuring calibration of humans and AI agents.

## Quick Start

### 1. Start the Service

```bash
python -m prediction_service
```

Service runs at `http://localhost:8000`. API docs at `/docs`.

### 2. Make Predictions

```bash
# CLI
python predict.py make "Fix bug" --prob 0.8 --horizon 30
python predict.py resolve 1 --outcome true
python predict.py stats --agent you

# Or HTTP API
curl -X POST http://localhost:8000/predictions \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "me", "probability": 0.8, "horizon_minutes": 30}'
```

### 3. View Results

```bash
# CLI
python predict.py leaderboard

# Or studio dashboard
cd studio && python main.py
# Click "Prediction Tracker"
```

## Architecture

**Service-first design:**

```
prediction_service/         # HTTP API (core)
  ├── api.py               # FastAPI endpoints
  ├── storage.py           # SQLite wrapper
  └── models.py            # Pydantic models

Clients:
  ├── predict.py           # CLI tool
  ├── mcp_server/          # MCP server for Claude Code
  └── studio/              # Tkinter dashboard

Core:
  └── tracker/metrics.py   # Pure calibration functions
```

## API Endpoints

- `POST /predictions` - Create prediction
- `POST /predictions/{id}/resolve` - Resolve prediction
- `GET /predictions` - Query predictions
- `GET /agents/{name}/stats` - Get calibration stats
- `GET /agents` - Leaderboard

## Integration Examples

### Python
```python
import httpx

client = httpx.Client()
response = client.post("http://localhost:8000/predictions", json={
    "agent_name": "me",
    "probability": 0.8,
    "horizon_minutes": 30
})
pred_id = response.json()["id"]
```

### Jira Webhook
```python
@webhook
def on_ticket_start(ticket):
    httpx.post("http://localhost:8000/predictions", json={
        "agent_name": ticket.assignee,
        "probability": 0.75,
        "horizon_minutes": ticket.estimate * 60
    })
```

### GitHub Action
```yaml
- run: |
    curl -X POST http://server:8000/predictions \
      -d '{"agent_name": "${{ github.actor }}", "probability": 0.9, ...}'
```

## Configuration

- `PREDICTION_DB` - Database path (default: `tracker.db`)
- `PREDICTION_API_URL` - API URL for clients (default: `http://localhost:8000`)

## Files

### Core Service
- `prediction_service/` - HTTP API
- `tracker/metrics.py` - Pure calibration functions

### Clients
- `predict.py` - CLI tool
- `mcp_server/server.py` - MCP server
- `studio/screens/prediction_dashboard.py` - Dashboard

### Tests
- `test_tracker.py` - Integration tests
- `examples/integrated_prediction_demo.py` - Full demo

### Documentation
- `DONE_SERVICE_REFACTOR.md` - Complete refactoring summary
- `prediction_service/README.md` - Service-specific docs
- `CLAUDE.md` - Repository guidance

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python test_tracker.py

# Start service
python -m prediction_service --reload

# Run demo
python examples/integrated_prediction_demo.py
```

## What's Different from Original Design

**Before:** Monolithic `TrackerDB` class (300+ lines), separate CLI scripts

**Now:** HTTP API (150 lines) + thin clients, service-first architecture

**Benefits:**
- Easy integration (just HTTP calls)
- Language-agnostic clients
- Clean separation of concerns
- Composable architecture

See `DONE_SERVICE_REFACTOR.md` for complete migration details.
