# -*- coding: utf-8 -*-
"""离线端到端演示：8 事件短剧弧线 → 逐事件情绪轨迹表（词+强度+4D+心情+记忆评分）。

无 LLM、无网络：结构化 Event 驱动（v0.1 接口边界），展示引擎全管线
（评价→生成→动力学→调节→表达）与三层状态（情绪/心情/峰终记忆）。

弧线设计（§5.4 爽感引擎/§3.3 十二族）：憋屈铺垫(1-2) → 转机(3-4) →
压力回升(5) → 反杀打脸(6-7) → 亲情和解收尾(8, HE 峰终)。
运行：python examples/demo_story.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent
from emotion_os.core.event import BondInfo, MoralInfo

STORY: list[tuple[str, float, Event]] = [
    ("反派当众羞辱主角", 1.0, Event(
        category=EventCategory.VIOLATION, affects="self", caused_by="villain",
        intent=Intent.DELIBERATE, goal_impacts={"esteem": -0.8},
        novelty=0.6, pleasantness=-0.8, expectancy_violation=0.6, probability=1.0,
        moral=MoralInfo(severity=0.8, victim="self", violator="villain", virtue=False),
    )),
    ("求助无门，孤立无援", 30.0, Event(
        category=EventCategory.FRUSTRATION, affects="self", caused_by="crowd",
        intent=Intent.UNKNOWN, goal_impacts={"esteem": -0.4, "bond": -0.3},
        novelty=0.2, pleasantness=-0.6, expectancy_violation=0.4,
        probability=1.0, control_hint=0.2,
    )),
    ("贵人暗中相助", 120.0, Event(
        category=EventCategory.BOND, affects="self", caused_by="mentor",
        intent=Intent.DELIBERATE, goal_impacts={"bond": 0.4},
        novelty=0.7, pleasantness=0.7,
        bond=BondInfo(delta=0.45, sudden=False, break_up=False, romantic=False),
    )),
    ("闭关修炼，信心渐复", 1440.0, Event(
        category=EventCategory.ACHIEVEMENT, affects="self", caused_by="self",
        intent=Intent.DELIBERATE, goal_impacts={"esteem": 0.3},
        novelty=0.3, pleasantness=0.6, effort=0.9, probability=1.0,
    )),
    ("反派再挑衅，赌上全部", 60.0, Event(
        category=EventCategory.VIOLATION, affects="self", caused_by="villain",
        intent=Intent.DELIBERATE, goal_impacts={"esteem": -0.5},
        novelty=0.5, pleasantness=-0.7, expectancy_violation=0.5,
        probability=1.0, urgency=0.8,
        moral=MoralInfo(severity=0.7, victim="self", violator="villain", virtue=False),
    )),
    ("当众反杀，一战成名", 10.0, Event(
        category=EventCategory.ACHIEVEMENT, affects="self", caused_by="self",
        intent=Intent.DELIBERATE, goal_impacts={"esteem": 0.8, "craft": 0.6},
        novelty=0.9, pleasantness=0.95, expectancy_violation=0.95,
        probability=0.2, urgency=0.9, effort=0.9,
        prior_adversity_resolved=True,
        justice_restored=0.9, justice_target="villain",
    )),
    ("反派身败名裂，众人声讨", 45.0, Event(
        category=EventCategory.ACHIEVEMENT, affects="villain",
        caused_by="public", intent=Intent.DELIBERATE,
        goal_impacts={"justice": 0.7},
        novelty=0.7, pleasantness=0.8, expectancy_violation=0.6,
        probability=1.0, justice_restored=0.85, justice_target="villain",
    )),
    ("失散亲人重逢相拥", 180.0, Event(
        category=EventCategory.BOND, affects="self", caused_by="family",
        intent=Intent.DELIBERATE, goal_impacts={"bond": 0.7},
        novelty=0.85, pleasantness=0.9,
        bond=BondInfo(delta=0.9, sudden=True, break_up=False, romantic=False),
    )),
]


def main() -> int:
    agent = AgentProfile.reader_example()
    engine = EmotionEngine(agent)
    print(f"demo_story —— 8 事件短剧弧线（agent={agent.agent_id}，dt=事件间隔分钟）\n")
    header = f"{'#':<2} {'事件':<12} {'情绪表达(词×强度)':<26} {'4D  V/A/D/P':<22} {'心情V':>6} {'记忆':>6}"
    print(header)
    print("-" * len(header))
    for i, (title, dt, ev) in enumerate(STORY, 1):
        r = engine.process(ev, dt_minutes=dt)
        words = "、".join(
            f"{en.word}×{en.intensity:.2f}" for en in r.expression.entries[:3]
        ) or "（平静）"
        d = r.expression.dims
        dims = f"{d.valence:+.2f}/{d.arousal:.2f}/{d.dominance:+.2f}/{d.unpredictability:.2f}"
        mood = engine.state.mood.valence
        mem = engine.state.memory.remembered_valence
        print(f"{i:<2} {title:<12} {words:<26} {dims:<22} {mood:>+6.2f} {mem:>+6.2f}")
        print(f"   └ {r.expression.summary}")

    peak_ep = max(engine.state.episodes.values(), key=lambda e: e.intensity) \
        if engine.state.episodes else None
    peak_cat = peak_ep.category if peak_ep else "-"
    print("\n收束：")
    print(f"  记忆评分（峰终）= {engine.state.memory.remembered_valence:+.2f}"
          f"（峰值×0.5 + 终值×0.5；HE 收尾 → 正分）")
    print(f"  当前最强残留 = {peak_cat}；心情 valence = {engine.state.mood.valence:+.2f}")

    # v0.6 语域对照：同一最终状态在三种场合的表达
    print("\n语域对照（同一状态，三种场合；lexicon 语域梯，自设标注）：")
    for reg, label in (("formal", "对外正式"), ("neutral", "通用（默认）"), ("colloquial", "私下口语")):
        out = engine.expressor.describe(engine.state, register=reg)
        print(f"  {label:<8} {out.summary or '（平静）'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
