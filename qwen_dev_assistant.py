from fastapi import FastAPI, Request, Form, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn, os
from llama_cpp import Llama

# -------------------------
# Config
# -------------------------
MODEL_PATH = os.path.expanduser("~/models/qwen/qwen2.5-7b-instruct-q4_0-00001-of-00002.gguf")
BASE_DIR = os.path.abspath(".")  # Project folder

print("🔹 Loading Qwen model, please wait...")
llm = Llama(model_path=MODEL_PATH, n_ctx=8192, n_threads=8)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -------------------------
# Web UI
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/", response_class=HTMLResponse)
def generate(request: Request, prompt: str = Form(...)):
    output = llm(prompt, max_tokens=1024, stop=["</s>"])
    code = output["choices"][0]["text"].strip()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": code, "prompt": prompt}
    )

# -------------------------
# File Operations
# -------------------------
@app.get("/list")
def list_files():
    return {"files": os.listdir(BASE_DIR)}

@app.get("/read/{filename}")
def read_file(filename: str):
    path = os.path.join(BASE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"error": "File not found"}

@app.post("/write/{filename}")
def write_file(filename: str, content: str = Body(..., embed=True)):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": f"{filename} saved."}

# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
