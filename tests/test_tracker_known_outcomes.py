"""
Test: Prediction Tracker with Known Outcomes

Tests the core tracker with EXPLICIT, KNOWN outcomes.
No simulation. No randomness. Just verify the math.

Each test:
- Sets up a prediction with known probability
- Logs a known outcome (True or False)
- Verifies exact Brier score computation
- Verifies exact calibration update
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.time import World, run_n_ticks
from core.predictions import register_prediction, mark_task_complete
from core.stats import get_calibration, get_prediction_count, get_leaderboard
from engine.environments.code_tracker import create_code_tracker


# =============================================================================
# TEST 1: Perfect Prediction (p=1.0, outcome=True)
# =============================================================================

def test_perfect_prediction():
    """
    Test Case: Perfect prediction

    Setup:
    - Agent predicts p=1.0 (certain)
    - Task actually completes (True)

    Expected:
    - Brier = (1.0 - 1.0)² = 0.0 (perfect!)
    - Calibration = 0.0
    """
    print("\n=== TEST: Perfect Prediction ===")
    world = create_code_tracker(agent_names=["claude"])

    # Agent makes prediction: 100% confident
    world = register_prediction(
        world,
        agent_id=1,
        probability=1.0,
        horizon=10,
        condition="task_complete"
    )
    print(f"  [SETUP] Prediction: p=1.0, horizon=10")

    # Task actually completes
    world = mark_task_complete(world, agent_id=1, task_id="perfect_task")
    print(f"  [SETUP] Task completed at tick {world.tick}")

    # Advance to horizon
    world = run_n_ticks(world, 10)
    print(f"  [EXEC] Advanced to tick {world.tick}")

    # Verify
    calibration = get_calibration(world, agent_id=1)
    assert calibration is not None, "Calibration should exist"
    assert abs(calibration - 0.0) < 0.001, f"Expected 0.0, got {calibration}"

    print(f"  [PASS] Calibration = {calibration:.4f} (perfect!)")


# =============================================================================
# TEST 2: Worst Prediction (p=1.0, outcome=False)
# =============================================================================

def test_worst_prediction():
    """
    Test Case: Worst possible prediction

    Setup:
    - Agent predicts p=1.0 (certain)
    - Task does NOT complete (False)

    Expected:
    - Brier = (1.0 - 0.0)² = 1.0 (worst!)
    - Calibration = 1.0
    """
    print("\n=== TEST: Worst Prediction ===")
    world = create_code_tracker(agent_names=["claude"])

    # Agent makes prediction: 100% confident
    world = register_prediction(
        world,
        agent_id=1,
        probability=1.0,
        horizon=10,
        condition="task_complete"
    )
    print(f"  [SETUP] Prediction: p=1.0, horizon=10")

    # Task does NOT complete (no mark_task_complete call)
    print(f"  [SETUP] Task did NOT complete")

    # Advance to horizon
    world = run_n_ticks(world, 10)
    print(f"  [EXEC] Advanced to tick {world.tick}")

    # Verify
    calibration = get_calibration(world, agent_id=1)
    assert calibration is not None
    assert abs(calibration - 1.0) < 0.001, f"Expected 1.0, got {calibration}"

    print(f"  [PASS] Calibration = {calibration:.4f} (worst possible!)")


# =============================================================================
# TEST 3: Good Calibration (p=0.8, outcome=True)
# =============================================================================

def test_good_calibration():
    """
    Test Case: Good but not perfect prediction

    Setup:
    - Agent predicts p=0.8
    - Task completes (True)

    Expected:
    - Brier = (0.8 - 1.0)² = 0.04
    - Calibration = 0.04
    """
    print("\n=== TEST: Good Calibration ===")
    world = create_code_tracker(agent_names=["claude"])

    world = register_prediction(
        world,
        agent_id=1,
        probability=0.8,
        horizon=10,
        condition="task_complete"
    )
    print(f"  [SETUP] Prediction: p=0.8, horizon=10")

    world = mark_task_complete(world, agent_id=1)
    print(f"  [SETUP] Task completed")

    world = run_n_ticks(world, 10)
    print(f"  [EXEC] Advanced to tick {world.tick}")

    calibration = get_calibration(world, agent_id=1)
    expected = 0.04  # (0.8 - 1.0)²
    assert abs(calibration - expected) < 0.001, f"Expected {expected}, got {calibration}"

    print(f"  [PASS] Calibration = {calibration:.4f} (good!)")


# =============================================================================
# TEST 4: Overconfident (p=0.9, outcome=False)
# =============================================================================

def test_overconfident():
    """
    Test Case: Overconfident prediction

    Setup:
    - Agent predicts p=0.9 (very confident)
    - Task does NOT complete (False)

    Expected:
    - Brier = (0.9 - 0.0)² = 0.81
    - Calibration = 0.81 (bad!)
    """
    print("\n=== TEST: Overconfident ===")
    world = create_code_tracker(agent_names=["claude"])

    world = register_prediction(
        world,
        agent_id=1,
        probability=0.9,
        horizon=10,
        condition="task_complete"
    )
    print(f"  [SETUP] Prediction: p=0.9, horizon=10")
    print(f"  [SETUP] Task did NOT complete")

    world = run_n_ticks(world, 10)
    print(f"  [EXEC] Advanced to tick {world.tick}")

    calibration = get_calibration(world, agent_id=1)
    expected = 0.81  # (0.9 - 0.0)²
    assert abs(calibration - expected) < 0.001

    print(f"  [PASS] Calibration = {calibration:.4f} (overconfident!)")


# =============================================================================
# TEST 5: Running Average (multiple predictions)
# =============================================================================

def test_running_average():
    """
    Test Case: Calibration as running average

    Setup:
    - Prediction 1: p=0.9, outcome=False → Brier=0.81
    - Prediction 2: p=0.7, outcome=True → Brier=0.09

    Expected:
    - After pred 1: calibration = 0.81
    - After pred 2: calibration = (0.81 + 0.09) / 2 = 0.45
    """
    print("\n=== TEST: Running Average ===")
    world = create_code_tracker(agent_names=["claude"])

    # Prediction 1: Overconfident failure
    print(f"  [SETUP] Prediction 1: p=0.9, horizon=10")
    world = register_prediction(world, agent_id=1, probability=0.9, horizon=10, condition="task_complete")
    world = run_n_ticks(world, 10)  # No completion

    calibration_1 = get_calibration(world, agent_id=1)
    expected_1 = 0.81
    assert abs(calibration_1 - expected_1) < 0.001
    print(f"  [CHECK] After pred 1: calibration = {calibration_1:.4f}")

    # Prediction 2: Good prediction
    print(f"  [SETUP] Prediction 2: p=0.7, horizon=20")
    world = register_prediction(world, agent_id=1, probability=0.7, horizon=20, condition="task_complete")
    world = mark_task_complete(world, agent_id=1, task_id="task2")
    world = run_n_ticks(world, 10)  # Advance to tick 20

    calibration_2 = get_calibration(world, agent_id=1)
    expected_2 = (0.81 + 0.09) / 2  # Running average
    assert abs(calibration_2 - expected_2) < 0.001
    print(f"  [CHECK] After pred 2: calibration = {calibration_2:.4f}")

    count = get_prediction_count(world, agent_id=1)
    assert count == 2
    print(f"  [PASS] Running average working: {count} predictions")


# =============================================================================
# TEST 6: Multiple Agents Leaderboard
# =============================================================================

def test_multiple_agents_leaderboard():
    """
    Test Case: Leaderboard with multiple agents

    Setup:
    - Agent 1 (alice): p=0.8, outcome=True → Brier=0.04 (good)
    - Agent 2 (bob): p=0.95, outcome=False → Brier=0.9025 (bad)
    - Agent 3 (charlie): p=0.6, outcome=True → Brier=0.16 (ok)

    Expected leaderboard order:
    1. alice (0.04)
    2. charlie (0.16)
    3. bob (0.9025)
    """
    print("\n=== TEST: Multiple Agents Leaderboard ===")
    world = create_code_tracker(agent_names=["alice", "bob", "charlie"])

    # Alice: good prediction
    print(f"  [SETUP] Alice: p=0.8, outcome=True")
    world = register_prediction(world, agent_id=1, probability=0.8, horizon=10, condition="task_complete")
    world = mark_task_complete(world, agent_id=1)

    # Bob: bad prediction
    print(f"  [SETUP] Bob: p=0.95, outcome=False")
    world = register_prediction(world, agent_id=2, probability=0.95, horizon=10, condition="task_complete")

    # Charlie: ok prediction
    print(f"  [SETUP] Charlie: p=0.6, outcome=True")
    world = register_prediction(world, agent_id=3, probability=0.6, horizon=10, condition="task_complete")
    world = mark_task_complete(world, agent_id=3)

    # Resolve all
    world = run_n_ticks(world, 10)
    print(f"  [EXEC] All predictions resolved at tick {world.tick}")

    # Get leaderboard
    leaderboard = get_leaderboard(world)
    assert len(leaderboard) == 3

    # Verify order
    assert leaderboard[0]["agent_id"] == 1  # alice (best)
    assert leaderboard[1]["agent_id"] == 3  # charlie (ok)
    assert leaderboard[2]["agent_id"] == 2  # bob (worst)

    print(f"  [PASS] Leaderboard:")
    for i, agent in enumerate(leaderboard, 1):
        print(f"    {i}. Agent {agent['agent_id']}: {agent['calibration']:.4f}")


# =============================================================================
# TEST 7: Edge Case - No predictions yet
# =============================================================================

def test_no_predictions():
    """
    Test Case: Agent with no predictions

    Expected:
    - Calibration = None
    - Prediction count = 0
    - Not on leaderboard
    """
    print("\n=== TEST: No Predictions ===")
    world = create_code_tracker(agent_names=["claude"])

    calibration = get_calibration(world, agent_id=1)
    count = get_prediction_count(world, agent_id=1)
    leaderboard = get_leaderboard(world)

    assert calibration is None, "Should have no calibration"
    assert count == 0, "Should have no predictions"
    assert len(leaderboard) == 0, "Leaderboard should be empty"

    print(f"  [PASS] Calibration = None, count = 0, leaderboard empty")


# =============================================================================
# RUN ALL TESTS
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("PREDICTION TRACKER: TESTS WITH KNOWN OUTCOMES")
    print("="*70)

    test_perfect_prediction()
    test_worst_prediction()
    test_good_calibration()
    test_overconfident()
    test_running_average()
    test_multiple_agents_leaderboard()
    test_no_predictions()

    print("\n" + "="*70)
    print("[PASS] ALL TESTS PASSED")
    print("\nThe tracker works correctly:")
    print("  • Brier scores computed exactly")
    print("  • Calibration updates as running average")
    print("  • Leaderboard sorts correctly")
    print("  • No simulation - just pure math on known outcomes")
    print("="*70)
