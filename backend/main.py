from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from llama_cpp import Llama
import os
import json
import uuid
from datetime import datetime

MODEL_PATH = os.path.expanduser(
    "~/models/llm/qwen/qwen2.5-7b-instruct-q4_0-00001-of-00002.gguf"
)

HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(messages):
    with open(HISTORY_FILE, "w") as f:
        json.dump(messages, f)

print("🔹 Loading Qwen model on Apple Silicon GPU...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=8192,
    n_threads=8,
    n_gpu_layers=-1   # ✅ offload all layers to GPU (Metal)
)

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
    Stream Qwen responses token by token in small batches.
    Expects JSON payload: { "messages": [ {"role": "user"/"assistant", "content": "..."} ] }
    """
    data = await request.json()
    messages = data.get("messages", [])

    # Save history after each request
    save_history(messages)

    # Build prompt from chat history
    prompt_text = ""
    for msg in messages:
        if msg["role"] == "user":
            prompt_text += f"> {msg['content']}\n\n"
        else:
            prompt_text += f"{msg['content']}\n\n"

    def event_stream():
        buffer = ""
        for token in llm(
            prompt_text,
            stream=True,
            max_tokens=4096,  # increase for long code
            stop=None         # avoid premature stopping
        ):
            text = token["choices"][0]["text"]
            buffer += text

            # Send output in chunks (reduce front-end re-rendering)
            if len(buffer) > 0:  # send every ~50 characters
                yield buffer
                buffer = ""

        # Send any remaining text
        if buffer:
            yield buffer

    return StreamingResponse(event_stream(), media_type="text/plain")

@app.get("/history")
async def get_history():
    """Return saved chat history."""
    return JSONResponse(load_history())

CHAT_DIR = "chats"
os.makedirs(CHAT_DIR, exist_ok=True)

@app.post("/save_chat")
async def save_chat(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    title = data.get("title") or (messages[0]["content"][:30] if messages else "Untitled")

    filename = f"{datetime.now().strftime('%Y-%m-%d')}_{uuid.uuid4().hex[:6]}.json"
    filepath = os.path.join(CHAT_DIR, filename)

    with open(filepath, "w") as f:
        json.dump({"title": title, "messages": messages}, f)

    return {"status": "ok", "filename": filename}

@app.get("/list_chats")
async def list_chats():
    files = []
    for fname in os.listdir(CHAT_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(CHAT_DIR, fname)) as f:
                data = json.load(f)
            files.append({"filename": fname, "title": data.get("title", fname)})
    return files

@app.get("/load_chat/{filename}")
async def load_chat(filename: str):
    filepath = os.path.join(CHAT_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": "not found"}
    with open(filepath) as f:
        return json.load(f)
