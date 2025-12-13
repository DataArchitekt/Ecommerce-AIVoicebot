import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.agents.planner import plan_track_order
from backend.app.agents.executor import execute_task
from backend.app.db_models import McpCall
from backend.app.db import SessionLocal  # or your DB session factory
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))


client = TestClient(app)

def test_planner_emits_tasks():
    plan = plan_track_order("Track order 12345 please", "sess_1")
    assert 2 <= len(plan) <= 4
    assert any(t["task"] == "get_order_status" for t in plan)

def test_executor_calls_and_audit(db_session=SessionLocal()):
    plan = plan_track_order("Track order 12345 please", "sess_1")
    # execute each task
    results = []
    for t in plan:
        r = execute_task(db_session, t, "sess_1")
        results.append(r)
    # assert at least one mcp_calls row exists
    # NOTE: adjust query according to your DB helper API
    rows = db_session.query(McpCall).filter(McpCall.session_id == "sess_1").all()
    assert len(rows) >= 1
    # ensure get_order_status produced a result with order_id
    order_results = [r for r in results if r["task"] == "get_order_status"]
    assert order_results and "result" in order_results[0]
    assert order_results[0]["result"].get("order_id", "") == "12345"