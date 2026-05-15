from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .db_migration_manager import TropeDatabaseMigrationManager


class AsyncMigrationWorker(QThread):
    progress_tick = pyqtSignal(int)
    log_output = pyqtSignal(str)
    task_complete = pyqtSignal(dict)

    def __init__(
        self,
        source_dir: str | Path,
        output_dir: str | Path,
        *,
        create_backups: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.is_cancelled = False
        self.manager = TropeDatabaseMigrationManager(create_backups=create_backups)

    def run(self) -> None:  # type: ignore[override]
        try:
            report = self.manager.batch_migrate_directory(
                self.source_dir,
                self.output_dir,
                progress_callback=self.progress_tick.emit,
                log_callback=self.log_output.emit,
                cancel_check=lambda: self.is_cancelled,
            )
            self.task_complete.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.log_output.emit(f"[SYSTEM ERROR]: {exc}")
            self.task_complete.emit(
                {
                    "status": "FAILED",
                    "total_files_scanned": self.manager.processed_count,
                    "successful_upgrades": self.manager.upgraded_count,
                    "failed_parses": self.manager.failure_count + 1,
                    "lore_nodes_compiled": self.manager.extracted_lore_nodes,
                }
            )
