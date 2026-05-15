from __future__ import annotations

import time

import requests

from .config import ApiSettings


class APIClient:
    def __init__(self, settings: ApiSettings):
        self.settings = settings

    def generate(self, prompt: str) -> str:
        return self._generate_from_messages([{"role": "user", "content": prompt}])

    def generate_chat(
        self,
        *,
        system_prompt: str,
        chat_history: list[dict[str, str]],
        user_message: str,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        for item in chat_history:
            role = self._normalize_role(item.get("role", "user"))
            content = item.get("content", "")
            if not content:
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})
        return self._generate_from_messages(messages)

    def _generate_from_messages(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "messages": messages,
            "mode": "instruct",
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
        }
        if self.settings.model:
            payload["model"] = self.settings.model

        headers = {"Content-Type": "application/json"}
        if self.settings.key:
            headers["Authorization"] = f"Bearer {self.settings.key}"

        for attempt in range(1, self.settings.max_retries + 1):
            try:
                response = requests.post(
                    self.settings.url,
                    json=payload,
                    headers=headers,
                    timeout=self.settings.timeout,
                )
                if response.status_code == 429 and attempt < self.settings.max_retries:
                    time.sleep(self.settings.retry_delay * attempt)
                    continue
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except requests.RequestException as exc:
                if attempt < self.settings.max_retries:
                    time.sleep(self.settings.retry_delay * attempt)
                    continue
                raise RuntimeError(f"Text generation failed: {exc}") from exc

        raise RuntimeError("Text generation failed")

    def _normalize_role(self, role: str) -> str:
        normalized = role.strip().lower()
        if normalized in {"assistant", "character", "char"}:
            return "assistant"
        if normalized == "system":
            return "system"
        return "user"
