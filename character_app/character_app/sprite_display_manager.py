from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class TropeSpriteDisplayManager(QFrame):
    """
    Render a character sprite/avatar from either a physical image file or a
    base64-encoded asset entry embedded in a CCV3 payload.
    """

    def __init__(self, width: int = 220, height: int = 220, parent=None) -> None:
        super().__init__(parent)
        self.target_size = QSize(width, height)
        self._init_canvas_styles()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.image_canvas = QLabel()
        self.image_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_canvas)

        self.clear_viewport_canvas()

    def _init_canvas_styles(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setFixedSize(self.target_size)
        self.setStyleSheet(
            """
            TropeSpriteDisplayManager {
                background-color: #0b0f19;
                border: 2px solid #1e293b;
                border-radius: 12px;
            }
            """
        )

    def clear_viewport_canvas(self) -> None:
        self.image_canvas.clear()
        self.image_canvas.setText(
            "<span style='color:#475569; font-size:10px; font-family:monospace;'>"
            "[ NO SPRITE ASSET ]"
            "</span>"
        )

    def load_sprite_from_file_path(self, absolute_filepath: str | Path) -> bool:
        pixmap = QPixmap(str(absolute_filepath))
        if pixmap.isNull():
            self.clear_viewport_canvas()
            return False
        self._render_pixmap_to_canvas(pixmap)
        return True

    def load_sprite_from_base64_string(self, base64_image_string: str) -> bool:
        try:
            candidate = base64_image_string.strip()
            if "," in candidate:
                candidate = candidate.split(",", 1)[1]

            image_bytes = base64.b64decode(candidate)
            q_image = QImage.fromData(image_bytes)
            if q_image.isNull():
                self.clear_viewport_canvas()
                return False

            pixmap = QPixmap.fromImage(q_image)
            if pixmap.isNull():
                self.clear_viewport_canvas()
                return False

            self._render_pixmap_to_canvas(pixmap)
            return True
        except Exception:
            self.clear_viewport_canvas()
            return False

    def load_sprite_from_card_payload(
        self,
        card_payload: dict[str, Any] | None,
        source_path: str | Path | None = None,
    ) -> bool:
        if source_path:
            source = Path(source_path)
            if source.suffix.lower() == ".png" and source.exists():
                if self.load_sprite_from_file_path(source):
                    return True

        asset_data = _extract_base64_asset_string(card_payload or {})
        if asset_data and self.load_sprite_from_base64_string(asset_data):
            return True

        if source_path:
            source = Path(source_path)
            sibling_png = source.with_suffix(".png")
            if sibling_png.exists():
                if self.load_sprite_from_file_path(sibling_png):
                    return True

        self.clear_viewport_canvas()
        return False

    def _render_pixmap_to_canvas(self, source_pixmap: QPixmap) -> None:
        scaled_pixmap = source_pixmap.scaled(
            self.target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_canvas.setText("")
        self.image_canvas.setPixmap(scaled_pixmap)


def _extract_base64_asset_string(card_payload: dict[str, Any]) -> str | None:
    assets = card_payload.get("assets", [])
    if not isinstance(assets, list):
        return None

    for asset in assets:
        candidate = _coerce_asset_candidate(asset)
        if candidate and _looks_like_image_payload(candidate):
            return candidate
    return None


def _coerce_asset_candidate(asset: Any) -> str | None:
    if isinstance(asset, str):
        return asset.strip() or None

    if not isinstance(asset, dict):
        return None

    preferred_keys = (
        "uri",
        "src",
        "data",
        "base64",
        "content",
        "payload",
        "value",
    )
    for key in preferred_keys:
        value = asset.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _looks_like_image_payload(candidate: str) -> bool:
    if candidate.startswith("data:image/"):
        return True

    raw_candidate = candidate
    if "," in raw_candidate:
        raw_candidate = raw_candidate.split(",", 1)[1]

    try:
        decoded = base64.b64decode(raw_candidate, validate=True)
    except Exception:
        return False

    image_headers = (
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"GIF87a",
        b"GIF89a",
        b"RIFF",
    )
    return any(decoded.startswith(header) for header in image_headers)
