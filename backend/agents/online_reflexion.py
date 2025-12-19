def reflexion_decide(evaluation: dict) -> dict:
    """
    Online reflexion agent:
    Decides how to adapt behavior based on evaluator output.
    """
    if evaluation["confidence"] == "low":
        return {
            "action": "replan",
            "reply": (
                f"I couldn’t find options that meet your criteria. "
                "Would you like to relax the price constraint?"
            )
        }

    return {
        "action": "proceed"
    }
