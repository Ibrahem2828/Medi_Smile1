# apps/ai/services/decision_policy.py

def merge_decisions(rule_based_result: dict, semantic_result: dict) -> dict:
    """
    Merge rule-based and semantic outputs.
    """

    diagnosis_label = semantic_result.get("top_label", "unknown")
    confidence = semantic_result.get("confidence", "medium")

    return {
        "diagnosis_label": diagnosis_label,
        "confidence_level": confidence,
    }
