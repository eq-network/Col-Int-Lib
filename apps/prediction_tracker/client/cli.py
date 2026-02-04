#!/usr/bin/env python
"""
Predict - Unified CLI for Prediction Tracker

Simple HTTP client for making and resolving predictions.

Usage:
    predict make "Fix bug" --prob 0.8 --horizon 30
    predict resolve 123 --outcome true
    predict list --pending
    predict stats --agent me
"""
import httpx
import argparse
import sys
import json
from typing import Optional
from datetime import datetime


class PredictCLI:
    """CLI client for prediction tracker API."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.client = httpx.Client(timeout=10.0)

    def make_prediction(
        self,
        task: str,
        probability: float,
        horizon: int,
        agent: str = "you",
        condition: str = "task_complete"
    ) -> dict:
        """Make a prediction."""
        try:
            response = self.client.post(
                f"{self.api_url}/predictions",
                json={
                    "agent_name": agent,
                    "probability": probability,
                    "horizon_minutes": horizon,
                    "condition": condition,
                    "context": {
                        "task": task,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}

    def resolve_prediction(self, prediction_id: int, outcome: bool) -> dict:
        """Resolve a prediction."""
        try:
            response = self.client.post(
                f"{self.api_url}/predictions/{prediction_id}/resolve",
                json={"outcome": outcome}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}

    def list_predictions(
        self,
        agent: Optional[str] = None,
        pending: bool = False,
        limit: int = 20
    ) -> list:
        """List predictions."""
        try:
            params = {"limit": limit}
            if agent:
                params["agent_name"] = agent
            if pending:
                params["resolved"] = False

            response = self.client.get(
                f"{self.api_url}/predictions",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}

    def get_stats(self, agent: str) -> dict:
        """Get agent stats."""
        try:
            response = self.client.get(f"{self.api_url}/agents/{agent}/stats")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}

    def get_leaderboard(self) -> list:
        """Get leaderboard."""
        try:
            response = self.client.get(f"{self.api_url}/agents")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}


def format_prediction(pred: dict) -> str:
    """Format a prediction for display."""
    status = "PENDING"
    if pred.get("resolved_at"):
        outcome_str = "SUCCESS" if pred["outcome"] else "FAILURE"
        status = f"{outcome_str} (Brier: {pred['brier_score']:.4f})"

    return (
        f"[{pred['id']}] {pred['agent_name']}\n"
        f"    Task: {pred.get('context', {}).get('task', 'unknown')}\n"
        f"    Confidence: {pred['probability']*100:.0f}%\n"
        f"    Status: {status}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Prediction Tracker CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    predict make "Fix import bug" --prob 0.85 --horizon 30
    predict resolve 42 --outcome true
    predict list --pending
    predict stats --agent alice
    predict leaderboard
        """
    )

    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API URL (default: http://localhost:8000)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Make prediction
    make_parser = subparsers.add_parser("make", help="Make a prediction")
    make_parser.add_argument("task", help="Task description")
    make_parser.add_argument("--prob", type=float, required=True, help="Probability (0.0-1.0)")
    make_parser.add_argument("--horizon", type=int, required=True, help="Horizon in minutes")
    make_parser.add_argument("--agent", default="you", help="Agent name (default: you)")
    make_parser.add_argument("--condition", default="task_complete", help="Condition")

    # Resolve prediction
    resolve_parser = subparsers.add_parser("resolve", help="Resolve a prediction")
    resolve_parser.add_argument("id", type=int, help="Prediction ID")
    resolve_parser.add_argument("--outcome", required=True, choices=["true", "false"], help="Outcome")

    # List predictions
    list_parser = subparsers.add_parser("list", help="List predictions")
    list_parser.add_argument("--agent", help="Filter by agent")
    list_parser.add_argument("--pending", action="store_true", help="Show only pending")
    list_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # Stats
    stats_parser = subparsers.add_parser("stats", help="Get agent stats")
    stats_parser.add_argument("--agent", default="you", help="Agent name")

    # Leaderboard
    subparsers.add_parser("leaderboard", help="Show leaderboard")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = PredictCLI(api_url=args.api_url)

    try:
        if args.command == "make":
            result = cli.make_prediction(
                task=args.task,
                probability=args.prob,
                horizon=args.horizon,
                agent=args.agent,
                condition=args.condition
            )

            if "error" in result:
                print(f"Error: {result['error']}")
                sys.exit(1)

            print(f"Prediction registered!")
            print(f"  ID: {result['id']}")
            print(f"  Agent: {result['agent_name']}")
            print(f"  Task: {args.task}")
            print(f"  Confidence: {args.prob*100:.0f}%")
            print(f"  Horizon: {args.horizon} minutes")

        elif args.command == "resolve":
            outcome = args.outcome == "true"
            result = cli.resolve_prediction(args.id, outcome)

            if "error" in result:
                print(f"Error: {result['error']}")
                sys.exit(1)

            print(f"Prediction resolved!")
            print(f"  ID: {result['id']}")
            print(f"  Outcome: {'SUCCESS' if result['outcome'] else 'FAILURE'}")
            print(f"  Brier score: {result['brier_score']:.4f}")

            if result['brier_score'] < 0.10:
                print("  Rating: Excellent!")
            elif result['brier_score'] < 0.20:
                print("  Rating: Good")
            elif result['brier_score'] < 0.30:
                print("  Rating: Okay")
            else:
                print("  Rating: Needs improvement")

        elif args.command == "list":
            predictions = cli.list_predictions(
                agent=args.agent,
                pending=args.pending,
                limit=args.limit
            )

            if isinstance(predictions, dict) and "error" in predictions:
                print(f"Error: {predictions['error']}")
                sys.exit(1)

            if not predictions:
                print("No predictions found.")
            else:
                print(f"\n{len(predictions)} predictions:\n")
                for pred in predictions:
                    print(format_prediction(pred))
                    print()

        elif args.command == "stats":
            stats = cli.get_stats(args.agent)

            if "error" in stats:
                print(f"Error: {stats['error']}")
                sys.exit(1)

            print(f"\nStats for {stats['name']}:")
            print(f"  Calibration: {stats.get('calibration', 'N/A')}")
            print(f"  Predictions: {stats['prediction_count']}")

            if stats.get('calibration'):
                cal = stats['calibration']
                if cal < 0.10:
                    print(f"  Rating: Excellent calibration!")
                elif cal < 0.20:
                    print(f"  Rating: Good calibration")
                elif cal < 0.30:
                    print(f"  Rating: Okay calibration")
                else:
                    print(f"  Rating: Needs improvement")

        elif args.command == "leaderboard":
            agents = cli.get_leaderboard()

            if isinstance(agents, dict) and "error" in agents:
                print(f"Error: {agents['error']}")
                sys.exit(1)

            print("\nLeaderboard (sorted by calibration):\n")
            for i, agent in enumerate(agents, 1):
                cal = agent.get('calibration', 0.0)
                print(f"{i}. {agent['name']:20} {cal:.4f} ({agent['prediction_count']} predictions)")

    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
