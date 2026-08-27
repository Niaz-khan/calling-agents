from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=3,
        max_length=5000,
    )

class ChatResponse(BaseModel):
    agent_id: int
    message: str
    