"""LLM 客户端封装（OpenAI 兼容格式）"""

import json
import time
from openai import OpenAI
from rich.console import Console

console = Console()


class LLMClient:

    def __init__(self, config: dict):
        llm_cfg = config.get("llm", {})
        pipe_cfg = config.get("pipeline", {})

        self.api_key = llm_cfg.get("api_key", "")
        self.base_url = llm_cfg.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        self.model = llm_cfg.get("model", "glm-4-flash")
        self.model_advanced = llm_cfg.get("model_advanced", "glm-4-plus")
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.temperature = llm_cfg.get("temperature", 0.3)

        self.retry = pipe_cfg.get("retry_on_failure", 2)
        self.verbose = pipe_cfg.get("verbose", False)

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: list,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        model = model or self.model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        for attempt in range(1, self.retry + 2):
            try:
                if self.verbose:
                    console.print(f"[dim][LLM] model={model}, attempt={attempt}[/dim]")

                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens and max_tokens > 0:
                    kwargs["max_tokens"] = max_tokens

                resp = self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content.strip()

            except Exception as e:
                console.print(f"[red][LLM 错误] 第 {attempt} 次调用失败: {e}[/red]")
                if attempt <= self.retry:
                    time.sleep(5 * attempt)
                else:
                    raise RuntimeError(f"LLM 调用失败（已重试 {self.retry} 次）: {e}") from e

    def chat_json(self, messages: list, model: str = None) -> dict | list:
        json_hint = "\n\n请严格以 JSON 格式返回结果，不要包含 markdown 代码块标记。"
        patched = list(messages)
        if patched and patched[-1]["role"] == "user":
            patched[-1] = {
                "role": patched[-1]["role"],
                "content": patched[-1]["content"] + json_hint,
            }
        else:
            patched.append({"role": "user", "content": json_hint})

        raw = self.chat(patched, model=model)

        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            console.print(f"[red][JSON 解析失败] {e}[/red]")
            console.print(f"[dim]{text[:500]}[/dim]")
            raise
