import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css"; // or any style you like
import { useState, useRef } from "react";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState("");
  const [showOutput, setShowOutput] = useState(false);
  const abortRef = useRef(null);
  const outputRef = useRef(null);

  const backendBase = "http://127.0.0.1:8501";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setShowOutput(true);
    setResult(`> ${prompt}\n\n`); // 1️⃣ Add prompt at top
    setPrompt(""); // 2️⃣ Blank textarea
    //setResult("");
    setStatus("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(
        `${backendBase}/stream?prompt=${encodeURIComponent(prompt)}`,
        { signal: controller.signal }
      );

      if (!res.ok) {
        setStatus(`Error ${res.status}`);
        setStreaming(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        setResult((prev) => prev + decoder.decode(value, { stream: true }));

        // Scroll down as new tokens arrive
        outputRef.current?.scrollTo({
          top: outputRef.current.scrollHeight,
          behavior: "smooth",
        });
      }

      setStatus("Completed");
    } catch (err) {
      if (err.name === "AbortError") setStatus("Cancelled");
      else setStatus("Error: " + err.message);
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const handleCancel = () => {
    if (abortRef.current) abortRef.current.abort();
  };

  const handleSave = async () => {
    try {
      const res = await fetch(`${backendBase}/write/${encodeURIComponent("generated.py")}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: result }),
      });
      const j = await res.json();
      setStatus(res.ok ? j.status || "Saved" : "Save error: " + JSON.stringify(j));
    } catch (err) {
      setStatus("Save error: " + err.message);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result);
      setStatus("Copied to clipboard");
    } catch {
      setStatus("Copy failed");
    }
  };

  return (
    <div className="w-screen h-screen flex items-center justify-center bg-slate-900 p-4 flex flex-col items-center">
        <h1 className="text-3xl font-semibold text-center text-white mb-6">
            💻 Mohit's Personal Code Assistant
        </h1>
      {/* Initial centered Google-style prompt */}
      {!showOutput && (
        <div className="flex items-center justify-center w-full h-screen">
          <form onSubmit={handleSubmit} className="w-full max-w-3xl">
            <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault(); // prevent newline
                      handleSubmit(e);
                    }
                  }}
                  placeholder="Type your prompt..."
                  className="w-full p-6 text-xl rounded-full bg-slate-900 border border-white text-center text-white focus:outline-none shadow-lg resize-none"
                />
          </form>
        </div>
      )}

      {/* Full-width output and input after submit */}
      {showOutput && (
        <div className="w-full">

          <div ref={outputRef} className="mb-4 w-full max-h-[60vh] overflow-auto p-6 rounded-lg bg-black text-green-300 whitespace-pre-wrap break-words shadow-lg" > {result || "Generating..."} </div>

          <form onSubmit={handleSubmit} className="w-full mb-4">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault(); // prevent newline
                  handleSubmit(e);
                }
              }}
              placeholder="Type your prompt..."
              className="w-full p-6 text-xl rounded-full bg-slate-900 border border-slate-700 text-center text-white focus:outline-none shadow-lg resize-none"
            />
          </form>

          <div className="flex flex-wrap gap-3 items-center justify-center">
            <button
              onClick={handleCancel}
              disabled={!streaming}
              className="px-6 py-3 rounded bg-rose-600 hover:bg-rose-500 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!result}
              className="px-5 py-3 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50"
            >
              Save
            </button>
            <button
              onClick={handleCopy}
              disabled={!result}
              className="px-5 py-3 rounded bg-slate-600 hover:bg-slate-500 disabled:opacity-50"
            >
              Copy
            </button>
            <div className="mt-2 text-sm text-slate-300">Status: {status}</div>
          </div>
        </div>
      )}
    </div>
  );
}