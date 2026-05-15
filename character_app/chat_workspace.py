from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid
from typing import Any, Callable

from .card_format_conversion import extract_trope_engine_card
from .card_library import CharacterCardLibrary
from .config import ApiSettings, AppPaths, load_runtime_settings
from .runtime_state import BOOLEAN_WEIGHT_KEYS, DEFAULT_RUNTIME_WEIGHTS, EngineStateCard
from .trope_engine_catalog import (
    ENGINE_PHASE_FOUR_TRIGGER_RULES,
    phase_four_trigger_satisfied,
    engine_weight_keys,
)

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    httpx = None

try:
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QTextCursor
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QPushButton,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    Qt = None
    QThread = None
    pyqtSignal = None
    QTextCursor = None
    QApplication = None
    QComboBox = None
    QFileDialog = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
    QListWidget = None
    QListWidgetItem = None
    QMainWindow = object
    QPushButton = None
    QSplitter = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None


def _stable_color(token: str) -> str:
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
    return f"#{digest[:6]}"


def _normalize_weights_for_session(
    engine_type: str,
    weights: dict[str, Any],
) -> dict[str, int | bool]:
    if engine_type == "Forced-Proximity" and isinstance(weights.get("proximity_heat"), int):
        weights = dict(weights)
        weights.setdefault(
            "proximity_awareness_acceleration",
            max(0, min(5, int(weights["proximity_heat"]))),
        )
        weights.setdefault("hostile_friction_heat", 4)
    normalized = dict(DEFAULT_RUNTIME_WEIGHTS)
    for key in engine_weight_keys(engine_type):
        value = weights.get(key, normalized.get(key, 0))
        if key in BOOLEAN_WEIGHT_KEYS:
            normalized[key] = bool(value)
            continue
        try:
            normalized[key] = max(0, min(5, int(value)))
        except (TypeError, ValueError):
            normalized[key] = 0
    return normalized


def build_session_from_card_payload(
    card_id: str,
    payload: dict[str, Any],
) -> EngineStateCard:
    canonical = extract_trope_engine_card(payload)
    metadata = canonical.get("metadata", {})
    engine_type = str(metadata.get("engine_type", "Meet-Cute"))
    state = EngineStateCard(card_id=card_id, engine_type=engine_type)
    state.current_phase = max(1, min(6, int(metadata.get("current_phase", 1))))
    state.weights.update(
        _normalize_weights_for_session(
            engine_type,
            dict(canonical.get("trope_engine_weights", {})),
        )
    )
    return state


def advance_session_for_turn(
    session: EngineStateCard,
    *,
    engine_type: str,
    user_message: str,
) -> EngineStateCard:
    inverse_trigger_keys = {
        key
        for key, operator, _threshold in ENGINE_PHASE_FOUR_TRIGGER_RULES.get(
            engine_type,
            (),
        )
        if operator == "<="
    }
    session.chat_history.append({"role": "user", "content": user_message})
    for key in engine_weight_keys(engine_type):
        if key in BOOLEAN_WEIGHT_KEYS or key == "lie_count":
            continue
        try:
            delta = -1 if key in inverse_trigger_keys else 1
            session.weights[key] = max(
                0,
                min(5, int(session.weights.get(key, 0)) + delta),
            )
        except (TypeError, ValueError):
            session.weights[key] = 1

    if phase_four_trigger_satisfied(engine_type, session.weights):
        session.current_phase = max(session.current_phase, 4)
    session.last_updated = time.time()
    return session


def _compose_mock_reply(
    *,
    name: str,
    engine_type: str,
    user_message: str,
    current_phase: int,
) -> str:
    if current_phase >= 4:
        return (
            f"{name} answers in a cracked-open {engine_type} register, clearly more affected by "
            f"your last line: \"{user_message}\"."
        )
    return (
        f"{name} answers from the {engine_type} lane, absorbing your last message and "
        "letting the room shift around it."
    )


