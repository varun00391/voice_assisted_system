import { useEffect, useRef } from "react";

import Message from "../Message/Message.jsx";

export default function ChatWindow({ messages }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (!messages.length) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center text-slate-500">
        <p className="text-lg font-medium text-slate-700">Ask anything by voice</p>
        <p className="mt-2 max-w-md text-sm">
          Pick an answer mode, tap the microphone and speak your question. Answers appear here as text.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-3 py-6 md:px-6" aria-live="polite">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
