# backend/app/tests/test_planner_basic.py
from backend.app.agents.planner import plan_track_order
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))

def test_planner_returns_tasks_for_order_id():
    transcript = "Hi, can you track order 12345 for me?"
    session_id = "sess_test"
    plan = plan_track_order(transcript, session_id)
    # planner must return between 2 and 4 tasks
    assert 2 <= len(plan) <= 4
    # must include authenticate_user and get_order_status
    task_names = [t.get("task") for t in plan]
    assert "authenticate_user" in task_names
    assert "get_order_status" in task_names

def test_planner_asks_when_no_order_id():
    transcript = "Where is my package?"
    session_id = "sess_test2"
    plan = plan_track_order(transcript, session_id)
    task_names = [t.get("task") for t in plan]
    assert "ask_for_order_id" in task_names or "get_order_status" not in task_names
