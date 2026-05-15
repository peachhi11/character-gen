from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from pathlib import Path
import sys
from threading import RLock
import time
from typing import Any

try:
    from PyQt6.QtCore import QThread, QSize, Qt, pyqtSignal
    from PyQt6.QtGui import QImage, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QHeaderView,
        QHBoxLayout,
        QLineEdit,
        QLabel,
        QMainWindow,
        QPushButton,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QThread = None
    QSize = None
    Qt = None
    pyqtSignal = None
    QImage = None
    QPixmap = None
    QApplication = None
    QHeaderView = None
    QHBoxLayout = None
    QLineEdit = None
    QLabel = None
    QMainWindow = object
    QPushButton = None
    QSplitter = None
    QTableWidget = None
    QTableWidgetItem = None
    QVBoxLayout = None
    QWidget = None

from .config import AppPaths
from .defensive_storage import DefensiveStorageRecoveryEngine
from .png_metadata_engine import PNGMetadataEngine

if QApplication is not None:
    from .sprite_display_manager import TropeSpriteDisplayManager
else:  # pragma: no cover - environment-specific
    TropeSpriteDisplayManager = None


@dataclass(frozen=True)
class LibraryRecord:
    id: str
    name: str
    spec_format: str
    engine_type: str
    file_path: str
    filename: str
    record_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "spec_format": self.spec_format,
            "engine_type": self.engine_type,
            "file_path": self.file_path,
            "filename": self.filename,
            "record_type": self.record_type,
        }


