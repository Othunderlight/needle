import subprocess
import time
import uuid
from typing import Any, List, Optional, Union
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import the workflow function from your existing script file
# (Rename 'workflow' if your file has a different name)
from codex import run_workflow

app = FastAPI(title="OpenAI-Compatible Agent Workflow API", version="1.0.0")

# Allow all origins and methods (including OPTIONS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Background Voice Task
# ---------------------------------------------------------------------------
def play_voice(message: str) -> None:
    """Runs in the background after the HTTP response has already been sent."""
    try:
        subprocess.run(["./say_kitten.sh", message], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[Voice Error]: Failed to run say_kitten.sh: {e}")


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


def extract_last_user_message(messages: List[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role.lower() == "user":
            if isinstance(msg.content, str):
                return msg.content.strip()
            elif isinstance(msg.content, list):
                parts = [
                    part.get("text", "")
                    for part in msg.content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                return " ".join(parts).strip()
    return ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/v1/models")
@app.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [{"id": "agent-workflow", "object": "model", "created": int(time.time()), "owned_by": "custom"}],
    }


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
@app.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    req: ChatCompletionRequest,
    background_tasks: BackgroundTasks,  # <-- Injected by FastAPI
):
    if req.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported.")

    user_query = extract_last_user_message(req.messages)
    if not user_query:
        raise HTTPException(status_code=400, detail="No user message provided.")

    try:
        final_answer = await run_workflow(
            user_query=user_query,
            max_retries=req.max_retries or 3,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(exc)}")

    # Enqueue TTS to run in the background right after sending the response
    if final_answer:
        background_tasks.add_task(play_voice, final_answer)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
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
