"""emotion_os.adapters：自然语言 → Event 适配层。"""
from .nl_event import (
    EVENT_JSON_CONTRACT,
    NLEventAdapter,
    ParseOutcome,
    EventParseError,
    build_extraction_prompt,
    parse_event,
)

__all__ = [
    "EVENT_JSON_CONTRACT",
    "NLEventAdapter",
    "ParseOutcome",
    "EventParseError",
    "build_extraction_prompt",
    "parse_event",
]
