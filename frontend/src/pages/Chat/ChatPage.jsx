import { useCallback, useEffect, useRef, useState } from "react";

import ChatWindow from "../../components/ChatWindow/ChatWindow.jsx";
import ConversationList from "../../components/ConversationList/ConversationList.jsx";
import ModeSelector from "../../components/ModeSelector/ModeSelector.jsx";
import ProviderSelector from "../../components/ProviderSelector/ProviderSelector.jsx";
import VoiceButton, { formatSeconds } from "../../components/VoiceButton/VoiceButton.jsx";
import { useVoiceRecorder } from "../../hooks/useVoiceRecorder.js";
import { api } from "../../services/api.js";
import { preferences } from "../../services/preferences.js";

let localIdCounter = 0;
const localId = () => `local-${++localIdCounter}`;

const TRANSCRIBING = "Transcribing…";
const GENERATING = "Generating answer…";

export default function ChatPage({
  modes,
  mode,
  onModeChange,
  providers,
  provider,
  onProviderChange,
  onAnswered,
  maxRecordingSeconds,
}) {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busyLabel, setBusyLabel] = useState(null);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState("");

  const activeIdRef = useRef(null);
  // Incremented whenever the visible conversation changes so late responses don't land in the wrong view.
  const viewRef = useRef(0);

  const setActive = (id) => {
    activeIdRef.current = id;
    setActiveId(id);
  };

  const patchMessage = (id, changes) =>
    setMessages((current) => current.map((message) => (message.id === id ? { ...message, ...changes } : message)));

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } catch (listError) {
      setError(listError.message);
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  async function ask(question, view) {
    const assistantId = localId();
    setMessages((current) => [
      ...current,
      { id: assistantId, role: "assistant", status: "pending", pendingLabel: GENERATING },
    ]);
    setBusyLabel(GENERATING);
    try {
      const response = await api.chat({
        conversationId: activeIdRef.current,
        message: question,
        mode,
        provider,
        customInstructions: mode === "custom" ? preferences.getCustomInstructions() : null,
      });
      if (view !== viewRef.current) return;
      patchMessage(assistantId, {
        status: "done",
        content: response.answer,
        provider: response.provider,
        fallbackUsed: response.fallback_used,
        truncated: response.truncated,
      });
      setActive(response.conversation_id);
    } catch (chatError) {
      if (view === viewRef.current) patchMessage(assistantId, { status: "error", content: chatError.message });
    } finally {
      if (view === viewRef.current) setBusyLabel(null);
      refreshConversations();
      onAnswered?.();
    }
  }

  async function handleRecording(blob) {
    const view = viewRef.current;
    const userMessageId = localId();
    setError(null);
    setMessages((current) => [
      ...current,
      { id: userMessageId, role: "user", status: "pending", pendingLabel: TRANSCRIBING },
    ]);
    setBusyLabel(TRANSCRIBING);

    let transcript;
    try {
      ({ text: transcript } = await api.transcribe(blob));
    } catch (transcribeError) {
      if (view === viewRef.current) {
        setMessages((current) => current.filter((message) => message.id !== userMessageId));
        setError(transcribeError.message);
        setBusyLabel(null);
      }
      return;
    }
    if (view !== viewRef.current) return;

    patchMessage(userMessageId, { status: "done", content: transcript });
    await ask(transcript, view);
  }

  const recorder = useVoiceRecorder({
    maxDurationSeconds: maxRecordingSeconds,
    onRecordingComplete: handleRecording,
  });

  async function handleSubmitText(event) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || busyLabel) return;
    setDraft("");
    setError(null);
    setMessages((current) => [...current, { id: localId(), role: "user", status: "done", content: question }]);
    await ask(question, viewRef.current);
  }

  function startNewConversation() {
    viewRef.current += 1;
    setActive(null);
    setMessages([]);
    setBusyLabel(null);
    setError(null);
  }

  async function selectConversation(conversationId) {
    viewRef.current += 1;
    const view = viewRef.current;
    setActive(conversationId);
    setMessages([]);
    setBusyLabel(null);
    setError(null);
    try {
      const detail = await api.getConversation(conversationId);
      if (view !== viewRef.current) return;
      setMessages(
        detail.messages.map((message) => ({
          id: message.message_id,
          role: message.role,
          content: message.content,
          provider: message.provider,
          status: "done",
        })),
      );
    } catch (loadError) {
      if (view === viewRef.current) setError(loadError.message);
    }
  }

  async function deleteConversation(conversationId) {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await api.deleteConversation(conversationId);
      if (activeIdRef.current === conversationId) startNewConversation();
      await refreshConversations();
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  const busy = Boolean(busyLabel) || recorder.status === "requesting";
  const displayedError = recorder.error || error;

  return (
    <div className="flex h-full min-h-0">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={startNewConversation}
        onDelete={deleteConversation}
      />

      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-2">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <ModeSelector modes={modes} value={mode} onChange={onModeChange} disabled={recorder.isRecording} />
            <ProviderSelector
              providers={providers}
              value={provider}
              onChange={onProviderChange}
              disabled={recorder.isRecording}
            />
          </div>
          <button
            type="button"
            onClick={startNewConversation}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 md:hidden"
          >
            New
          </button>
        </div>

        <ChatWindow messages={messages} />

        <div className="border-t border-slate-200 bg-white px-3 pt-3 pb-2 md:px-6">
          {displayedError && (
            <p role="alert" className="mx-auto mb-3 max-w-6xl rounded-lg bg-red-50 px-3 py-2 text-center text-sm text-red-700">
              {displayedError}
            </p>
          )}
          <div className="mx-auto flex max-w-6xl items-center gap-3">
            <VoiceButton
              isRecording={recorder.isRecording}
              disabled={busy}
              onStart={recorder.start}
              onStop={recorder.stop}
            />
            <form onSubmit={handleSubmitText} className="flex flex-1 gap-2">
              <input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Tap the mic and speak, or type a question…"
                aria-label="Type a question"
                maxLength={4000}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <button
                type="submit"
                disabled={busy || recorder.isRecording || !draft.trim()}
                className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
          <p className="mx-auto mt-1.5 min-h-4 max-w-6xl pl-[3.75rem] text-xs text-slate-500" aria-live="polite">
            {recorder.isRecording
              ? `Listening… ${formatSeconds(recorder.elapsedSeconds)} / ${formatSeconds(maxRecordingSeconds)}, tap to stop`
              : busyLabel}
          </p>
        </div>
      </section>
    </div>
  );
}
