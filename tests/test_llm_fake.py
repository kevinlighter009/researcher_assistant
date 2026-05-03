import pytest

from lib.llm.fake import FakeLLMClient


def test_fake_returns_scripted():
    c = FakeLLMClient(responses=["hello", "world"])
    assert c.complete(system="s", user="u1") == "hello"
    assert c.complete(system="s", user="u2") == "world"


def test_fake_records_calls():
    c = FakeLLMClient(responses=["x"])
    c.complete(system="sys", user="usr", max_tokens=10, temperature=0.5)
    assert len(c.calls) == 1
    call = c.calls[0]
    assert call.system == "sys"
    assert call.user == "usr"
    assert call.max_tokens == 10
    assert call.temperature == 0.5


def test_fake_callable_response():
    def resp(system, user, **kw):
        return f"echo:{user}"
    c = FakeLLMClient(responses=resp)
    assert c.complete(system="s", user="hi") == "echo:hi"
    assert c.complete(system="s", user="bye") == "echo:bye"


def test_fake_runs_out():
    c = FakeLLMClient(responses=["only one"])
    c.complete(system="s", user="u")
    with pytest.raises(IndexError):
        c.complete(system="s", user="u")
