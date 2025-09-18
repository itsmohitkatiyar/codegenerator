# 💻 Mohit's Personal Code Assistant

![GitHub Repo Size](https://img.shields.io/github/repo-size/your-username/qwen-code-generator)
![Python Version](https://img.shields.io/badge/python-3.11+-blue)
![Node Version](https://img.shields.io/badge/node-18+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

A modern developer assistant that generates code using the Qwen LLM **locally**.  
Built with **React + Tailwind CSS** for a sleek frontend and **FastAPI** for streaming responses from the Qwen model.  

Supports **real-time streaming**, saving generated code, and copying results to clipboard.

---

## Features

- Interactive prompt box for code generation  
- Streaming output token-by-token from Qwen  
- Save generated code to local files  
- Copy generated code to clipboard  
- Modern, responsive UI  
- Fully local — runs Qwen from GGUF files  

---

## Project Structure

```
.
├── backend/
│   └── main.py               # FastAPI backend
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # React main component
│   │   ├── main.jsx          # React entry point
│   │   ├── index.css         # Tailwind base CSS
│   │   └── components/
│   │       └── ChatBox.jsx   # Streaming output box
│   ├── package.json
│   ├── vite.config.js
│   └── node_modules/
└── README.md
```

---

## Prerequisites

- Node.js ≥ 18  
- Python ≥ 3.11  
- pip  
- Qwen `.gguf` model files  

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/code-generator.git
cd CodeGenerator
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv          # optional but recommended
source .venv/bin/activate     # macOS/Linux
pip install --upgrade pip
pip install fastapi uvicorn llama-cpp-python
```

> Edit `main.py` and set `MODEL_PATH` to your local Qwen `.gguf` files.

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

---

## Running the Project

### Start the Backend

```bash
cd backend
python main.py
```

- Runs FastAPI on port **8501** by default.
- Endpoints:
  - `GET /stream?prompt=...` → streams code from Qwen
  - `POST /write/{filename}` → saves code locally

### Start the Frontend

```bash
cd frontend
npm run dev
```

- Opens React + Tailwind UI (default `http://localhost:5173`)  
- Ensure `backendBase` in `App.jsx` points to `http://127.0.0.1:8501`

---

## Usage

1. Open the frontend in your browser.  
2. Type a prompt describing the code to generate.  
3. Click **Generate** → code will stream in real-time.  
4. Use **Save to file** or **Copy** buttons for convenience.

---

## Customizing Ports

- **Backend (FastAPI)**:  
  ```bash
  uvicorn main:app --reload --port 8501
  ```  
  Or change `port` in `main.py`.

- **Frontend (Vite/React)**: edit `vite.config.js`:
  ```js
  server: { port: 8501 }
  ```  

- Update `backendBase` in `App.jsx` to match backend port.

---

## Dependencies

### Backend

- `fastapi`  
- `uvicorn`  
- `llama_cpp`  

### Frontend

- `react`  
- `react-dom`  
- `vite`  
- `tailwindcss`  
- `postcss`  
- `autoprefixer`  

---

## License

MIT License. Feel free to fork and modify.

