import { useCallback, useEffect, useRef, useState } from "react";

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

export const MICROPHONE_PERMISSION_ERROR = "Microphone access is required to use voice input.";

function pickMimeType() {
  if (typeof MediaRecorder.isTypeSupported !== "function") return "";
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function describeMediaError(error) {
  switch (error?.name) {
    case "NotAllowedError":
    case "SecurityError":
      return MICROPHONE_PERMISSION_ERROR;
    case "NotFoundError":
    case "OverconstrainedError":
      return "No microphone was found. Please connect one and try again.";
    case "NotReadableError":
      return "The microphone is in use by another application.";
    default:
      return "Unable to start recording. Please try again.";
  }
}

/**
 * Records microphone audio with MediaRecorder.
 * `onRecordingComplete(blob)` is called after stop() or when `maxDurationSeconds` is reached.
 */
export function useVoiceRecorder({ maxDurationSeconds = 60, onRecordingComplete }) {
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const onCompleteRef = useRef(onRecordingComplete);
  const mountedRef = useRef(true);

  useEffect(() => {
    onCompleteRef.current = onRecordingComplete;
  }, [onRecordingComplete]);

  const releaseResources = useCallback(() => {
    clearInterval(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (recorderRef.current?.state === "recording") recorderRef.current.stop();
      releaseResources();
    };
  }, [releaseResources]);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Voice recording is not supported in this browser.");
      return;
    }

    setStatus("requesting");
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (mediaError) {
      if (mountedRef.current) {
        setError(describeMediaError(mediaError));
        setStatus("idle");
      }
      return;
    }
    if (!mountedRef.current) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }

    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    streamRef.current = stream;
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data?.size) chunks.push(event.data);
    };
    recorder.onstop = () => {
      releaseResources();
      recorderRef.current = null;
      if (!mountedRef.current) return;
      setStatus("idle");
      setElapsedSeconds(0);
      const blob = new Blob(chunks, { type: recorder.mimeType || mimeType || "audio/webm" });
      if (blob.size) onCompleteRef.current?.(blob);
    };

    const startedAt = Date.now();
    recorder.start();
    setStatus("recording");
    setElapsedSeconds(0);
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setElapsedSeconds(elapsed);
      if (elapsed >= maxDurationSeconds) stop();
    }, 250);
  }, [maxDurationSeconds, releaseResources, stop]);

  return { status, error, elapsedSeconds, start, stop, isRecording: status === "recording" };
}
