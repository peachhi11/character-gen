from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class TropeDragDropZone(QFrame):
    file_dropped_signal = pyqtSignal(str)

    def __init__(
        self,
        display_label_text: str = "Drop Card File Here\n(.json or .png)",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._base_style = (
            "QFrame {"
            " background-color: #f7efe3;"
            " border: 2px dashed #c8b497;"
            " border-radius: 18px;"
            " min-height: 132px;"
            " min-width: 180px;"
            "}"
        )
        self._active_style = (
            "QFrame {"
            " background-color: #efe6ff;"
            " border: 2px dashed #6f63c7;"
            " border-radius: 18px;"
            " min-height: 132px;"
            " min-width: 180px;"
            "}"
        )
        self._invalid_style = (
            "QFrame {"
            " background-color: #f8e9e6;"
            " border: 2px dashed #c77263;"
            " border-radius: 18px;"
            " min-height: 132px;"
            " min-width: 180px;"
            "}"
        )
        self._apply_base_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        self.lbl = QLabel(display_label_text)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet(
            "color: #7b6755; font-size: 12px; font-weight: 700; letter-spacing: 0.4px;"
        )
        layout.addWidget(self.lbl)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        local_file_path = self._extract_single_supported_path(event)
        if local_file_path is not None:
            self.setStyleSheet(self._active_style)
            event.acceptProposedAction()
            return
        self.setStyleSheet(self._invalid_style)
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # type: ignore[override]
        self._apply_base_style()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        self._apply_base_style()
        local_file_path = self._extract_single_supported_path(event)
        if local_file_path is None:
            event.ignore()
            return
        self.file_dropped_signal.emit(local_file_path)
        event.acceptProposedAction()

    def _extract_single_supported_path(self, event) -> str | None:
        if not event.mimeData().hasUrls():
            return None
        urls = event.mimeData().urls()
        if len(urls) != 1:
            return None
        local_file_path = urls[0].toLocalFile()
        suffix = Path(local_file_path).suffix.lower()
        if suffix not in {".json", ".png"}:
            return None
        return local_file_path

    def _apply_base_style(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setStyleSheet(self._base_style)
