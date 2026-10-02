import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")


def sanitize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _CONTROL_CHARS.sub("", value)
    return _EXCESS_NEWLINES.sub("\n\n", value).strip()
