# backend/app/tests/test_executor_and_audit.py
from backend.app.agents.planner import plan_track_order
from backend.app.agents.executor import execute_task
from backend.app.db_models import McpCall

def test_executor_calls_and_creates_audit(db_session, mcp_respx):
    transcript = "Please track order 12345"
    session_id = "sess_test"
    plan = plan_track_order(transcript, session_id)

    results = []
    for t in plan:
        r = execute_task(db_session, t, session_id)
        results.append(r)

    # assert executor returned results for get_order_status
    order_results = [r for r in results if r.get("task") == "get_order_status"]
    assert order_results, "executor did not produce get_order_status result"

    # assert there is at least one McpCall recorded for this session
    rows = db_session.query(McpCall).filter(McpCall.session_id == session_id).all()
    assert len(rows) >= 1

    # check one of the audit rows contains order_id in args/result
    found_order_call = any(
        (row.tool_name == "get_order_status" or (row.args and "order_id" in (row.args or {})))
        for row in rows
    )
    assert found_order_call, "no mcp_calls row associated with order lookup"
