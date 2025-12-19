from backend.agents.planner import plan_user_request

def route_to_planner(transcript: str, session_id: str, db):
    text = transcript.lower()
    return plan_user_request(transcript, session_id, db)

