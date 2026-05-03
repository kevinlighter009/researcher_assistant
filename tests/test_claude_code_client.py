from unittest.mock import MagicMock

import pytest

from lib.llm.claude_code_client import ClaudeCodeClient


def test_claude_code_client_invokes_subprocess(mocker):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "thinking...\n<result>final answer</result>\nbye\n"
    fake.stderr = ""
    run = mocker.patch("lib.llm.claude_code_client.subprocess.run",
                       return_value=fake)
    c = ClaudeCodeClient(binary="claude")
    out = c.complete(system="be helpful", user="hello")
    assert out == "final answer"
    args, kwargs = run.call_args
    cmd = args[0]
    assert cmd[0] == "claude"
    assert "-p" in cmd
    # combined system+user passed via stdin
    assert kwargs["input"]
    assert "be helpful" in kwargs["input"]
    assert "hello" in kwargs["input"]


def test_claude_code_client_no_result_tag_returns_full_stdout(mocker):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "raw answer with no tags"
    fake.stderr = ""
    mocker.patch("lib.llm.claude_code_client.subprocess.run",
                 return_value=fake)
    c = ClaudeCodeClient(binary="claude")
    assert c.complete(system="s", user="u") == "raw answer with no tags"


def test_claude_code_client_raises_on_failure(mocker):
    fake = MagicMock()
    fake.returncode = 2
    fake.stdout = ""
    fake.stderr = "boom"
    mocker.patch("lib.llm.claude_code_client.subprocess.run",
                 return_value=fake)
    c = ClaudeCodeClient(binary="claude")
    with pytest.raises(RuntimeError, match="claude CLI failed"):
        c.complete(system="s", user="u")
