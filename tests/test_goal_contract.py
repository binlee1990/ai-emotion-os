# -*- coding: utf-8 -*-
"""goal id 契约化（v0.5）：修 v0.4 复审观察的静默零效应——LLM 抽取自由格式
goal id 与 profile 目标词表失联 → R-INT-01 归零但无人知晓。

fixture 驱动（无 LLM）：注入 goal_ids（prompt 主防线）+ goal_aliases（映射兜底）
+ 表外键 warning 可见化；端到端对照（映射激活 vs 不映射零激活）。
"""
from __future__ import annotations

import json

from emotion_os import AgentProfile, EmotionEngine
from emotion_os.adapters import NLEventAdapter

# goal_impacts 用自由格式键（真实 e2e 中 LLM 的实际输出形态）
EVENT_FREEFORM = {
    "category": "E_violation",
    "description": "主管抢走小林的方案署名",
    "affects": "self",
    "caused_by": "主管",
    "intent": "deliberate",
    "goal_impacts": {"方案获认可与署名": -0.8, "职业声誉": -0.6},
    "pleasantness": -0.8,
    "moral": {"severity": 0.8, "victim": "self", "violator": "主管", "virtue": False},
}

GOALS = ["safety", "esteem", "justice"]
ALIASES = {"方案获认可与署名": "esteem", "职业声誉": "esteem"}


def mock_llm(payload: dict):
    captured: dict[str, str] = {}

    def call(prompt: str) -> str:
        captured["prompt"] = prompt
        return json.dumps(payload, ensure_ascii=False)

    return call, captured


def adapter(payload: dict, **kw) -> tuple[NLEventAdapter, dict[str, str]]:
    call, captured = mock_llm(payload)
    return NLEventAdapter(llm_call=call, **kw), captured


class TestPromptInjection:
    def test_goal_ids_injected_into_prompt(self):
        _, cap = adapter(EVENT_FREEFORM, goal_ids=GOALS)
        _.adapt("主管抢走署名")
        assert "主体目标词表" in cap["prompt"] and "esteem" in cap["prompt"]

    def test_no_goal_ids_prompt_unchanged(self):
        _, cap = adapter(EVENT_FREEFORM)
        _.adapt("任意叙事")
        assert "主体目标词表" not in cap["prompt"]


class TestGoalMapping:
    def test_alias_maps_freeform_to_legal_goal(self):
        a, _ = adapter(EVENT_FREEFORM, goal_ids=GOALS, goal_aliases=ALIASES)
        ev = a.adapt("主管抢走署名").event
        assert ev.goal_impacts == {"esteem": -0.8}   # 同键合并取更极端（同号取 max）

    def test_out_of_table_key_warned_but_kept(self):
        a, _ = adapter(EVENT_FREEFORM, goal_ids=GOALS)   # 无别名：两键均表外
        outcome = a.adapt("主管抢走署名")
        assert set(outcome.event.goal_impacts) == {"方案获认可与署名", "职业声誉"}
        assert sum(1 for w in outcome.warnings if "不在主体目标词表" in w) == 2

    def test_alias_keys_normalized(self):
        a, _ = adapter(EVENT_FREEFORM, goal_ids=GOALS, goal_aliases={"方案 获认可与署名": "esteem"})
        ev = a.adapt("主管抢走署名").event
        assert "esteem" in ev.goal_impacts

    def test_in_table_variant_canonicalized(self):
        """复审 P2：`Esteem` 归一命中词表时改写为词表原键 `esteem`——
        引擎是字面 goals.get 匹配，不改写会静默零相关。"""
        payload = {**EVENT_FREEFORM, "goal_impacts": {"Esteem": -0.8}}
        a, _ = adapter(payload, goal_ids=GOALS)
        outcome = a.adapt("主管抢走署名")
        assert set(outcome.event.goal_impacts) == {"esteem"}   # 改写为原键
        assert not any("不在主体目标词表" in w for w in outcome.warnings)
        eng = EmotionEngine(AgentProfile.reader_example())
        r = eng.process(outcome.event, dt_minutes=1.0)
        acts = {e.category: e.intensity for e in r.episodes}
        assert acts.get("indignation", 0) > 0.5   # 字面匹配命中（未改写则为 0.44 档）

    def test_merge_zero_keeps_nonzero_side(self):
        """复审 P2：同键合并遇 0.0 保留非零侧（(负,0) 不得归 0）。"""
        from emotion_os.adapters.nl_event import map_goal_impacts
        from emotion_os.adapters import parse_event as _pe
        base = _pe(json.dumps({**EVENT_FREEFORM, "goal_impacts": {
            "方案获认可与署名": -0.5, "职业声誉": 0.0}}, ensure_ascii=False)).event
        ev = map_goal_impacts(base, GOALS, ALIASES, [])
        assert ev.goal_impacts == {"esteem": -0.5}


class TestEndToEnd:
    def test_mapped_goal_activates_vs_unmapped_zero(self):
        """端到端：自由格式键经别名映射 → profile 目标受冲击 → 义愤激活；
        不映射（v0.4 前行为）→ goal_relevance 走道德通道但仍无目标冲击 →
        憋屈/失望显著弱（R-INT-01 乘法结构）。"""
        eng_mapped = EmotionEngine(AgentProfile.reader_example())
        a_mapped, _ = adapter(EVENT_FREEFORM, goal_ids=GOALS, goal_aliases=ALIASES)
        r_mapped = eng_mapped.process(a_mapped.adapt("主管抢走署名").event, dt_minutes=1.0)
        m = {e.category: e.intensity for e in r_mapped.episodes}

        eng_plain = EmotionEngine(AgentProfile.reader_example())
        a_plain, _ = adapter(EVENT_FREEFORM)
        r_plain = eng_plain.process(a_plain.adapt("主管抢走署名").event, dt_minutes=1.0)
        p = {e.category: e.intensity for e in r_plain.episodes}

        assert m.get("indignation", 0) > p.get("indignation", 0), (
            f"映射后义愤应更强：{m.get('indignation')} vs {p.get('indignation')}"
        )
        assert m.get("bie_qu", 0) > p.get("bie_qu", 0)

    def test_backward_compatible_without_params(self):
        a, _ = adapter(EVENT_FREEFORM)
        outcome = a.adapt("任意叙事")
        assert outcome.event.goal_impacts == {"方案获认可与署名": -0.8, "职业声誉": -0.6}
        assert not any("目标词表" in w for w in outcome.warnings)
