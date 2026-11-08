"""调节：Gross 过程模型的策略参数化（调研 §4.5；架构合同 §4.1）。

- 重评（先于生成）：修改评价向量——降相关性、重新归因（故意→意外）、降严重度；
  效力 = 调节力 × 情绪粒度加成。早干预、低成本（Gross 1998/2002）。
- 抑制（后于生成）：掩表达、留体验，付生理与记忆代价（唤醒残余↑、调节资源↓）。
- 调节力是人格参数而非常数（调研 §4.5 对 ai-emotion-os 的提示）。
"""
from __future__ import annotations

from dataclasses import replace

from ..appraiser import AppraisalResult
from ..core.agent import AgentProfile
from ..core.state import AffectState

SUPPRESSION_RESIDUE_COST = 0.10   # 抑制的生理代价：唤醒残余增量（待标定）
SUPPRESSION_DEPLETION = 0.20      # 调节资源消耗


class Strategy:
    SITUATION_SELECTION = "situation_selection"
    SITUATION_MODIFICATION = "situation_modification"
    ATTENTION_DEPLOYMENT = "attention_deployment"
    COGNITIVE_REAPPRAISAL = "cognitive_reappraisal"
    RESPONSE_SUPPRESSION = "response_suppression"


def regulation_strength(agent: AgentProfile) -> float:
    return min(1.0, agent.regulation_capacity * (0.7 + 0.6 * agent.emotion_granularity))


def reappraise(r: AppraisalResult, agent: AgentProfile, strategy: str) -> AppraisalResult:
    """生成前调节：返回修改后的评价向量（不改动输入）。"""
    eff = regulation_strength(agent)
    if strategy == Strategy.COGNITIVE_REAPPRAISAL:
        return replace(
            r,
            goal_relevance=max(0.0, r.goal_relevance * (1.0 - 0.35 * eff)),
            urgency=max(0.0, r.urgency * (1.0 - 0.30 * eff)),
        )
    if strategy == Strategy.ATTENTION_DEPLOYMENT:
        return replace(
            r,
            novelty=max(0.0, r.novelty * (1.0 - 0.40 * eff)),
            urgency=max(0.0, r.urgency * (1.0 - 0.25 * eff)),
        )
    return r


def reinterpret_intent(r: AppraisalResult, agent: AgentProfile) -> AppraisalResult:
    """善意的重新归因：他人故意 → 意外（降愤怒的最有效重评之一）。"""
    from ..core.types import Intent

    eff = regulation_strength(agent)
    if r.causality_intent == Intent.DELIBERATE and eff > 0.25:
        return replace(r, causality_intent=Intent.ACCIDENTAL)
    return r


def suppress(state: AffectState, agent: AgentProfile) -> AffectState:
    """生成后调节：表达被掩（表达层读 suppressed 标志），体验不减、付代价。"""
    state.regulation_depletion = min(1.0, state.regulation_depletion + SUPPRESSION_DEPLETION)
    state.arousal_residue = min(1.0, state.arousal_residue + SUPPRESSION_RESIDUE_COST)
    return state
