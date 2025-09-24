from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from llama_cpp import Llama
import os
import json
import uuid
from datetime import datetime

# -------------------------------
# Model Paths
# -------------------------------
MODEL_PATHS = {
    "qwen": os.path.expanduser(
        "~/models/llm/qwen/qwen2.5-7b-instruct-q4_0-00001-of-00002.gguf"
    ),
    "codeLLama": os.path.expanduser(
        "/Users/mohitkatiyar/Models/llm/codellama/codellama-7b-instruct.Q6_K.gguf"
    ),
}

# Keep cached models so we don't reload repeatedly
loaded_models = {}

def get_model(model_name: str) -> Llama:
    """Return a cached model instance, load if not already loaded."""
    if model_name not in MODEL_PATHS:
        raise ValueError(f"Unknown model: {model_name}")

    if model_name not in loaded_models:
        print(f"🔹 Loading {model_name} model...")
        loaded_models[model_name] = Llama(
            model_path=MODEL_PATHS[model_name],
            n_ctx=8192,
            n_threads=8,
            n_gpu_layers=-1   # ✅ offload all layers to GPU (Metal)
        )
    return loaded_models[model_name]

# -------------------------------
# Chat Storage
# -------------------------------
CHAT_DIR = os.path.expanduser("~/saved_chats")
os.makedirs(CHAT_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(CHAT_DIR, "chat_history.json")

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

# -------------------------------
# FastAPI Setup
# -------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/stream")
async def stream(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    model_name = data.get("model", "qwen")

    # Save history
    save_history(messages)

    # ✅ Build model-specific prompt
    prompt_text = build_prompt(messages, model_name)

    llm = get_model(model_name)

    def event_stream():
        buffer = ""
        for token in llm(
            prompt_text,
            stream=True,
            max_tokens=4096,
            stop=None
        ):
            text = token["choices"][0]["text"]
            buffer += text
            if len(buffer) > 0:
                yield buffer
                buffer = ""
        if buffer:
            yield buffer

    return StreamingResponse(event_stream(), media_type="text/plain")

# -------------------------------
# Session History
# -------------------------------
@app.get("/history")
async def get_history():
    return JSONResponse(load_history())

# -------------------------------
# Save Chat
# -------------------------------
@app.post("/save_chat")
async def save_chat(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    title = data.get("title") or (messages[0]["content"][:30] if messages else "Untitled")

    filename = data.get("filename")
    if not filename:
        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{uuid.uuid4().hex[:6]}.json"

    filepath = os.path.join(CHAT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump({"title": title, "messages": messages}, f)

    return {"status": "ok", "filename": filename}

# -------------------------------
# List Saved Chats
# -------------------------------
@app.get("/list_chats")
async def list_chats():
    files = []
    for fname in os.listdir(CHAT_DIR):
        if fname.endswith(".json") and fname != "chat_history.json":
            with open(os.path.join(CHAT_DIR, fname)) as f:
                data = json.load(f)
            files.append({"filename": fname, "title": data.get("title", fname)})
    return files

# -------------------------------
# Load Specific Chat
# -------------------------------
@app.get("/load_chat/{filename}")
async def load_chat(filename: str):
    filepath = os.path.join(CHAT_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse({"error": "not found"}, status_code=404)
    with open(filepath) as f:
        return json.load(f)

# -------------------------------
# Delete Chat
# -------------------------------
@app.delete("/delete_chat/{filename}")
async def delete_chat(filename: str):
    filepath = os.path.join(CHAT_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return JSONResponse({"status": "success", "message": f"{filename} deleted"})
    else:
        return JSONResponse({"status": "error", "message": f"{filename} not found"}, status_code=404)

# -------------------------------
# Prompt Builder
# -------------------------------
def build_prompt(messages, model_name: str) -> str:
    if model_name == "codeLLama":
        # CodeLlama-Instruct format
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"<s>[INST] {msg['content']} [/INST]"
            elif msg["role"] == "assistant":
                prompt += f" {msg['content']} </s>"
        return prompt
    else:
        # Qwen (or fallback) format
        system_prompt = (
            "You are a helpful coding assistant. Always respond in English unless explicitly asked otherwise. "
            "ONLY RESPOND TO THE QUESTION."
        )
        prompt = system_prompt + "\n\n"
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"> {msg['content']}\n\n"
            else:
                prompt += f"{msg['content']}\n\n"
        return prompt
