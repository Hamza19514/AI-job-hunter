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

    return json.loads(raw)
