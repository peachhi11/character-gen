from __future__ import annotations

import copy
import hashlib
from typing import Any


class TelemetryFilteringMask:
    def __init__(
        self,
        *,
        redact_chat_history: bool = True,
        anonymous_mode: bool = True,
    ) -> None:
        self.redact_chat_history = redact_chat_history
        self.anonymous_mode = anonymous_mode

    def scrub_session_state(
        self,
        state_snapshot_dict: dict[str, Any],
    ) -> dict[str, Any]:
        scrubbed_data = copy.deepcopy(state_snapshot_dict)

        if self.redact_chat_history and "chat_history" in scrubbed_data:
            chat_history = scrubbed_data.get("chat_history", [])
            if isinstance(chat_history, list):
                scrubbed_data["chat_history"] = [
                    {
                        "role": turn.get("role", "user"),
                        "content": self._redacted_content(turn.get("content", "")),
                    }
                    for turn in chat_history
                    if isinstance(turn, dict)
                ]

        if self.anonymous_mode:
            if "user_id" in scrubbed_data:
                scrubbed_data["user_id"] = self._mask_user_id(
                    scrubbed_data["user_id"]
                )
            if "session_id" in scrubbed_data:
                scrubbed_data["session_id"] = self._mask_session_id(
                    scrubbed_data["session_id"]
                )

        return scrubbed_data

    def _redacted_content(self, content: Any) -> str:
        text = str(content)
        return f"[REDACTED_CONTENT_LEN_{len(text)}]"

    def _mask_user_id(self, user_id: Any) -> str:
        digest = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:8]
        return f"anon_{digest}"

    def _mask_session_id(self, session_id: Any) -> str:
        value = str(session_id)
        if len(value) <= 8:
            return "sess_hidden"
        return f"{value[:5]}***{value[-4:]}"
