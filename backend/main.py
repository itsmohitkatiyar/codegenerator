from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from llama_cpp import Llama
import os
import json

MODEL_PATH = os.path.expanduser(
    "~/models/llm/qwen/qwen2.5-7b-instruct-q4_0-00001-of-00002.gguf"
)

print("🔹 Loading Qwen model...")
llm = Llama(model_path=MODEL_PATH, n_ctx=8192, n_threads=8)

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/stream")
async def stream(request: Request):
    """
    Stream Qwen responses token by token.
    Expects JSON payload: { "messages": [ {"role": "user"/"assistant", "content": "..."} ] }
    """
    data = await request.json()
    messages = data.get("messages", [])

    # Build prompt from chat history
    prompt_text = ""
    for msg in messages:
        if msg["role"] == "user":
            prompt_text += f"> {msg['content']}\n\n"
        else:
            prompt_text += f"{msg['content']}\n\n"

    def event_stream():
        for token in llm(prompt_text, stream=True, max_tokens=1024, stop=["</s>"]):
            yield token["choices"][0]["text"]

    return StreamingResponse(event_stream(), media_type="text/plain")
