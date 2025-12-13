from typing import List, Dict

def simple_evaluate(results: List[Dict]) -> Dict:
    """
    Very small evaluator: checks if get_order_status returned success.
    """
    summary = {"ok": True, "issues": []}
    for r in results:
        if r.get("task") == "get_order_status":
            res = r.get("result", {})
            if res.get("status") is None:
                summary["ok"] = False
                summary["issues"].append("missing_order_status")
    return summary
