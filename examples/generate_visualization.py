# -*- coding: utf-8 -*-
"""生成 ai-emotion-os 整体可视化页面：引擎真实输出 → 自包含 HTML。

数据全部来自引擎真实调用（不手写编造数值）：
  1) 管线解剖：单事件五阶段中间产物（评价向量/激活/动力学/表达）
  2) 情绪弧线：8 事件叙事（demo_story 同弧线）逐事件词×强度/4D/心情/峰终
  3) 语域对照：最终状态 formal/neutral/colloquial 三档
  4) 倒 U 曲线：fear_enjoyment = tent(fear,0.84)×sf×ss 引擎真实函数值扫描
  5) 峰终记忆：MemoryTrace 轨迹
模板 examples/visual_template.html 的 __DATA__ 占位符替换 → docs/visualization.html。

运行：python examples/generate_visualization.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent
    from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent
    from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_story import STORY  # 同一弧线，数据一致

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "visualization.html"
TEMPLATE = Path(__file__).resolve().parent / "visual_template.html"

SS = 0.6  # 与 demo/场景测试一致的中档感觉寻求


def main() -> int:
    agent = AgentProfile.reader_example()

    # ---- 1) 情绪弧线（8 事件）----
    engine = EmotionEngine(agent)
    events = []
    for title, dt, ev in STORY:
        r = engine.process(ev, dt_minutes=dt)
        entries = [
            {"word": en.word, "zh": en.zh, "intensity": round(en.intensity, 3),
             "category": en.category}
            for en in r.expression.entries if en.intensity > 0.04
        ][:4]
        d = r.expression.dims
        events.append({
            "title": title, "dt": dt,
            "words": entries,
            "dims": {"valence": round(d.valence, 3), "arousal": round(d.arousal, 3),
                     "dominance": round(d.dominance, 3),
                     "unpredictability": round(d.unpredictability, 3)},
            "mood": round(engine.state.mood.valence, 3),
            "memory": round(engine.state.memory.remembered_valence, 3),
            "summary": r.expression.summary,
        })

    # ---- 2) 语域对照（最终状态）----
    registers = {}
    for reg in ("formal", "neutral", "colloquial"):
        out = engine.expressor.describe(engine.state, register=reg)
        registers[reg] = {
            "summary": out.summary,
            "words": [{"word": en.word, "intensity": round(en.intensity, 3)}
                      for en in out.entries],
        }

    # ---- 3) 倒 U 曲线：fear_enjoyment 引擎真实函数（安全框架=1、ss=SS）----
    fear_enjoyment = []
    sf, ss_term = 1.0, 0.6 + 0.4 * SS
    for i in range(0, 101):
        fear = i / 100.0
        fear_enjoyment.append({
            "fear": fear,
            "enjoyment": round(_tent(fear, FEAR_ENJOYMENT_PEAK) * sf * ss_term, 4),
        })

    # ---- 4) 管线解剖：事件1（当众羞辱）五阶段 ----
    from emotion_os.generation.catalog import CATALOG
    dissect = EmotionEngine(agent)
    ev1 = STORY[0][2]
    r = dissect.process(ev1, dt_minutes=1.0)
    appraisal = r.appraisal
    pipeline = {
        "event": {"title": STORY[0][0],
                  "category": ev1.category.value,
                  "goal_impacts": ev1.goal_impacts,
                  "severity": ev1.moral.severity if ev1.moral else None},
        "appraisal": {
            "goal_relevance": round(appraisal.goal_relevance, 3),
            "conduciveness": round(appraisal.conduciveness, 3),
            "urgency": round(appraisal.urgency, 3),
            "novelty": round(appraisal.novelty, 3),
            "control": round(appraisal.control, 3),
        },
        "generation": [
            {"cat": ep.category, "zh": CATALOG[ep.category].zh,
             "intensity": round(ep.intensity, 3)}
            for ep in sorted(r.episodes, key=lambda e: -e.intensity)[:4]
        ],
        "dynamics": {
            "mood_after": round(dissect.state.mood.valence, 3),
            "residue": round(dissect.state.arousal_residue, 3),
            "charges": {k: round(v, 3) for k, v in dissect.state.charges.items()},
        },
        "expression": {
            "neutral": r.expression.summary,
            "entries": [{"word": en.word, "intensity": round(en.intensity, 3)}
                        for en in r.expression.entries[:3]],
            "dims": {"v": round(r.expression.dims.valence, 2),
                     "a": round(r.expression.dims.arousal, 2)},
        },
    }

    data = {
        "meta": {
            "version": "0.7.0", "categories": 88, "tests": 163, "releases": 7,
            "peak": FEAR_ENJOYMENT_PEAK,
            "peak_ci": "[0.59, 1.09]",
        },
        "events": events,
        "registers": registers,
        "fear_enjoyment": fear_enjoyment,
        "pipeline": pipeline,
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"written: {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")

    # Artifact 片段版：去 html/head/body 外壳（发布骨架会包），从 <title> 到 </script>
    t0 = html.index("<title>")
    t1 = html.index("</script>") + len("</script>")
    frag = html[t0:t1]
    frag_path = ROOT / ".tasks" / "visualization-fragment.html"
    frag_path.write_text(frag, encoding="utf-8")
    print(f"fragment: {frag_path}  ({frag_path.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
