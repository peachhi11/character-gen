from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable

from .card_format_conversion import extract_trope_engine_card
from .card_schema_validation import CharacterCardValidator, VALID_ENGINES

try:
    from PyQt6.QtCore import QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QApplication,
        QFileDialog,
        QLabel,
        QHBoxLayout,
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
    QLabel = None
    QHBoxLayout = None
    QMainWindow = object
    QProgressBar = None
    QPushButton = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None


def scan_schema_directory(
    target_dir: str,
    valid_schema_enums: set[str] | frozenset[str],
) -> tuple[dict[str, Any], list[str]]:
    return _scan_directory_impl(target_dir, valid_schema_enums)


def _emit_log(
    logs: list[str],
    message: str,
    log_callback: Callable[[str], None] | None,
) -> None:
    logs.append(message)
    if log_callback is not None:
        log_callback(message)


def _scan_directory_impl(
    target_dir: str,
    valid_schema_enums: set[str] | frozenset[str],
    *,
    progress_callback: Callable[[int], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    logs: list[str] = []
    _emit_log(
        logs,
        "Initiating asynchronous structural schema validation check scan...",
        log_callback,
    )
    target_files: list[str] = []
    for root, _dirs, files in os.walk(target_dir):
        for file_name in files:
            if file_name.lower().endswith(".json"):
                target_files.append(os.path.join(root, file_name))

    total_files = len(target_files)
    if total_files == 0:
        _emit_log(
            logs,
            "[SYSTEM ABORT]: Target directory contains zero .json data records.",
            log_callback,
        )
        return {"status": "EMPTY"}, logs

    validator = CharacterCardValidator()
    passed = 0
    failed_validation = 0
    malformed = 0
    scanned = 0

    for index, path in enumerate(target_files):
        if cancel_check is not None and cancel_check():
            _emit_log(
                logs,
                "[SYSTEM CANCEL]: Process explicitly halted by operator command.",
                log_callback,
            )
            return {
                "status": "CANCELLED",
                "scanned": scanned,
                "passed": passed,
                "failed_validation": failed_validation,
                "corrupted": malformed,
            }, logs

        filename = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError:
            malformed += 1
            _emit_log(
                logs,
                f"  -> [MALFORMED STREAM]: '{filename}' contains corrupted JSON syntax code.",
                log_callback,
            )
        except Exception as exc:  # noqa: BLE001
            malformed += 1
            _emit_log(
                logs,
                f"  -> [READ REJECTION]: Processing exception inside '{filename}': {exc}",
                log_callback,
            )
        else:
            try:
                canonical = extract_trope_engine_card(data)
            except ValueError as exc:
                failed_validation += 1
                _emit_log(
                    logs,
                    f"  -> [FAIL VALIDATION]: '{filename}' could not be normalized into a trope engine card: {exc}",
                    log_callback,
                )
            else:
                result = validator.validate_card_json(canonical)
                metadata = result.normalized_card.get("metadata", {}) if result.normalized_card else {}
                engine_type = metadata.get("engine_type")
                if result.success and engine_type in valid_schema_enums:
                    passed += 1
                    log_line = (
                        f"  -> [PASS]: '{filename}' validated as engine '{engine_type}'."
                    )
                    if result.warnings:
                        log_line += f" Warning: {result.warnings[0]}"
                    _emit_log(logs, log_line, log_callback)
                else:
                    failed_validation += 1
                    detail = (
                        result.errors[0]
                        if result.errors
                        else f"Engine '{engine_type}' is not in the active validation registry."
                    )
                    _emit_log(
                        logs,
                        f"  -> [FAIL VALIDATION]: '{filename}' failed structural validation. {detail}",
                        log_callback,
                    )

        scanned = index + 1
        if progress_callback is not None:
            progress_callback(int((scanned / total_files) * 100))

    return {
        "status": "SUCCESS",
        "scanned": scanned,
        "passed": passed,
        "failed_validation": failed_validation,
        "corrupted": malformed,
    }, logs


if QThread is not None and pyqtSignal is not None:
    class AsyncBatchValidatorWorker(QThread):
        progress_update = pyqtSignal(int)
        log_output = pyqtSignal(str)
        validation_complete = pyqtSignal(dict)

        def __init__(self, target_dir: str, valid_schema_enums: set[str]):
            super().__init__()
            self.target_dir = target_dir
            self.valid_enums = valid_schema_enums
            self.is_cancelled = False

        def run(self) -> None:  # type: ignore[override]
            report, _logs = _scan_directory_impl(
                self.target_dir,
                self.valid_enums,
                progress_callback=self.progress_update.emit,
                log_callback=self.log_output.emit,
                cancel_check=lambda: self.is_cancelled,
            )
            self.validation_complete.emit(report)


    class BatchValidatorDashboardUI(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Trope Engine Schema Batch Validator")
            self.setMinimumSize(800, 500)
            self.schema_registry = set(VALID_ENGINES)
            self.worker: AsyncBatchValidatorWorker | None = None
            self.target_folder = ""
            self._build_ui()

        def _build_ui(self) -> None:
            widget = QWidget()
            self.setCentralWidget(widget)
            layout = QVBoxLayout(widget)

            self.lbl_path = QLabel("<b>Target Scanning Directory:</b> Not Chosen")
            layout.addWidget(self.lbl_path)

            btn_row = QHBoxLayout()
            select_btn = QPushButton("Choose Cards Folder")
            select_btn.clicked.connect(self.select_directory)
            self.run_btn = QPushButton("ENGAGE SCHEMA VALIDATION RUN")
            self.run_btn.clicked.connect(self.toggle_validation)

            btn_row.addWidget(select_btn)
            btn_row.addWidget(self.run_btn)
            layout.addLayout(btn_row)

            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)

            self.console = QTextEdit()
            self.console.setReadOnly(True)
            layout.addWidget(self.console)

        def select_directory(self) -> None:
            self.target_folder = QFileDialog.getExistingDirectory(
                self,
                "Open Character Cards Directory Source",
            )
            if self.target_folder:
                self.lbl_path.setText(
                    f"<b>Target Scanning Directory:</b> <code>{self.target_folder}</code>"
                )

        def toggle_validation(self) -> None:
            if self.worker and self.worker.isRunning():
                self.worker.is_cancelled = True
                self.run_btn.setEnabled(False)
                return

            if not self.target_folder:
                self.console.append(
                    "[INTERFACE ALERT]: Select a folder directory path node before executing scans."
                )
                return

            self.progress_bar.setValue(0)
            self.console.clear()
            self.worker = AsyncBatchValidatorWorker(
                self.target_folder,
                self.schema_registry,
            )
            self.worker.progress_update.connect(self.progress_bar.setValue)
            self.worker.log_output.connect(self.console.append)
            self.worker.validation_complete.connect(self.handle_completion)
            self.worker.start()
            self.run_btn.setEnabled(True)
            self.run_btn.setText("ABORT VALIDATION PROCESS")

        def handle_completion(self, report: dict[str, Any]) -> None:
            self.run_btn.setEnabled(True)
            self.run_btn.setText("ENGAGE SCHEMA VALIDATION RUN")
            if report.get("status") == "SUCCESS":
                self.progress_bar.setValue(100)
                self.console.append(
                    "\n<b>[DATABASE INVENTORY AUDIT COMPLETED]:</b>\n"
                    f"- Cumulative JSON Asset Data Objects Audited: {report['scanned']}\n"
                    f"- Total Confirmed Compliant Profiles: {report['passed']}\n"
                    f"- Total Validation Failures Intercepted: {report['failed_validation']}\n"
                    f"- Total Corrupted Truncated Syntax Files Isolated: {report['corrupted']}"
                )
            elif report.get("status") == "CANCELLED":
                self.console.append(
                    "\n<b>[DATABASE INVENTORY AUDIT CANCELLED]:</b>\n"
                    f"- Files Audited Before Cancellation: {report['scanned']}\n"
                    f"- Total Confirmed Compliant Profiles: {report['passed']}\n"
                    f"- Total Validation Failures Intercepted: {report['failed_validation']}\n"
                    f"- Total Corrupted Truncated Syntax Files Isolated: {report['corrupted']}"
                )
else:  # pragma: no cover - environment-specific
    AsyncBatchValidatorWorker = None
    BatchValidatorDashboardUI = None


def run_mac_batch_validator_app() -> int:
    if QApplication is None or BatchValidatorDashboardUI is None:
        raise RuntimeError("PyQt6 is not available in this Python environment.")
    app = QApplication.instance() or QApplication(sys.argv)
    window = BatchValidatorDashboardUI()
    window.show()
    return app.exec()
