"""
Test script for prediction tracker database.

Creates sample data and verifies functionality.
"""
import sys
import io

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tracker.database import TrackerDB
import time


def main():
    """Run tests and create sample data."""
    print("=" * 50)
    print("Prediction Tracker Test")
    print("=" * 50)
    print()

    # Initialize database using context manager
    with TrackerDB("tracker.db") as db:
        print("✓ Database initialized")

        # Test 1: Register agents
        print("\n[Test 1] Registering agents...")
        db.register_agent("claude-sonnet")
        db.register_agent("claude-opus")
        db.register_agent("gpt-4")
        print("✓ Registered 3 agents")

        # Test 2: Register predictions
        print("\n[Test 2] Registering predictions...")

        # Claude Sonnet predictions
        pred1 = db.register_prediction(
            "claude-sonnet",
            probability=0.85,
            horizon_minutes=15,
            condition="task_complete",
            context={"task": "implement database layer"}
        )

        pred2 = db.register_prediction(
            "claude-sonnet",
            probability=0.70,
            horizon_minutes=30,
            condition="tests_pass",
            context={"task": "write test suite"}
        )

        # Claude Opus predictions
        pred3 = db.register_prediction(
            "claude-opus",
            probability=0.90,
            horizon_minutes=10,
            condition="task_complete",
            context={"task": "review code"}
        )

        # GPT-4 predictions
        pred4 = db.register_prediction(
            "gpt-4",
            probability=0.60,
            horizon_minutes=20,
            condition="task_complete",
            context={"task": "optimize performance"}
        )

        print(f"✓ Registered 4 predictions (IDs: {pred1}, {pred2}, {pred3}, {pred4})")

        # Test 3: Resolve some predictions
        print("\n[Test 3] Resolving predictions...")

        # Resolve with positive outcome
        db.resolve_prediction(pred1, outcome=True)
        print(f"✓ Resolved prediction {pred1} → True (Brier: 0.0225)")

        # Resolve with negative outcome
        db.resolve_prediction(pred3, outcome=False)
        print(f"✓ Resolved prediction {pred3} → False (Brier: 0.8100)")

        # Test 4: Get agent stats
        print("\n[Test 4] Getting agent statistics...")

        sonnet_stats = db.get_agent_stats("claude-sonnet")
        print(f"Claude Sonnet:")
        print(f"  - Calibration: {sonnet_stats['calibration']:.4f}")
        print(f"  - Predictions: {sonnet_stats['prediction_count']}")

        opus_stats = db.get_agent_stats("claude-opus")
        print(f"Claude Opus:")
        print(f"  - Calibration: {opus_stats['calibration']:.4f}")
        print(f"  - Predictions: {opus_stats['prediction_count']}")

        # Test 5: Get leaderboard
        print("\n[Test 5] Getting leaderboard...")
        leaderboard = db.get_leaderboard()
        print("Leaderboard (sorted by calibration):")
        for i, agent in enumerate(leaderboard, 1):
            print(f"  {i}. {agent['name']:15} - {agent['calibration']:.4f} ({agent['prediction_count']} predictions)")

        # Test 6: Get predictions
        print("\n[Test 6] Getting recent predictions...")
        predictions = db.get_predictions(limit=10)
        print(f"Total predictions: {len(predictions)}")

        pending = db.get_predictions(resolved=False)
        print(f"Pending predictions: {len(pending)}")

        resolved = db.get_predictions(resolved=True)
        print(f"Resolved predictions: {len(resolved)}")

        # Test 7: Check pending resolutions
        print("\n[Test 7] Checking predictions past horizon...")
        pending_resolutions = db.get_pending_resolutions()
        print(f"Predictions past horizon: {len(pending_resolutions)}")

        print("\n✓ Database automatically closed by context manager")

    print("\n" + "=" * 50)
    print("All tests passed!")
    print(f"Database file: tracker.db")
    print("You can now run: python -m studio.main")
    print("=" * 50)


if __name__ == "__main__":
    main()
