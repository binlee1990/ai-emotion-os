# -*- coding: utf-8 -*-
"""cli_providers 单元测试：错误路径全测；真实调用在 CLI 缺席环境 skipif 跳过。"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from emotion_os.adapters.cli_providers import (
    CLICallError,
    CLIUnavailableError,
    claude_cli_call,
    codex_cli_call,
)

CLAUDE_OK = shutil.which("claude") is not None
CODEX_OK = shutil.which("codex") is not None


class TestErrorPaths:
    def test_claude_missing_raises(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        with pytest.raises(CLIUnavailableError):
            claude_cli_call("x")

    def test_codex_missing_raises(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        with pytest.raises(CLIUnavailableError):
            codex_cli_call("x")

    def test_claude_nonzero_exit_raises(self, monkeypatch):
        cmd_path = shutil.which("cmd") or "cmd"
        monkeypatch.setattr(shutil, "which", lambda name: cmd_path)
        monkeypatch.setattr(
            "emotion_os.adapters.cli_providers.subprocess.run",
            lambda *a, **k: subprocess.CompletedProcess(a, returncode=1, stdout="", stderr="boom"),
        )
        with pytest.raises(CLICallError):
            claude_cli_call("x", timeout=30)

    def test_codex_nonzero_exit_raises(self, monkeypatch):
        cmd_path = shutil.which("cmd") or "cmd"
        monkeypatch.setattr(shutil, "which", lambda name: cmd_path)

        def fake_run(*a, **k):
            # codex 路径依赖临时文件：写空文件后返回非零
            for arg in a[0]:
                if str(arg).endswith(".txt"):
                    Path(arg).write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(a, returncode=1, stdout="", stderr="boom")

        monkeypatch.setattr("emotion_os.adapters.cli_providers.subprocess.run", fake_run)
        with pytest.raises(CLICallError):
            codex_cli_call("x", timeout=30)

    def test_claude_timeout_raises_clicallerror(self, monkeypatch):
        """文档契约：超时也走 CLICallError（非裸 TimeoutExpired）。"""
        cmd_path = shutil.which("cmd") or "cmd"
        monkeypatch.setattr(shutil, "which", lambda name: cmd_path)

        def fake_run(*a, **k):
            raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

        monkeypatch.setattr("emotion_os.adapters.cli_providers.subprocess.run", fake_run)
        with pytest.raises(CLICallError, match="超时"):
            claude_cli_call("x", timeout=1)

    def test_codex_timeout_raises_clicallerror(self, monkeypatch):
        cmd_path = shutil.which("cmd") or "cmd"
        monkeypatch.setattr(shutil, "which", lambda name: cmd_path)
        monkeypatch.setattr(
            "emotion_os.adapters.cli_providers.subprocess.run",
            lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd="codex", timeout=1)),
        )
        with pytest.raises(CLICallError, match="超时"):
            codex_cli_call("x", timeout=1)

    def test_codex_zero_exit_but_missing_message_file_raises(self, monkeypatch):
        """退出码 0 但 last-message 文件缺失（异常 CLI 形态）。"""
        cmd_path = shutil.which("cmd") or "cmd"
        monkeypatch.setattr(shutil, "which", lambda name: cmd_path)
        monkeypatch.setattr(
            "emotion_os.adapters.cli_providers.subprocess.run",
            lambda *a, **k: subprocess.CompletedProcess(a, returncode=0, stdout="", stderr=""),
        )
        with pytest.raises(CLICallError, match="last-message"):
            codex_cli_call("x", timeout=30)


@pytest.mark.skipif(not CLAUDE_OK, reason="claude CLI 不在 PATH")
class TestRealClaudeCall:
    def test_roundtrip_plain_text(self):
        out = claude_cli_call("只输出两个字：可用", timeout=120)
        assert "可用" in out


@pytest.mark.skipif(not CODEX_OK, reason="codex CLI 不在 PATH")
class TestRealCodexCall:
    def test_roundtrip_plain_text(self):
        out = codex_cli_call("只输出两个字：可用", timeout=180)
        assert "可用" in out
