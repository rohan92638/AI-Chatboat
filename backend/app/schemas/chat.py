from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique ID for the conversation",
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Message sent to the AI model",
    )


class ChatResponse(BaseModel):
    response: str
    model: str
    request_id: str