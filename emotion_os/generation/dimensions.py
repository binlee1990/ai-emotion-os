"""4D 维度通道：类别激活的连续空间混合（调研 §2.2 Fontaine 四维、§6.3.2 双表示）。

类别是语义空间中的吸引子，激活加权混合允许「又好气又好笑」等梯度状态（§3.1）。
"""
from __future__ import annotations

from dataclasses import dataclass

from .catalog import CATALOG

VALENCE, AROUSAL, DOMINANCE, UNPREDICTABILITY = "valence", "arousal", "dominance", "unpredictability"


@dataclass(frozen=True)
class Dims4:
    valence: float = 0.0        # -1–1
    arousal: float = 0.0        # 0–1
    dominance: float = 0.0      # -1–1
    unpredictability: float = 0.0  # 0–1


def blend(activations: dict[str, float]) -> Dims4:
    """激活加权平均原型 → 连续坐标（软类别：混合即插值）。"""
    total = sum(activations.values())
    if total <= 1e-9:
        return Dims4()
    v = sum(CATALOG[c].valence * a for c, a in activations.items()) / total
    ar = sum(CATALOG[c].arousal * a for c, a in activations.items()) / total
    d = sum(CATALOG[c].dominance * a for c, a in activations.items()) / total
    u = sum(CATALOG[c].unpredictability * a for c, a in activations.items()) / total
    return Dims4(
        valence=max(-1.0, min(1.0, v)),
        arousal=max(0.0, min(1.0, ar)),
        dominance=max(-1.0, min(1.0, d)),
        unpredictability=max(0.0, min(1.0, u)),
    )
