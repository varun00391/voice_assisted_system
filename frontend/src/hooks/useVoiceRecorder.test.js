import { act, renderHook } from "@testing-library/react";

import { MICROPHONE_PERMISSION_ERROR, useVoiceRecorder } from "./useVoiceRecorder.js";

class FakeMediaRecorder {
  static isTypeSupported = () => true;

  constructor(stream, options) {
    this.stream = stream;
    this.mimeType = options?.mimeType || "audio/webm";
    this.state = "inactive";
  }

  start() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

function stubMicrophone(getUserMedia) {
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
  Object.defineProperty(navigator, "mediaDevices", { value: { getUserMedia }, configurable: true });
}

describe("useVoiceRecorder", () => {
  it("explains when microphone permission is denied", async () => {
    stubMicrophone(vi.fn().mockRejectedValue(new DOMException("denied", "NotAllowedError")));
    const { result } = renderHook(() => useVoiceRecorder({ onRecordingComplete: vi.fn() }));

    await act(() => result.current.start());

    expect(result.current.error).toBe(MICROPHONE_PERMISSION_ERROR);
    expect(result.current.status).toBe("idle");
  });

  it("records and hands the audio blob to the callback on stop", async () => {
    const track = { stop: vi.fn() };
    stubMicrophone(vi.fn().mockResolvedValue({ getTracks: () => [track] }));
    const onRecordingComplete = vi.fn();
    const { result } = renderHook(() => useVoiceRecorder({ onRecordingComplete }));

    await act(() => result.current.start());
    expect(result.current.isRecording).toBe(true);

    act(() => result.current.stop());

    expect(result.current.status).toBe("idle");
    expect(track.stop).toHaveBeenCalled();
    expect(onRecordingComplete).toHaveBeenCalledWith(expect.any(Blob));
  });
});