def simulate_participant_turns(
    participant_snapshots: list[dict[str, Any]],
    user_message: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for snapshot in participant_snapshots:
        session = EngineStateCard.from_dict(snapshot["session"])
        session = advance_session_for_turn(
            session,
            engine_type=snapshot["engine_type"],
            user_message=user_message,
        )
        reply = _compose_mock_reply(
            name=snapshot["name"],
            engine_type=snapshot["engine_type"],
            user_message=user_message,
            current_phase=session.current_phase,
        )
        session.chat_history.append({"role": "character", "content": reply})
        session.last_updated = time.time()
        results.append(
            {
                "participant_id": snapshot["participant_id"],
                "session": session.to_dict(),
                "message": {
                    "sender": snapshot["participant_id"],
                    "name": snapshot["name"],
                    "content": reply,
                },
            }
        )
    return results


def build_completion_messages(
    *,
    snapshot: dict[str, Any],
    message_history_snapshot: list[dict[str, str]],
    user_message: str,
) -> list[dict[str, str]]:
    system_directive = (
        f"You are {snapshot['name']}, operating under the romance trope paradigm "
        f"{snapshot['engine_type']}. Active relationship variable weights on a 0-5 scale: "
        f"{json.dumps(snapshot['session'].get('weights', {}), ensure_ascii=False)}. "
        "Stay in character, react concisely, and never speak for the user."
    )
    messages = [{"role": "system", "content": system_directive}]
    for turn in message_history_snapshot[-6:]:
        role = "user" if turn["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": f"{turn['name']}: {turn['content']}"})
    messages.append({"role": "user", "content": f"PLAYER: {user_message}"})
    return messages


def build_chat_export_package(controller: "ChatWorkspaceController") -> dict[str, Any]:
    participants = []
    for participant_id in controller.current_participant_ids():
        participant = controller.participants.get(participant_id)
        if participant is None:
            continue
        participants.append(
            {
                "id": participant.participant_id,
                "name": participant.name,
                "engine_type": participant.engine_type,
                "spec_format": participant.spec_format,
                "file_path": participant.file_path,
                "current_phase": participant.session.current_phase,
                "weights": dict(participant.session.weights),
            }
        )
    return {
        "spec": "chara_card_v3_chat_history",
        "spec_version": "3.0",
        "export_timestamp": time.time(),
        "session_id": controller.session_id,
        "mode": "group" if controller.is_group_chat_mode else "solo",
        "participants_index": participants,
        "total_turns_compiled": len(controller.message_backlog),
        "history_buffer_stream": list(controller.message_backlog),
    }


