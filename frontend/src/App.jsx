import React, { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState("");
  const abortRef = useRef(null);
  const outputRef = useRef(null);

  const backendBase = "http://127.0.0.1:8501";

  // Markdown component with copy button inside code blocks
  const MarkdownWithCopy = ({ content }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        pre: ({ node, ...props }) => (
          <div className="relative rounded-lg shadow overflow-hidden mb-2">
            <pre className="p-4 overflow-auto bg-[#0d1117] text-white rounded-lg">
              {props.children}
            </pre>
            <button
              onClick={() =>
                navigator.clipboard.writeText(
                  props.children[0].props.children
                )
              }
              className="absolute top-2 right-2 bg-slate-700 text-white px-2 py-1 rounded text-sm hover:bg-slate-600 z-10"
            >
              Copy
            </button>
          </div>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
};



  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    const userMessage = { role: "user", content: prompt };
    const newHistory = [...chatHistory, userMessage];
    setChatHistory(newHistory);
    setPrompt("");
    setStatus("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${backendBase}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newHistory }),
        signal: controller.signal,
      });

      if (!res.ok) {
        setStatus(`Error ${res.status}`);
        setStreaming(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let assistantReply = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        assistantReply += chunk;

        setChatHistory((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [...prev.slice(0, -1), { role: "assistant", content: last.content + chunk }];
          } else {
            return [...prev, { role: "assistant", content: chunk }];
          }
        });

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

  return (
    <div className="w-screen h-screen flex flex-col items-center bg-slate-900 p-4">
      <h1 className="text-3xl font-semibold text-white mb-6">💻 Mohit's Code Assistant</h1>

      {/* Chat Output */}
      <div
        ref={outputRef}
        className="w-3/5 max-h-[60vh] overflow-auto p-6 rounded-lg bg-black text-green-300 shadow-lg mb-4"
      >
        {chatHistory.length === 0 && <p className="text-slate-400">Your chat will appear here...</p>}

        {chatHistory.map((msg, idx) => (
          <div key={idx} className="mb-4">
            <strong className="text-white">{msg.role === "user" ? "You:" : "Assistant:"}</strong>

            <div className="mt-1">
              <MarkdownWithCopy content={msg.content} />
            </div>
          </div>
        ))}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="w-3/5 mb-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Type your prompt..."
          className="w-full p-4 text-lg rounded-lg bg-slate-900 border border-white text-white focus:outline-none resize-none"
          rows={3}
        />
      </form>

      {/* Buttons */}
      <div className="flex gap-3 items-center justify-center">
        <button
          onClick={handleCancel}
          disabled={!streaming}
          className="px-6 py-3 rounded bg-rose-600 hover:bg-rose-500 disabled:opacity-50"
        >
          Cancel
        </button>
        <div className="mt-2 text-sm text-slate-300">Status: {status}</div>
      </div>
    </div>
  );
}
