import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { v4 as uuidv4 } from "uuid";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [savedChats, setSavedChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(null); // filename to confirm deletion

  const abortRef = useRef(null);
  const outputRef = useRef(null);

  const backendBase = "http://127.0.0.1:8501";
  document.title = "Code Generator";

  // Load saved chats on mount
  useEffect(() => {
    fetch(`${backendBase}/list_chats`)
      .then((res) => res.json())
      .then(setSavedChats)
      .catch(() => console.log("⚠️ Could not load saved chats"));
  }, []);

  const loadChat = async (filename) => {
  const res = await fetch(`${backendBase}/load_chat/${filename}`);
  const data = await res.json();
  setChatHistory(data.messages || []);
  setActiveChat(filename); // this ensures next save updates this chat
  setDeleteConfirm(null);
};


  const saveChat = async () => {
  // Use existing activeChat filename if it exists, otherwise generate a new one
  let filename = activeChat;
  if (!filename) {
    filename = `${new Date().toISOString().split("T")[0]}_${uuidv4().slice(0, 6)}.json`;
  }

  await fetch(`${backendBase}/save_chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: chatHistory[0]?.content || "Untitled",
      messages: chatHistory,
      filename, // pass the filename to backend
    }),
  });

  // Refresh saved chats from backend
  const updated = await fetch(`${backendBase}/list_chats`).then((res) => res.json());
  setSavedChats(updated);

  // Keep this chat as active
  setActiveChat(filename);
};



  const deleteChat = async (filename) => {
    const res = await fetch(`${backendBase}/delete_chat/${filename}`, {
      method: "DELETE",
    });
    if (res.ok) {
      setSavedChats((prev) => prev.filter((c) => c.filename !== filename));
      if (activeChat === filename) {
        setChatHistory([]);
        setActiveChat(null);
      }
    }
    setDeleteConfirm(null);
  };



  // Markdown component with copy button inside code blocks
  const MarkdownWithCopy = ({ content }) => (
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
              onClick={() => navigator.clipboard.writeText(props.children[0].props.children)}
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

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        handleCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleCancel]);

  return (
    <div className="w-screen h-screen flex bg-slate-900 text-white">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 p-4 overflow-y-auto flex-shrink-0 flex flex-col">
        <h2 className="text-xl font-semibold mb-4">📂 Saved Chats</h2>
        <button
          className="w-full mb-4 px-3 py-2 rounded-full bg-slate-700 hover:bg-slate-600 text-white"
          onClick={() => {
            setChatHistory([]);
            setActiveChat(null);
            setDeleteConfirm(null);
          }}
        >
          + New Chat
        </button>

        {savedChats.length === 0 && <p className="text-slate-400">No saved chats yet.</p>}
        {savedChats.map((chat) => (
          <div key={chat.filename} className="relative p-2 mb-2 rounded cursor-pointer hover:bg-slate-700 flex justify-between items-center">
            <div onClick={() => loadChat(chat.filename)} className={`flex-1 ${deleteConfirm === chat.filename ? "opacity-50" : ""}`}>
              {chat.title}
            </div>
            {deleteConfirm === chat.filename ? (
              <div className="absolute right-0 top-0 flex gap-2">
                <button
                  onClick={() => deleteChat(chat.filename)}
                  className="px-2 py-1 text-green-500 hover:text-green-400 text-xl"
                  title="Yes"
                >
                  ✔
                </button>
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-2 py-1 text-red-500 hover:text-red-400 text-xl"
                  title="Cancel"
                >
                  ✖
                </button>
              </div>
            ) : (
              <button
                onClick={() => setDeleteConfirm(chat.filename)}
                className="px-2 py-2 text-red-500 hover:text-red-400"
              >
                🗑
              </button>
            )}
          </div>
        ))}

        <button
          onClick={saveChat}
          disabled={chatHistory.length === 0}
          className="w-full mt-auto px-3 py-2 rounded-full disabled:opacity-50 bg-slate-700 hover:bg-slate-600 text-white"
        >
          Save Current Chat
        </button>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col items-center p-4 relative">
        <div
          ref={outputRef}
          className="w-[calc(100%-16rem)] max-h-[calc(100vh-80px)] overflow-auto p-6 rounded-lg bg-black text-green-300 shadow-lg mb-4 break-words whitespace-pre-wrap"
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

        {/* Bottom-fixed prompt bar */}
        <div className="fixed bottom-0 left-64 w-[calc(100%-16rem)] bg-slate-900 p-4 flex items-end shadow-inner z-50 rounded-md">
          <form onSubmit={handleSubmit} className="w-full flex items-center gap-2">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Send a message..."
              rows={1}
              className="flex-1 p-3 bg-slate-800 text-white rounded-full placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 resize-none"
            />

            {streaming && (
              <button
                type="button"
                onClick={handleCancel}
                className="w-8 h-8 flex items-center justify-center bg-black hover:bg-gray-800 rounded-md"
                title="Stop Generation"
              >
                X
              </button>
            )}

            <button
              type="submit"
              disabled={streaming || !prompt.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-full disabled:opacity-50"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 transform -rotate-45"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
