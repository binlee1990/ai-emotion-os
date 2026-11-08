"""表达层单元测试（N8 出条件；承载 grammar R-EXP-01 的 formal 声明）。"""
from __future__ import annotations

from emotion_os.core.state import AffectState, EmotionEpisode
from emotion_os.expression import Expressor
from emotion_os.expression.lexicon import graded_word


def state_with(cats: dict[str, float]) -> AffectState:
    return AffectState(
        now_min=0.0,
        episodes={c: EmotionEpisode(c, i, half_life_min=30.0) for c, i in cats.items()},
    )


class TestDualChannel:
    def test_dual_channel_and_mixing(self):
        """R-EXP-01：双通道（类别词+4D）并存；异号效价双峰 → 又X又Y。"""
        out = Expressor().describe(state_with({"anger": 0.6, "amusement": 0.55}))
        # 类别通道：两个条目，各有中文分档词
        assert len(out.entries) == 2
        assert all(e.word for e in out.entries)
        words = {e.category: e.word for e in out.entries}
        assert "anger" in words and "amusement" in words
        # 混合描述：又X又Y（异号效价）
        assert out.summary.startswith("又") and "又" in out.summary[1:]
        # 维度通道：效价近中（-0.6 与 0.55 加权）
        assert -0.15 < out.dims.valence < 0.15
        assert out.dims.arousal > 0.5

    def test_single_dominant_summary(self):
        out = Expressor().describe(state_with({"sadness": 0.7, "serenity": 0.1}))
        assert out.summary == "悲痛"          # 0.7 命中阈值 0.7 档
        assert len(out.entries) == 2

    def test_suppressed_flag(self):
        out = Expressor().describe(state_with({"anger": 0.5}), suppressed=True)
        assert out.suppressed is True


class TestGradedLexicon:
    def test_grading_monotonic(self):
        words = [graded_word("anger", x) for x in (0.1, 0.45, 0.75, 0.9)]
        assert words[0] == "生气" and words[1] == "愤怒"
        assert words.index(words[1]) < words.index(words[2]) or words[1] != words[2]
        assert len(set(words)) >= 3           # 分档确实区分

    def test_kama_muta_ladder(self):
        assert graded_word("kama_muta", 0.3) == "鼻头一酸"
        assert graded_word("kama_muta", 0.5) == "感动"
        assert graded_word("kama_muta", 0.95) == "泪崩"

    def test_generic_fallback(self):
        w = graded_word("heartbreak", 0.9)
        assert w  # 未显式分档类别也有输出
