from backend.agents.planner import plan_user_request, plan_track_order

def route_to_planner(transcript: str, session_id: str, db):
    text = transcript.lower()

    if any(k in text for k in ["order", "track", "delivery", "shipment"]):
        return plan_track_order(transcript, session_id, db)

    return plan_user_request(transcript, session_id, db)
