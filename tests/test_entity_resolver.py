# -*- coding: utf-8 -*-
"""EntityResolver（v0.4）：跨事件实体规范化——修 v0.3 LLM 端到端实测缺口
（同一实体不同写法 → charges 不命中 → 解气不触发）。

fixture 驱动（无 LLM）：两事件 JSON 直接喂 NLEventAdapter（mock llm_call），
验证归一后引擎端到端触发解气；以及 prompt 注入、前缀保留、保留字透传。
"""
from __future__ import annotations

import json

from emotion_os import AgentProfile, EmotionEngine
from emotion_os.adapters import EntityResolver, NLEventAdapter

# 事件1：violator=主管（中文写法，登记）
EVENT1 = {
    "category": "E_violation",
    "description": "主管抢走小林的方案署名",
    "affects": "self",
    "caused_by": "主管",
    "intent": "deliberate",
    "goal_impacts": {"esteem": -0.8},
    "pleasantness": -0.8,
    "moral": {"severity": 0.8, "victim": "self", "violator": "主管", "virtue": False},
}
# 事件2：justice_target=supervisor（英文写法，LLM 未复用已见写法的情形）
EVENT2 = {
    "category": "D_achievement",
    "description": "客户当场揭穿 supervisor，其为小林正名",
    "affects": "self",
    "caused_by": "客户",
    "intent": "deliberate",
    "goal_impacts": {"esteem": 0.7},
    "pleasantness": 0.9,
    "justice_restored": 0.95,
    "justice_target": "supervisor",
}


def mock_llm(*payloads: dict):
    """按调用次序返回 payloads[k]（越界重复最后一个）；捕获 prompt。"""
    captured: dict[str, str] = {}
    state = {"i": 0}

    def call(prompt: str) -> str:
        captured["prompt"] = prompt
        payload = payloads[min(state["i"], len(payloads) - 1)]
        state["i"] += 1
        return json.dumps(payload, ensure_ascii=False)

    return call, captured


class TestNormalize:
    def test_alias_table_maps_to_canonical(self):
        r = EntityResolver(aliases={"supervisor": "主管", "boss": "主管"})
        assert r.normalize("主管") == "主管"          # 首次：登记
        assert r.normalize("supervisor") == "主管"    # 别名表命中
        assert r.normalize("Boss") == "主管"          # 大小写不敏感
        assert r.renames == [("supervisor", "主管"), ("Boss", "主管")]

    def test_alias_keys_normalized_on_init(self):
        """复审 P2：别名表键含大写/空格（"Super Visor"）同样命中——构造时归一键。"""
        r = EntityResolver(aliases={"Super Visor": "主管"})
        assert r.normalize("supervisor") == "主管"
        assert "主管" in r.seen                        # 别名先命中也登记规范名（roster 完整）

    def test_reserved_variant_folds_to_lowercase(self):
        """复审 P2：保留字变体拼写归一到小写——引擎字面比较 "self" 不漏配。"""
        r = EntityResolver()
        assert r.normalize("Self") == "self"
        assert r.normalize(" NONE ") == "none"
        assert r.seen == []

    def test_violator_nonstring_parses_not_crashes(self):
        """复审 P2：moral.violator 非字符串（LLM 异常输出）不崩溃——parse 层 str 化。"""
        payload = {**EVENT1, "moral": {"severity": 0.8, "victim": "self", "violator": 42, "virtue": False}}
        call, _ = mock_llm(payload)
        outcome = NLEventAdapter(llm_call=call).adapt("任意叙事")
        assert outcome.event.moral.violator == "42"

    def test_seen_casefold_match(self):
        r = EntityResolver()
        r.normalize("Team Red")
        assert r.normalize("team red") == "Team Red"   # 已见写法优先保留首次形态
        assert r.normalize("TEAM  RED") == "Team Red"  # 空白不敏感

    def test_prefix_preserved(self):
        r = EntityResolver()
        r.normalize("team red")                       # 首次写法即规范名
        assert r.normalize("group:Team Red") == "group:team red"

    def test_reserved_passthrough_not_registered(self):
        r = EntityResolver()
        assert r.normalize("self") == "self"
        assert r.normalize(None) is None
        assert r.seen == []


class TestAdapterIntegration:
    def test_two_event_cross_script_triggers_jieqi(self):
        """端到端：事件1 violator=主管 → 事件2 justice_target=supervisor，
        别名表归一后 charges 命中 → 解气触发（v0.3 缺口的回归测试）。"""
        resolver = EntityResolver(aliases={"supervisor": "主管"})
        call, _ = mock_llm(EVENT1, EVENT2)
        adapter = NLEventAdapter(llm_call=call, resolver=resolver)
        eng = EmotionEngine(AgentProfile.reader_example())

        eng.process(adapter.adapt("主管抢走小林的方案署名").event, dt_minutes=1.0)
        r2 = eng.process(adapter.adapt("客户当场揭穿主管，为小林正名").event, dt_minutes=5.0)
        acts = {ep.category: ep.intensity for ep in r2.episodes}
        assert acts.get("jie_qi", 0) > 0.3, f"jie_qi={acts.get('jie_qi')}（归一未命中则解气不触发）"

    def test_prompt_injects_roster_hint(self):
        resolver = EntityResolver(aliases={"supervisor": "主管"})
        call, cap = mock_llm(EVENT1, EVENT2)
        adapter = NLEventAdapter(llm_call=call, resolver=resolver)
        adapter.adapt("第一次")   # 登记「主管」；首次名单为空
        assert "已见实体" not in cap["prompt"]
        adapter.adapt("第二次")
        assert "已见实体" in cap["prompt"] and "主管" in cap["prompt"]

    def test_no_resolver_backward_compatible(self):
        call, _ = mock_llm(EVENT2)
        outcome = NLEventAdapter(llm_call=call).adapt("任意叙事")
        assert outcome.event.justice_target == "supervisor"   # 原样透传

    def test_resolve_event_normalizes_moral_fields(self):
        resolver = EntityResolver(aliases={"supervisor": "主管"})
        call, _ = mock_llm(EVENT1, {**EVENT2, "moral": {"severity": 0.7, "victim": "xiaolin",
                                                        "violator": "supervisor", "virtue": False}})
        adapter = NLEventAdapter(llm_call=call, resolver=resolver)
        adapter.adapt("第一次")
        ev2 = adapter.adapt("第二次").event
        assert ev2.moral.violator == "主管"
        assert ev2.justice_target == "主管"
