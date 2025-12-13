# backend/app/tests/test_end_to_end_flow.py
import json
from backend.app.agents.planner import plan_track_order
from backend.app.agents.executor import execute_task
from backend.app.agents.evaluator import simple_evaluate
from backend.app.agents import trace_helpers
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))


def simple_compose(transcript, mcp_results):
    """Minimal composer that uses the order status result to produce a text reply."""
    # find order status
    order = next((r["result"] for r in mcp_results if r["task"] == "get_order_status"), None)
    if order:
        return f"Your order {order.get('order_id')} is {order.get('status')}."
    return "I need your order id to proceed."

def test_end_to_end_planner_executor_and_trace(db_session, mcp_respx, patch_tracer):
    # patch_tracer is the DummyTracer instance returned by conftest fixture
    tracer = trace_helpers.make_langchain_tracer()
    session_id = "sess_test"
    transcript = "Track order 12345 please"

    # 1. planner
    plan = plan_track_order(transcript, session_id)
    assert 2 <= len(plan) <= 4

    # log planner output into tracer (simulate you calling tracer.record)
    tracer.record("planner_output", {"plan": plan})

    # 2. executor for each task
    mcp_results = []
    for t in plan:
        res = execute_task(db_session, t, session_id)
        mcp_results.append(res)
        tracer.record("executor_call", {"task": t.get("task"), "result": res})

    # 3. simple evaluate
    eval_summary = simple_evaluate(mcp_results)
    tracer.record("evaluation", eval_summary)

    # 4. compose final reply using RAG + mcp_results (here we use simple_compose)
    reply = simple_compose(transcript, mcp_results)
    tracer.record("final_reply", {"reply": reply})

    # Assertions (map to acceptance criteria)
    # Planner produced subtasks
    assert any(t["task"] == "get_order_status" for t in plan)

    # Executor created audit rows
    from backend.app.db_models import McpCall
    rows = db_session.query(McpCall).filter(McpCall.session_id == session_id).all()
    assert len(rows) >= 1

    # The DummyTracer recorded events for planner, executor, eval, final
    events = tracer.events
    event_names = [e[0] if isinstance(e, tuple) else e for e in events]
    # We expect planner_output, executor_call, evaluation, final_reply entries recorded
    assert any(e[0] == "planner_output" for e in events)
    assert any(e[0] == "executor_call" for e in events)
    assert any(e[0] == "evaluation" for e in events)
    assert any(e[0] == "final_reply" for e in events)

    # Final reply sanity
    assert "order 12345" in reply or "12345" in reply
