from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from .png_metadata_engine import PNGMetadataEngine

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
    from PyQt6.QtWidgets import (
        QApplication,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    Qt = None
    pyqtSignal = None
    QDragEnterEvent = None
    QDragLeaveEvent = None
    QDropEvent = None
    QApplication = None
    QFormLayout = None
    QFrame = object
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QMainWindow = object
    QMessageBox = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None


SUPPORTED_DROP_SUFFIXES = frozenset({".json", ".png"})


def parse_card_asset_file(
    file_path: str | Path,
    *,
    png_metadata_engine: PNGMetadataEngine | None = None,
) -> dict[str, Any]:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_DROP_SUFFIXES:
        raise ValueError(
            f"Unsupported asset type '{suffix or '<none>'}'. Expected one of: .json, .png."
        )

    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Dropped JSON asset must decode to a top-level object.")
        return payload

    engine = png_metadata_engine or PNGMetadataEngine()
    return engine.extract_card_data(path.read_bytes())


if pyqtSignal is not None:
    class TropeDragDropListenerPanel(QFrame):
        payload_extracted_signal = pyqtSignal(dict, str)

        def __init__(
            self,
            baseline_prompt_text: str = (
                "Drag & Drop Card Asset Here\n(.json data or .png character cards)"
            ),
            *,
            png_metadata_engine: PNGMetadataEngine | None = None,
            parent=None,
        ) -> None:
            super().__init__(parent)
            self.png_metadata_engine = png_metadata_engine or PNGMetadataEngine()
            self.baseline_prompt = baseline_prompt_text
            self.setAcceptDrops(True)
            self._base_style = (
                "TropeDragDropListenerPanel {"
                " background-color: #0f172a;"
                " border: 2px dashed #334155;"
                " border-radius: 12px;"
                " min-height: 200px;"
                " min-width: 240px;"
                "}"
            )
            self._active_style = (
                "TropeDragDropListenerPanel {"
                " background-color: #1e1b4b;"
                " border: 2px dashed #6366f1;"
                " border-radius: 12px;"
                " min-height: 200px;"
                " min-width: 240px;"
                "}"
            )
            self._apply_base_style()

            layout = QVBoxLayout(self)
            self.lbl_status = QLabel(self.baseline_prompt)
            self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_status.setWordWrap(True)
            self.lbl_status.setStyleSheet(
                "color: #94a3b8; font-size: 12px; font-weight: bold; font-family: monospace;"
            )
            layout.addWidget(self.lbl_status)

        def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
            local_path = self._extract_single_supported_path(event)
            if local_path is None:
                event.ignore()
                return
            self.setStyleSheet(self._active_style)
            self.lbl_status.setText("[ DROP TO INGEST ASSET POOL ]")
            event.acceptProposedAction()

        def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # type: ignore[override]
            self._restore_idle_state()
            event.accept()

        def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
            self._restore_idle_state()
            local_path = self._extract_single_supported_path(event)
            if local_path is None:
                event.ignore()
                return
            event.acceptProposedAction()
            self._execute_file_payload_extraction_pipeline(local_path)

        def _extract_single_supported_path(self, event) -> str | None:
            if not event.mimeData().hasUrls():
                return None
            urls = event.mimeData().urls()
            if len(urls) != 1:
                return None
            local_path = urls[0].toLocalFile()
            if Path(local_path).suffix.lower() not in SUPPORTED_DROP_SUFFIXES:
                return None
            return local_path

        def _execute_file_payload_extraction_pipeline(self, file_path: str) -> None:
            try:
                payload = parse_card_asset_file(
                    file_path,
                    png_metadata_engine=self.png_metadata_engine,
                )
            except Exception as exc:  # noqa: BLE001
                self._show_error_dialog(file_path, exc)
                return
            self.payload_extracted_signal.emit(payload, file_path)

        def _show_error_dialog(self, file_path: str, exc: Exception) -> None:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Ingestion Pipeline Failure")
            msg_box.setText(
                "Failed to cleanly decode dropped asset target file:\n"
                f"{os.path.basename(file_path)}"
            )
            msg_box.setInformativeText(str(exc))
            msg_box.setStyleSheet("background-color: #1e293b; color: #f1f5f9;")
            msg_box.exec()

        def _apply_base_style(self) -> None:
            self.setFrameShape(QFrame.Shape.StyledPanel)
            self.setFrameShadow(QFrame.Shadow.Sunken)
            self.setStyleSheet(self._base_style)

        def _restore_idle_state(self) -> None:
            self._apply_base_style()
            self.lbl_status.setText(self.baseline_prompt)


    class LiveDragDropWorkspaceDemo(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Trope Engine Drag-and-Drop Extraction Workspace")
            self.setMinimumSize(950, 500)
            self._build_ui()

        def _build_ui(self) -> None:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            master_layout = QHBoxLayout(main_widget)

            left_column = QVBoxLayout()
            left_column.addWidget(QLabel("<b>Asset Drop Capture Target Portal:</b>"))

            self.drop_panel = TropeDragDropListenerPanel()
            self.drop_panel.payload_extracted_signal.connect(
                self.handle_incoming_extracted_payload_snapshot
            )
            left_column.addWidget(self.drop_panel)
            left_column.addStretch()
            master_layout.addLayout(left_column, 1)

            right_column = QGroupBox("Target Profile Ingestion Data Fields")
            form_layout = QFormLayout(right_column)

            self.lbl_spec_type = QLabel(
                "<span style='color:#64748b;'>No Active Asset</span>"
            )
            self.lbl_name_field = QLabel("-")
            self.lbl_engine_field = QLabel("-")
            self.metadata_terminal = QTextEdit()
            self.metadata_terminal.setReadOnly(True)
            self.metadata_terminal.setStyleSheet(
                "font-family: 'Courier New', monospace; font-size: 11px; background-color: #020617; color: #34d399;"
            )

            form_layout.addRow("Detected Card Type Spec:", self.lbl_spec_type)
            form_layout.addRow("Character Name ID:", self.lbl_name_field)
            form_layout.addRow("Trope Engine Sub-type:", self.lbl_engine_field)
            form_layout.addRow("Raw Object Blueprint:", self.metadata_terminal)

            master_layout.addWidget(right_column, 2)

        def handle_incoming_extracted_payload_snapshot(
            self,
            payload_dict: dict[str, Any],
            file_source_path: str,
        ) -> None:
            self.metadata_terminal.clear()

            spec = payload_dict.get("spec", "legacy_v1")
            data_block = payload_dict.get("data", {})
            if not isinstance(data_block, dict):
                data_block = {}
            name = str(
                payload_dict.get("name")
                or data_block.get("name")
                or "Unknown Archetype"
            )

            extensions = payload_dict.get("extensions", {})
            if not isinstance(extensions, dict):
                extensions = {}
            nested_extensions = data_block.get("extensions", {})
            if not isinstance(nested_extensions, dict):
                nested_extensions = {}
            te_data = extensions.get("trope_engine") or nested_extensions.get(
                "trope_engine", {}
            )
            if not isinstance(te_data, dict):
                te_data = {}
            engine_type = str(te_data.get("engine_type", "Standard/None"))

            if spec == "chara_card_v3":
                spec_label_text = "<b>NATIVE CCV3 SPEC PROFILE</b>"
                color = "#6366f1"
            elif spec == "chara_card_v2":
                spec_label_text = "LEGACY SPEC V2"
                color = "#eab308"
            else:
                spec_label_text = "LEGACY SPEC V1"
                color = "#eab308"

            self.lbl_spec_type.setText(
                f"<span style='color:{color};'>{spec_label_text}</span>"
            )
            self.lbl_name_field.setText(f"<b>{name}</b>")
            self.lbl_engine_field.setText(
                f"<code style='color:#38bdf8;'>{engine_type}</code>"
            )
            self.metadata_terminal.append(
                f"// Loaded from local disk index: {os.path.basename(file_source_path)}\n"
            )
            self.metadata_terminal.append(
                json.dumps(payload_dict, indent=2, ensure_ascii=False)
            )
else:  # pragma: no cover - environment-specific
    TropeDragDropListenerPanel = None
    LiveDragDropWorkspaceDemo = None


def run_drag_drop_listener_demo_app() -> int:
    if QApplication is None:
        raise RuntimeError("PyQt6 is required to run the drag-and-drop listener demo.")
    app = QApplication.instance() or QApplication(sys.argv)
    window = LiveDragDropWorkspaceDemo()
    window.show()
    return app.exec()
