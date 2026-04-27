from __future__ import annotations

import json


def encode_sse_event(envelope: dict[str, object]) -> str:
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n"
