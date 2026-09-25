import time
import uuid
from typing import Any, List, Optional, Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Import the workflow function from your existing script file
# (Rename 'workflow' if your file has a different name)
from codex import run_workflow

app = FastAPI(title="OpenAI-Compatible Agent Workflow API", version="1.0.0")


# ---------------------------------------------------------------------------
# OpenAI Schema Definitions
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[dict[str, Any]]]


class ChatCompletionRequest(BaseModel):
    model: str = "agent-workflow"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    max_retries: Optional[int] = Field(default=3, description="Custom retry limit")


class ChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


# ---------------------------------------------------------------------------
# Helper: Extract User Prompt
# ---------------------------------------------------------------------------
def extract_last_user_message(messages: List[ChatMessage]) -> str:
    """Finds and extracts the text from the latest user message."""
    for msg in reversed(messages):
        if msg.role.lower() == "user":
            if isinstance(msg.content, str):
                return msg.content.strip()
            elif isinstance(msg.content, list):
                # Handle OpenAI multi-part / multimodal text blocks
                parts = []
                for part in msg.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                return " ".join(parts).strip()
    return ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/v1/models")
@app.get("/models")
async def list_models():
    """Satisfies standard OpenAI client discovery checks."""
    return {
        "object": "list",
        "data": [
            {
                "id": "agent-workflow",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "custom",
            }
        ],
    }


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
@app.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest):
    if req.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming is not supported for this multi-step agent workflow.",
        )

    user_query = extract_last_user_message(req.messages)
    if not user_query:
        raise HTTPException(
            status_code=400,
            detail="No valid user message found in the 'messages' array.",
        )

    try:
        # Run your existing agent workflow
        final_answer = await run_workflow(
            user_query=user_query,
            max_retries=req.max_retries or 3,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent workflow error: {str(exc)}",
        )

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_time = int(time.time())

    return ChatCompletionResponse(
        id=completion_id,
        created=created_time,
        model=req.model,
        choices=[
            Choice(
                index=0,
                message=ChoiceMessage(role="assistant", content=final_answer or ""),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=len(user_query.split()),
            completion_tokens=len((final_answer or "").split()),
            total_tokens=len(user_query.split()) + len((final_answer or "").split()),
        ),
    )


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
