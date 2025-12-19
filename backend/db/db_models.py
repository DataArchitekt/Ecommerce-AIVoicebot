
from sqlalchemy import Column, Integer, Text, JSON, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class McpCall(Base):
    __tablename__ = "mcp_calls"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    session_id = Column(Text, nullable=True)
    task_name = Column(Text, nullable=False)
    tool_name = Column(Text, nullable=True)
    args = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    run_id = Column(Text, nullable=True, index=True)
