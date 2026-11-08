"""表达层：双通道输出（类别中文词+强度档 / 4D 连续坐标；R-EXP-01；调研 §6.3.2）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.state import AffectState
from ..generation.catalog import CATALOG
from ..generation.dimensions import Dims4, blend
from .lexicon import graded_word


@dataclass(frozen=True)
class ExprEntry:
    category: str
    zh: str          # 目录标准名
    word: str        # 强度分档词
    intensity: float
    family: str


@dataclass(frozen=True)
class ExpressionOutput:
    entries: list[ExprEntry] = field(default_factory=list)   # 类别通道（top-k）
    dims: Dims4 = Dims4()                                    # 维度通道
    summary: str = ""                                        # 可读混合描述
    suppressed: bool = False                                 # 反应抑制掩码


def _mixture_note(entries: list[ExprEntry]) -> str:
    """混合情绪可读化：双峰且接近 → 又X又Y（「又好气又好笑」，调研 §3.4）。"""
    if len(entries) < 2:
        return entries[0].word if entries else ""
    first, second = entries[0], entries[1]
    if second.intensity >= 0.75 * first.intensity:
        v1 = CATALOG[first.category].valence
        v2 = CATALOG[second.category].valence
        if v1 * v2 < 0:   # 异号效价 → 又X又Y
            return f"又{first.word}又{second.word}"
        return f"{first.word}与{second.word}交织"
    return first.word


class Expressor:
    def describe(self, state: AffectState, top_k: int = 3, min_activation: float = 0.04,
                 suppressed: bool = False, register: str = "neutral") -> ExpressionOutput:
        """register（v0.6）：语域分档——formal（书面/对外正式）/ neutral（默认）/
        colloquial（口语/对内私下）；未覆盖类别回退 neutral（lexicon.REGISTERS）。"""
        acts = {
            cat: state.activation(cat)
            for cat in state.episodes
            if state.activation(cat) >= min_activation
        }
        ranked = sorted(acts.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        entries = [
            ExprEntry(
                category=cat,
                zh=CATALOG[cat].zh,
                word=graded_word(cat, act, register),
                intensity=round(act, 3),
                family=CATALOG[cat].family,
            )
            for cat, act in ranked
        ]
        return ExpressionOutput(
            entries=entries,
            dims=blend(acts),
            summary=_mixture_note(entries),
            suppressed=suppressed,
        )
