import subprocess
import time
import uuid
import asyncio
import json
from typing import Any, List, Optional, Union
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

# Import the workflow function from your existing script file
# (Rename 'workflow' if your file has a different name)
# from codex import run_workflow
from ndl import run_command_agent

def format_agent_response(agent_output: Any) -> str:
    """Extracts a clean string message from the dict returned by run_command_agent."""
    if isinstance(agent_output, dict):
        if agent_output.get("error"):
            return str(agent_output["error"])

        results = agent_output.get("results")
        if results:
            if isinstance(results, list):
                items = [str(item) for item in results if item]
                if not items:
                    return ""
                if len(items) == 1:
                    return items[0]
                if len(items) == 2:
                    return f"{items[0]} and {items[1]}"
                return f"{', '.join(items[:-1])}, and {items[-1]}"
            return str(results)

        if agent_output.get("success"):
            return "Command executed successfully."
        return "Command completed with no output."

    return str(agent_output or "")

app = FastAPI(title="OpenAI-Compatible Agent Workflow API", version="1.0.0")

# Allow all origins and methods (including OPTIONS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RawRequestLogger(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/v1") or request.url.path.startswith("/chat"):
            try:
                body_bytes = await request.body()
                print(f"[RAW REQUEST] {request.method} {request.url.path}")
                print(f"[RAW BODY] {body_bytes.decode('utf-8', errors='replace')}")
                print(f"[RAW HEADERS] {dict(request.headers)}")
                print("---")
            except Exception as e:
                print(f"[ERROR reading raw request] {e}")
        response = await call_next(request)
        return response


app.add_middleware(RawRequestLogger)


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
    content: Optional[Union[str, List[dict[str, Any]]]] = None


class ChatCompletionRequest(BaseModel):
    model: str = "agent-workflow"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    max_retries: Optional[int] = Field(default=3, description="Custom retry limit")
    model_config = {"extra": "ignore"}


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


async def stream_generator(content: str, model: str, chat_id: str, created: int):
    """Generates OpenAI-compatible SSE stream chunks."""
    words = content.split() if content else []
    for i, word in enumerate(words):
        word_chunk = word + " " if i < len(words) - 1 else word
        chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": word_chunk},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.05)

    final_chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


def extract_last_user_message(messages: List[ChatMessage]) -> str:
    # Find the last user message (ignore system, assistant, and everything else)
    for msg in reversed(messages):
        if msg.role.lower() == "user" and msg.content is not None:
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
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


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


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    background_tasks: BackgroundTasks,  # <-- Injected by FastAPI
):
    user_query = extract_last_user_message(req.messages)
    if not user_query:
        raise HTTPException(status_code=400, detail="No user message provided.")

    try:
        # final_answer = await run_workflow(
        #     user_query=user_query,
        #     max_retries=req.max_retries or 3,
        # )

        # Run sync function in thread pool and convert dict output to string
        raw_result = await asyncio.to_thread(run_command_agent, user_query)
        final_answer = format_agent_response(raw_result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(exc)}")

    chat_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if final_answer:
        background_tasks.add_task(play_voice, final_answer)

    if req.stream:
        return StreamingResponse(
            stream_generator(final_answer or "", req.model, chat_id, created),
            media_type="text/event-stream"
        )

    return ChatCompletionResponse(
        id=chat_id,
        created=created,
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
