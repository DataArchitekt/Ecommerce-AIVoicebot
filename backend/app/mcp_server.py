# backend/app/mcp_server.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/mcp", tags=["mcp"])

class OrderStatusResp(BaseModel):
    order_id: str
    status: str
    items: list
    expected_delivery: str

class UserProfileResp(BaseModel):
    user_id: str
    name: str
    email: str
    phone: str
    verified: bool

class CreateInvestigationReq(BaseModel):
    order_id: str
    reason: str

class CreateInvestigationResp(BaseModel):
    investigation_id: str
    status: str

# Replace fake logic with DB lookups / business logic
@router.get("/order_status/{order_id}", response_model=OrderStatusResp)
def get_order_status(order_id: str):
    # here: real logic to query orders table
    # For testing: return fake data
    return OrderStatusResp(
        order_id=order_id,
        status="IN_TRANSIT",
        items=[{"product_id": "1", "qty": 1}],
        expected_delivery="2025-12-20"
    )

@router.get("/user_profile/{session_id}", response_model=UserProfileResp)
def get_user_profile(session_id: str):
    # Map session to user; for now return a fake verified user
    return UserProfileResp(user_id="user_abc", name="Mitalee", email="mitalee@example.com", phone="+91xxxx", verified=True)

@router.post("/create_investigation", response_model=CreateInvestigationResp)
def create_investigation(payload: CreateInvestigationReq):
    # persist investigation in investigations table or return fake id
    return CreateInvestigationResp(investigation_id="invest_1234", status="CREATED")
