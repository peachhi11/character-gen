from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

try:
    from PyQt6.QtCore import QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QApplication,
        QFileDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QProgressBar,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QThread = None
    pyqtSignal = None
    QApplication = None
    QFileDialog = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QMainWindow = object
    QProgressBar = None
    QPushButton = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None

from .png_metadata_engine import PNGMetadataEngine


INVENTORY_KEYS = (
    "character_cards_v3",
    "character_cards_v2_legacy",
    "character_cards_v1_legacy",
    "worldbooks_parsed",
    "unmapped_or_corrupted_assets",
)


@dataclass
class RepoAssetInventoryParser:
    png_metadata_engine: PNGMetadataEngine | None = None

    def __post_init__(self) -> None:
        if self.png_metadata_engine is None:
            self.png_metadata_engine = PNGMetadataEngine()
        self.inventory = self._blank_inventory()

    def scan_directory(
        self,
        target_repo_path: str | Path,
        output_ledger_path: str | Path,
        *,
        progress_callback=None,
        log_callback=None,
        cancel_check=None,
    ) -> dict[str, Any]:
        target_repo = Path(target_repo_path)
        output_dir = Path(output_ledger_path)
        self.inventory = self._blank_inventory()

        if not target_repo.exists():
            raise FileNotFoundError(
                f"Target repository path '{target_repo}' does not exist."
            )

        all_file_targets = self._collect_targets(target_repo)
        total_files = len(all_file_targets)
        self._emit_log(log_callback, "Engaging repo-wide file discovery loops...")

        if total_files == 0:
            self._emit_log(
                log_callback,
                "[PARSER WARNING]: Target folder contains zero valid card assets.",
            )
            return {"status": "EMPTY"}

        for index, file_path in enumerate(all_file_targets, start=1):
            if cancel_check and cancel_check():
                self._emit_log(
                    log_callback,
                    "[PARSER ABORT]: Process explicitly canceled by desktop operator.",
                )
                return self._build_summary("CANCELLED", None)

            try:
                self._parse_single_path(file_path)
            except Exception as exc:  # noqa: BLE001
                self._emit_log(
                    log_callback,
                    f"  -> [CRITICAL READ FAIL] inside '{file_path.name}': {exc}",
                )
                self.inventory["unmapped_or_corrupted_assets"].append(
                    {"file_path": str(file_path), "error": str(exc)}
                )

            if progress_callback is not None:
                progress_callback(int(index / total_files * 100))

        output_dir.mkdir(parents=True, exist_ok=True)
        ledger_file_path = output_dir / "repo_asset_inventory_ledger.json"
        ledger_file_path.write_text(
            json.dumps(self.inventory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return self._build_summary("SUCCESS", ledger_file_path)

    def _blank_inventory(self) -> dict[str, list[dict[str, Any]]]:
        return {key: [] for key in INVENTORY_KEYS}

    def _collect_targets(self, target_repo: Path) -> list[Path]:
        return sorted(
            path
            for path in target_repo.rglob("*")
            if path.is_file() and path.suffix.lower() in {".json", ".png", ".entries"}
        )

    def _parse_single_path(self, file_path: Path) -> None:
        suffix = file_path.suffix.lower()
        if suffix == ".png":
            self._parse_png_metadata_card(file_path)
            return
        self._parse_json_or_entries_structures(file_path)

    def _parse_png_metadata_card(self, filepath: Path) -> None:
        raw_json = self.png_metadata_engine.extract_card_data(filepath.read_bytes())
        self._categorize_json_payload(
            raw_json,
            filepath,
            is_embedded_png=True,
        )

    def _parse_json_or_entries_structures(self, filepath: Path) -> None:
        payload = json.loads(filepath.read_text(encoding="utf-8").strip())

        if self._is_worldbook_payload(payload, filepath):
            self.inventory["worldbooks_parsed"].append(
                self._worldbook_record(filepath, payload)
            )
            return

        if isinstance(payload, dict):
            self._categorize_json_payload(
                payload,
                filepath,
                is_embedded_png=False,
            )
            return

        self.inventory["unmapped_or_corrupted_assets"].append(
            {
                "file_path": str(filepath),
                "error": "Unmatched profile schema markers configuration.",
            }
        )

    def _is_worldbook_payload(self, payload: Any, filepath: Path) -> bool:
        if filepath.suffix.lower() == ".entries":
            return True
        if isinstance(payload, list):
            return True
        return isinstance(payload, dict) and "entries" in payload

    def _worldbook_record(self, filepath: Path, payload: Any) -> dict[str, Any]:
        entry_count = 0
        if isinstance(payload, list):
            entry_count = len(payload)
        elif isinstance(payload, dict):
            entries = payload.get("entries", {})
            if isinstance(entries, dict):
                entry_count = len(entries)
            elif isinstance(entries, list):
                entry_count = len(entries)

        return {
            "file_path": str(filepath),
            "source_filename": filepath.name,
            "entry_count": entry_count,
        }

    def _categorize_json_payload(
        self,
        payload: dict[str, Any],
        filepath: Path,
        *,
        is_embedded_png: bool,
    ) -> None:
        spec = payload.get("spec")
        data_block = payload.get("data")
        if isinstance(data_block, dict):
            name = data_block.get("name", "Unknown Character")
        else:
            name = payload.get("name", "Unknown Character")

        record_entry = {
            "character_name": name,
            "file_path": str(filepath),
            "filename": filepath.name,
            "is_embedded_png_metadata": is_embedded_png,
            "has_trope_engine": self._has_trope_engine(payload),
        }

        if spec == "chara_card_v3":
            self.inventory["character_cards_v3"].append(record_entry)
        elif spec == "chara_card_v2" or (
            isinstance(data_block, dict) and "description" in data_block
        ):
            self.inventory["character_cards_v2_legacy"].append(record_entry)
        elif spec is None and "description" in payload and "name" in payload:
            self.inventory["character_cards_v1_legacy"].append(record_entry)
        else:
            self.inventory["unmapped_or_corrupted_assets"].append(
                {
                    "file_path": str(filepath),
                    "error": "Unmatched profile schema markers configuration.",
                }
            )

    def _has_trope_engine(self, payload: dict[str, Any]) -> bool:
        if payload.get("spec") == "chara_card_v2":
            return "trope_engine" in payload.get("data", {}).get("extensions", {})
        return "trope_engine" in payload.get("extensions", {})

    def _emit_log(self, callback, message: str) -> None:
        if callback is not None:
            callback(message)

    def _build_summary(
        self,
        status: str,
        ledger_file_path: Path | None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "ledger_path": str(ledger_file_path) if ledger_file_path else None,
            "v3_count": len(self.inventory["character_cards_v3"]),
            "v2_count": len(self.inventory["character_cards_v2_legacy"]),
            "v1_count": len(self.inventory["character_cards_v1_legacy"]),
            "wb_count": len(self.inventory["worldbooks_parsed"]),
            "fail_count": len(self.inventory["unmapped_or_corrupted_assets"]),
        }


if QThread is not None and pyqtSignal is not None:
    class RepoAssetParserWorker(QThread):
        progress_update = pyqtSignal(int)
        log_stream = pyqtSignal(str)
        parsing_complete = pyqtSignal(dict)

        def __init__(
            self,
            target_repo_path: str | Path,
            output_ledger_path: str | Path,
            *,
            parent=None,
        ) -> None:
            super().__init__(parent)
            self.target_repo_path = Path(target_repo_path)
            self.output_ledger_path = Path(output_ledger_path)
            self.is_cancelled = False
            self.parser = RepoAssetInventoryParser()

        def run(self) -> None:  # type: ignore[override]
            try:
                report = self.parser.scan_directory(
                    self.target_repo_path,
                    self.output_ledger_path,
                    progress_callback=self.progress_update.emit,
                    log_callback=self.log_stream.emit,
                    cancel_check=lambda: self.is_cancelled,
                )
                self.parsing_complete.emit(report)
            except Exception as exc:  # noqa: BLE001
                self.log_stream.emit(f"[SYSTEM ERROR]: {exc}")
                self.parsing_complete.emit(
                    {
                        "status": "FAILED",
                        "ledger_path": None,
                        "v3_count": len(self.parser.inventory["character_cards_v3"]),
                        "v2_count": len(self.parser.inventory["character_cards_v2_legacy"]),
                        "v1_count": len(self.parser.inventory["character_cards_v1_legacy"]),
                        "wb_count": len(self.parser.inventory["worldbooks_parsed"]),
                        "fail_count": len(
                            self.parser.inventory["unmapped_or_corrupted_assets"]
                        )
                        + 1,
                    }
                )


    class RepoAssetParserWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Repo-Wide Trope Asset Parser Framework")
            self.setMinimumSize(900, 550)
            self.worker: RepoAssetParserWorker | None = None
            self.src_repo_path = ""
            self.dest_ledger_path = ""
            self._build_ui()

        def _build_ui(self) -> None:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            master_layout = QVBoxLayout(main_widget)

            io_group = QGroupBox("Target Workspace Paths")
            io_layout = QVBoxLayout(io_group)
            self.lbl_src = QLabel("<b>Target Source Repository:</b> Not Chosen")
            self.lbl_dest = QLabel("<b>Ledger Output Location:</b> Not Chosen")
            btn_row = QHBoxLayout()
            btn_src = QPushButton("Select Source Repository")
            btn_src.clicked.connect(self.select_source_repo)
            btn_dest = QPushButton("Select Output Ledger Directory")
            btn_dest.clicked.connect(self.select_output_ledger_dir)
            btn_row.addWidget(btn_src)
            btn_row.addWidget(btn_dest)
            io_layout.addWidget(self.lbl_src)
            io_layout.addWidget(self.lbl_dest)
            io_layout.addLayout(btn_row)
            master_layout.addWidget(io_group)

            progress_group = QGroupBox("Asynchronous Scanning Core Status")
            progress_layout = QVBoxLayout(progress_group)
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            progress_layout.addWidget(self.progress_bar)
            self.action_btn = QPushButton("ENGAGE ASYNCHRONOUS DIRECTORY SWEEP")
            self.action_btn.clicked.connect(self.toggle_parser_execution_state)
            progress_layout.addWidget(self.action_btn)
            master_layout.addWidget(progress_group)

            master_layout.addWidget(
                QLabel("<b>Real-Time Execution Logs Console:</b>")
            )
            self.log_terminal = QTextEdit()
            self.log_terminal.setReadOnly(True)
            master_layout.addWidget(self.log_terminal)

        def select_source_repo(self) -> None:
            selected = QFileDialog.getExistingDirectory(
                self,
                "Select Root App Repository Source Folder",
            )
            if not selected:
                return
            self.src_repo_path = selected
            self.lbl_src.setText(
                f"<b>Target Source Repository:</b> <code>{self.src_repo_path}</code>"
            )

        def select_output_ledger_dir(self) -> None:
            selected = QFileDialog.getExistingDirectory(
                self,
                "Select Compilation Ledger Save Directory Location",
            )
            if not selected:
                return
            self.dest_ledger_path = selected
            self.lbl_dest.setText(
                f"<b>Ledger Output Location:</b> <code>{self.dest_ledger_path}</code>"
            )

        def toggle_parser_execution_state(self) -> None:
            if self.worker and self.worker.isRunning():
                self.worker.is_cancelled = True
                self.action_btn.setEnabled(False)
                return

            if not self.src_repo_path or not self.dest_ledger_path:
                self.log_terminal.append(
                    "[INTERFACE ALERT]: Valid source and target directory paths must be designated before engaging scanning lines."
                )
                return

            self.progress_bar.setValue(0)
            self.log_terminal.clear()
            self.worker = RepoAssetParserWorker(
                self.src_repo_path,
                self.dest_ledger_path,
                parent=self,
            )
            self.worker.progress_update.connect(self.progress_bar.setValue)
            self.worker.log_stream.connect(self.log_terminal.append)
            self.worker.parsing_complete.connect(self.handle_parser_task_finalization)
            self.worker.start()
            self.action_btn.setText("ABORT REPO SWEEP / FORCE CANCELLATION")

        def handle_parser_task_finalization(self, summary_dict: dict) -> None:
            self.action_btn.setEnabled(True)
            self.action_btn.setText("ENGAGE ASYNCHRONOUS DIRECTORY SWEEP")
            status = summary_dict.get("status")
            if status == "SUCCESS":
                self.progress_bar.setValue(100)
                self.log_terminal.append(
                    "\n[REPO MIGRATION INVENTORY LEDGER GENERATED SUCCESSFULLY]\n"
                    f"- Inventory Ledger Document Written To: {summary_dict['ledger_path']}\n"
                    f"- Native Flat Spec CCV3 Profiles Discovered: {summary_dict['v3_count']}\n"
                    f"- Legacy Spec V2 Cards Segmented: {summary_dict['v2_count']}\n"
                    f"- Legacy Spec V1 Profile Elements Catalogued: {summary_dict['v1_count']}\n"
                    f"- Structured Worldbook Databases Located: {summary_dict['wb_count']}\n"
                    f"- Unmapped / Corrupted Files Isolated: {summary_dict['fail_count']} assets."
                )
            elif status == "EMPTY":
                self.log_terminal.append(
                    "[PARSER WARNING]: Target folder contains zero valid card assets."
                )
            elif status == "CANCELLED":
                self.log_terminal.append("[PARSER ABORT]: Process explicitly canceled.")
            else:
                self.log_terminal.append("[PARSER ERROR]: Scan finished with failures.")


    def run_repo_asset_parser_app() -> int:
        app = QApplication.instance() or QApplication(sys.argv)
        window = RepoAssetParserWindow()
        window.show()
        return app.exec()


    AsyncBatchParserWorker = RepoAssetParserWorker
    AsyncBatchParserUI = RepoAssetParserWindow


    run_mac_batch_parser_app = run_repo_asset_parser_app
else:
    class RepoAssetParserWorker:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use RepoAssetParserWorker.")


    class RepoAssetParserWindow:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use RepoAssetParserWindow.")


    def run_repo_asset_parser_app() -> int:  # pragma: no cover - PyQt-only shim
        raise ModuleNotFoundError("PyQt6 is required to launch the repo asset parser UI.")


    class AsyncBatchParserWorker:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use AsyncBatchParserWorker.")


    class AsyncBatchParserUI:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use AsyncBatchParserUI.")


    run_mac_batch_parser_app = run_repo_asset_parser_app
