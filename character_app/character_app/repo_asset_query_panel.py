from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any

try:
    from PyQt6.QtCore import QThread, Qt, pyqtSignal
    from PyQt6.QtGui import QAction, QKeySequence
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QFileDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QThread = None
    Qt = None
    pyqtSignal = None
    QAction = None
    QKeySequence = None
    QApplication = None
    QCheckBox = None
    QFileDialog = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
    QListWidget = None
    QListWidgetItem = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QSplitter = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None

from .repo_asset_parser import INVENTORY_KEYS


SPEC_TAG_TO_LEDGER_KEY = {
    "V3_CARD": "character_cards_v3",
    "V2_LEGACY": "character_cards_v2_legacy",
    "V1_LEGACY": "character_cards_v1_legacy",
    "WORLDBOOK": "worldbooks_parsed",
    "CORRUPTED": "unmapped_or_corrupted_assets",
}

LEDGER_KEY_TO_SPEC_TAG = {value: key for key, value in SPEC_TAG_TO_LEDGER_KEY.items()}
LEDGER_KEY_ALIASES = {
    "unmapped_or_corrupted_assets": ("corrupted_or_unmapped_assets",),
}


def blank_ledger_data() -> dict[str, list[dict[str, Any]]]:
    return {key: [] for key in INVENTORY_KEYS}


