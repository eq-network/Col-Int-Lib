"""
Pure functions for prediction metrics.

These functions are completely separate from persistence.
All business logic for prediction scoring and calibration lives here.
"""
from typing import List


def compute_brier_score(probability: float, outcome: bool) -> float:
    """
    Compute Brier score for a prediction.

    Brier score = (p - outcome)²

    Lower is better:
    - Perfect prediction: 0.0
    - Worst prediction: 1.0

    Args:
        probability: Predicted probability in [0, 1]
        outcome: Actual outcome (True/False)

    Returns:
        Brier score in [0.0, 1.0]

    Raises:
        ValueError: If probability not in [0, 1]
    """
    if not 0 <= probability <= 1:
        raise ValueError(f"Probability must be in [0, 1], got {probability}")

    return (probability - float(outcome)) ** 2


def compute_calibration(brier_scores: List[float]) -> float:
    """
    Compute calibration as average of Brier scores.

    Args:
        brier_scores: List of Brier scores

    Returns:
        Average Brier score (lower is better)

    Raises:
        ValueError: If list is empty
    """
    if not brier_scores:
        raise ValueError("Cannot compute calibration from empty list")

    return sum(brier_scores) / len(brier_scores)


def compute_incremental_calibration(
    current_calibration: float,
    current_count: int,
    new_brier_score: float
) -> float:
    """
    Update calibration with a new Brier score using incremental averaging.

    Uses running average: new_avg = (old_avg * n + new_value) / (n + 1)

    Args:
        current_calibration: Current average (-1.0 if none)
        current_count: Number of scores in current average
        new_brier_score: New Brier score to incorporate

    Returns:
        Updated calibration

    Note:
        This is provided for incremental updates, but the current database
        implementation uses SQL AVG() which is equivalent and more efficient.
    """
    if current_calibration < 0:  # First score
        return new_brier_score

    total = current_calibration * current_count
    return (total + new_brier_score) / (current_count + 1)
