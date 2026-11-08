"""emotion_os.adapters：自然语言 → Event 适配层。"""
from .cli_providers import (
    CLICallError,
    CLIUnavailableError,
    claude_cli_call,
    codex_cli_call,
)
from .entity_resolver import EntityResolver
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
    "EntityResolver",
    "CLICallError",
    "CLIUnavailableError",
    "claude_cli_call",
    "codex_cli_call",
]
