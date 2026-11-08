"""评价器：事件×主体 → SEC 评价向量 + OCC 分支判定（调研 §2.1–§2.4；架构合同 §4.1）。

评价先行：本模块是「事件→情绪」映射的源头——所有下游情绪都由这里的评价配置决定，
事件类别本身不直接产生情绪（调研 §6.3.1）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.agent import AgentProfile
from ..core.event import Event
from ..core.types import Intent, OCCBranch


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class AppraisalResult:
    """SEC 四检查输出（调研 §2.1 Sander/Grandjean/Scherer 2005 配置）。"""

    # SEC① 相关性
    novelty: float            # 新异性/突发性 0–1
    pleasantness: float       # 内在愉悦度 -1–1
    goal_relevance: float     # 目标/需要相关性 0–1（零→零情绪，R-INT-01）
    # SEC② 含义
    conduciveness: float      # 目标促进(+)/阻碍(-) -1–1（重要性加权）
    causality_agent: str | None
    causality_intent: Intent
    outcome_probability: float
    expectancy_violation: float
    urgency: float
    # SEC③ 应对潜力
    control: float            # 能改变它吗 0–1
    power: float              # 能承受它吗 0–1
    adjustment: float         # 能调整适应吗 0–1
    # SEC④ 规范意义
    internal_standard: float  # 违反自我理想(-)…符合(+) -1–1
    external_standard: float  # 违反群体规范(-)…美德(+) -1–1
    # 派生
    occ_branches: tuple[OCCBranch, ...]   # 适用分支（可多个）
    primary_branch: OCCBranch
    safety_frame: float       # 安全框架 0–1
    fictionality: float
    affects: str
    n_goals_affected: int

    @property
    def threat_level(self) -> float:
        """威胁水平 = 相关性×阻碍×概率（恐惧族共享底座）。"""
        return _clip(self.goal_relevance * max(0.0, -self.conduciveness) * self.outcome_probability)

    @property
    def deliberate_other(self) -> bool:
        return (
            self.causality_agent is not None
            and self.causality_agent not in ("self", "")
            and self.causality_intent == Intent.DELIBERATE
        )

    @property
    def self_caused(self) -> bool:
        return self.causality_agent == "self"


class AppraisalEngine:
    """无状态评价器：同一事件对不同主体给出不同评价（个体差异入口）。"""

    def appraise(self, event: Event, agent: AgentProfile) -> AppraisalResult:
        # ---- SEC① 相关性 ----
        novelty = _clip(event.novelty)
        pleasantness = event.pleasantness

        touched = [
            (gid, delta, agent.goal_importance(gid))
            for gid, delta in event.goal_impacts.items()
            if abs(delta) > 0.05 and agent.goal_importance(gid) > 0.05
        ]
        n_goals = len(touched)
        goal_relevance = max((imp for _, _, imp in touched), default=0.0)

        # 他者/虚构对象：相关性经共情特质与态度传导（调研 §2.5 指向对象维度）
        if event.affects not in ("self", agent.agent_id):
            attitude = abs(agent.attitude_toward(event.affects))
            goal_relevance = max(goal_relevance, _clip(agent.empathic_trait * (0.25 + 0.75 * attitude)))

        # 道德见证（无论对象）经共情与正义目标传导
        if event.moral is not None:
            justice_importance = agent.goal_importance("justice")
            moral_relevance = _clip(
                0.4 * agent.empathic_trait + 0.6 * justice_importance
            )
            goal_relevance = max(goal_relevance, moral_relevance * _clip(event.moral.severity + 0.2))

        # 结构化事件的内隐需要（评价理论：这些事件触及不需要显式 goal_impacts 注解的需要）
        if event.bond is not None:
            # 依恋需要：关系变化本身即相关（骤增/断裂都是强扳机，§1.5.8/§1.5.5）
            bond_mag = event.bond.delta if not event.bond.break_up else 1.0
            goal_relevance = max(goal_relevance, _clip(0.3 + 0.7 * bond_mag))
        if event.social is not None:
            # 自尊需要：社会比较默认触及（§2.5 G）
            goal_relevance = max(goal_relevance, max(0.35, 0.8 * agent.goal_importance("esteem")))
        if event.aesthetic is not None:
            # 审美：内在愉悦度主导，但仍需基线相关（§3.3 审美族要点）
            goal_relevance = max(goal_relevance, 0.45)
        if event.category.value == "H_novelty" and goal_relevance < 0.3:
            # 认识性需要：信息缺口基线相关，开放性调制
            goal_relevance = max(goal_relevance, _clip(0.25 + 0.3 * agent.personality.openness))
        if event.category.value == "J_body" and event.pleasantness != 0.0:
            # 内感受显著性感：身体状态变化本身即相关（§2.5 J；岛叶内感受）
            goal_relevance = max(goal_relevance, _clip(0.3 + 0.4 * abs(event.pleasantness)))

        # ---- SEC② 含义 ----
        if touched:
            w_sum = sum(imp for _, _, imp in touched)
            conduciveness = sum(delta * imp for _, delta, imp in touched) / max(w_sum, 1e-6)
        else:
            conduciveness = 0.0
        causality_agent = event.caused_by if event.caused_by not in ("", None) else None
        if causality_agent == agent.agent_id:
            causality_agent = "self"

        # ---- SEC③ 应对潜力（人格参与：控制/力量/调整是主体属性，§4.2）----
        default_control = _clip(0.35 + 0.4 * agent.personality.conscientiousness - 0.2 * agent.personality.neuroticism)
        control = default_control if event.control_hint is None else _clip(event.control_hint)
        power = _clip(0.3 + 0.5 * (1 - agent.personality.neuroticism) + 0.2 * agent.regulation_capacity)
        adjustment = _clip(0.25 + 0.35 * agent.personality.openness + 0.4 * agent.regulation_capacity)

        # ---- SEC④ 规范意义 ----
        moral = event.moral
        external_standard = 0.0
        internal_standard = 0.0
        if moral is not None:
            sign = 1.0 if moral.virtue else -1.0
            external_standard = sign * _clip(moral.severity)
        is_self_caused = causality_agent == "self"
        if is_self_caused:
            if moral is not None:
                internal_standard = (1.0 if moral.virtue else -1.0) * _clip(moral.severity)
            elif conduciveness > 0:
                internal_standard = _clip(0.7 * conduciveness * max(goal_relevance, 0.3))
            elif conduciveness < 0:
                internal_standard = -_clip(0.3 * -conduciveness)
        elif event.aesthetic is not None:
            internal_standard = 0.0  # 审美：目标相关性退居次要（§3.3 审美族要点）

        # ---- OCC 分支判定（可多分支；primary 按特异性排序）----
        branches: list[OCCBranch] = []
        if event.social is not None:
            branches.append(OCCBranch.SOCIAL_COMPARISON)
        if event.bond is not None:
            branches.append(OCCBranch.BOND)
        if event.justice_restored > 0.05:
            branches.append(OCCBranch.JUSTICE)
        if event.aesthetic is not None and not touched:
            branches.append(OCCBranch.AESTHETIC)
        if moral is not None and not is_self_caused and causality_agent is not None:
            branches.append(OCCBranch.AGENCY_OTHER)
        if moral is not None and is_self_caused:
            branches.append(OCCBranch.AGENCY_SELF)
        if causality_agent is not None and not touched and event.pleasantness != 0.0:
            branches.append(OCCBranch.ATTRACTION)
        if event.affects not in ("self", agent.agent_id) and event.social is None and event.bond is None:
            branches.append(OCCBranch.FORTUNES_OF_OTHERS)
        if event.probability < 0.95 and touched:
            branches.append(OCCBranch.PROSPECTS)
        if event.category.value == "H_novelty" or event.insight or (novelty > 0.4 and not touched):
            branches.append(OCCBranch.EPISTEMIC)
        if touched:
            branches.append(OCCBranch.CONSEQUENCES)

        # 特异性优先：比较/联结/正义/审美 > 归因 > 前景 > 认识 > 后果
        priority = [
            OCCBranch.SOCIAL_COMPARISON,
            OCCBranch.BOND,
            OCCBranch.JUSTICE,
            OCCBranch.AESTHETIC,
            OCCBranch.AGENCY_OTHER,
            OCCBranch.AGENCY_SELF,
            OCCBranch.FORTUNES_OF_OTHERS,
            OCCBranch.EPISTEMIC,
            OCCBranch.PROSPECTS,
            OCCBranch.ATTRACTION,
            OCCBranch.CONSEQUENCES,
        ]
        ordered = tuple(b for b in priority if b in branches) or (OCCBranch.CONSEQUENCES,)

        return AppraisalResult(
            novelty=novelty,
            pleasantness=pleasantness,
            goal_relevance=_clip(goal_relevance),
            conduciveness=max(-1.0, min(1.0, conduciveness)),
            causality_agent=causality_agent,
            causality_intent=event.intent,
            outcome_probability=_clip(event.probability),
            expectancy_violation=_clip(event.expectancy_violation),
            urgency=_clip(event.urgency),
            control=control,
            power=power,
            adjustment=adjustment,
            internal_standard=max(-1.0, min(1.0, internal_standard)),
            external_standard=max(-1.0, min(1.0, external_standard)),
            occ_branches=ordered,
            primary_branch=ordered[0],
            safety_frame=_clip(event.safety_frame),
            fictionality=_clip(event.fictionality),
            affects=event.affects,
            n_goals_affected=n_goals,
        )
