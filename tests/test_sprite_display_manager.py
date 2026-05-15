from __future__ import annotations

import base64
import io
import unittest

from PIL import Image

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

if QApplication is not None:
    from character_app.sprite_display_manager import TropeSpriteDisplayManager


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class TropeSpriteDisplayManagerTest(unittest.TestCase):
    def test_load_sprite_from_base64_string_renders_pixmap(self) -> None:
        widget = TropeSpriteDisplayManager(120, 120)
        image = Image.new("RGBA", (12, 12), (80, 150, 220, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        success = widget.load_sprite_from_base64_string(
            f"data:image/png;base64,{encoded}"
        )

        self.assertTrue(success)
        self.assertIsNotNone(widget.image_canvas.pixmap())
        widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
