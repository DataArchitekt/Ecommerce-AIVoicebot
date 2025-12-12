# backend/app/mcp_server.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/mcp/get_order_status")
def get_order_status(order_id: str):
    fake = {
        "12345": {"order_id":"12345","status":"IN_TRANSIT","eta":"2 days"},
        "11111": {"order_id":"11111","status":"DELIVERED","eta":"2025-11-26"}
    }
    return fake.get(order_id, {"order_id": order_id, "status":"UNKNOWN", "eta": None})
