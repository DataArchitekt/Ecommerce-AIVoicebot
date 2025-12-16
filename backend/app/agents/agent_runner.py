import time
from typing import Optional

from backend.app.agents.evaluator import evaluate_response
from backend.app.agents.reflexion import reflexion_rerun
from app.db import record_mcp_call

BLEU_THRESHOLD = 0.30


def run_with_evaluation(
    *,
    execute_fn,
    db,
    transcript: str,
    session_id: str,
    ground_truth: Optional[str],
    run_id: str
):
    """
    Orchestrates:
    - Agent execution
    - Evaluation (BLEU / ROUGE)
    - Reflexion rerun (if needed)

    main.py MUST call only this function.
    """

    # ===============================
    # 1️⃣ AGENT EXECUTION
    # ===============================
    start = time.time()

    agent_response = execute_fn(
        db=db,
        task={
            "task": "agent",
            "args": {"transcript": transcript}
        },
        session_id=session_id
    )

    duration_ms = int((time.time() - start) * 1000)

    record_mcp_call(
        db=db,
        session_id=session_id,
        name="agent",
        tool="run",
        args={"transcript": transcript},
        result=agent_response,
        status="success",
        duration_ms=duration_ms,
        run_id=run_id
    )

    # Production path (no evaluation)
    if not ground_truth:
        return agent_response

    # ===============================
    # 2️⃣ EVALUATION
    # ===============================
    start = time.time()

    scores = evaluate_response(
        pred=agent_response["reply"],
        ref=ground_truth
    )

    duration_ms = int((time.time() - start) * 1000)

    status = "failed" if scores["bleu"] < BLEU_THRESHOLD else "success"

    record_mcp_call(
        db=db,
        session_id=session_id,
        name="evaluator",
        tool="score",
        args={
            "prediction": agent_response["reply"],
            "reference": ground_truth
        },
        result=scores,
        status=status,
        duration_ms=duration_ms,
        run_id=run_id
    )

    # If evaluation passed → done
    if scores["bleu"] >= BLEU_THRESHOLD:
        agent_response["evaluation"] = scores
        return agent_response

    # ===============================
    # 3️⃣ REFLEXION
    # ===============================
    def rerun_fn(text: str, system_override: Optional[str] = None):
        task_payload = {
            "task": "agent",
            "args": {"transcript": text}
        }

        if system_override:
            task_payload["args"]["system_override"] = system_override

        return execute_fn(
            db=db,
            task=task_payload,
            session_id=session_id
        )

    start = time.time()

    improved_response = reflexion_rerun(
        transcript,
        agent_response["reply"],
        rerun_fn
    )

    improved_scores = evaluate_response(
        pred=improved_response["reply"],
        ref=ground_truth
    )

    duration_ms = int((time.time() - start) * 1000)

    reflexion_status = (
        "improved"
        if improved_scores["bleu"] > scores["bleu"]
        else "no_gain"
    )

    record_mcp_call(
        db=db,
        session_id=session_id,
        name="reflexion",
        tool="rerun",
        args={
            "previous_reply": agent_response["reply"],
            "reason": "bleu_below_threshold"
        },
        result={
            "improved_reply": improved_response,
            "improved_scores": improved_scores
        },
        status=reflexion_status,
        duration_ms=duration_ms,
        run_id=run_id
    )

    improved_response["evaluation"] = improved_scores

    return improved_response if reflexion_status == "improved" else agent_response
