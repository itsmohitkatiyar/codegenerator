export default function ChatBox({ result }) {
  return (
    <pre
      className="w-full max-h-[60vh] overflow-auto rounded-lg p-4 bg-black text-green-300 whitespace-pre-wrap break-words"
    >
      {result || "No output yet. Click Generate to start streaming."}
    </pre>
  );
}
