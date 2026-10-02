import { normalizeMarkdown } from "./markdown.js";

describe("normalizeMarkdown", () => {
  it("removes leaked reasoning blocks", () => {
    expect(normalizeMarkdown("<think>planning...</think>\n\n**Answer**")).toBe("**Answer**");
    expect(normalizeMarkdown("reasoning</think>Answer")).toBe("Answer");
    expect(normalizeMarkdown("Answer<think>unfinished")).toBe("Answer");
  });

  it("converts LaTeX delimiters to remark-math syntax", () => {
    expect(normalizeMarkdown("Area is \\(\\pi r^2\\).")).toBe("Area is $$\\pi r^2$$.");
    expect(normalizeMarkdown("\\[\nE = mc^2\n\\]")).toBe("$$\nE = mc^2\n$$");
  });

  it("leaves code untouched", () => {
    const code = "```python\nprint('\\(not math\\)')\n```";
    expect(normalizeMarkdown(code)).toBe(code);
    expect(normalizeMarkdown("Use `\\(x\\)` literally")).toBe("Use `\\(x\\)` literally");
  });
});
