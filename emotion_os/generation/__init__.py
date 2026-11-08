"""EmotionGenerator：评价结果 → 情绪发作集（类别+4D+强度，架构合同 §4.2）。"""
from __future__ import annotations

from dataclasses import dataclass

from ..appraiser import AppraisalResult
from ..core.agent import AgentProfile
from ..core.event import Event
from ..core.state import AffectState, EmotionEpisode, FAMILY_HALF_LIFE_MIN
from .catalog import CATALOG, FAMILY_OF, HALF_LIFE_BY_CATEGORY
from .dimensions import Dims4, blend
from .intensity import episode_intensity
from .mapping import evaluate_activations


@dataclass(frozen=True)
class GenerationResult:
    episodes: list[EmotionEpisode]
    raw_activations: dict[str, float]
    dims: Dims4


def half_life_of(category_id: str) -> float:
    if category_id in HALF_LIFE_BY_CATEGORY:
        return HALF_LIFE_BY_CATEGORY[category_id]
    return FAMILY_HALF_LIFE_MIN.get(FAMILY_OF[category_id], 12.0)


class EmotionGenerator:
    """生成器：原始激活 → 强度缩放 → EmotionEpisode 列表 + 4D 混合。"""

    def generate(
        self, r: AppraisalResult, e: Event, agent: AgentProfile, state: AffectState
    ) -> GenerationResult:
        raw = evaluate_activations(r, e, agent, state)
        episodes: list[EmotionEpisode] = []
        final_acts: dict[str, float] = {}
        for cat_id, raw_a in raw.items():
            intensity = episode_intensity(raw_a, cat_id, r, agent, state)
            if intensity <= 0.02:
                continue
            cat = CATALOG[cat_id]
            episodes.append(
                EmotionEpisode(
                    category=cat_id,
                    intensity=intensity,
                    onset_min=state.now_min,
                    half_life_min=half_life_of(cat_id),
                    family=cat.family,
                    wanting=cat.wanting * intensity,
                    liking=cat.liking * intensity,
                )
            )
            final_acts[cat_id] = intensity
        return GenerationResult(episodes=episodes, raw_activations=raw, dims=blend(final_acts))
