"""Minimal client for llama.cpp's `llama-server`, stdlib-only (urllib).

Deliberately not using `requests` or an OpenAI SDK — on Termux, every extra
pip dependency is a chance to hit a package with no prebuilt ARM64/bionic
wheel that then needs a C compile. `urllib` ships with Python itself, so
this file has zero install risk.

Talks to llama-server's native `/completion` endpoint (not the OpenAI-
compatible `/v1/chat/completions` one) because it's simpler and exposes
`stop` sequences and `n_predict` directly without wrapping everything in
chat-message JSON.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error


class LlamaServerError(RuntimeError):
    pass


class LlamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def complete(self, prompt: str, max_tokens: int = 200, temperature: float = 0.2,
                 stop: list[str] | None = None) -> str:
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stop": stop or ["<|im_end|>", "\n\n\n"],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/completion",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise LlamaServerError(
                f"Could not reach llama-server at {self.base_url} — is it running? "
                f"(engine/setup_termux.sh starts it on port 8080). Original error: {e}"
            ) from e
        return body.get("content", "").strip()


QWEN_CHAT_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n"
)


def build_prompt(system: str, user: str) -> str:
    return QWEN_CHAT_TEMPLATE.format(system=system, user=user)


if __name__ == "__main__":
    import sys
    client = LlamaClient()
    if not client.health():
        print("llama-server not reachable at http://127.0.0.1:8080 — start it first "
              "(see engine/setup_termux.sh).")
        sys.exit(1)
    q = " ".join(sys.argv[1:]) or "Say hello in one short sentence."
    prompt = build_prompt(
        system="You are a concise assistant.",
        user=q,
    )
    print(client.complete(prompt, max_tokens=100))
