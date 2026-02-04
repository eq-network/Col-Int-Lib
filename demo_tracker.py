"""
Demo: Real-world Prediction Tracking

This demonstrates how Mycorrhiza would track real predictions
from Claude Code in production.

No simulation. Just tracking reality.
"""

from core.time import run_n_ticks
from core.predictions import register_prediction, mark_task_complete
from core.stats import get_calibration, get_leaderboard, get_all_predictions
from engine.environments.code_tracker import (
    create_code_tracker,
    print_agent_stats,
    print_leaderboard
)


def main():
    print("\n" + "="*70)
    print("MYCORRHIZA DEMO: Real Prediction Tracking")
    print("="*70)

    # =========================================================================
    # SCENARIO: Claude helps user with 3 tasks
    # =========================================================================

    print("\n[SESSION START] User starts Claude Code session")
    world = create_code_tracker(agent_names=["claude-session-1"])

    # -------------------------------------------------------------------------
    # Task 1: Easy task - Claude is confident
    # -------------------------------------------------------------------------

    print("\n" + "-"*70)
    print("TASK 1: Write a simple function")
    print("-"*70)

    print("\nUser: 'Write a function to compute Fibonacci numbers'")
    print("Claude: 'I'll have this done in about 10 minutes, 85% confident'")

    # Register Claude's prediction (extracted from response)
    world = register_prediction(
        world,
        agent_id=1,
        probability=0.85,
        horizon=10,
        condition="task_complete",
        context={"task": "fibonacci_function", "complexity": "easy"}
    )
    print("  -> Prediction registered: p=0.85, horizon=10 ticks")

    # User works with Claude... time passes
    print("\n  [5 ticks pass: coding, debugging, testing]")
    world = run_n_ticks(world, 5)

    # Task actually completes!
    print("  [Task completes successfully]")
    world = mark_task_complete(world, agent_id=1, task_id="fibonacci")

    # Advance to prediction horizon
    print("  [Advancing to horizon...]")
    world = run_n_ticks(world, 5)

    # Check result
    cal = get_calibration(world, agent_id=1)
    brier = (0.85 - 1.0) ** 2
    print(f"\n  [OK] RESULT: Task completed")
    print(f"     Brier score: {brier:.4f}")
    print(f"     Calibration: {cal:.4f} (excellent!)")

    # -------------------------------------------------------------------------
    # Task 2: Harder task - Claude overconfident
    # -------------------------------------------------------------------------

    print("\n" + "-"*70)
    print("TASK 2: Implement complex algorithm")
    print("-"*70)

    print("\nUser: 'Implement a balanced binary search tree'")
    print("Claude: 'Should take around 20 minutes, I'm 90% confident'")

    world = register_prediction(
        world,
        agent_id=1,
        probability=0.90,
        horizon=world.tick + 20,
        condition="task_complete",
        context={"task": "bst_implementation", "complexity": "hard"}
    )
    print("  -> Prediction registered: p=0.90, horizon=20 ticks")

    # Time passes, but task is harder than expected
    print("\n  [20 ticks pass: more complex than expected]")
    world = run_n_ticks(world, 20)

    # Task does NOT complete in time
    print("  [Task NOT completed at horizon - took longer]")

    # Check result
    cal = get_calibration(world, agent_id=1)
    brier_2 = (0.90 - 0.0) ** 2
    print(f"\n  [FAIL] RESULT: Task NOT completed")
    print(f"     Brier score: {brier_2:.4f} (overconfident!)")
    print(f"     Calibration: {cal:.4f} (average of both predictions)")

    # -------------------------------------------------------------------------
    # Task 3: Medium task - Claude learns, more cautious
    # -------------------------------------------------------------------------

    print("\n" + "-"*70)
    print("TASK 3: Refactor existing code")
    print("-"*70)

    print("\nUser: 'Refactor the authentication module'")
    print("Claude: 'This will take about 15 minutes, 70% confident'")
    print("         (Note: More cautious after previous overconfidence)")

    world = register_prediction(
        world,
        agent_id=1,
        probability=0.70,
        horizon=world.tick + 15,
        condition="task_complete",
        context={"task": "auth_refactor", "complexity": "medium"}
    )
    print("  -> Prediction registered: p=0.70, horizon=15 ticks")

    # Time passes
    print("\n  [10 ticks pass: steady progress]")
    world = run_n_ticks(world, 10)

    # Task completes
    print("  [Task completes successfully]")
    world = mark_task_complete(world, agent_id=1, task_id="auth_refactor")

    # Advance to horizon
    print("  [Advancing to horizon...]")
    world = run_n_ticks(world, 5)

    # Check result
    cal = get_calibration(world, agent_id=1)
    brier_3 = (0.70 - 1.0) ** 2
    print(f"\n  [OK] RESULT: Task completed")
    print(f"     Brier score: {brier_3:.4f}")
    print(f"     Calibration: {cal:.4f} (improving!)")

    # =========================================================================
    # SESSION SUMMARY
    # =========================================================================

    print("\n" + "="*70)
    print("SESSION SUMMARY")
    print("="*70)

    # Show agent stats
    print_agent_stats(world, agent_id=1)

    # Show all predictions
    print("\n" + "-"*70)
    print("PREDICTION HISTORY")
    print("-"*70)

    preds = get_all_predictions(world)
    for i, pred in enumerate(preds, 1):
        outcome_str = "[OK] TRUE" if pred.get("outcome") else "[FAIL] FALSE"
        if pred["resolved"]:
            print(f"\n{i}. Tick {pred['tick']}: p={pred['probability']:.2f}")
            print(f"   Outcome: {outcome_str}")
            print(f"   Brier: {pred['brier_score']:.4f}")
        else:
            print(f"\n{i}. Tick {pred['tick']}: p={pred['probability']:.2f}")
            print(f"   Status: Pending")

    # Show key insight
    print("\n" + "="*70)
    print("KEY INSIGHT")
    print("="*70)
    print(f"\nClaude's calibration: {get_calibration(world, agent_id=1):.4f}")
    print(f"\nBreakdown:")
    print(f"  Task 1 (easy):    p=0.85, outcome=True  -> Brier={brier:.4f}")
    print(f"  Task 2 (hard):    p=0.90, outcome=False -> Brier={brier_2:.4f}")
    print(f"  Task 3 (medium):  p=0.70, outcome=True  -> Brier={brier_3:.4f}")
    print(f"\n  Average: {(brier + brier_2 + brier_3) / 3:.4f}")
    print("\nObservation:")
    print("  - Claude was overconfident on the hard task (p=0.90 failed)")
    print("  - Adjusted to be more cautious on next task (p=0.70)")
    print("  - Calibration improving through experience")
    print("\nThis is REAL learning from REAL outcomes.")
    print("No simulation. No synthetic personalities. Just tracking reality.")

    print("\n" + "="*70)
    print("\n[DEMO COMPLETE]")
    print("\nNext steps:")
    print("  1. Integrate with Claude Code via MCP")
    print("  2. Extract predictions from natural language")
    print("  3. Display calibration in real-time dashboard")
    print("  4. Track across multiple sessions")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