class CharacterCardLibrary:
    def __init__(
        self,
        paths: AppPaths | None = None,
        library_path: str | Path | None = None,
        runtime_path: str | Path | None = None,
    ) -> None:
        self.paths = paths or AppPaths()
        self.paths.ensure_directories()
        self.library_path = Path(library_path) if library_path else self.paths.characters_dir
        self.runtime_path = Path(runtime_path) if runtime_path else self.paths.runtime_saves_dir
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.runtime_path.mkdir(parents=True, exist_ok=True)
        self.card_index: dict[str, dict[str, Any]] = {}
        self._lock = RLock()
        self.png_metadata_engine = PNGMetadataEngine()
        self.recovery_engine = DefensiveStorageRecoveryEngine()

    def scan_and_rebuild_library_index(self) -> int:
        with self._lock:
            self.card_index.clear()

            for file_path in self._iter_index_targets():
                try:
                    record = self._extract_metadata_header(file_path)
                except Exception:
                    continue
                if record is None:
                    continue
                self.card_index[record.id] = record.to_dict()

            return len(self.card_index)

    def list_records(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(
                (dict(record) for record in self.card_index.values()),
                key=lambda item: (
                    item.get("record_type", ""),
                    item.get("name", "").lower(),
                    item.get("filename", "").lower(),
                ),
            )

    def get_card_payload_for_deployment(self, card_id: str) -> dict[str, Any]:
        with self._lock:
            metadata = self.card_index.get(card_id)
        if metadata is None:
            raise KeyError(
                f"Library Exception: Character card reference ID '{card_id}' does not exist inside index logs."
            )

        target_path = Path(metadata["file_path"])
        if target_path.suffix.lower() == ".png":
            return self.png_metadata_engine.extract_card_data(target_path.read_bytes())

        payload = self.recovery_engine.safe_read_session(
            target_path,
            fallback_session_id=card_id if metadata.get("record_type") == "runtime_state" else None,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"Library payload root must be an object: {target_path.name}")
        return payload

    def resolve_thumbnail_source(self, card_id: str) -> str | None:
        with self._lock:
            metadata = self.card_index.get(card_id)
        if metadata is None:
            return None

        target_path = Path(metadata["file_path"])
        if target_path.suffix.lower() == ".png" and target_path.exists():
            return str(target_path)

        sibling_png = target_path.with_suffix(".png")
        if sibling_png.exists():
            return str(sibling_png)

        if metadata.get("record_type") == "runtime_state":
            card_id_value = Path(metadata["filename"]).stem
            try:
                payload = self.get_card_payload_for_deployment(card_id)
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                linked_card_id = str(payload.get("card_id") or card_id_value)
                for candidate in (
                    self.library_path / f"{linked_card_id}.png",
                    self.library_path / f"{linked_card_id}.json",
                ):
                    if candidate.exists():
                        return str(candidate)

        return str(target_path)

    def _iter_index_targets(self) -> list[Path]:
        files: list[Path] = []
        for root in (self.library_path, self.runtime_path):
            if not root.exists():
                continue
            for file_path in sorted(root.iterdir()):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in {".json", ".png"}:
                    continue
                files.append(file_path)
        return files

    def _extract_metadata_header(self, filepath: Path) -> LibraryRecord | None:
        if filepath.suffix.lower() == ".json":
            return self._extract_json_metadata_header(filepath)
        return self._extract_png_metadata_header(filepath)

    def _extract_json_metadata_header(self, filepath: Path) -> LibraryRecord | None:
        data = self.recovery_engine.safe_read_session(filepath)
        if not isinstance(data, dict):
            return None

        if "session_id" in data and "weights" in data:
            session_id = str(data.get("session_id") or filepath.stem)
            card_id = str(data.get("card_id") or "unknown_card")
            return LibraryRecord(
                id=session_id,
                name=f"Runtime Session: {card_id}",
                spec_format="STATE",
                engine_type=str(data.get("engine_type", "None")),
                file_path=str(filepath),
                filename=filepath.name,
                record_type="runtime_state",
            )

        spec = data.get("spec", "legacy_v1")
        data_block = data.get("data", {})
        extensions = data.get("extensions", {})
        if not isinstance(data_block, dict):
            data_block = {}
        if not isinstance(extensions, dict):
            extensions = {}
        data_extensions = data_block.get("extensions", {})
        if not isinstance(data_extensions, dict):
            data_extensions = {}

        name = str(data.get("name") or data_block.get("name") or "Unknown Archetype")
        card_id = str(data.get("id") or data_block.get("id") or filepath.stem)
        trope_engine = extensions.get("trope_engine") or data_extensions.get("trope_engine") or {}
        if not isinstance(trope_engine, dict):
            trope_engine = {}

        if spec == "chara_card_v3":
            spec_format = "CCV3"
        elif spec == "chara_card_v2":
            spec_format = "V2"
        else:
            spec_format = "V1"

        return LibraryRecord(
            id=card_id,
            name=name,
            spec_format=spec_format,
            engine_type=str(trope_engine.get("engine_type", "None")),
            file_path=str(filepath),
            filename=filepath.name,
            record_type="character_card",
        )

    def _extract_png_metadata_header(self, filepath: Path) -> LibraryRecord | None:
        data = self.png_metadata_engine.extract_card_data(filepath.read_bytes())
        if not isinstance(data, dict):
            return None

        spec = data.get("spec", "legacy_v1")
        data_block = data.get("data", {})
        if not isinstance(data_block, dict):
            data_block = {}

        extensions = data.get("extensions", {})
        if not isinstance(extensions, dict):
            extensions = {}
        data_extensions = data_block.get("extensions", {})
        if not isinstance(data_extensions, dict):
            data_extensions = {}

        name = str(data.get("name") or data_block.get("name") or "Unknown")
        card_id = str(data.get("id") or data_block.get("id") or filepath.stem)
        trope_engine = extensions.get("trope_engine") or data_extensions.get("trope_engine") or {}
        if not isinstance(trope_engine, dict):
            trope_engine = {}

        spec_format = "CCV3" if spec == "chara_card_v3" else "V2"
        return LibraryRecord(
            id=card_id,
            name=name,
            spec_format=spec_format,
            engine_type=str(trope_engine.get("engine_type", "None")),
            file_path=str(filepath),
            filename=filepath.name,
            record_type="character_card",
        )


def _extract_base64_asset_from_payload(payload: dict[str, Any]) -> str | None:
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        return None

    for asset in assets:
        candidate: str | None = None
        if isinstance(asset, str):
            candidate = asset.strip()
        elif isinstance(asset, dict):
            for key in ("uri", "src", "data", "base64", "content", "value"):
                value = asset.get(key)
                if isinstance(value, str) and value.strip():
                    candidate = value.strip()
                    break
        if candidate:
            return candidate
    return None


if QThread is not None and pyqtSignal is not None and QImage is not None and QSize is not None:
    class AsyncThumbnailDecoder(QThread):
        texture_decoded_signal = pyqtSignal(object, str)

        def __init__(
            self,
            *,
            card_id: str,
            filepath: str,
            target_size: QSize,
            library_path: str,
        ) -> None:
            super().__init__()
            self.card_id = card_id
            self.filepath = filepath
            self.target_size = QSize(target_size)
            self.library_path = Path(library_path)

        def run(self) -> None:  # type: ignore[override]
            image = self._decode_image()
            if image is None or image.isNull():
                return
            scaled = image.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.texture_decoded_signal.emit(scaled, self.card_id)

        def _decode_image(self) -> QImage | None:
            source_path = Path(self.filepath)
            if source_path.suffix.lower() == ".png" and source_path.exists():
                return QImage(str(source_path))

            if not source_path.exists():
                return None

            try:
                payload = json.loads(source_path.read_text(encoding="utf-8"))
            except Exception:
                return None

            if not isinstance(payload, dict):
                return None

            asset_data = _extract_base64_asset_from_payload(payload)
            if asset_data:
                candidate = asset_data.split(",", 1)[1] if "," in asset_data else asset_data
                try:
                    decoded = base64.b64decode(candidate)
                except Exception:
                    decoded = b""
                image = QImage.fromData(decoded)
                if not image.isNull():
                    return image

            linked_card_id = str(payload.get("card_id") or payload.get("id") or source_path.stem)
            for fallback in (
                source_path.with_suffix(".png"),
                self.library_path / f"{linked_card_id}.png",
            ):
                if fallback.exists():
                    image = QImage(str(fallback))
                    if not image.isNull():
                        return image
            return None


if QMainWindow is not object and Qt is not None:
    class DesktopLibraryBrowserUI(QMainWindow):
        def __init__(self, paths: AppPaths | None = None) -> None:
            super().__init__()
            self.paths = paths or AppPaths()
            self.library_manager = CharacterCardLibrary(paths=self.paths)
            self.filtered_records: list[dict[str, Any]] = []
            self.active_decoders: list[AsyncThumbnailDecoder] = []
            self._latest_thumbnail_request_card_id: str | None = None
            self.setWindowTitle("Character Card Library Explorer")
            self.setMinimumSize(1200, 700)
            self.init_browser_interface_grid()
            self.trigger_refresh_library_index_pass()

        def init_browser_interface_grid(self) -> None:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            master_layout = QVBoxLayout(main_widget)

            header_strip = QHBoxLayout()
            header_strip.addWidget(QLabel("<b>CENTRALIZED CARD STORAGE VAULT</b>"))
            header_strip.addStretch()

            refresh_btn = QPushButton("Scan & Rebuild Index")
            refresh_btn.clicked.connect(self.trigger_refresh_library_index_pass)
            header_strip.addWidget(refresh_btn)
            master_layout.addLayout(header_strip)

            self.search_bar_input = QLineEdit()
            self.search_bar_input.setPlaceholderText(
                "Filter cards instantly by name, record type, format, trope engine, or filename..."
            )
            self.search_bar_input.textChanged.connect(
                self.execute_live_query_filtration_refresh
            )
            master_layout.addWidget(self.search_bar_input)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            master_layout.addWidget(splitter, 1)

            center_panel = QWidget()
            center_layout = QVBoxLayout(center_panel)
            center_layout.setContentsMargins(0, 0, 0, 0)

            self.library_table = QTableWidget()
            self.library_table.setColumnCount(5)
            self.library_table.setHorizontalHeaderLabels(
                [
                    "Character Name",
                    "Record Type",
                    "Specification Format",
                    "Trope Logic Engine",
                    "Source Filename",
                ]
            )
            self.library_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            self.library_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows
            )
            self.library_table.setSelectionMode(
                QTableWidget.SelectionMode.SingleSelection
            )
            self.library_table.currentItemChanged.connect(
                self.handle_focused_row_changed
            )
            center_layout.addWidget(self.library_table)

            self.lbl_summary = QLabel("Total Cards Loaded: 0")
            center_layout.addWidget(self.lbl_summary)
            splitter.addWidget(center_panel)

            right_panel = QWidget()
            right_layout = QVBoxLayout(right_panel)
            right_layout.setContentsMargins(8, 0, 0, 0)

            right_layout.addWidget(QLabel("<b>Selected Avatar Sprite Canvas</b>"))
            self.sprite_manager = TropeSpriteDisplayManager(240, 240, parent=right_panel)
            right_layout.addWidget(
                self.sprite_manager,
                alignment=Qt.AlignmentFlag.AlignHCenter,
            )

            self.lbl_details_pane = QLabel(
                "Select a character card row\nto inspect its index schema blocks."
            )
            self.lbl_details_pane.setWordWrap(True)
            self.lbl_details_pane.setAlignment(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
            )
            right_layout.addWidget(self.lbl_details_pane, 1)
            splitter.addWidget(right_panel)
            splitter.setSizes([820, 320])

            self.clear_avatar_canvas_display()

        def trigger_refresh_library_index_pass(self) -> None:
            total_indexed = self.library_manager.scan_and_rebuild_library_index()
            self.lbl_summary.setText(
                f"Total Profiles Indexed inside RAM Cache: {total_indexed} assets found."
            )
            self.execute_live_query_filtration_refresh()

        def execute_live_query_filtration_refresh(self) -> None:
            search_token = self.search_bar_input.text().strip().lower()
            all_records = self.library_manager.list_records()
            self.filtered_records = []
            self.library_table.setRowCount(0)

            for meta in all_records:
                combined = " ".join(
                    [
                        str(meta.get("name", "")),
                        str(meta.get("record_type", "")),
                        str(meta.get("spec_format", "")),
                        str(meta.get("engine_type", "")),
                        str(meta.get("filename", "")),
                    ]
                ).lower()
                if search_token and search_token not in combined:
                    continue
                self.filtered_records.append(meta)

            for row_index, meta in enumerate(self.filtered_records):
                self.library_table.insertRow(row_index)
                name_item = QTableWidgetItem(meta["name"])
                type_item = QTableWidgetItem(meta["record_type"])
                spec_item = QTableWidgetItem(meta["spec_format"])
                engine_item = QTableWidgetItem(meta["engine_type"])
                file_item = QTableWidgetItem(meta["filename"])
                name_item.setData(Qt.ItemDataRole.UserRole, meta["id"])

                self.library_table.setItem(row_index, 0, name_item)
                self.library_table.setItem(row_index, 1, type_item)
                self.library_table.setItem(row_index, 2, spec_item)
                self.library_table.setItem(row_index, 3, engine_item)
                self.library_table.setItem(row_index, 4, file_item)

            if self.filtered_records:
                self.library_table.setCurrentCell(0, 0)
            else:
                self.clear_avatar_canvas_display()
                self.lbl_details_pane.setText("No matching cards in the current filter.")

        def clear_avatar_canvas_display(self) -> None:
            self.sprite_manager.clear_viewport_canvas()

        def handle_focused_row_changed(
            self,
            current_item: QTableWidgetItem | None,
            previous_item: QTableWidgetItem | None,
        ) -> None:
            del previous_item
            if current_item is None:
                self.clear_avatar_canvas_display()
                self.lbl_details_pane.setText("Select a card to evaluate its metrics.")
                return

            row_index = current_item.row()
            if row_index < 0 or row_index >= len(self.filtered_records):
                self.clear_avatar_canvas_display()
                return

            meta = self.filtered_records[row_index]
            card_id = str(meta["id"])
            self._latest_thumbnail_request_card_id = card_id
            self.lbl_details_pane.setText(
                "\n".join(
                    [
                        "<b>SPEC SCHEMA LEDGER RECORD:</b>",
                        f"- Asset ID: {meta['id']}",
                        f"- Name: {meta['name']}",
                        f"- Record Type: {meta['record_type']}",
                        f"- Base Format: {meta['spec_format']}",
                        f"- Logic Engine: {meta['engine_type']}",
                        f"- Storage File: {meta['filename']}",
                    ]
                )
            )
            self.sprite_manager.image_canvas.setText(
                "<span style='color:#6366f1; font-size:10px; font-family:monospace;'>"
                "[ DECODING SPRITE... ]"
                "</span>"
            )

            self.active_decoders = [worker for worker in self.active_decoders if worker.isRunning()]
            source = self.library_manager.resolve_thumbnail_source(card_id)
            if not source:
                self.clear_avatar_canvas_display()
                return

            decoder = AsyncThumbnailDecoder(
                card_id=card_id,
                filepath=source,
                target_size=self.sprite_manager.target_size,
                library_path=str(self.library_manager.library_path),
            )
            decoder.texture_decoded_signal.connect(self.paint_decoded_sprite_to_canvas)
            self.active_decoders.append(decoder)
            decoder.start()

        def paint_decoded_sprite_to_canvas(
            self,
            decoded_image: QImage,
            source_card_id: str,
        ) -> None:
            if source_card_id != self._latest_thumbnail_request_card_id:
                return
            pixmap = QPixmap.fromImage(decoded_image)
            if pixmap.isNull():
                self.clear_avatar_canvas_display()
                return
            self.sprite_manager.image_canvas.setText("")
            self.sprite_manager.image_canvas.setPixmap(pixmap)


    def run_card_library_browser_app() -> int:
        app = QApplication.instance() or QApplication(sys.argv)
        window = DesktopLibraryBrowserUI()
        window.show()
        return app.exec()
else:
    class DesktopLibraryBrowserUI:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use DesktopLibraryBrowserUI.")


    def run_card_library_browser_app() -> int:  # pragma: no cover - PyQt-only shim
        raise ModuleNotFoundError("PyQt6 is required to launch the card library browser.")
