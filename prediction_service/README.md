# Prediction Service

HTTP API for prediction tracking - simple, clean, composable.

## Quick Start

### 1. Start the service

```bash
python -m prediction_service
```

The service runs on `http://localhost:8000`

Docs available at: `http://localhost:8000/docs`

### 2. Use the CLI

```bash
# Make a prediction
python predict.py make "Fix bug" --prob 0.8 --horizon 30

# Resolve it
python predict.py resolve 1 --outcome true

# View stats
python predict.py stats --agent you

# See leaderboard
python predict.py leaderboard
```

### 3. Or call the API directly

```bash
# Create prediction
curl -X POST http://localhost:8000/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "alice",
    "probability": 0.85,
    "horizon_minutes": 30,
    "condition": "task_complete"
  }'

# Resolve prediction
curl -X POST http://localhost:8000/predictions/1/resolve \
  -H "Content-Type: application/json" \
  -d '{"outcome": true}'

# Get agent stats
curl http://localhost:8000/agents/alice/stats

# List predictions
curl http://localhost:8000/predictions?resolved=false
```

## Architecture

```
prediction_service/
  ├── api.py          # FastAPI endpoints (4 core endpoints)
  ├── storage.py      # Minimal SQLite wrapper
  ├── models.py       # Pydantic models
  └── __main__.py     # Service runner

clients/
  ├── predict.py      # CLI tool
  └── mcp_server/     # MCP server for Claude Code
```

**Service-first architecture:**
- Core is HTTP API
- Everything else is a thin client
- Easy to add integrations (Jira, GitHub, etc.)

## API Endpoints

### POST /predictions
Create a prediction

### POST /predictions/{id}/resolve
Resolve a prediction with an outcome

### GET /predictions
Query predictions (with filters)

### GET /agents/{name}/stats
Get agent calibration stats

### GET /agents
Get leaderboard

## Clients

### CLI Tool (`predict.py`)
```bash
predict make <task> --prob <0-1> --horizon <minutes>
predict resolve <id> --outcome true|false
predict list [--pending] [--agent <name>]
predict stats --agent <name>
predict leaderboard
```

### MCP Server
For Claude Code integration.

Set `PREDICTION_API_URL` to point to the service.

```bash
python -m mcp_server.server
```

### Python Client
```python
import httpx

client = httpx.Client()

# Make prediction
response = client.post("http://localhost:8000/predictions", json={
    "agent_name": "me",
    "probability": 0.8,
    "horizon_minutes": 30,
    "condition": "task_complete"
})
pred_id = response.json()["id"]

# Resolve it
client.post(f"http://localhost:8000/predictions/{pred_id}/resolve",
            json={"outcome": True})
```

## Configuration

### Environment Variables

- `PREDICTION_DB` - Database path (default: `tracker.db`)
- `PREDICTION_API_URL` - API URL for clients (default: `http://localhost:8000`)

### Running on Different Port

```bash
python -m prediction_service --port 8001
```

## Integration Examples

### Jira Webhook
```python
# Jira webhook handler
@app.post("/jira/webhook")
def jira_webhook(data: dict):
    if data["event"] == "issue_updated":
        if data["issue"]["status"] == "In Progress":
            # Log prediction when ticket starts
            httpx.post("http://localhost:8000/predictions", json={
                "agent_name": data["user"]["name"],
                "probability": 0.75,  # Default confidence
                "horizon_minutes": estimate_from_story_points(data["issue"]),
                "condition": "ticket_complete",
                "context": {"jira_key": data["issue"]["key"]}
            })
```

### GitHub Action
```yaml
- name: Log Prediction
  run: |
    curl -X POST http://your-server:8000/predictions \
      -H "Content-Type: application/json" \
      -d '{
        "agent_name": "${{ github.actor }}",
        "probability": 0.9,
        "horizon_minutes": 60,
        "condition": "ci_passes"
      }'
```

### CI/CD Pipeline
```python
# In your CI script
import httpx

# Before running tests
pred_id = httpx.post("http://prediction-api:8000/predictions", json={
    "agent_name": "ci-bot",
    "probability": predict_test_success(),  # ML model
    "horizon_minutes": 5,
    "condition": "tests_pass"
}).json()["id"]

# After tests
httpx.post(f"http://prediction-api:8000/predictions/{pred_id}/resolve",
           json={"outcome": all_tests_passed})
```

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY prediction_service/ ./prediction_service/

CMD ["python", "-m", "prediction_service", "--host", "0.0.0.0"]
```

### Docker Compose
```yaml
services:
  prediction-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PREDICTION_DB=/data/tracker.db
    volumes:
      - ./data:/data
```

## Comparison to Old Architecture

**Old (monolithic):**
- TrackerDB class with 300+ lines
- Database + business logic mixed
- Hard to integrate with external tools
- Requires Python imports

**New (service-first):**
- Simple HTTP API (100 lines)
- Clean separation of concerns
- Easy integrations via HTTP
- Language-agnostic clients

## Next Steps

See the forest walk insights in `SIMPLIFICATION_PLAN.md` for:
- Webhook-driven predictions (from Jira, GitHub, etc.)
- Team-level aggregations
- Automated agent predictions
- Sprint planning integration
