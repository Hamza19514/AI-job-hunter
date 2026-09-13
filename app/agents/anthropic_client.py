import json
import re

import anthropic
from flask import current_app


def get_client():
    api_key = current_app.config["ANTHROPIC_API_KEY"]
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file before running the agents."
        )
    return anthropic.Anthropic(api_key=api_key)


def extract_text(message) -> str:
    """Concatenates all text blocks of an Anthropic message response, in order."""
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts)


_JSON_BLOCK_RE = re.compile(r"<RESULTS_JSON>(.*?)</RESULTS_JSON>", re.DOTALL)


def _escape_bare_control_chars(raw: str) -> str:
    """Models occasionally emit a literal newline/tab inside a JSON string
    value instead of an escaped \\n/\\t, which breaks strict JSON parsing.
    Walks the text and escapes control characters that fall inside a
    string literal (tracking quote/escape state), leaving structural
    whitespace between tokens untouched."""
    out = []
    in_string = False
    escaped = False
    for ch in raw:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
            elif ch == "\\":
                out.append(ch)
                escaped = True
            elif ch == '"':
                out.append(ch)
                in_string = False
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\t":
                out.append("\\t")
            elif ch == "\r":
                out.append("\\r")
            else:
                out.append(ch)
        else:
            if ch == '"':
                in_string = True
            out.append(ch)
    return "".join(out)


def extract_json_payload(text: str):
    """Pulls the JSON object out of a model response wrapped in
    <RESULTS_JSON>...</RESULTS_JSON> tags, falling back to the largest
    {...} block if the tags are missing."""
    match = _JSON_BLOCK_RE.search(text)
    raw = match.group(1).strip() if match else None

    if raw is None:
        # Fallback: find the outermost { ... } span.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"No JSON payload found in model response:\n{text[:2000]}")
        raw = text[start : end + 1]

    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(_escape_bare_control_chars(raw), strict=False)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse JSON from model response ({exc}):\n{raw[:3000]}"
        ) from exc
