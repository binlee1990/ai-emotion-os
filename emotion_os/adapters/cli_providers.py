# -*- coding: utf-8 -*-
"""CLI LLM 调用包装：注入 NLEventAdapter.llm_call 的真实供应商实现。

双供应商交叉（用户授权「claude CLI 与 codex CLI，各供应商最适合的模型与 effort」），
档位依据模型路由 SOP「结构化抽取」取各供应商轻量档：

- claude CLI：``claude -p <prompt> --model sonnet``。本机 GLM 网关
  （ANTHROPIC_BASE_URL=open.bigmodel.cn）把别名 sonnet 映射为 glm-5.3-flash[1M]
  （SOP 的 glm-flash 抽取档）；别名 haiku 在该网关映射 glm-5.3-flashx（订阅未开放，
  实测 429），故不用。stdout 即纯回复，网关警告走 stderr 已分离。
- codex CLI：``codex exec -m gpt-6-luna -c model_reasoning_effort="low"
  --output-last-message <tmp> <prompt>``（headless；默认 read-only 沙箱、
  approval=never，无副作用）。最终消息写入临时文件，绕开 banner 解析。

两者均为零第三方依赖（subprocess + shutil.which）。CLI 缺席抛 CLIUnavailableError，
非零退出/超时抛 CLICallError。CLI 不在 PATH 的环境（含 CI）由单元测试 skipif 处理。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 180.0
CODEX_EFFORT = "low"  # SOP：结构化抽取低推理档


class CLIUnavailableError(RuntimeError):
    """CLI 可执行文件不在 PATH。"""


class CLICallError(RuntimeError):
    """CLI 调用非零退出或超时（保留 stderr 摘要）。"""


def _which(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise CLIUnavailableError(f"{name} CLI 不在 PATH")
    return resolved


def claude_cli_call(prompt: str, *, timeout: float = DEFAULT_TIMEOUT, model: str = "sonnet") -> str:
    """claude CLI 单轮文本调用（prompt 进、纯回复出）。"""
    exe = _which("claude")
    try:
        proc = subprocess.run(
            [exe, "-p", prompt, "--model", model],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CLICallError(f"claude CLI 超时（>{timeout:.0f}s）") from exc
    if proc.returncode != 0:
        raise CLICallError(f"claude CLI 退出码 {proc.returncode}: {proc.stderr.strip()[:300]}")
    return proc.stdout.strip()


def codex_cli_call(prompt: str, *, timeout: float = DEFAULT_TIMEOUT, model: str = "gpt-6-luna") -> str:
    """codex CLI headless 单轮调用（read-only 沙箱；--output-last-message 取纯回复）。

    prompt 经 stdin 传入（codex 的 "additional input from stdin" 通道）：实测
    Windows 下位置参数携带长 prompt（契约 ~1.3K 字符）会被截断/破坏——模型侧
    表现为「未提供叙事文本」；stdin 传递完整可靠。位置参数只留极简指令。
    """
    exe = _which("codex")
    with tempfile.TemporaryDirectory(prefix="codex-msg-") as tmp_dir:
        msg_path = Path(tmp_dir) / "last.txt"
        try:
            proc = subprocess.run(
                [exe, "exec", "-m", model, "-c", f'model_reasoning_effort="{CODEX_EFFORT}"',
                 "--output-last-message", str(msg_path), "按 stdin 提供的指示执行，只输出指示要求的内容"],
                input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise CLICallError(f"codex CLI 超时（>{timeout:.0f}s）") from exc
        if proc.returncode != 0:
            raise CLICallError(f"codex CLI 退出码 {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}")
        if not msg_path.exists():
            raise CLICallError("codex CLI 未写出 last-message 文件")
        return msg_path.read_text(encoding="utf-8").strip()
