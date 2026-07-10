"""
Sales call scoring rubric and roll-up calculations.

Why this approach:
We define explicit weights for each of the five core evaluation dimensions:
- Needs Discovery: 25% (Foundational to understanding the client)
- Product Knowledge: 20% (Ensures accurate coaching details)
- Objection Handling: 20% (Critical for deal progression)
- Compliance: 20% (Required for brand safety and legal protection)
- Trial Booking: 15% (Measures call conversion/next-step confirmation)

To ensure that critical compliance violations are heavily penalized (e.g. over-promising or high-pressure),
our roll-up math calculates the weighted average and deducts 0.5 points for each critical tag raised.
This aligns with realistic sales auditing standards where compliance failures override good sales technique.
"""

from typing import Dict

# Rubric weights summing up to 1.0 (100%)
RUBRIC_WEIGHTS = {
    "needs_discovery": 0.25,
    "product_knowledge": 0.20,
    "objection_handling": 0.20,
    "compliance": 0.20,
    "trial_booking": 0.15
}

def calculate_overall_score(scores: dict, critical_tags_count: int = 0) -> float:
    """
    Calculates the overall call score as a weighted average of the five dimensions,
    applying a penalty for critical compliance violations.
    
    Args:
        scores (dict): Dictionary containing the 5 dimension scores (needs_discovery, etc.)
        critical_tags_count (int): Number of critical compliance tags flagged on the call.
        
    Returns:
        float: Rounded overall score between 1.0 and 5.0.
    """
    # 1. Compute weighted average
    weighted_sum = 0.0
    for key, weight in RUBRIC_WEIGHTS.items():
        score_val = scores.get(key, 1.0)
        # Clamp score between 1.0 and 5.0
        score_val = max(1.0, min(5.0, float(score_val)))
        weighted_sum += score_val * weight
        
    # 2. Apply penalty for critical compliance violations (e.g. deduct 0.5 per critical tag)
    penalty = 0.5 * critical_tags_count
    final_score = weighted_sum - penalty
    
    # 3. Clamp final overall score to [1.0, 5.0]
    final_score = max(1.0, min(5.0, final_score))
    
    return round(final_score, 2)
