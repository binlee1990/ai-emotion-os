"""NL→Event 适配器测试（N3 出条件）：解析校验、错误用例、fixture 端到端。"""
from __future__ import annotations

import json

import pytest

from emotion_os import AgentProfile, EmotionEngine, EventCategory, Intent
from emotion_os.adapters import (
    NLEventAdapter,
    EventParseError,
    build_extraction_prompt,
    parse_event,
)
from emotion_os.core.types import TimeOrientation

HUMILIATION_JSON = {
    "category": "E_violation",
    "description": "反派当众羞辱主角并夺走成果",
    "affects": "self",
    "caused_by": "villain",
    "intent": "deliberate",
    "goal_impacts": {"esteem": -0.7},
    "moral": {"severity": 0.7, "victim": "self", "violator": "villain"},
    "control_hint": 0.2,
    "novelty": 0.4,
    "safety_frame": 1.0,
    "fictionality": 1.0,
}

FACESLAP_JSON = {
    "category": "E_violation",
    "description": "反派身份曝光当众伏诛，主角扬眉吐气",
    "affects": "self",
    "goal_impacts": {"justice": 0.8, "esteem": 0.4},
    "justice_restored": 0.9,
    "justice_target": "villain",
    "prior_adversity_resolved": True,
    "effort": 0.7,
    "safety_frame": 1.0,
    "fictionality": 1.0,
}


class TestParse:
    def test_parse_full_payload(self):
        out = parse_event(HUMILIATION_JSON)
        e = out.event
        assert e.category is EventCategory.VIOLATION
        assert e.caused_by == "villain" and e.intent == Intent.DELIBERATE
        assert e.moral is not None and e.moral.violator == "villain"
        assert out.warnings == []

    def test_parse_from_json_string(self):
        out = parse_event(json.dumps(FACESLAP_JSON, ensure_ascii=False))
        assert out.event.justice_target == "villain"
        assert out.event.prior_adversity_resolved is True

    def test_missing_category_raises(self):
        with pytest.raises(EventParseError):
            parse_event({"description": "无类别"})

    def test_bad_category_raises_with_legal_values(self):
        with pytest.raises(EventParseError, match="E_violation"):
            parse_event({"category": "Z_nonsense"})

    def test_out_of_range_clipped_with_warning(self):
        payload = dict(HUMILIATION_JSON)
        payload["novelty"] = 1.7
        payload["urgency"] = -0.5
        out = parse_event(payload)
        assert out.event.novelty == 1.0 and out.event.urgency == 0.0
        assert any("novelty" in w for w in out.warnings)

    def test_unknown_field_and_bad_enum_downgraded(self):
        payload = dict(HUMILIATION_JSON)
        payload["weather"] = "rain"
        payload["intent"] = "spiteful"
        out = parse_event(payload)
        assert any("weather" in w for w in out.warnings)
        assert any("intent" in w for w in out.warnings)
        assert out.event.intent == Intent.UNKNOWN

    def test_bad_nested_type_raises(self):
        payload = dict(HUMILIATION_JSON)
        payload["moral"] = "very bad"
        with pytest.raises(EventParseError):
            parse_event(payload)

    def test_time_orientation_enum(self):
        payload = {"category": "I_aesthetic", "time_orientation": "past", "pleasantness": 0.5}
        out = parse_event(payload)
        assert out.event.time_orientation is TimeOrientation.PAST

    def test_non_numeric_field_raises_parse_error(self):
        payload = dict(HUMILIATION_JSON)
        payload["novelty"] = "high"
        with pytest.raises(EventParseError, match="novelty"):
            parse_event(payload)

    def test_string_booleans_parsed_tolerantly(self):
        payload = {
            "category": "F_bond",
            "bond": {"delta": 0.8, "sudden": "false", "romantic": "true"},
        }
        out = parse_event(payload)
        assert out.event.bond.sudden is False and out.event.bond.romantic is True
        assert out.warnings == []

    def test_markdown_fences_stripped(self):
        fenced = "```json\n" + json.dumps(FACESLAP_JSON, ensure_ascii=False) + "\n```"
        out = parse_event(fenced)
        assert out.event.justice_target == "villain"

    def test_trailing_noise_after_json_extracted(self):
        """v0.3：轻量档 CLI 在 JSON 后追加说明/围栏外文字——取首个完整对象。"""
        body = json.dumps(FACESLAP_JSON, ensure_ascii=False)
        noisy = f"```json\n{body}\n```\n以上为抽取结果，字段范围均已核对。"
        out = parse_event(noisy)
        assert out.event.justice_target == "villain"

    def test_leading_prose_before_json_extracted(self):
        body = json.dumps(FACESLAP_JSON, ensure_ascii=False)
        out = parse_event(f"好的，以下是转换结果：\n{body}")
        assert out.event.category is not None


class TestPrompt:
    def test_prompt_contains_contract_and_text(self):
        p = build_extraction_prompt("主角被反派羞辱")
        assert "JSON 契约" in p and "主角被反派羞辱" in p
        assert "category" in p and "goal_impacts" in p


class TestEndToEnd:
    def test_fake_llm_full_pipeline(self):
        """fixture 驱动端到端：JSON→Event→引擎→解气路径（无网络调用）。"""
        from emotion_os.expression import Expressor

        queue = [json.dumps(HUMILIATION_JSON, ensure_ascii=False),
                 json.dumps(FACESLAP_JSON, ensure_ascii=False)]
        adapter = NLEventAdapter(llm_call=lambda prompt: queue.pop(0))
        eng = EmotionEngine(AgentProfile.reader_example())
        for text in ("第一集：反派当众羞辱主角", "第二集：反派伏诛主角反杀"):
            eng.process(adapter.adapt(text).event, dt_minutes=2.0)
        assert eng.state.activation("jie_qi") > 0.25       # 解气路径贯通
        assert eng.state.charges.get("villain", 0) > 0.1   # 记账链贯通
        words = "、".join(e.word for e in Expressor().describe(eng.state).entries)
        assert words  # 输出非空中文词
