# -*- coding: utf-8 -*-
"""真实 LLM 端到端验收：叙事 → CLI 抽取 Event → 引擎全管线 → 中文表达。

双供应商交叉（用户授权；档位按模型路由 SOP 结构化抽取轻量档）：
  - claude CLI：--model sonnet → GLM 网关 glm-5.3-flash[1M]
  - codex CLI：gpt-6-luna，model_reasoning_effort=low（headless read-only）

每家跑同一段两事件叙事（当众羞辱 → 客户还名），依次注入同一引擎：
事件1（道德越界）应出义愤/委屈族；事件2（正义恢复）应触 发解气/爽族（跨事件 charges 机制）。

用法：
  python examples/llm_e2e.py [--log .tasks/llm-e2e-log.md] [--timeout 240]
CLI 缺席时对应供应商标记 SKIP 后退出码 0（离线环境不阻断）。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    from emotion_os import AgentProfile, EmotionEngine
    from emotion_os.adapters import (
        CLICallError,
        CLIUnavailableError,
        EntityResolver,
        ParseOutcome,
        build_extraction_prompt,
        claude_cli_call,
        codex_cli_call,
        parse_event,
    )
except ImportError:   # 仓库内裸跑（未安装）：从仓库根解析
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from emotion_os import AgentProfile, EmotionEngine
    from emotion_os.adapters import (
        CLICallError,
        CLIUnavailableError,
        EntityResolver,
        ParseOutcome,
        build_extraction_prompt,
        claude_cli_call,
        codex_cli_call,
        parse_event,
    )

NARRATIVE_EVENTS = [
    # 事件1：道德越界（预测：义愤/委屈族）
    "办公室里，主管当众把小林熬夜两周做出的方案贬低为「实习生水平」，"
    "还把署名改成了自己，周围同事跟着哄笑。",
    # 事件2：正义恢复（预测：解气/爽族——依赖事件1建立的 charges）
    "第二天客户视频会上，客户当场点名只要小林署名的原版方案，"
    "并质问主管为什么隐瞒真实作者，主管当众语塞道歉。",
]

PROVIDERS = [
    ("claude", "claude CLI · glm-5.3-flash[1M]（--model sonnet，GLM 网关）", claude_cli_call),
    ("codex", "codex CLI · gpt-6-luna · effort=low（headless read-only）", codex_cli_call),
]


def extract_with_retry(narrative: str, llm_call, timeout: float, lines: list[str],
                       resolver: EntityResolver | None = None,
                       goal_ids: list[str] | None = None,
                       goal_aliases: dict[str, str] | None = None):
    """三步编排（prompt→CLI→parse→归一/映射），失败带原始返回留证并自纠错重试一次。"""
    from emotion_os.adapters import EventParseError

    def build_prompt() -> str:
        p = build_extraction_prompt(narrative, goal_ids=goal_ids)
        if resolver is not None:
            hint = resolver.roster_hint()
            if hint:
                p = f"{p}\n\n{hint}"
        return p

    prompt = build_prompt()
    last_raw = ""
    for attempt in (1, 2):
        try:
            raw = llm_call(prompt, timeout=timeout)
            last_raw = raw
            outcome = parse_event(raw)
            warnings = list(outcome.warnings)
            event = outcome.event
            if resolver is not None:
                event = resolver.resolve_event(event)
            if goal_ids is not None or goal_aliases:
                from emotion_os.adapters.nl_event import map_goal_impacts
                event = map_goal_impacts(event, goal_ids, goal_aliases or {}, warnings)
            return raw, ParseOutcome(event=event, warnings=warnings)
        except EventParseError as exc:
            lines.append(f"- 尝试{attempt} 解析失败：{exc}；原始返回（前 400 字）：\n  ```\n  {last_raw[:400]}\n  ```")
            if attempt == 2:
                raise
            prompt = (
                f"{build_prompt()}\n\n"
                f"你上次的返回不符合契约（{exc}）。只输出符合契约的 JSON 对象，"
                "category 必须是给定的枚举值之一，不要输出 error 字段或任何解释。"
            )
    raise RuntimeError("unreachable")


def run_provider(name: str, label: str, llm_call, timeout: float, lines: list[str]) -> bool:
    agent = AgentProfile.neurotic_example()
    engine = EmotionEngine(agent)
    # v0.4 跨事件实体规范化：prompt 注入已见实体（主防线）+ parse 后别名/已见归一（兜底）
    resolver = EntityResolver(aliases={"supervisor": "主管"})
    # v0.5 goal id 契约化：prompt 注入主体目标词表 + 自由格式键别名映射
    goal_ids = list(agent.goals.keys())
    goal_aliases = {
        "方案获认可与署名": "esteem", "作品署名获得认可": "esteem", "职业声誉": "esteem",
        "原版方案署名获认可": "esteem", "safety": "safety", "esteem": "esteem",
    }
    lines.append(f"\n## {label}\n")
    for idx, narrative in enumerate(NARRATIVE_EVENTS, 1):
        t0 = time.perf_counter()
        try:
            raw, outcome = extract_with_retry(
                narrative, llm_call, timeout, lines, resolver, goal_ids, goal_aliases)
        except CLIUnavailableError as exc:
            if idx == 1:
                lines.append(f"- SKIP：{type(exc).__name__}: {exc}")
                print(f"[{name}] SKIP: {exc}")
                return False
            raise
        dt = time.perf_counter() - t0
        ev = outcome.event
        lines.append(f"### 事件{idx}（{dt:.1f}s）")
        lines.append(f"- 叙事：{narrative}")
        lines.append(f"- CLI 原始返回：\n  ```json\n  {raw.strip()[:800]}\n  ```")
        lines.append(f"- 抽取：category=`{ev.category.value}` intent=`{ev.intent.value}` "
                     f"novelty={ev.novelty:.2f} pleasantness={ev.pleasantness:+.2f}")
        if ev.moral is not None:
            lines.append(f"  - moral: severity={ev.moral.severity:.2f} violator=`{ev.moral.violator}`")
        if idx == 2 and ev.justice_target:
            lines.append(f"  - justice_restored={ev.justice_restored:.2f} target=`{ev.justice_target}`")
        if outcome.warnings:
            lines.append(f"- 解析警告：{outcome.warnings}")
        if resolver.renames:
            lines.append(f"- 实体归一（v0.4）：{resolver.renames}")
        if ev.goal_impacts:
            lines.append(f"- goal_impacts（v0.5 契约化后）：{ev.goal_impacts}")

        result = engine.process(ev, dt_minutes=3.0)
        top = sorted(result.episodes, key=lambda e: -e.intensity)[:4]
        words = "、".join(f"{e.category}({e.intensity:.2f})" for e in top if e.intensity > 0.04)
        lines.append(f"- 引擎输出：{words or '（无显著激活）'}")
        lines.append(f"- 中文表达：{result.expression.summary}")
        print(f"[{name}] 事件{idx}: {result.expression.summary[:60]}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", default=None, help="证据日志路径（默认 .tasks/llm-e2e-log.md，追加）")
    ap.add_argument("--timeout", type=float, default=240.0)
    args = ap.parse_args()

    log_path = Path(args.log) if args.log else Path(__file__).resolve().parents[1] / ".tasks" / "llm-e2e-log.md"
    lines: list[str] = [f"\n\n# LLM 端到端运行 {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
                        f"- 叙事：{len(NARRATIVE_EVENTS)} 个事件；agent=neurotic_example；dt=3min"]
    ok = 0
    for name, label, call in PROVIDERS:
        try:
            if run_provider(name, label, call, args.timeout, lines):
                ok += 1
        except Exception as exc:  # 第二事件失败才到这里
            lines.append(f"- 失败：{type(exc).__name__}: {exc}")
            print(f"[{name}] FAILED: {exc}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\n供应商贯通 {ok}/{len(PROVIDERS)}；日志 → {log_path}")
    return 0 if ok == len(PROVIDERS) else 1


if __name__ == "__main__":
    sys.exit(main())
