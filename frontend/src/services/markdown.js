const FENCED_CODE = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$))/g;
const INLINE_CODE = /(`[^`\n]*`)/g;

function stripReasoning(text) {
  let result = text.replace(/<think>[\s\S]*?<\/think>/gi, "");
  const lastClose = result.toLowerCase().lastIndexOf("</think>");
  if (lastClose !== -1) result = result.slice(lastClose + "</think>".length);
  return result.replace(/<think>[\s\S]*$/i, "");
}

function convertMathDelimiters(text) {
  return text
    .replace(/\\\[([\s\S]+?)\\\]/g, (_match, body) => `\n$$\n${body.trim()}\n$$\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_match, body) => `$$${body.trim()}$$`);
}

function outsideCode(text, transform, pattern) {
  return text
    .split(pattern)
    .map((part, index) => (index % 2 === 1 ? part : transform(part)))
    .join("");
}

/**
 * Prepares LLM output for react-markdown: drops leaked `<think>` reasoning and converts
 * LaTeX `\[ \]` / `\( \)` delimiters (which remark-math does not parse) to `$$`, leaving code untouched.
 */
export function normalizeMarkdown(text) {
  if (!text) return "";
  const withoutReasoning = stripReasoning(text);
  return outsideCode(
    withoutReasoning,
    (prose) => outsideCode(prose, convertMathDelimiters, INLINE_CODE),
    FENCED_CODE,
  ).trim();
}
