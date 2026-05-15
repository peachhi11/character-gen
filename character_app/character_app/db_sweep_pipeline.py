from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import time
import zipfile
from typing import Any

from .config import AppPaths

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
        QSpinBox,
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
    QSpinBox = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None


SESSION_SAVE_PATTERNS = ("sess_*.json", "state_*.json")


@dataclass
class DatabaseSweepReport:
    status: str
    archive_package: str | None
    total_scanned: int
    archived_records: int
    skipped_active_records: int
    archived_files: list[str]
    skipped_files: list[str]
    failed_files: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "archive_package": self.archive_package,
            "total_scanned": self.total_scanned,
            "archived_records": self.archived_records,
            "skipped_active_records": self.skipped_active_records,
            "archived_files": list(self.archived_files),
            "skipped_files": list(self.skipped_files),
            "failed_files": list(self.failed_files),
        }


def collect_runtime_session_paths(save_vault_dir: str | Path) -> list[Path]:
    vault = Path(save_vault_dir)
    collected: dict[Path, None] = {}
    for pattern in SESSION_SAVE_PATTERNS:
        for path in vault.glob(pattern):
            if path.is_file():
                collected[path] = None
    return sorted(collected)


def archive_stale_session_files(
    save_vault_dir: str | Path,
    *,
    max_age_days: int,
    active_session_ids: set[str] | None = None,
    current_time: float | None = None,
    progress_callback=None,
    log_callback=None,
    cancel_check=None,
) -> DatabaseSweepReport:
    save_vault = Path(save_vault_dir)
    if not save_vault.exists():
        raise FileNotFoundError(
            f"Designated save vault directory path cannot be resolved: {save_vault}"
        )

    archive_dir = save_vault / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)

    active_ids = set(active_session_ids or set())
    all_targets = collect_runtime_session_paths(save_vault)
    if log_callback is not None:
        log_callback("Engaging database sweep and maintenance pipeline...")

    if not all_targets:
        if log_callback is not None:
            log_callback(
                "[SWEEP NOTICE]: Save directory contains zero cold session data records."
            )
        return DatabaseSweepReport(
            status="EMPTY",
            archive_package=None,
            total_scanned=0,
            archived_records=0,
            skipped_active_records=0,
            archived_files=[],
            skipped_files=[],
            failed_files=[],
        )

    now = time.time() if current_time is None else float(current_time)
    max_age_seconds = max(1, int(max_age_days)) * 86400
    archive_zip_path = archive_dir / (
        f"archive_batch_{time.strftime('%Y%m%d', time.localtime(now))}.zip"
    )

    archived_files: list[str] = []
    skipped_files: list[str] = []
    failed_files: list[dict[str, str]] = []

    for index, file_path in enumerate(all_targets, start=1):
        if cancel_check is not None and cancel_check():
            if log_callback is not None:
                log_callback(
                    "[SWEEP ABORT]: Process explicitly terminated by user command request."
                )
            return DatabaseSweepReport(
                status="CANCELLED",
                archive_package=str(archive_zip_path) if archived_files else None,
                total_scanned=len(all_targets),
                archived_records=len(archived_files),
                skipped_active_records=len(skipped_files),
                archived_files=archived_files,
                skipped_files=skipped_files,
                failed_files=failed_files,
            )

        try:
            if file_path.stem in active_ids:
                skipped_files.append(file_path.name)
                if log_callback is not None:
                    log_callback(
                        f"Skipping live in-memory session target [{index}/{len(all_targets)}]: {file_path.name}"
                    )
                continue

            file_age = now - file_path.stat().st_mtime
            if file_age <= max_age_seconds:
                skipped_files.append(file_path.name)
                if log_callback is not None:
                    log_callback(
                        f"Skipping active/fresh session target [{index}/{len(all_targets)}]: {file_path.name}"
                    )
                continue

            if log_callback is not None:
                log_callback(
                    f"Archiving cold session target [{index}/{len(all_targets)}]: {file_path.name}"
                )

            with zipfile.ZipFile(
                archive_zip_path,
                mode="a",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive_handle:
                archive_handle.write(file_path, arcname=file_path.name)
            file_path.unlink()
            archived_files.append(file_path.name)
        except Exception as exc:  # noqa: BLE001
            failed_files.append({"file_path": str(file_path), "error": str(exc)})
            if log_callback is not None:
                log_callback(
                    f"  -> [WRITE REJECTION ERROR] processing '{file_path.name}': {exc}"
                )
        finally:
            if progress_callback is not None:
                progress_callback(int(index / len(all_targets) * 100))

    return DatabaseSweepReport(
        status="SUCCESS",
        archive_package=str(archive_zip_path) if archived_files else None,
        total_scanned=len(all_targets),
        archived_records=len(archived_files),
        skipped_active_records=len(skipped_files),
        archived_files=archived_files,
        skipped_files=skipped_files,
        failed_files=failed_files,
    )


if QThread is not None and pyqtSignal is not None:
    class AsyncDatabaseSweepWorker(QThread):
        progress_tick = pyqtSignal(int)
        log_stream = pyqtSignal(str)
        sweep_complete = pyqtSignal(dict)

        def __init__(
            self,
            save_vault_dir: str,
            max_age_days: int,
            parent=None,
        ) -> None:
            super().__init__(parent)
            self.save_vault_dir = save_vault_dir
            self.max_age_days = max_age_days
            self.is_cancelled = False

        def run(self) -> None:  # type: ignore[override]
            try:
                report = archive_stale_session_files(
                    self.save_vault_dir,
                    max_age_days=self.max_age_days,
                    progress_callback=self.progress_tick.emit,
                    log_callback=self.log_stream.emit,
                    cancel_check=lambda: self.is_cancelled,
                )
                self.sweep_complete.emit(report.to_dict())
            except FileNotFoundError:
                self.log_stream.emit(
                    "[SWEEP ERROR]: Designated save vault directory path cannot be resolved."
                )
                self.sweep_complete.emit(
                    {
                        "status": "FAILED",
                        "error": "Path not found.",
                        "archive_package": None,
                        "total_scanned": 0,
                        "archived_records": 0,
                        "skipped_active_records": 0,
                        "archived_files": [],
                        "skipped_files": [],
                        "failed_files": [],
                    }
                )


    class DatabaseSweepPipelineUI(QMainWindow):
        def __init__(self, paths: AppPaths | None = None) -> None:
            super().__init__()
            self.paths = paths or AppPaths()
            self.paths.ensure_directories()
            self.worker: AsyncDatabaseSweepWorker | None = None
            self.saves_vault_path = str(self.paths.runtime_saves_dir)
            self.setWindowTitle("Local Database Sweep & Archival Pipeline")
            self.setMinimumSize(800, 500)
            self._build_ui()

        def _build_ui(self) -> None:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            master_layout = QVBoxLayout(main_widget)

            path_group = QGroupBox("Directory Configuration Parameters")
            path_layout = QVBoxLayout(path_group)
            self.lbl_vault_path = QLabel()

            setup_row = QHBoxLayout()
            btn_select_dir = QPushButton("Choose Saves Vault Folder")
            btn_select_dir.clicked.connect(self.select_saves_directory)

            self.spin_age = QSpinBox()
            self.spin_age.setRange(1, 365)
            self.spin_age.setValue(7)
            self.spin_age.setSuffix(" Days Inactive")

            setup_row.addWidget(btn_select_dir)
            setup_row.addWidget(QLabel("<b>Archival Threshold Age:</b>"))
            setup_row.addWidget(self.spin_age)
            setup_row.addStretch()

            path_layout.addWidget(self.lbl_vault_path)
            path_layout.addLayout(setup_row)
            master_layout.addWidget(path_group)

            progress_group = QGroupBox("Asynchronous Maintenance Task Controller")
            progress_layout = QVBoxLayout(progress_group)
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            progress_layout.addWidget(self.progress_bar)

            self.action_btn = QPushButton(
                "ENGAGE ASYNCHRONOUS STORAGE CLEANUP SWEEP"
            )
            self.action_btn.clicked.connect(self.toggle_sweep_pipeline_execution)
            progress_layout.addWidget(self.action_btn)
            master_layout.addWidget(progress_group)

            master_layout.addWidget(
                QLabel("<b>Real-Time Pipeline Execution Logging Output:</b>")
            )
            self.log_terminal = QTextEdit()
            self.log_terminal.setReadOnly(True)
            master_layout.addWidget(self.log_terminal)

            self._refresh_vault_label()

        def _refresh_vault_label(self) -> None:
            self.lbl_vault_path.setText(
                f"<b>Target Saves Directory:</b> <code>{self.saves_vault_path}</code>"
            )

        def select_saves_directory(self) -> None:
            selected = QFileDialog.getExistingDirectory(
                self,
                "Select Player Save Sessions Vault Location",
                self.saves_vault_path,
            )
            if selected:
                self.saves_vault_path = selected
                self._refresh_vault_label()

        def toggle_sweep_pipeline_execution(self) -> None:
            if self.worker and self.worker.isRunning():
                self.worker.is_cancelled = True
                self.action_btn.setEnabled(False)
                return

            if not self.saves_vault_path:
                self.log_terminal.append(
                    "[INTERFACE ALERT]: You must select a valid saves vault directory before engaging sweeps."
                )
                return

            self.progress_bar.setValue(0)
            self.log_terminal.clear()
            self.worker = AsyncDatabaseSweepWorker(
                save_vault_dir=self.saves_vault_path,
                max_age_days=self.spin_age.value(),
                parent=self,
            )
            self.worker.progress_tick.connect(self.progress_bar.setValue)
            self.worker.log_stream.connect(self.log_terminal.append)
            self.worker.sweep_complete.connect(self.handle_sweep_pipeline_finalization)
            self.worker.start()
            self.action_btn.setText("ABORT SWEEP PIPELINE / FORCE CANCEL")
            self.action_btn.setEnabled(True)

        def handle_sweep_pipeline_finalization(self, results_dict: dict[str, Any]) -> None:
            self.action_btn.setEnabled(True)
            self.action_btn.setText("ENGAGE ASYNCHRONOUS STORAGE CLEANUP SWEEP")
            status_code = results_dict.get("status")
            if status_code == "SUCCESS":
                self.progress_bar.setValue(100)
                self.log_terminal.append(
                    "\n<b>[DATABASE CLEANUP PIPELINE CONCLUDED SUCCESSFULLY]:</b>\n"
                    f"- Cumulative Save Files Audited: {results_dict['total_scanned']}\n"
                    f"- Stale Save Sessions Compressed to ZIP Archive: {results_dict['archived_records']}\n"
                    f"- Active/Fresh Session Profiles Retained Intact: {results_dict['skipped_active_records']}\n"
                    f"- Target Archive File Output Path: <span style='color:#34d399;'>{results_dict['archive_package']}</span>"
                )
            elif status_code == "EMPTY":
                self.log_terminal.append(
                    "\n[DATABASE CLEANUP PIPELINE]: No archived sessions were found."
                )
            elif status_code == "FAILED":
                self.log_terminal.append(
                    f"\n[DATABASE CLEANUP PIPELINE FAILED]: {results_dict.get('error', 'Unknown error.')}"
                )
            elif status_code == "CANCELLED":
                self.log_terminal.append(
                    "\n[DATABASE CLEANUP PIPELINE]: Sweep cancelled before completion."
                )
else:  # pragma: no cover - environment-specific
    AsyncDatabaseSweepWorker = None
    DatabaseSweepPipelineUI = None


def run_database_sweep_pipeline_app(paths: AppPaths | None = None) -> int:
    if QApplication is None:
        raise RuntimeError("PyQt6 is required to run the database sweep pipeline UI.")

    app = QApplication.instance() or QApplication(sys.argv)
    window = DatabaseSweepPipelineUI(paths=paths)
    window.show()
    return app.exec()
