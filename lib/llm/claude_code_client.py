"""LLMClient that shells out to the `claude` CLI in non-interactive mode."""
from __future__ import annotations

import re
import subprocess


_RESULT_RE = re.compile(r"<result>(.*?)</result>", re.DOTALL)

_PROMPT_TEMPLATE = """\
{system}

You MUST wrap your final answer in <result>...</result> tags. \
Do not include anything else inside the tags. \
Reasoning, tool use, and explanations may appear outside the tags.

USER REQUEST:
{user}
"""


class ClaudeCodeClient:
    def __init__(self, *, binary: str = "claude"):
        self.binary = binary

    def complete(
        self, *, system: str, user: str,
        max_tokens: int = 4096, temperature: float = 0.2,
    ) -> str:
        prompt = _PROMPT_TEMPLATE.format(system=system, user=user)
        # `claude -p` reads prompt from argv; stdin is also accepted on newer
        # builds. We pass via stdin for robustness (no argv length limits).
        proc = subprocess.run(
            [self.binary, "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (rc={proc.returncode}): {proc.stderr.strip()}"
            )
        m = _RESULT_RE.search(proc.stdout)
        return m.group(1).strip() if m else proc.stdout.strip()
