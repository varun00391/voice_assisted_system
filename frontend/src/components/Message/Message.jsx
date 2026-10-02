import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { normalizeMarkdown } from "../../services/markdown.js";
import { providerLabel } from "../../services/providers.js";

// Single `$` is left as text so prices like "$5 and $10" are not parsed as math.
const remarkPlugins = [remarkGfm, remarkBreaks, [remarkMath, { singleDollarTextMath: false }]];
const rehypePlugins = [[rehypeKatex, { throwOnError: false, strict: "ignore" }]];

const markdownComponents = {
  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
  table: ({ node: _node, ...props }) => (
    <div className="my-4 overflow-x-auto">
      <table {...props} className="my-0" />
    </div>
  ),
};

function PendingIndicator({ label }) {
  return (
    <span className="inline-flex items-center gap-2 text-slate-500">
      <span className="flex gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
      </span>
      {label}
    </span>
  );
}

function bubbleStyle(isUser, status) {
  if (status === "error") return "border border-red-200 bg-red-50 text-red-700";
  if (isUser) return "bg-indigo-600 text-white";
  return "border border-slate-200 bg-white text-slate-800";
}

export default function Message({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={isUser ? "max-w-[85%] md:max-w-[75%]" : "w-full min-w-0"}>
        <div className={`mb-1 text-xs font-medium text-slate-500 ${isUser ? "text-right" : ""}`}>
          {isUser ? "You" : "AI"}
        </div>
        <div
          className={`rounded-2xl px-4 py-3 shadow-sm [overflow-wrap:anywhere] md:px-5 ${bubbleStyle(isUser, message.status)}`}
        >
          {message.status === "pending" ? (
            <PendingIndicator label={message.pendingLabel} />
          ) : isUser || message.status === "error" ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-slate max-w-none prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-code:before:content-none prose-code:after:content-none">
              <ReactMarkdown
                remarkPlugins={remarkPlugins}
                rehypePlugins={rehypePlugins}
                components={markdownComponents}
              >
                {normalizeMarkdown(message.content)}
              </ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && message.status === "done" && message.truncated && (
          <div className="mt-1 text-xs text-amber-700">
            This answer reached the maximum length and may be incomplete. Ask “continue” for the rest.
          </div>
        )}
        {!isUser && message.status === "done" && message.provider && (
          <div className="mt-1 text-xs text-slate-400">
            Answered by {providerLabel(message.provider)}
            {message.fallbackUsed && " (fallback: preferred provider was unavailable)"}
          </div>
        )}
      </div>
    </div>
  );
}
