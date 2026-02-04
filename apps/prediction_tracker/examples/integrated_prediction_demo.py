"""
Integrated Prediction Demo

Shows how to use the functional prediction system with the database tracker.

This demo:
1. Creates agents with personalities
2. Runs predictions using core/predictions.py
3. Syncs to database for studio visualization
4. Shows both systems working together
"""
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.synthetic_agents import (
    create_prediction_environment,
    generate_task_scenario,
    complete_task_at_tick,
    print_leaderboard
)
from core.time import tick_world
from core.predictions import check_and_resolve_predictions
from tracker.bridge import PredictionBridge


def run_integrated_demo():
    """Run a demo showing functional + database integration."""
    print("=" * 70)
    print("INTEGRATED PREDICTION DEMO")
    print("Functional predictions + Database tracker + Studio visualization")
    print("=" * 70)
    print()

    # Initialize bridge using context manager
    print("[1] Initializing database bridge...")
    with PredictionBridge("tracker.db") as bridge:
        print("    ✓ Connected to tracker.db")
        print()

        # Create environment with personality-based agents
        print("[2] Creating prediction environment...")
        agent_names = ["Alice", "Bob", "Charlie"]
        agent_personalities = ["optimist", "realist", "pessimist"]

        world = create_prediction_environment(agent_names, agent_personalities)
        print(f"    ✓ Created {len(agent_names)} agents:")
        for i, (name, personality) in enumerate(zip(agent_names, agent_personalities), start=1):
            print(f"      - Agent {i}: {name} ({personality})")
        print()

        # Run 5 task scenarios
        print("[3] Running task scenarios...")
        print()

        scenarios = [
            {"agent_id": 1, "true_prob": 0.8, "horizon": 5},  # Alice (optimist) - likely success
            {"agent_id": 2, "true_prob": 0.5, "horizon": 5},  # Bob (realist) - uncertain
            {"agent_id": 3, "true_prob": 0.3, "horizon": 5},  # Charlie (pessimist) - likely fail
            {"agent_id": 1, "true_prob": 0.6, "horizon": 8},  # Alice - another task
            {"agent_id": 2, "true_prob": 0.7, "horizon": 8},  # Bob - another task
        ]

        for i, scenario in enumerate(scenarios, 1):
            agent_id = scenario["agent_id"]
            true_prob = scenario["true_prob"]
            horizon = world.tick + scenario["horizon"]

            # Generate scenario (agent makes prediction)
            world, predicted_prob, will_complete = generate_task_scenario(
                world, agent_id, true_prob, horizon, task_id=f"task_{i}"
            )

            agent_meta = world.state.global_attrs["agents"][str(agent_id)]
            agent_name = agent_meta["name"]
            personality = agent_meta["personality"]

            print(f"    Scenario {i}: {agent_name} ({personality})")
            print(f"      True probability: {true_prob:.2f}")
            print(f"      Agent predicts: {predicted_prob:.2f}")
            print(f"      Will complete: {will_complete}")
            print(f"      Horizon: tick {horizon}")

            # Sync prediction to database
            db_pred_id = bridge.sync_prediction(world, agent_id)
            print(f"      ✓ Synced to database (ID: {db_pred_id})")
            print()

            # Schedule task completion if it will complete
            if will_complete:
                world = complete_task_at_tick(world, agent_id, horizon, f"task_{i}")

        # Advance time to resolve predictions
        print("[4] Advancing time to resolve predictions...")
        print()

        for tick in range(world.tick, 10):
            world = tick_world(world)
            world = check_and_resolve_predictions(world)

            # Check for any new resolutions and sync them
            for event in world.log.completed:
                if event.event_type == "resolution" and event.tick == world.tick:
                    pred_id = event.payload["prediction_id"]
                    outcome = event.payload["outcome"]
                    brier = event.payload["brier_score"]

                    print(f"    Tick {tick}: Resolved {pred_id}")
                    print(f"      Outcome: {outcome}")
                    print(f"      Brier score: {brier:.4f}")

                    # Sync resolution to database
                    synced = bridge.sync_resolution(world, pred_id)
                    if synced:
                        print(f"      ✓ Synced to database")
                    print()

        # Show functional system results
        print("[5] Functional system leaderboard:")
        print_leaderboard(world)
        print()

        # Show database results
        print("[6] Database tracker status:")
        db_leaderboard = bridge.db.get_leaderboard()
        print(f"    Total agents in DB: {len(db_leaderboard)}")
        print()
        print("    Database Leaderboard:")
        for i, agent in enumerate(db_leaderboard, 1):
            print(f"      {i}. {agent['name']}")
            print(f"         Calibration: {agent['calibration']:.4f}")
            print(f"         Predictions: {agent['prediction_count']}")
        print()

        # Show pending predictions
        pending = bridge.db.get_predictions(resolved=False)
        print(f"    Pending predictions: {len(pending)}")
        if pending:
            for pred in pending:
                print(f"      - {pred['agent_name']}: {pred['probability']:.2f} (horizon: {pred['horizon_minutes']} min)")
        print()

        # Context manager automatically closes connection

    print("=" * 70)
    print("DEMO COMPLETE")
    print()
    print("Next steps:")
    print("  1. Run: python -m studio.main")
    print("  2. Click 'Prediction Tracker' button")
    print("  3. See your agents visualized in real-time!")
    print("=" * 70)


if __name__ == "__main__":
    run_integrated_demo()
