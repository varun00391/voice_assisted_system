function MicrophoneIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

export function formatSeconds(total) {
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function VoiceButton({ isRecording, disabled, onStart, onStop }) {
  return (
    <button
      type="button"
      aria-label={isRecording ? "Stop recording" : "Start recording"}
      title={isRecording ? "Stop recording" : "Speak your question"}
      disabled={disabled && !isRecording}
      onClick={isRecording ? onStop : onStart}
      className={[
        "flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white shadow-md transition",
        "focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-300",
        isRecording ? "animate-pulse bg-red-500 hover:bg-red-600" : "bg-indigo-600 hover:bg-indigo-700",
        "disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none",
      ].join(" ")}
    >
      {isRecording ? <StopIcon /> : <MicrophoneIcon />}
    </button>
  );
}
