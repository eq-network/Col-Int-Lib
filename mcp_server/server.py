"""
Mycorrhiza MCP Server - Thin HTTP Client

Exposes prediction tracker to Claude Code via MCP protocol.
Calls the HTTP API instead of directly managing database.
"""
import asyncio
import sys
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.types import Tool, Resource, TextContent
import httpx
import json


class TrackerMCPServer:
    """Thin MCP server that calls prediction service HTTP API."""

    def __init__(self, api_url: str = None):
        self.server = Server("mycorrhiza-tracker")
        self.api_url = api_url or os.getenv("PREDICTION_API_URL", "http://localhost:8000")
        self.client = httpx.AsyncClient(timeout=10.0)

        self._register_tools()
        self._register_resources()

    def _register_tools(self):
        """Register MCP tools."""

        @self.server.tool()
        async def register_prediction(
            agent_name: str,
            probability: float,
            horizon_minutes: int,
            condition: str = "task_complete",
            context: dict = None
        ) -> dict:
            """Register a prediction from an agent."""
            try:
                response = await self.client.post(
                    f"{self.api_url}/predictions",
                    json={
                        "agent_name": agent_name,
                        "probability": probability,
                        "horizon_minutes": horizon_minutes,
                        "condition": condition,
                        "context": context
                    }
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError as e:
                return {"status": "error", "error": str(e)}

        @self.server.tool()
        async def resolve_prediction(
            prediction_id: int,
            outcome: bool
        ) -> dict:
            """Resolve a prediction with an outcome."""
            try:
                response = await self.client.post(
                    f"{self.api_url}/predictions/{prediction_id}/resolve",
                    json={"outcome": outcome}
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError as e:
                return {"status": "error", "error": str(e)}

        @self.server.tool()
        async def get_pending_predictions(agent_name: str = None) -> dict:
            """Get pending predictions."""
            try:
                params = {"resolved": False}
                if agent_name:
                    params["agent_name"] = agent_name

                response = await self.client.get(
                    f"{self.api_url}/predictions",
                    params=params
                )
                response.raise_for_status()
                predictions = response.json()

                return {
                    "status": "success",
                    "count": len(predictions),
                    "predictions": predictions
                }

            except httpx.HTTPError as e:
                return {"status": "error", "error": str(e)}

    def _register_resources(self):
        """Register MCP resources."""

        @self.server.resource("tracker://status")
        async def get_status() -> TextContent:
            """Get tracker status."""
            try:
                # Get leaderboard
                response = await self.client.get(f"{self.api_url}/agents")
                response.raise_for_status()
                agents = response.json()

                # Get predictions
                response = await self.client.get(f"{self.api_url}/predictions", params={"limit": 10})
                response.raise_for_status()
                predictions = response.json()

                # Get pending
                response = await self.client.get(
                    f"{self.api_url}/predictions",
                    params={"resolved": False}
                )
                response.raise_for_status()
                pending = response.json()

                status = {
                    "total_agents": len(agents),
                    "total_predictions": len(predictions),
                    "pending_resolutions": len(pending)
                }

                return TextContent(text=json.dumps(status, indent=2))

            except httpx.HTTPError as e:
                return TextContent(text=json.dumps({"error": str(e)}))

        @self.server.resource("tracker://agents/{agent_name}")
        async def get_agent(agent_name: str) -> TextContent:
            """Get agent statistics."""
            try:
                response = await self.client.get(f"{self.api_url}/agents/{agent_name}/stats")

                if response.status_code == 404:
                    return TextContent(text=f"Agent {agent_name} not found")

                response.raise_for_status()
                stats = response.json()

                return TextContent(text=json.dumps(stats, indent=2))

            except httpx.HTTPError as e:
                return TextContent(text=json.dumps({"error": str(e)}))

        @self.server.resource("tracker://leaderboard")
        async def get_leaderboard() -> TextContent:
            """Get agent leaderboard."""
            try:
                response = await self.client.get(f"{self.api_url}/agents")
                response.raise_for_status()
                leaderboard = response.json()

                return TextContent(text=json.dumps({
                    "agents": leaderboard
                }, indent=2))

            except httpx.HTTPError as e:
                return TextContent(text=json.dumps({"error": str(e)}))

        @self.server.resource("tracker://predictions")
        async def get_predictions() -> TextContent:
            """Get recent predictions."""
            try:
                response = await self.client.get(
                    f"{self.api_url}/predictions",
                    params={"limit": 50}
                )
                response.raise_for_status()
                predictions = response.json()

                return TextContent(text=json.dumps({
                    "predictions": predictions
                }, indent=2))

            except httpx.HTTPError as e:
                return TextContent(text=json.dumps({"error": str(e)}))

    async def run(self):
        """Run the MCP server."""
        try:
            print(f"MCP Server starting...")
            print(f"Connecting to Prediction API: {self.api_url}")

            async with self.server:
                await self.server.run()
        finally:
            # Close HTTP client
            await self.client.aclose()
            print("MCP Server stopped")


def main():
    server = TrackerMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
