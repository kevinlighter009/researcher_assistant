from unittest.mock import MagicMock

from lib.llm.anthropic_client import AnthropicClient


def test_anthropic_client_calls_sdk(mocker):
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="hi there")]
    fake_anthropic = MagicMock()
    fake_anthropic.messages.create.return_value = fake_msg
    mocker.patch("lib.llm.anthropic_client.Anthropic",
                 return_value=fake_anthropic)
    c = AnthropicClient(api_key="sk-ant-x", model="m1",
                        default_max_tokens=100, default_temperature=0.1)
    out = c.complete(system="sys", user="usr")
    assert out == "hi there"
    fake_anthropic.messages.create.assert_called_once()
    kwargs = fake_anthropic.messages.create.call_args.kwargs
    assert kwargs["model"] == "m1"
    assert kwargs["system"] == "sys"
    assert kwargs["max_tokens"] == 100
    assert kwargs["temperature"] == 0.1
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]


def test_anthropic_client_respects_overrides(mocker):
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="ok")]
    fake = MagicMock()
    fake.messages.create.return_value = fake_msg
    mocker.patch("lib.llm.anthropic_client.Anthropic", return_value=fake)
    c = AnthropicClient(api_key="k", model="m", default_max_tokens=10,
                        default_temperature=0.0)
    c.complete(system="s", user="u", max_tokens=999, temperature=0.7)
    kwargs = fake.messages.create.call_args.kwargs
    assert kwargs["max_tokens"] == 999
    assert kwargs["temperature"] == 0.7
