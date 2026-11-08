"""EmotionEngine：事件→评价→生成→动力学→调节→表达 的单入口编排（架构合同 §4.2）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from .appraiser import AppraisalEngine, AppraisalResult
from .core.agent import AgentProfile
from .core.event import Event
from .core.state import AffectState, EmotionEpisode
from .dynamics import AffectDynamics
from .expression import ExpressionOutput, Expressor
from .generation import EmotionGenerator
from .regulation import Strategy, reappraise, suppress


@dataclass(frozen=True)
class ProcessResult:
    appraisal: AppraisalResult
    episodes: list[EmotionEpisode]
    state: AffectState
    expression: ExpressionOutput
    habituation_multiplier: float = 1.0


class EmotionEngine:
    """管线编排。strategy 可在构造或 process 时指定（Gross 策略 id，见 regulation.Strategy）。"""

    def __init__(self, agent: AgentProfile, default_strategy: str | None = None) -> None:
        self.agent = agent
        self.appraiser = AppraisalEngine()
        self.generator = EmotionGenerator()
        self.dynamics = AffectDynamics()
        self.expressor = Expressor()
        self.state = AffectState()
        self.default_strategy = default_strategy

    def process(self, event: Event, dt_minutes: float = 1.0,
                strategy: str | None = None) -> ProcessResult:
        active = strategy or self.default_strategy

        # 0) 时间推进：距上一事件 dt 分钟——先衰减（发作/残余/记账/双池，R-DYN-01
        #    三层时间尺度）再生成。修复 v0.3 前的时序缺陷：生成先于时钟推进，
        #    事件间隔从未参与衰减（兴奋转移/残余读到的永远是上一事件结束瞬间的值）。
        if dt_minutes > 0:
            self.dynamics.tick(self.state, dt_minutes)

        # 1) 评价（评价先行）
        r = self.appraiser.appraise(event, self.agent)

        # 2) 生成前调节（重评类：改评价向量；效力含调节资源耗竭）
        if active in (Strategy.COGNITIVE_REAPPRAISAL, Strategy.ATTENTION_DEPLOYMENT):
            r = reappraise(r, self.agent, active, state=self.state)

        # 3) 生成（习惯化/敏感化乘数施加于发作强度）
        hab = self.dynamics.habituation_multiplier(event.stimulus_key, self.state, self.agent.sensitized_keys)
        gen = self.generator.generate(r, event, self.agent, self.state)
        episodes = [
            EmotionEpisode(
                category=ep.category,
                intensity=min(1.0, ep.intensity * hab),
                onset_min=ep.onset_min,
                half_life_min=ep.half_life_min,
                family=ep.family,
                wanting=ep.wanting,
                liking=ep.liking,
            )
            for ep in gen.episodes
        ]

        # 4) 动力学整合（惯性/心情/残余/峰终/反刍/对象记账）+ 习惯化计数
        repeat_stimulus = (
            event.stimulus_key is not None
            and self.state.habituation.get(event.stimulus_key, 0) >= 1
        )
        final_acts = {ep.category: ep.intensity for ep in episodes}
        charge_updates: dict[str, float] = {}
        if event.moral is not None and event.moral.violator:
            grievance = max(
                final_acts.get("indignation", 0.0),
                final_acts.get("wei_yuan", 0.0),
                final_acts.get("anger", 0.0),
            )
            if grievance > 0.05:
                charge_updates[event.moral.violator] = grievance   # R-APP-02 跨事件链
        if final_acts.get("malicious_envy", 0.0) > 0.05 and event.affects not in ("self", self.agent.agent_id):
            charge_updates[event.affects] = final_acts["malicious_envy"]  # R-APP-03 跨事件链
        self.dynamics.integrate(
            episodes, self.state,
            event_valence=gen.dims.valence,
            event_arousal=gen.dims.arousal,
            event_importance=r.goal_relevance,
            event_irreversibility=1.0 - event.reversibility,
            dt_minutes=0.0,   # 时钟已在第 0 步推进，这里只并入新发作
            charge_updates=charge_updates,
            repeat_stimulus=repeat_stimulus,
        )
        self.dynamics.record_stimulus(event.stimulus_key, self.state)

        # 5) 生成后调节（抑制：掩表达、留体验、付代价）
        suppressed = False
        if active == Strategy.RESPONSE_SUPPRESSION:
            suppress(self.state, self.agent)
            suppressed = True

        # 6) 表达（类别+维度双通道）
        expression = self.expressor.describe(self.state, suppressed=suppressed)
        return ProcessResult(
            appraisal=r,
            episodes=episodes,
            state=self.state,
            expression=expression,
            habituation_multiplier=hab,
        )
