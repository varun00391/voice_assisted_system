import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN = re.compile(r"<think>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</think>", re.IGNORECASE)


def strip_reasoning(text: str) -> tuple[str, bool]:
    """Remove `<think>` reasoning that reasoning models (e.g. Qwen, DeepSeek-R1) put in the content.

    Returns the answer text and whether the output stopped while still reasoning
    (an unclosed `<think>` block).
    """
    text = _THINK_BLOCK.sub("", text)

    # Some chat templates open the block in the prompt, so the output only contains the closing tag.
    closes = list(_THINK_CLOSE.finditer(text))
    if closes:
        text = text[closes[-1].end():]

    opening = _THINK_OPEN.search(text)
    if opening:
        return text[: opening.start()], True
    return text, False