class RepoAssetLedgerStore:
    def __init__(self) -> None:
        self.ledger_data = blank_ledger_data()
        self.loaded_path: Path | None = None

    def load_from_path(self, file_path: str | Path) -> dict[str, list[dict[str, Any]]]:
        path = Path(file_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        required_keys = {
            "character_cards_v3",
            "character_cards_v2_legacy",
            "character_cards_v1_legacy",
            "worldbooks_parsed",
        }
        if not any(key in payload for key in required_keys):
            raise KeyError(
                "Selected file contains an invalid layout: Missing core data arrays keys."
            )

        normalized = blank_ledger_data()
        for key in normalized:
            value = payload.get(key, [])
            aliases = LEDGER_KEY_ALIASES.get(key, ())
            if key not in payload or not isinstance(value, list):
                for alias in aliases:
                    alias_value = payload.get(alias, [])
                    if isinstance(alias_value, list):
                        value = alias_value
                        break
            normalized[key] = list(value) if isinstance(value, list) else []
        self.ledger_data = normalized
        self.loaded_path = path
        return self.ledger_data

    def iter_filtered_records(
        self,
        search_token: str,
        enabled_spec_tags: set[str],
    ) -> list[tuple[str, dict[str, Any]]]:
        normalized_search = search_token.strip().lower()
        results: list[tuple[str, dict[str, Any]]] = []

        for spec_tag, ledger_key in SPEC_TAG_TO_LEDGER_KEY.items():
            if spec_tag not in enabled_spec_tags:
                continue
            for item in self.ledger_data.get(ledger_key, []):
                name = item.get("character_name", item.get("filename", "Unknown Resource"))
                filepath = item.get("file_path", "")
                error_msg = item.get("error", "")
                combined_match = f"{name} {filepath} {spec_tag} {error_msg}".lower()
                if normalized_search and normalized_search not in combined_match:
                    continue
                results.append((spec_tag, item))

        return results

    def remove_item(self, spec_tag: str, target_filepath: str) -> None:
        ledger_key = SPEC_TAG_TO_LEDGER_KEY.get(spec_tag)
        if ledger_key is None:
            return
        self.ledger_data[ledger_key] = [
            item
            for item in self.ledger_data.get(ledger_key, [])
            if item.get("file_path") != target_filepath
        ]

    def corrupted_filepaths(self) -> list[str]:
        return [
            str(item.get("file_path", ""))
            for item in self.ledger_data.get("unmapped_or_corrupted_assets", [])
            if str(item.get("file_path", "")).strip()
        ]


def purge_filepaths(
    target_filepaths: list[str],
    *,
    sleep_seconds: float = 0.0,
    log_callback=None,
) -> dict[str, Any]:
    purged_paths: list[str] = []
    skipped_paths: list[str] = []
    failed_paths: list[dict[str, str]] = []

    for raw_path in target_filepaths:
        path = Path(raw_path)
        if not path.exists():
            skipped_paths.append(str(path))
            if log_callback is not None:
                log_callback(
                    f"  -> [SKIP]: File path does not exist on disk: {path.name}"
                )
            continue

        try:
            if not os.access(path, os.W_OK):
                raise PermissionError(
                    f"macOS System Level Write Access Denied for: {path}"
                )
            os.remove(path)
            purged_paths.append(str(path))
            if log_callback is not None:
                log_callback(
                    f"  -> [PURGED SUCCESSFULLY]: Permanently unlinked file: {path.name}"
                )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        except Exception as exc:  # noqa: BLE001
            failed_paths.append({"file_path": str(path), "error": str(exc)})
            if log_callback is not None:
                log_callback(
                    f"  -> [CRITICAL WRITE OVERRIDE FAILURE] inside '{path.name}': {exc}"
                )

    return {
        "purged_paths": purged_paths,
        "skipped_paths": skipped_paths,
        "failed_paths": failed_paths,
        "success_count": len(purged_paths),
    }


if QThread is not None and pyqtSignal is not None:
    class AsyncBatchPurgeWorker(QThread):
        log_update_signal = pyqtSignal(str)
        batch_complete_signal = pyqtSignal(dict)

        def __init__(self, target_filepaths: list[str], parent=None) -> None:
            super().__init__(parent)
            self.target_filepaths = list(target_filepaths)

        def run(self) -> None:  # type: ignore[override]
            self.log_update_signal.emit(
                f"Engaging asynchronous batch purge pipeline over {len(self.target_filepaths)} files..."
            )
            report = purge_filepaths(
                self.target_filepaths,
                sleep_seconds=0.02,
                log_callback=self.log_update_signal.emit,
            )
            self.batch_complete_signal.emit(report)


    class TropeQueryInterfacePanel(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Repo Asset Ledger Query Portal")
            self.setMinimumSize(1200, 750)
            self.store = RepoAssetLedgerStore()
            self.purge_worker: AsyncBatchPurgeWorker | None = None
            self._build_ui()
            self.refresh_query_results_viewport()

        def _build_ui(self) -> None:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            master_layout = QVBoxLayout(main_widget)

            top_bar = QHBoxLayout()
            top_bar.addWidget(QLabel("<b>LEDGER DATABASE ENGINE SEARCH WORKSPACE</b>"))
            self.lbl_ledger_status = QLabel(
                "<span style='color:#ef4444;'>No Ledger Loaded</span>"
            )
            top_bar.addWidget(self.lbl_ledger_status)
            top_bar.addStretch()

            load_ledger_btn = QPushButton("Load Asset Ledger (.JSON)")
            load_ledger_btn.clicked.connect(self.execute_ledger_import_flow)
            top_bar.addWidget(load_ledger_btn)
            master_layout.addLayout(top_bar)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            master_layout.addWidget(splitter)

            search_results_container = QWidget()
            left_layout = QVBoxLayout(search_results_container)
            left_layout.setContentsMargins(0, 0, 0, 0)

            filter_group = QGroupBox("Search Parameters & Filters Matrix")
            filter_layout = QVBoxLayout(filter_group)

            self.search_bar = QLineEdit()
            self.search_bar.setPlaceholderText(
                "Search character names, filenames, directory paths, or metadata tokens..."
            )
            self.search_bar.textChanged.connect(self.refresh_query_results_viewport)
            filter_layout.addWidget(self.search_bar)

            checkbox_row = QHBoxLayout()
            self.cb_v3 = QCheckBox("Spec CCV3 Profiles")
            self.cb_v2 = QCheckBox("Legacy Spec V2")
            self.cb_v1 = QCheckBox("Legacy Spec V1")
            self.cb_wb = QCheckBox("Worldbook Assets")
            self.cb_fail = QCheckBox("Corrupted Files")

            for checkbox in (
                self.cb_v3,
                self.cb_v2,
                self.cb_v1,
                self.cb_wb,
                self.cb_fail,
            ):
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(self.refresh_query_results_viewport)
                checkbox_row.addWidget(checkbox)

            filter_layout.addLayout(checkbox_row)
            left_layout.addWidget(filter_group)

            left_layout.addWidget(QLabel("<b>Discovered Inventory Ledger Matches:</b>"))
            self.results_list_widget = QListWidget()
            self.results_list_widget.currentItemChanged.connect(
                self.handle_row_selection_changed
            )
            left_layout.addWidget(self.results_list_widget)
            splitter.addWidget(search_results_container)

            self.right_drawer_panel = QGroupBox(
                "Target Object Payload Metadata Canvas"
            )
            right_layout = QVBoxLayout(self.right_drawer_panel)

            self.asset_details_viewer = QTextEdit()
            self.asset_details_viewer.setReadOnly(True)
            right_layout.addWidget(self.asset_details_viewer)

            self.btn_purge_asset = QPushButton(
                "PURGE SELECTED ASSET FROM DISK"
            )
            self.btn_purge_asset.setEnabled(False)
            self.btn_purge_asset.clicked.connect(self.execute_secure_file_removal_flow)
            right_layout.addWidget(self.btn_purge_asset)

            splitter.addWidget(self.right_drawer_panel)
            splitter.setSizes([700, 500])

            self._create_native_menubar_shortcuts()
            self.statusBar().showMessage("Ledger idle.")

        def _create_native_menubar_shortcuts(self) -> None:
            menu_bar = self.menuBar()
            menu_bar.setNativeMenuBar(True)
            tools_menu = menu_bar.addMenu("Trope Engines Tools")
            purge_action = QAction("Batch Purge Corrupted Files", self)
            purge_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
            purge_action.setStatusTip(
                "Safely deletes all flagged corrupt data caches off disk."
            )
            purge_action.triggered.connect(
                self.trigger_batch_purge_confirmation_flow
            )
            tools_menu.addAction(purge_action)

        def execute_ledger_import_flow(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Ingested Asset Inventory Ledger",
                "",
                "JSON Files (*.json)",
            )
            if not file_path:
                return
            try:
                self.store.load_from_path(file_path)
            except Exception as exc:
                self.asset_details_viewer.setPlainText(
                    f"[INGESTION PARSING EXCEPTION]: Validation failed on selection: {exc}"
                )
                return

            self.lbl_ledger_status.setText(
                f"<span style='color:#10b981;'><b>ACTIVE LEDGER SECURED:</b> {Path(file_path).name}</span>"
            )
            self.refresh_query_results_viewport()

        def refresh_query_results_viewport(self) -> None:
            self.results_list_widget.clear()
            enabled_tags = self._enabled_spec_tags()
            for spec_tag, item in self.store.iter_filtered_records(
                self.search_bar.text(),
                enabled_tags,
            ):
                display_name = item.get(
                    "character_name",
                    item.get("filename", "Unknown Resource"),
                )
                filename = item.get("filename", "Embedded Image Text Metadata")
                row = QListWidgetItem(
                    f"[{spec_tag}] {display_name}  -->  ({filename})"
                )
                row.setData(Qt.ItemDataRole.UserRole, (spec_tag, item))
                self.results_list_widget.addItem(row)

            if self.results_list_widget.count() == 0:
                self.asset_details_viewer.setPlainText("")
                self.btn_purge_asset.setEnabled(False)

        def handle_row_selection_changed(
            self,
            current_item: QListWidgetItem | None,
            previous_item: QListWidgetItem | None,
        ) -> None:
            del previous_item
            if current_item is None:
                self.asset_details_viewer.clear()
                self.btn_purge_asset.setEnabled(False)
                return

            spec_tag, source_payload_dict = current_item.data(Qt.ItemDataRole.UserRole)
            report_buffer = [
                f"=== METADATA SCHEMATIC SPEC LAYER: {spec_tag} ===",
                "Database Source Object Map Dump:",
                json.dumps(source_payload_dict, indent=2, ensure_ascii=False),
            ]
            if spec_tag == "V2_LEGACY":
                report_buffer.append(
                    "\n[ENGINE HIGHLIGHT]: Port this configuration through the polymorphic factory switcher to upgrade parameters to CCV3 specs."
                )
            elif spec_tag == "CORRUPTED":
                report_buffer.append(
                    "\n[CRITICAL HARDWARE ALARM]: Payload content is broken or truncated. Execute file recovery triage engines."
                )

            self.asset_details_viewer.setPlainText("\n".join(report_buffer))
            self.btn_purge_asset.setEnabled(
                bool(source_payload_dict.get("file_path"))
            )

        def execute_secure_file_removal_flow(self) -> None:
            current_item = self.results_list_widget.currentItem()
            if current_item is None:
                return

            spec_tag, source_payload_dict = current_item.data(Qt.ItemDataRole.UserRole)
            target_filepath = str(source_payload_dict.get("file_path", ""))
            target_path = Path(target_filepath)

            if not target_filepath or not target_path.exists():
                self.asset_details_viewer.setPlainText(
                    "[FILE DISPOSAL ERROR]: Target file path cannot be resolved on local disk paths."
                )
                return

            confirm_box = QMessageBox(self)
            confirm_box.setIcon(QMessageBox.Icon.Warning)
            confirm_box.setWindowTitle("Critical Action Required")
            confirm_box.setText(
                "Are you completely certain you want to permanently delete this asset file?"
            )
            confirm_box.setInformativeText(
                f"Target: {target_path.name}\nPath: {target_path}\n\nThis action cannot be undone."
            )
            confirm_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            confirm_box.setDefaultButton(QMessageBox.StandardButton.Cancel)

            if confirm_box.exec() != QMessageBox.StandardButton.Yes:
                self.statusBar().showMessage("Purge operation aborted by user.")
                return

            report = purge_filepaths([target_filepath])
            if report["success_count"] != 1:
                error_message = report["failed_paths"][0]["error"] if report["failed_paths"] else "Unknown removal failure."
                self.statusBar().showMessage("File Purge Failed.")
                self.asset_details_viewer.setPlainText(
                    f"[OS STORAGE EXCEPTION]: Failed to cleanly execute os.remove().\nError Context: {error_message}"
                )
                return

            self.store.remove_item(spec_tag, target_filepath)
            self.statusBar().showMessage("Asset successfully purged from storage lines.")
            self.asset_details_viewer.setPlainText(
                f"[SYSTEM SUCCESS]: Physical file permanently unlinked:\n{target_filepath}"
            )
            self.refresh_query_results_viewport()
            self.btn_purge_asset.setEnabled(False)

        def trigger_batch_purge_confirmation_flow(self) -> None:
            target_filepaths = self.store.corrupted_filepaths()
            if not target_filepaths:
                self.asset_details_viewer.append(
                    "[System Notification]: Active cache clean. Zero file unlinking actions required."
                )
                return

            confirm_box = QMessageBox(self)
            confirm_box.setIcon(QMessageBox.Icon.Critical)
            confirm_box.setWindowTitle("System Security Authorization")
            confirm_box.setText(
                "Confirm batch deletion of all flagged corrupted file profiles?"
            )
            confirm_box.setInformativeText(
                f"Targeting {len(target_filepaths)} files inside project directory path nodes.\n\nThis cannot be undone."
            )
            confirm_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            confirm_box.setDefaultButton(QMessageBox.StandardButton.Cancel)

            if confirm_box.exec() == QMessageBox.StandardButton.Yes:
                self.execute_asynchronous_batch_purge_pipeline(target_filepaths)

        def execute_asynchronous_batch_purge_pipeline(
            self,
            target_filepaths: list[str],
        ) -> None:
            self.asset_details_viewer.clear()
            self.purge_worker = AsyncBatchPurgeWorker(target_filepaths, parent=self)
            self.purge_worker.log_update_signal.connect(self.asset_details_viewer.append)
            self.purge_worker.batch_complete_signal.connect(
                self.handle_batch_purge_task_completion
            )
            self.purge_worker.start()

        def handle_batch_purge_task_completion(self, report: dict[str, Any]) -> None:
            for path in report.get("purged_paths", []):
                self.store.remove_item("CORRUPTED", path)
            self.refresh_query_results_viewport()
            self.btn_purge_asset.setEnabled(False)
            self.statusBar().showMessage(
                f"Batch purge completed: removed {report.get('success_count', 0)} files."
            )
            self.asset_details_viewer.append(
                "\n[MIGRATION PURGE BATCH SUCCESSFUL]: "
                f"Asynchronously unlinked {report.get('success_count', 0)} broken assets off disk storage files cleanly."
            )

        def _enabled_spec_tags(self) -> set[str]:
            enabled: set[str] = set()
            if self.cb_v3.isChecked():
                enabled.add("V3_CARD")
            if self.cb_v2.isChecked():
                enabled.add("V2_LEGACY")
            if self.cb_v1.isChecked():
                enabled.add("V1_LEGACY")
            if self.cb_wb.isChecked():
                enabled.add("WORLDBOOK")
            if self.cb_fail.isChecked():
                enabled.add("CORRUPTED")
            return enabled


    def run_repo_asset_query_panel_app() -> int:
        app = QApplication.instance() or QApplication(sys.argv)
        window = TropeQueryInterfacePanel()
        window.show()
        return app.exec()


    TropeQueryDashboardPanel = TropeQueryInterfacePanel
    run_mac_query_dashboard_app = run_repo_asset_query_panel_app
else:
    class AsyncBatchPurgeWorker:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use AsyncBatchPurgeWorker.")


    class TropeQueryInterfacePanel:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use TropeQueryInterfacePanel.")


    def run_repo_asset_query_panel_app() -> int:  # pragma: no cover - PyQt-only shim
        raise ModuleNotFoundError("PyQt6 is required to launch the repo asset query panel UI.")


    class TropeQueryDashboardPanel:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError("PyQt6 is required to use TropeQueryDashboardPanel.")


    run_mac_query_dashboard_app = run_repo_asset_query_panel_app
