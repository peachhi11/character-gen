from __future__ import annotations

import base64
import io
import json
from typing import Any

from PIL import Image
from PIL.PngImagePlugin import PngInfo


class PNGMetadataEngine:
    def __init__(self, metadata_key: str = "chara") -> None:
        self.metadata_key = metadata_key

    def extract_card_data(self, image_bytes: bytes) -> dict[str, Any]:
        """
        Parse a PNG byte stream and recover the embedded character card payload.
        Standard Character Card V2/V3 payloads are supported. Raw engine-state
        payloads remain JSON-only and are rejected.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
            metadata = img.info
            if self.metadata_key not in metadata:
                raise KeyError(
                    f"Target metadata key '{self.metadata_key}' not found in PNG file structure."
                )

            raw_data = metadata[self.metadata_key]
            decoded_bytes = base64.b64decode(raw_data)
            decoded_str = decoded_bytes.decode("utf-8")
            card_payload = json.loads(decoded_str)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"Failed to cleanly extract Character Card array: {str(exc)}"
            ) from exc

        if _is_raw_engine_state_payload(card_payload):
            raise ValueError(
                "Engine-state character cards are JSON-only and cannot be read from PNG metadata."
            )
        return card_payload

    def inject_card_data(
        self, base_image_bytes: bytes, card_payload: dict[str, Any]
    ) -> bytes:
        """
        Embed a Character Card V2/V3 payload into PNG metadata. Raw engine-state
        cards are rejected because they are JSON-only by format policy.
        """
        if _is_raw_engine_state_payload(card_payload):
            raise RuntimeError(
                "Engine-state character cards are JSON-only and cannot be embedded into PNG metadata."
            )

        try:
            img = Image.open(io.BytesIO(base_image_bytes))
            img.load()
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")

            json_str = json.dumps(card_payload, ensure_ascii=False)
            encoded_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

            metadata_container = PngInfo()
            metadata_container.add_text(self.metadata_key, encoded_str)

            output_stream = io.BytesIO()
            img.save(output_stream, format="PNG", pnginfo=metadata_container)
            return output_stream.getvalue()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to compile and inject payload block structure inside PNG: {str(exc)}"
            ) from exc


def _is_raw_engine_state_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("spec") in {"chara_card_v2", "chara_card_v3"}:
        return False
    return all(
        key in payload
        for key in (
            "card_id",
            "metadata",
            "trope_engine_weights",
            "origin_context",
            "dialogue_nodes",
        )
    )
