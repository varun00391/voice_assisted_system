export default function ConversationList({ conversations, activeId, onSelect, onNew, onDelete }) {
  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-white md:flex xl:w-64">
      <div className="p-3">
        <button
          type="button"
          onClick={onNew}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          + New conversation
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-3" aria-label="Conversations">
        {!conversations.length && <p className="px-2 py-4 text-sm text-slate-400">No conversations yet.</p>}
        <ul className="space-y-1">
          {conversations.map((conversation) => {
            const active = conversation.conversation_id === activeId;
            return (
              <li key={conversation.conversation_id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(conversation.conversation_id)}
                  className={`w-full truncate rounded-lg px-3 py-2 pr-8 text-left text-sm ${
                    active ? "bg-indigo-50 font-medium text-indigo-700" : "text-slate-700 hover:bg-slate-100"
                  }`}
                  title={conversation.title}
                >
                  {conversation.title}
                </button>
                <button
                  type="button"
                  aria-label={`Delete conversation ${conversation.title}`}
                  onClick={() => onDelete(conversation.conversation_id)}
                  className="absolute top-1/2 right-2 -translate-y-1/2 rounded px-1 text-slate-400 opacity-0 group-hover:opacity-100 hover:text-red-600 focus:opacity-100"
                >
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