def save_chat_export_package(
    export_package: dict[str, Any],
    target_path: str | Path,
) -> Path:
    path = Path(target_path)
    path.write_text(
        json.dumps(export_package, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


async def _request_agent_reply_async(
    snapshot: dict[str, Any],
    *,
    user_message: str,
    message_history_snapshot: list[dict[str, str]],
    settings: ApiSettings,
    client: "httpx.AsyncClient",
) -> dict[str, Any]:
    session = EngineStateCard.from_dict(snapshot["session"])
    session = advance_session_for_turn(
        session,
        engine_type=snapshot["engine_type"],
        user_message=user_message,
    )

    payload = {
        "messages": build_completion_messages(
            snapshot={**snapshot, "session": session.to_dict()},
            message_history_snapshot=message_history_snapshot,
            user_message=user_message,
        ),
        "mode": "instruct",
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
        "top_p": settings.top_p,
    }
    if settings.model:
        payload["model"] = settings.model

    headers = {"Content-Type": "application/json"}
    if settings.key:
        headers["Authorization"] = f"Bearer {settings.key}"

    try:
        response = await client.post(
            settings.url,
            json=payload,
            headers=headers,
            timeout=settings.timeout,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        reply = (
            f"[Simulation Response from {snapshot['name']} due to connection dropout: {exc}]"
        )

    session.chat_history.append({"role": "character", "content": reply})
    session.last_updated = time.time()
    return {
        "participant_id": snapshot["participant_id"],
        "session": session.to_dict(),
        "message": {
            "sender": snapshot["participant_id"],
            "name": snapshot["name"],
            "content": reply,
        },
    }


async def generate_participant_turns_async(
    participant_snapshots: list[dict[str, Any]],
    *,
    user_message: str,
    message_history_snapshot: list[dict[str, str]],
    settings: ApiSettings,
    client_factory: Callable[[], "httpx.AsyncClient"] | None = None,
) -> list[dict[str, Any]]:
    if httpx is None:
        return simulate_participant_turns(participant_snapshots, user_message)

    factory = client_factory or (lambda: httpx.AsyncClient())
    async with factory() as client:
        tasks = [
            _request_agent_reply_async(
                snapshot,
                user_message=user_message,
                message_history_snapshot=message_history_snapshot,
                settings=settings,
                client=client,
            )
            for snapshot in participant_snapshots
        ]
        return list(await asyncio.gather(*tasks))


@dataclass
class ChatParticipant:
    participant_id: str
    name: str
    engine_type: str
    spec_format: str
    file_path: str
    accent_color: str
    payload: dict[str, Any]
    session: EngineStateCard


class ChatWorkspaceController:
    def __init__(
        self,
        *,
        paths: AppPaths | None = None,
        library: CharacterCardLibrary | None = None,
    ) -> None:
        self.paths = paths or AppPaths()
        self.library = library or CharacterCardLibrary(paths=self.paths)
        self.is_group_chat_mode = False
        self.active_group_participants: list[str] = []
        self.active_solo_character_id: str | None = None
        self.message_backlog: list[dict[str, str]] = []
        self.participants: dict[str, ChatParticipant] = {}
        self.session_id = f"sess_{uuid.uuid4().hex[:8]}"
        self.refresh_library()

    def refresh_library(self) -> int:
        self.library.scan_and_rebuild_library_index()
        loaded: dict[str, ChatParticipant] = {}
        for record in self.library.list_records():
            if record.get("record_type") != "character_card":
                continue
            participant_id = str(record["id"])
            payload = self.library.get_card_payload_for_deployment(participant_id)
            session = build_session_from_card_payload(participant_id, payload)
            loaded[participant_id] = ChatParticipant(
                participant_id=participant_id,
                name=str(record["name"]),
                engine_type=str(record["engine_type"]),
                spec_format=str(record["spec_format"]),
                file_path=str(record["file_path"]),
                accent_color=_stable_color(participant_id),
                payload=payload,
                session=session,
            )

        self.participants = loaded
        participant_ids = list(self.participants.keys())
        if participant_ids:
            if self.active_solo_character_id not in self.participants:
                self.active_solo_character_id = participant_ids[0]
            self.active_group_participants = [
                participant_id
                for participant_id in self.active_group_participants
                if participant_id in self.participants
            ]
            if not self.active_group_participants:
                self.active_group_participants = participant_ids[: min(2, len(participant_ids))]
        else:
            self.active_solo_character_id = None
            self.active_group_participants = []

        if self.message_backlog and not self.participants:
            self.message_backlog.clear()
        return len(self.participants)

    def set_group_mode(self, is_group: bool) -> None:
        self.is_group_chat_mode = is_group
        self.message_backlog.clear()
        participant_ids = list(self.participants.keys())
        if is_group and not self.active_group_participants:
            self.active_group_participants = participant_ids[: min(2, len(participant_ids))]
        elif (
            not is_group
            and participant_ids
            and self.active_solo_character_id not in self.participants
        ):
            self.active_solo_character_id = participant_ids[0]

    def select_solo_character(self, participant_id: str) -> None:
        if participant_id in self.participants:
            self.active_solo_character_id = participant_id

    def toggle_group_participant(self, participant_id: str) -> None:
        if participant_id not in self.participants:
            return
        if participant_id in self.active_group_participants:
            self.active_group_participants.remove(participant_id)
            return
        self.active_group_participants.append(participant_id)

    def current_participant_ids(self) -> list[str]:
        if self.is_group_chat_mode:
            return list(self.active_group_participants)
        if self.active_solo_character_id:
            return [self.active_solo_character_id]
        return []

    def queue_user_message(self, text: str) -> None:
        self.message_backlog.append({"sender": "user", "name": "PLAYER", "content": text})

    def queue_system_message(self, text: str) -> None:
        self.message_backlog.append({"sender": "system", "name": "SYSTEM", "content": text})

    def participant_snapshots(self) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for participant_id in self.current_participant_ids():
            participant = self.participants[participant_id]
            snapshots.append(
                {
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "engine_type": participant.engine_type,
                    "session": participant.session.to_dict(),
                }
            )
        return snapshots

    def apply_turn_results(self, results: list[dict[str, Any]]) -> None:
        for result in results:
            participant_id = str(result["participant_id"])
            participant = self.participants.get(participant_id)
            if participant is None:
                continue
            participant.session = EngineStateCard.from_dict(result["session"])
            self.message_backlog.append(dict(result["message"]))

    def render_chat_html(self) -> str:
        chunks: list[str] = []
        for message in self.message_backlog:
            sender = message["sender"]
            name = message["name"]
            content = message["content"]
            if sender == "user":
                chunks.append(f"<p><b style='color:#8b5cf6;'>{name}:</b> {content}</p>")
                continue
            if sender == "system":
                chunks.append(
                    f"<p style='color:#64748b; font-style:italic;'>{content}</p>"
                )
                continue
            participant = self.participants.get(sender)
            color = participant.accent_color if participant else "#38bdf8"
            chunks.append(f"<p><b style='color:{color};'>{name}:</b> {content}</p>")
        return "".join(chunks)

    def telemetry_text(self) -> str:
        lines = ["=== LIVE MATRIX TELEMETRY CONFIG ===", ""]
        if self.is_group_chat_mode:
            lines.append("Active Group Room Context Instances Pool:")
            lines.append(f"Active Participants Token List: {self.active_group_participants}")
            lines.append("")
            for participant_id in self.active_group_participants:
                participant = self.participants.get(participant_id)
                if participant is None:
                    continue
                lines.extend(self._participant_telemetry_lines(participant))
                lines.append("")
            return "\n".join(lines)

        if self.active_solo_character_id is None:
            lines.append("No active solo session.")
            return "\n".join(lines)
        participant = self.participants.get(self.active_solo_character_id)
        if participant is None:
            lines.append("No active solo session.")
            return "\n".join(lines)
        lines.append("Active Solo Session Room Context:")
        lines.append(f"Character target reference: {participant.name}")
        lines.append(f"Trope Engine Paradigm Class: {participant.engine_type}")
        lines.append("")
        lines.extend(self._participant_telemetry_lines(participant))
        return "\n".join(lines)

    def _participant_telemetry_lines(self, participant: ChatParticipant) -> list[str]:
        lines = [
            f"[{participant.name} - {participant.engine_type}]",
            f"Current Phase: {participant.session.current_phase}",
            f"Spec Format: {participant.spec_format}",
            "Engine Weights Registry:",
        ]
        for key in engine_weight_keys(participant.engine_type):
            value = participant.session.weights.get(key, 0)
            suffix = "" if isinstance(value, bool) else "/5"
            lines.append(f"  - {key}: {value}{suffix}")
        return lines

    def export_package(self) -> dict[str, Any]:
        return build_chat_export_package(self)

    def default_export_filename(self) -> str:
        return f"chat_log_{self.session_id}.json"


if QThread is not None and pyqtSignal is not None:
    class ChatTurnWorker(QThread):
        turn_ready = pyqtSignal(list)
        generation_notice = pyqtSignal(str)

        def __init__(
            self,
            participant_snapshots: list[dict[str, Any]],
            user_message: str,
            *,
            message_history_snapshot: list[dict[str, str]] | None = None,
            settings: ApiSettings | None = None,
            client_factory: Callable[[], "httpx.AsyncClient"] | None = None,
            parent=None,
        ) -> None:
            super().__init__(parent)
            self.participant_snapshots = participant_snapshots
            self.user_message = user_message
            self.message_history_snapshot = list(message_history_snapshot or [])
            self.settings = settings
            self.client_factory = client_factory

        def run(self) -> None:  # type: ignore[override]
            if self.settings is None:
                self.generation_notice.emit(
                    "No runtime API configuration found. Using local simulated replies."
                )
                self.turn_ready.emit(
                    simulate_participant_turns(self.participant_snapshots, self.user_message)
                )
                return

            self.generation_notice.emit(
                f"Dispatching asynchronous completion requests for {len(self.participant_snapshots)} participant(s)..."
            )
            results = asyncio.run(
                generate_participant_turns_async(
                    self.participant_snapshots,
                    user_message=self.user_message,
                    message_history_snapshot=self.message_history_snapshot,
                    settings=self.settings,
                    client_factory=self.client_factory,
                )
            )
            self.turn_ready.emit(results)


    class DesktopChatWorkspaceUI(QMainWindow):
        def __init__(
            self,
            paths: AppPaths | None = None,
            *,
            runtime_settings: ApiSettings | None = None,
            client_factory: Callable[[], "httpx.AsyncClient"] | None = None,
        ) -> None:
            super().__init__()
            self.paths = paths or AppPaths()
            self.paths.ensure_directories()
            self.controller = ChatWorkspaceController(paths=self.paths)
            self.turn_worker: ChatTurnWorker | None = None
            self.runtime_settings = runtime_settings
            self.client_factory = client_factory
            self._suppress_roster_signal = False
            self.setWindowTitle("Trope Engine Chat & Group Arena Workspace")
            self.setMinimumSize(1300, 800)
            self._build_ui()
            self._resolve_runtime_settings_if_possible()
            self._apply_mode(False)

        def _build_ui(self) -> None:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            master_layout = QVBoxLayout(main_widget)
            master_layout.setContentsMargins(12, 12, 12, 12)

            header_strip = QHBoxLayout()
            header_strip.addWidget(QLabel("<b>NATIVE TROPE SIMULATION ARENA</b>"))
            self.session_label = QLabel(
                f"<b>Active Session:</b> <code>{self.controller.session_id}</code>"
            )
            header_strip.addWidget(self.session_label)
            header_strip.addStretch()

            refresh_btn = QPushButton("Refresh Library")
            refresh_btn.clicked.connect(self.refresh_library_roster)
            header_strip.addWidget(refresh_btn)

            export_btn = QPushButton("EXPORT BACKLOG TO CCV3")
            export_btn.clicked.connect(self.execute_json_file_compilation_export_flow)
            header_strip.addWidget(export_btn)

            self.view_selector = QComboBox()
            self.view_selector.addItems(
                ["1-on-1 Solo Chat Mode", "Multi-Card Group Chat Arena"]
            )
            self.view_selector.currentTextChanged.connect(
                self.handle_view_mode_dropdown_changed
            )
            header_strip.addWidget(QLabel("<b>Active Execution Mode:</b>"))
            header_strip.addWidget(self.view_selector)
            master_layout.addLayout(header_strip)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            master_layout.addWidget(splitter)

            self.sidebar_group = QGroupBox("Character Curation Vault")
            sidebar_layout = QVBoxLayout(self.sidebar_group)
            self.roster_list_widget = QListWidget()
            self.roster_list_widget.currentItemChanged.connect(
                self.handle_roster_current_changed
            )
            self.roster_list_widget.itemChanged.connect(self.handle_roster_item_changed)
            sidebar_layout.addWidget(self.roster_list_widget)
            self.lbl_sidebar_instruction = QLabel()
            self.lbl_sidebar_instruction.setWordWrap(True)
            sidebar_layout.addWidget(self.lbl_sidebar_instruction)
            splitter.addWidget(self.sidebar_group)

            center = QWidget()
            center_layout = QVBoxLayout(center)
            center_layout.setContentsMargins(0, 0, 0, 0)

            self.chat_display_viewport = QTextEdit()
            self.chat_display_viewport.setReadOnly(True)
            center_layout.addWidget(self.chat_display_viewport)

            input_strip = QHBoxLayout()
            self.msg_input_field = QLineEdit()
            self.msg_input_field.setPlaceholderText(
                "Type a message or append action cues..."
            )
            self.msg_input_field.returnPressed.connect(
                self.execute_message_submission_flow
            )
            input_strip.addWidget(self.msg_input_field)
            self.send_btn = QPushButton("SEND TURN")
            self.send_btn.clicked.connect(self.execute_message_submission_flow)
            input_strip.addWidget(self.send_btn)
            center_layout.addLayout(input_strip)

            self.pipeline_status_label = QLabel("")
            center_layout.addWidget(self.pipeline_status_label)
            splitter.addWidget(center)

            self.telemetry_group = QGroupBox("Live Metrics Telemetry Inspector")
            telemetry_layout = QVBoxLayout(self.telemetry_group)
            self.metrics_readout_pane = QTextEdit()
            self.metrics_readout_pane.setReadOnly(True)
            telemetry_layout.addWidget(self.metrics_readout_pane)
            splitter.addWidget(self.telemetry_group)
            splitter.setSizes([240, 720, 340])

        def _resolve_runtime_settings_if_possible(self) -> None:
            if self.runtime_settings is not None:
                self.pipeline_status_label.setText(
                    f"Live API pipeline armed for {self.runtime_settings.url}"
                )
                return
            try:
                self.runtime_settings = load_runtime_settings(self.paths)
                self.pipeline_status_label.setText(
                    f"Live API pipeline armed for {self.runtime_settings.url}"
                )
            except Exception as exc:  # noqa: BLE001
                self.runtime_settings = None
                self.pipeline_status_label.setText(f"Simulation mode active: {exc}")

        def refresh_library_roster(self) -> None:
            self.controller.refresh_library()
            self.rebuild_sidebar_roster_widget_items()
            self.render_chat_log_stream_viewport()
            self.flush_telemetry_metrics_readout()

        def handle_view_mode_dropdown_changed(self, selected_text: str) -> None:
            self._apply_mode("Group" in selected_text)

        def _apply_mode(self, is_group: bool) -> None:
            self.controller.set_group_mode(is_group)
            self.sidebar_group.setTitle(
                "Room Pool Participants" if is_group else "Active Character Vault"
            )
            self.lbl_sidebar_instruction.setText(
                "Check rows to add or remove character cards from the room."
                if is_group
                else "Select a character card row to open an isolated 1-on-1 session."
            )
            self.rebuild_sidebar_roster_widget_items()
            self.render_chat_log_stream_viewport()
            self.flush_telemetry_metrics_readout()

        def rebuild_sidebar_roster_widget_items(self) -> None:
            self._suppress_roster_signal = True
            self.roster_list_widget.clear()
            is_group = self.controller.is_group_chat_mode
            for participant_id, participant in self.controller.participants.items():
                item = QListWidgetItem(f"{participant.name}  ({participant.engine_type})")
                item.setData(Qt.ItemDataRole.UserRole, participant_id)
                if is_group:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(
                        Qt.CheckState.Checked
                        if participant_id in self.controller.active_group_participants
                        else Qt.CheckState.Unchecked
                    )
                self.roster_list_widget.addItem(item)

            if not is_group and self.controller.active_solo_character_id:
                for row in range(self.roster_list_widget.count()):
                    item = self.roster_list_widget.item(row)
                    if item.data(Qt.ItemDataRole.UserRole) == self.controller.active_solo_character_id:
                        self.roster_list_widget.setCurrentItem(item)
                        break
            self._suppress_roster_signal = False

        def handle_roster_current_changed(
            self,
            current_item: QListWidgetItem | None,
            previous_item: QListWidgetItem | None,
        ) -> None:
            del previous_item
            if self._suppress_roster_signal or self.controller.is_group_chat_mode:
                return
            if current_item is None:
                return
            participant_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.controller.select_solo_character(str(participant_id))
            self.flush_telemetry_metrics_readout()

        def handle_roster_item_changed(self, item: QListWidgetItem) -> None:
            if self._suppress_roster_signal or not self.controller.is_group_chat_mode:
                return
            participant_id = str(item.data(Qt.ItemDataRole.UserRole))
            should_be_checked = item.checkState() == Qt.CheckState.Checked
            is_active = participant_id in self.controller.active_group_participants
            if should_be_checked != is_active:
                self.controller.toggle_group_participant(participant_id)
                self.flush_telemetry_metrics_readout()

        def execute_message_submission_flow(self) -> None:
            user_message = self.msg_input_field.text().strip()
            if not user_message:
                return
            self.msg_input_field.clear()
            self.controller.queue_user_message(user_message)
            self.render_chat_log_stream_viewport()

            participant_snapshots = self.controller.participant_snapshots()
            if not participant_snapshots:
                self.controller.queue_system_message(
                    "Room empty. Add participants from the sidebar."
                )
                self.render_chat_log_stream_viewport()
                self.flush_telemetry_metrics_readout()
                return

            self.send_btn.setEnabled(False)
            self.msg_input_field.setEnabled(False)
            self.turn_worker = ChatTurnWorker(
                participant_snapshots,
                user_message,
                message_history_snapshot=list(self.controller.message_backlog),
                settings=self.runtime_settings,
                client_factory=self.client_factory,
                parent=self,
            )
            self.turn_worker.turn_ready.connect(self._handle_turn_ready)
            self.turn_worker.generation_notice.connect(self._handle_generation_notice)
            self.turn_worker.finished.connect(self._handle_turn_worker_finished)
            self.turn_worker.start()

        def _handle_turn_ready(self, results: list[dict[str, Any]]) -> None:
            self.controller.apply_turn_results(results)
            self.render_chat_log_stream_viewport()
            self.flush_telemetry_metrics_readout()

        def _handle_generation_notice(self, message: str) -> None:
            self.pipeline_status_label.setText(message)

        def _handle_turn_worker_finished(self) -> None:
            self.send_btn.setEnabled(True)
            self.msg_input_field.setEnabled(True)
            if self.runtime_settings is not None:
                self.pipeline_status_label.setText(
                    f"Pipeline idle. Connected to {self.runtime_settings.url}"
                )
            else:
                self.pipeline_status_label.setText(
                    "Pipeline idle. Simulation mode still active."
                )
            self.msg_input_field.setFocus()

        def render_chat_log_stream_viewport(self) -> None:
            self.chat_display_viewport.setHtml(self.controller.render_chat_html())
            self.chat_display_viewport.moveCursor(QTextCursor.MoveOperation.End)

        def flush_telemetry_metrics_readout(self) -> None:
            self.metrics_readout_pane.setPlainText(self.controller.telemetry_text())

        def execute_json_file_compilation_export_flow(self) -> None:
            if not self.controller.message_backlog:
                self.pipeline_status_label.setText(
                    "Backlog data register is empty. Export cancelled."
                )
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Compiled CCV3 Chat History Log",
                self.controller.default_export_filename(),
                "JSON Files (*.json)",
            )
            if not file_path:
                return
            try:
                save_chat_export_package(self.controller.export_package(), file_path)
                self.pipeline_status_label.setText(
                    f"Unified history tracking ledger written to {Path(file_path).name}"
                )
            except Exception as exc:  # noqa: BLE001
                self.pipeline_status_label.setText(
                    f"Compilation dump failed: {exc}"
                )
else:  # pragma: no cover - environment-specific
    ChatTurnWorker = None
    DesktopChatWorkspaceUI = None


def run_chat_workspace_app(paths: AppPaths | None = None) -> int:
    if QApplication is None:
        raise RuntimeError("PyQt6 is required to run the chat workspace UI.")
    app = QApplication.instance() or QApplication(sys.argv)
    window = DesktopChatWorkspaceUI(paths=paths)
    window.show()
    return app.exec()
