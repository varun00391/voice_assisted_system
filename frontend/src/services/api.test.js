import { api, ApiError } from "./api.js";

function mockFetch(status, body) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api", () => {
  it("sends chat requests in the backend schema", async () => {
    const fetchMock = mockFetch(200, { answer: "hi" });

    await api.chat({ conversationId: null, message: "Hello", mode: "concise" });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/chat");
    expect(JSON.parse(options.body)).toEqual({
      conversation_id: null,
      message: "Hello",
      mode: "concise",
      provider: null,
      custom_instructions: null,
    });
  });

  it("sends the selected provider, and null for Auto", async () => {
    const fetchMock = mockFetch(200, { answer: "hi" });

    await api.chat({ message: "Hello", mode: "concise", provider: "euron" });
    await api.chat({ message: "Hello", mode: "concise", provider: "auto" });

    expect(JSON.parse(fetchMock.mock.calls[0][1].body).provider).toBe("euron");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).provider).toBeNull();
  });

  it("surfaces the backend's user-facing error message", async () => {
    mockFetch(503, { error: { code: "llm_unavailable", message: "The AI providers are temporarily unavailable." } });

    await expect(api.chat({ message: "Hello", mode: "concise" })).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      code: "llm_unavailable",
      message: "The AI providers are temporarily unavailable.",
    });
  });

  it("reports network failures clearly", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await api.getModes().catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("network_error");
  });

  it("uploads recordings as multipart form data", async () => {
    const fetchMock = mockFetch(200, { text: "Explain RAG" });

    await api.transcribe(new Blob(["audio"], { type: "audio/webm;codecs=opus" }));

    const form = fetchMock.mock.calls[0][1].body;
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("audio").name).toBe("recording.webm");
  });
});
