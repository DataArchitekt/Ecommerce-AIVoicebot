import re
from typing import List, Dict

def extract_order_id(text: str):
    m = re.search(r"\b(?:order|order id|order#|order no\.?)[:\s#-]*([0-9]{3,})\b", text, re.I)
    return m.group(1) if m else None

def plan_track_order(transcript: str, session_id: str) -> List[Dict]:
    """
    Return ordered list of tasks (max 4). Each task: {"task": "...", "args": {...}}
    """
    tasks = []
    order_id = extract_order_id(transcript)
    # Always authenticate first
    tasks.append({"task": "authenticate_user", "args": {"session_id": session_id}})
    if order_id:
        tasks.append({"task": "get_order_status", "args": {"order_id": order_id}})
        tasks.append({"task": "format_reply", "args": {"include_docs": True}})
    else:
        # If user didn't provide order id
        tasks.append({"task": "ask_for_order_id", "args": {}})
        tasks.append({"task": "format_reply", "args": {}})
    return tasks
