import re

def evaluate_price_constraint(query: str, sources: list) -> dict:
    """
    Online evaluator agent:
    Checks whether retrieved products satisfy user constraints.
    """
    match = re.search(r"under\s+(\d+)", query.lower())
    if not match:
        return {
            "confidence": "high",
            "reason": "no_price_constraint"
        }

    max_price = int(match.group(1))

    violating = []
    for s in sources:
        price = s.get("metadata", {}).get("price")
        if price and price > max_price:
            violating.append(price)

    if violating:
        return {
            "confidence": "low",
            "reason": "price_constraint_violated",
            "max_price": max_price,
            "found_prices": violating
        }

    return {
        "confidence": "high",
        "reason": "constraint_satisfied"
    }
