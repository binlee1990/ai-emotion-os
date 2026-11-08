"""NL→Event 适配器：LLM 结构化输出 → Event schema（架构合同 §8 v0.2 第一项）。

设计：零运行时依赖、provider 无关——LLM 调用经 `Callable[[str], str]` 注入
（prompt 进、JSON 文本出），解析与校验是纯函数、离线可测。
提示词契约与 Event 字段一一对应（docs/architecture-contract.md §4.3）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..core.event import AestheticInfo, BondInfo, Event, MoralInfo, SocialInfo
from ..core.types import EventCategory, Intent, TimeOrientation


class EventParseError(ValueError):
    """payload 结构性错误（缺类别/类型不符），无法构造 Event。"""


@dataclass
class ParseOutcome:
    event: Event
    warnings: list[str] = field(default_factory=list)


# ---- 提示词契约（与 Event 字段一一对应）----

EVENT_JSON_CONTRACT = """{
  "category": "A_loss|B_threat|C_frustration|D_achievement|E_violation|F_bond|G_comparison|H_novelty|I_aesthetic|J_body|K_fiction  [必填]",
  "description": "一句话事件描述",
  "affects": "受影响者：self / 个体id / group:xxx / fictional:xxx",
  "caused_by": "行为者id（归因键；自己造成填主体id）",
  "intent": "deliberate|accidental|unknown|none",
  "goal_impacts": {"目标id": -1..+1 的促进/阻碍},
  "novelty": 0..1, "pleasantness": -1..1,
  "expectancy_violation": 0..1, "probability": 0..1, "urgency": 0..1,
  "reversibility": 0..1, "control_hint": 0..1 或 null,
  "moral": {"severity": 0..1, "victim": "...", "violator": "...", "virtue": bool},
  "social": {"direction": "up|down", "deservedness": 0..1, "domain": "status|relationship|..."},
  "bond": {"delta": 0..1, "sudden": bool, "break_up": bool, "romantic": bool},
  "aesthetic": {"vastness": 0..1, "beauty": 0..1, "skill": 0..1, "virtue": 0..1},
  "justice_restored": 0..1, "justice_target": "受罚方id",
  "prior_threat_resolved": bool, "prior_adversity_resolved": bool,
  "effort": 0..1, "insight": bool,
  "safety_frame": 0..1, "fictionality": 0..1,
  "time_orientation": "past|present|future", "stimulus_key": "重复刺激键"
}"""


def build_extraction_prompt(narrative_text: str) -> str:
    system = (
        "你是情绪事件抽取器。把叙事文本中发生的一个事件转成 JSON（只输出 JSON，不要解释）。"
        "规则：①事件类别必选且只能从给定枚举选；②数值严格遵守字段范围；"
        "③goal_impacts 只填与叙事主体目标明确相关的条目；④没有依据的字段省略，不要编造。"
        f"\nJSON 契约：\n{EVENT_JSON_CONTRACT}"
    )
    return f"{system}\n\n叙事文本：\n{narrative_text}"


# ---- 解析与校验 ----

_FLOAT_RANGES: dict[str, tuple[float, float]] = {
    "novelty": (0.0, 1.0), "pleasantness": (-1.0, 1.0),
    "expectancy_violation": (0.0, 1.0), "probability": (0.0, 1.0),
    "urgency": (0.0, 1.0), "reversibility": (0.0, 1.0),
    "justice_restored": (0.0, 1.0), "effort": (0.0, 1.0),
    "safety_frame": (0.0, 1.0), "fictionality": (0.0, 1.0),
}
_KNOWN_TOP = set(_FLOAT_RANGES) | {
    "category", "description", "affects", "caused_by", "intent", "goal_impacts",
    "control_hint", "moral", "social", "bond", "aesthetic", "justice_target",
    "prior_threat_resolved", "prior_adversity_resolved", "insight",
    "time_orientation", "stimulus_key",
}


def _clip(value: float, lo: float, hi: float, name: str, warnings: list[str]) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise EventParseError(f"字段 {name} 非数值: {value!r}") from exc
    if v < lo or v > hi:
        warnings.append(f"{name}={v} 超出 [{lo},{hi}]，已截断")
        return max(lo, min(hi, v))
    return v


def _to_bool(raw: Any, default: bool, name: str, warnings: list[str]) -> bool:
    """布尔解析：真 bool 直通；字符串 true/false/1/0 宽容解析；其余警告回默认。"""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        if raw.strip().lower() in ("true", "yes", "1"):
            return True
        if raw.strip().lower() in ("false", "no", "0"):
            return False
    warnings.append(f"{name}={raw!r} 非布尔，用默认 {default}")
    return default


def _strip_fences(text: str) -> str:
    """剥掉真实 LLM 常见的 markdown 代码围栏（```json ... ```）。"""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
        return t.strip()
    return t


def _first_json_object(text: str) -> dict[str, Any]:
    """提取首个完整 JSON 对象（raw_decode），忽略前导说明与尾随噪音。

    轻量档模型常见形态：JSON 后追加一句解释、或围栏闭合后再补文字——
    整体 json.loads 报 Extra data，但首个对象本身合法。
    """
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise EventParseError(f"文本中无合法 JSON 对象: {text[:120]!r}")


def parse_event(payload: dict[str, Any] | str) -> ParseOutcome:
    """dict/JSON 字符串 → Event。结构性错误抛 EventParseError；越界截断记 warning。"""
    warnings: list[str] = []
    if isinstance(payload, str):
        text = _strip_fences(payload)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            # 尾随/前导噪音（低 effort 模型在 JSON 外追加文字）：取首个完整对象
            try:
                payload = _first_json_object(text)
            except EventParseError:
                raise EventParseError(f"非法 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise EventParseError(f"payload 须为 JSON 对象，得到 {type(payload).__name__}")

    for key in payload:
        if key not in _KNOWN_TOP:
            warnings.append(f"未知字段 {key!r} 已忽略")

    raw_cat = payload.get("category")
    if raw_cat is None:
        raise EventParseError("缺少必填字段 category")
    try:
        category = EventCategory(raw_cat)
    except ValueError:
        legal = [c.value for c in EventCategory]
        raise EventParseError(f"category={raw_cat!r} 不合法；合法值: {legal}") from None

    kwargs: dict[str, Any] = {"category": category, "description": str(payload.get("description", ""))}
    for name, (lo, hi) in _FLOAT_RANGES.items():
        if name in payload:
            kwargs[name] = _clip(payload[name], lo, hi, name, warnings)
    if payload.get("control_hint") is not None:
        kwargs["control_hint"] = _clip(payload["control_hint"], 0.0, 1.0, "control_hint", warnings)
    for name in ("affects", "caused_by", "justice_target", "stimulus_key"):
        if payload.get(name) is not None:
            kwargs[name] = str(payload[name])
    if "intent" in payload:
        try:
            kwargs["intent"] = Intent(str(payload["intent"]))
        except ValueError:
            warnings.append(f"intent={payload['intent']!r} 不合法，用 unknown")
            kwargs["intent"] = Intent.UNKNOWN
    if "time_orientation" in payload:
        try:
            kwargs["time_orientation"] = TimeOrientation(str(payload["time_orientation"]))
        except ValueError:
            warnings.append(f"time_orientation={payload['time_orientation']!r} 不合法，用 present")
    for name in ("prior_threat_resolved", "prior_adversity_resolved", "insight"):
        if name in payload:
            kwargs[name] = _to_bool(payload[name], False, name, warnings)

    gi = payload.get("goal_impacts")
    if gi is not None:
        if not isinstance(gi, dict):
            raise EventParseError("goal_impacts 须为对象 {目标id: -1..+1}")
        kwargs["goal_impacts"] = {
            str(k): _clip(v, -1.0, 1.0, f"goal_impacts.{k}", warnings) for k, v in gi.items()
        }

    moral = payload.get("moral")
    if moral is not None:
        if not isinstance(moral, dict):
            raise EventParseError("moral 须为对象")
        kwargs["moral"] = MoralInfo(
            severity=_clip(moral.get("severity", 0.5), 0.0, 1.0, "moral.severity", warnings),
            victim=str(moral.get("victim", "self")),
            violator=moral.get("violator"),
            virtue=_to_bool(moral.get("virtue", False), False, "moral.virtue", warnings),
        )
    social = payload.get("social")
    if social is not None:
        if not isinstance(social, dict):
            raise EventParseError("social 须为对象")
        direction = str(social.get("direction", "up"))
        if direction not in ("up", "down"):
            warnings.append(f"social.direction={direction!r} 不合法，用 up")
            direction = "up"
        kwargs["social"] = SocialInfo(
            direction=direction,
            deservedness=_clip(social.get("deservedness", 0.5), 0.0, 1.0, "social.deservedness", warnings),
            domain=str(social.get("domain", "status")),
        )
    bond = payload.get("bond")
    if bond is not None:
        if not isinstance(bond, dict):
            raise EventParseError("bond 须为对象")
        kwargs["bond"] = BondInfo(
            delta=_clip(bond.get("delta", 0.5), 0.0, 1.0, "bond.delta", warnings),
            sudden=_to_bool(bond.get("sudden", True), True, "bond.sudden", warnings),
            break_up=_to_bool(bond.get("break_up", False), False, "bond.break_up", warnings),
            romantic=_to_bool(bond.get("romantic", False), False, "bond.romantic", warnings),
        )
    aesthetic = payload.get("aesthetic")
    if aesthetic is not None:
        if not isinstance(aesthetic, dict):
            raise EventParseError("aesthetic 须为对象")
        kwargs["aesthetic"] = AestheticInfo(
            vastness=_clip(aesthetic.get("vastness", 0.0), 0.0, 1.0, "aesthetic.vastness", warnings),
            beauty=_clip(aesthetic.get("beauty", 0.0), 0.0, 1.0, "aesthetic.beauty", warnings),
            skill=_clip(aesthetic.get("skill", 0.0), 0.0, 1.0, "aesthetic.skill", warnings),
            virtue=_clip(aesthetic.get("virtue", 0.0), 0.0, 1.0, "aesthetic.virtue", warnings),
        )

    return ParseOutcome(event=Event(**kwargs), warnings=warnings)


@dataclass
class NLEventAdapter:
    """把叙事文本变成 Event：prompt 契约 → 注入的 LLM 调用 → 解析校验。"""

    llm_call: Callable[[str], str]     # provider 无关：prompt 进，JSON 文本出

    def adapt(self, narrative_text: str) -> ParseOutcome:
        raw = self.llm_call(build_extraction_prompt(narrative_text))
        return parse_event(raw)
