import { render, screen } from "@testing-library/react";

import Message from "./Message.jsx";

describe("Message", () => {
  it("renders assistant answers as markdown", () => {
    render(<Message message={{ id: "1", role: "assistant", status: "done", content: "**RAG** steps:\n\n1. Chunking" }} />);

    expect(screen.getByText("RAG").tagName).toBe("STRONG");
    expect(screen.getByRole("listitem")).toHaveTextContent("Chunking");
  });

  it("renders user transcripts as plain text", () => {
    render(<Message message={{ id: "2", role: "user", status: "done", content: "**not bold**" }} />);

    expect(screen.getByText("**not bold**")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
  });

  it("shows which provider answered and whether fallback was used", () => {
    render(
      <Message
        message={{ id: "4", role: "assistant", status: "done", content: "hi", provider: "euron", fallbackUsed: true }}
      />,
    );

    expect(screen.getByText(/Answered by Euron/)).toHaveTextContent("fallback");
  });

  it("renders tables, math, single line breaks and hides reasoning", () => {
    const content = "<think>internal</think>Line one\nLine two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\nArea: \\(\\pi r^2\\)";
    const { container } = render(<Message message={{ id: "5", role: "assistant", status: "done", content }} />);

    expect(screen.queryByText(/internal/)).not.toBeInTheDocument();
    expect(container.querySelector("br")).not.toBeNull();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(container.querySelector(".katex")).not.toBeNull();
  });

  it("warns when an answer was truncated", () => {
    render(<Message message={{ id: "6", role: "assistant", status: "done", content: "partial", truncated: true }} />);
    expect(screen.getByText(/may be incomplete/)).toBeInTheDocument();
  });

  it("shows a pending label while waiting", () => {
    render(<Message message={{ id: "3", role: "assistant", status: "pending", pendingLabel: "Generating answer…" }} />);

    expect(screen.getByText("Generating answer…")).toBeInTheDocument();
  });
});
