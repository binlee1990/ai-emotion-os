# -*- coding: utf-8 -*-
"""语域分档（v0.6）：正式度/场合——调研附录最后一项表达层未决项。

标注为语言常识自设（无语言学实证，lexicon.py docstring 诚实声明）；
断言语义：三语域输出可区分、formal 无口语/网络语标记词、
未覆盖类别回退 neutral、默认参数向后兼容（=v0.5 输出）。
"""
from __future__ import annotations

import pytest

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, MoralInfo
from emotion_os.expression import Expressor
from emotion_os.expression.lexicon import REGISTERS, _REGISTER_LADDERS, graded_word

# 口语/网络语标记词——不得出现在任何 formal 梯
COLLOQUIAL_MARKERS = ("麻了", "笑死", "磕疯", "破防了", "社死", "脚趾抠地", "上头", "发怵")


class TestGradedWordRegister:
    def test_three_registers_distinguishable(self):
        assert graded_word("indignation", 0.8, "formal") == "义愤填膺"
        assert graded_word("indignation", 0.8, "neutral") == "义愤填膺"
        assert graded_word("indignation", 0.8, "colloquial") == "肺都气炸了"
        assert graded_word("po_fang", 0.9, "formal") == "心理防线被击穿"
        assert graded_word("numb", 0.9, "formal") == "彻底麻木"

    def test_formal_ladders_contain_no_colloquial_markers(self):
        """全量断言：所有 formal 梯不含口语/网络语标记词。"""
        for (cat, reg), ladder in _REGISTER_LADDERS.items():
            if reg != "formal":
                continue
            for _, word in ladder:
                for marker in COLLOQUIAL_MARKERS:
                    assert marker not in word, f"{cat}/{reg} 梯含口语标记 {marker!r}: {word}"

    def test_uncovered_category_falls_back_to_neutral(self):
        """语域梯只覆盖差异显著类别（~27），其余回退 neutral 基准梯。"""
        for reg in REGISTERS:
            assert graded_word("serenity", 0.5, reg) == graded_word("serenity", 0.5)

    def test_bad_register_raises(self):
        with pytest.raises(ValueError, match="register"):
            graded_word("joy", 0.5, "slang")

    def test_default_register_is_v05_behavior(self):
        """默认参数向后兼容：不传 register 与显式 neutral 完全一致（抽 4 类×3 档）。"""
        for cat in ("indignation", "po_fang", "numb", "fear"):
            for intensity in (0.1, 0.5, 0.9):
                assert graded_word(cat, intensity) == graded_word(cat, intensity, "neutral")


class TestExpressorRegister:
    def _state_with(self) -> EmotionEngine:
        eng = EmotionEngine(AgentProfile.reader_example())
        eng.process(Event(
            category=EventCategory.VIOLATION, description="被抢功",
            affects="self", caused_by="villain",
            goal_impacts={"esteem": -0.8}, pleasantness=-0.8, probability=1.0,
            moral=MoralInfo(severity=0.8, victim="self", violator="villain", virtue=False),
        ), dt_minutes=1.0)
        return eng

    def test_expressor_register_passes_through_and_summary_follows(self):
        eng = self._state_with()
        exp = Expressor()
        formal = exp.describe(eng.state, register="formal")
        colloquial = exp.describe(eng.state, register="colloquial")
        neutral = exp.describe(eng.state)
        assert formal.entries and colloquial.entries
        # 义愤高激活：三语域顶层词可区分，summary 跟随语域
        assert formal.summary != colloquial.summary or formal.entries[0].word != colloquial.entries[0].word
        assert neutral.summary == exp.describe(eng.state, register="neutral").summary
        # colloquial 不含书面成语腔（该状态顶层是义愤族）
        words_c = "、".join(e.word for e in colloquial.entries)
        assert "气" in words_c  # 口语义愤词（气不过/气不打一处来/肺都气炸了）落地

    def test_formal_workplace_vs_colloquial_private(self):
        """场景：同状态两种场合——对外正式汇报（formal）vs 私下吐槽（colloquial）。"""
        eng = self._state_with()
        exp = Expressor()
        workplace = exp.describe(eng.state, top_k=2, register="formal")
        private = exp.describe(eng.state, top_k=2, register="colloquial")
        assert all("麻了" not in e.word and "笑死" not in e.word for e in workplace.entries)
        assert workplace.summary != private.summary

    def test_formal_passes_through_on_covered_category(self):
        """复审 P2：Expressor 级 formal 透传需被覆盖类别的真词激活——
        恐惧事件（fear 有 formal 梯）在 formal 场合输出书面词而非「发怵」。"""
        eng = EmotionEngine(AgentProfile.neurotic_example())
        eng.process(Event(
            category=EventCategory.THREAT, description="深夜异响",
            affects="self", goal_impacts={"safety": -0.8},
            novelty=0.8, pleasantness=-0.7, probability=1.0, urgency=0.9,
        ), dt_minutes=1.0)
        out = Expressor().describe(eng.state, register="formal")
        assert out.entries, "恐惧事件应有激活"
        fear_words = [e.word for e in out.entries if e.category == "fear"]
        if fear_words:   # fear 在 top-k 时必须是 formal 梯词
            assert fear_words[0] in ("有所惧", "恐惧", "极度恐惧"), fear_words
