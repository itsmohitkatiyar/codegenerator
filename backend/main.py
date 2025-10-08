from fastapi import FastAPI, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from llama_cpp import Llama
import os
import json
import uuid
from datetime import datetime
from projects_context import set_project, get_project_context


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
    """Return a fresh model instance on each switch."""
    if model_name not in MODEL_PATHS:
        raise ValueError(f"Unknown model: {model_name}")

    print(f"🔹 Loading {model_name} model...")
    return Llama(
        model_path=MODEL_PATHS[model_name],
        n_ctx=8192,
        n_threads=8,
        n_gpu_layers=-1
    )

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
    project_path = data.get("project_path")  # Selected folder path

    # ✅ Build prompt with project context
    prompt_text = build_prompt(messages, model_name, project_path)

    # Optional: save chat history
    save_history(messages)

    llm = get_model(model_name)

    def event_stream():
        buffer = ""
        for token in llm(
            prompt_text,
            stream=True,
            max_tokens=4096,
            stop=None
        ):
            # Extract token text
            text = token.get("choices", [{}])[0].get("text", "")
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
def build_prompt(messages, model_name: str, project_path: str = None) -> str:
    project_context = get_project_context(project_path) if project_path else ""

    print(f"Project Context is {project_context}")

    if model_name == "codeLLama":
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"<s>[INST] {msg['content']} [/INST]"
            elif msg["role"] == "assistant":
                prompt += f" {msg['content']} </s>"
        if project_context:
            prompt += f"\n\n--- Project Context ---\n{project_context}"
        return prompt

    else:
        system_prompt = (
            "You are a helpful coding assistant. Always output code in Markdown fenced blocks with proper language tags. "
            "Always respond in English unless explicitly asked otherwise. ONLY RESPOND TO THE QUESTION."
        )
        if project_context:
            system_prompt += f"\n\n--- Project Context ---\n{project_context}"

        prompt_text = system_prompt + "\n\n"
        for msg in messages:
            if msg["role"] == "user":
                prompt_text += f"> {msg['content']}\n\n"
            else:
                prompt_text += f"{msg['content']}\n\n"

        return prompt_text




@app.post("/set_project")
async def set_project(request: Request):
    global PROJECT_PATH
    data = await request.json()
    path = data.get("path", "").strip()

    if path and os.path.isdir(path):
        PROJECT_PATH = path
        return {"status": "ok"}
    else:
        PROJECT_PATH = None
        return {"status": "ok", "message": "No project selected. Agent will be project-agnostic."}


@app.get("/list_project_dirs")
async def list_project_dirs(path: str = None):
    """List subdirectories of the given path. Default: home directory."""
    if not path:
        path = os.path.expanduser("~")
    if not os.path.isdir(path):
        return JSONResponse({"error": "Invalid directory"}, status_code=400)

    dirs = []
    files = []
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            dirs.append(entry)
        else:
            files.append(entry)
    return {"path": path, "dirs": dirs, "files": files}

@app.get("/home_dir")
def get_home_dir():
    return {"home": os.path.expanduser("~")}

@app.get("/list_dir")
def list_dir(path: str = Query("/")):
    try:
        if not os.path.exists(path) or not os.path.isdir(path):
            return JSONResponse(status_code=404, content={"error": "Directory not found"})
        contents = os.listdir(path)
        # Optionally, sort: folders first, then files
        folders = sorted([c for c in contents if os.path.isdir(os.path.join(path, c))])
        files = sorted([c for c in contents if os.path.isfile(os.path.join(path, c))])
        return {"contents": folders + files}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})