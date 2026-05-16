from __future__ import annotations

import unittest

from character_app.api import APIClient
from character_app.config import ApiSettings


def make_settings(*, chat_backend: str = "direct", url: str = "https://api.example.com/v1/chat/completions") -> ApiSettings:
    return ApiSettings(
        url=url,
        model="test-model",
        key="test-key",
        chat_backend=chat_backend,
        max_tokens=256,
        temperature=0.7,
        top_p=0.9,
        timeout=5,
        max_retries=1,
        retry_delay=0.01,
    )


class APIClientTest(unittest.TestCase):
    def test_langchain_backend_routes_through_langchain_generator(self) -> None:
        class RecordingAPIClient(APIClient):
            def __init__(self) -> None:
                super().__init__(make_settings(chat_backend="langchain"))
                self.messages: list[dict[str, str]] | None = None

            def _generate_from_langchain(self, messages: list[dict[str, str]]) -> str:
                self.messages = list(messages)
                return "langchain response"

        client = RecordingAPIClient()

        result = client.generate_chat(
            system_prompt="System prompt.",
            chat_history=[
                {"role": "character", "content": "Existing reply."},
                {"role": "user", "content": "Earlier question."},
            ],
            user_message="Current question.",
        )

        self.assertEqual(result, "langchain response")
        self.assertEqual(
            client.messages,
            [
                {"role": "system", "content": "System prompt."},
                {"role": "assistant", "content": "Existing reply."},
                {"role": "user", "content": "Earlier question."},
                {"role": "user", "content": "Current question."},
            ],
        )

    def test_openai_compatible_base_url_strips_completion_suffixes(self) -> None:
        client = APIClient(make_settings())

        self.assertEqual(
            client._openai_compatible_base_url("https://api.example.com/v1/chat/completions"),
            "https://api.example.com/v1",
        )
        self.assertEqual(
            client._openai_compatible_base_url("https://api.example.com/v1/completions/"),
            "https://api.example.com/v1",
        )
        self.assertEqual(
            client._openai_compatible_base_url("https://api.example.com/v1"),
            "https://api.example.com/v1",
        )


if __name__ == "__main__":
    unittest.main()
