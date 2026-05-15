from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import uuid

from PyQt6.QtCore import QSettings, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .api import APIClient
from .async_migration import AsyncMigrationWorker
from .cache_sync_manager import CacheSyncManagerWorker
from .card_format_conversion import extract_trope_engine_card, wrap_trope_engine_card_as_v3
from .card_schema_validation import CharacterCardValidator
from .cards import CharacterRepository
from .config import ApiSettings, AppPaths, load_reference_bundle, load_runtime_settings
from .constants import FieldId, SAVE_FORMATS
from .db_migration_manager import TropeDatabaseMigrationManager
from .drag_drop_zone import TropeDragDropZone
from .generation import GenerationEngine
from .mode_switcher import TropeModeSwitcher
from .models import CharacterCard, PromptSet, PromptTemplate
from .png_metadata_engine import PNGMetadataEngine
from .prompt_mapper import LLMPromptMapper
from .repo_asset_parser import RepoAssetParserWorker
from .prompts import PromptRepository, validate_prompt_text
from .runtime_state import EngineStateCard, TropeStorageController
from .sprite_display_manager import TropeSpriteDisplayManager
from .state_io_controller import StateIOController
from .telemetry_sync import TelemetrySyncHook
from .trope_dynamic_pivot import TropeDynamicPivotParser
from .trope_telemetry_system import TropeTelemetrySystem
from .engine_state_card_tropes import (
    BUCKET_SUBGROUP_ENGINE_TYPES,
    SUPERSEDED_SAFE_EQUIVALENTS,
    bucket_for_engine,
)
from .trope_engine_catalog import (
    ENGINE_OPTION_ORDER,
    engine_weight_keys,
    phase_four_activation_condition,
)


@dataclass(frozen=True)
class TabTheme:
    name: str
    accent: str
    accent_strong: str
    panel: str
    panel_soft: str
    draft_surface: str
    result_surface: str
    border: str


CHARACTER_THEME = TabTheme(
    name="characters",
    accent="#dce8f8",
    accent_strong="#6b89b8",
    panel="#d8e5f7",
    panel_soft="#eef5fd",
    draft_surface="#eef4fb",
    result_surface="#fffdf9",
    border="#bdd0ea",
)

PERSONA_THEME = TabTheme(
    name="persona",
    accent="#e6ddf7",
    accent_strong="#8872b4",
    panel="#ddd2f1",
    panel_soft="#f3edfb",
    draft_surface="#f0eaf9",
    result_surface="#fffdfb",
    border="#cdbfe7",
)

PROMPTS_THEME = TabTheme(
    name="prompts",
    accent="#e1f1e5",
    accent_strong="#699277",
    panel="#d7e9dc",
    panel_soft="#eef8f1",
    draft_surface="#edf7f0",
    result_surface="#fffefa",
    border="#bdd6c4",
)

WORLD_THEME = TabTheme(
    name="world",
    accent="#f7ead8",
    accent_strong="#b6855d",
    panel="#f0e0ca",
    panel_soft="#fcf5eb",
    draft_surface="#f7efe3",
    result_surface="#fffdfa",
    border="#e2c7a5",
)

FIELD_HINTS = {
    FieldId.NAME: "Keep this focused. One naming nudge is usually enough.",
    FieldId.DESCRIPTION: "Use this as the reader-facing or orientation layer, not a second dossier.",
    FieldId.PERSONALITY: "This is the private engine of the card: voice, behavior, psychology, and roleplay logic.",
    FieldId.SCENARIO: "Frame the scene pressure clearly so the dynamic has somewhere to move.",
    FieldId.FIRST_MES: "Treat this as the true scene start, not a summary.",
    FieldId.MES_EXAMPLE: "Voice reference only. Teach cadence and posture, not canned dialogue.",
}

PROMPT_FIELD_HINTS = {
    FieldId.NAME: "Set the naming logic and any target tone or background constraints.",
    FieldId.DESCRIPTION: "Define the output shape for the overview or public-facing layer.",
    FieldId.PERSONALITY: "Keep this disciplined. Dense prompts produce cleaner cards than sprawling ones.",
    FieldId.SCENARIO: "Use earlier fields to anchor tone, route energy, and relationship pressure.",
    FieldId.FIRST_MES: "Build the opener from scene tension instead of generic greeting language.",
    FieldId.MES_EXAMPLE: "This should steer voice, rhythm, and emotional range without overfitting.",
}

ENGINE_BOOLEAN_WEIGHT_KEYS = frozenset(
    {"lie_active", "distance_locked", "safeword_breached"}
)


def _canonical_visible_engine(engine_type: str | None) -> str | None:
    if not engine_type:
        return engine_type
    return SUPERSEDED_SAFE_EQUIVALENTS.get(engine_type, engine_type)


def _visible_bucket_keys() -> list[str]:
    return [
        bucket_key
        for bucket_key, subgroup_map in BUCKET_SUBGROUP_ENGINE_TYPES.items()
        if any(_visible_engine_names(bucket_key, subgroup_name) for subgroup_name in subgroup_map)
    ]


def _visible_subgroup_names(bucket_key: str) -> list[str]:
    subgroup_map = BUCKET_SUBGROUP_ENGINE_TYPES.get(bucket_key, {})
    return [
        subgroup_name
        for subgroup_name, engine_names in subgroup_map.items()
        if any(
            engine_name not in SUPERSEDED_SAFE_EQUIVALENTS
            for engine_name in engine_names
        )
    ]


def _visible_engine_names(bucket_key: str, subgroup_name: str) -> list[str]:
    return [
        engine_name
        for engine_name in BUCKET_SUBGROUP_ENGINE_TYPES.get(bucket_key, {}).get(
            subgroup_name, ()
        )
        if engine_name not in SUPERSEDED_SAFE_EQUIVALENTS
    ]


def _combo_data(combo: QComboBox) -> str:
    return str(combo.currentData() or combo.currentText())


def _find_combo_data(combo: QComboBox, value: str) -> int:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            return index
    return combo.findText(value)


def _display_bucket_label(bucket_key: str) -> str:
    return bucket_key.replace("_", " ").title()

PERSONA_LABELS = {
    FieldId.DESCRIPTION: "Overview",
    FieldId.FIRST_MES: "First Reply",
}


def serialize_reference_card(card: CharacterCard) -> str:
    parts: list[str] = []
    card_name = card.fields.get(FieldId.NAME, "").strip() or card.name.strip()
    if card_name:
        parts.append(f"Name:\n{card_name}")

    for field_id in FieldId.ui_order():
        if field_id == FieldId.NAME:
            continue
        value = card.fields.get(field_id, "").strip()
        if not value:
            continue
        parts.append(f"{field_id.display_name}:\n{value}")

    return "\n\n".join(parts).strip()


def make_card(object_name: str) -> QFrame:
    card = QFrame()
    card.setObjectName(object_name)
    card.setFrameShape(QFrame.Shape.NoFrame)
    return card


def display_label(
    field_id: FieldId,
    overrides: dict[FieldId, str] | None = None,
) -> str:
    if overrides and field_id in overrides:
        return overrides[field_id]
    return field_id.display_name


def build_page_stylesheet(theme: TabTheme) -> str:
    return f"""
    QWidget#pageRoot {{
        background: #f7f4ef;
        color: #2c2532;
    }}
    QFrame#heroCard, QFrame#controlCard, QFrame#referenceCard, QFrame#fieldCard {{
        background: {theme.panel};
        border: 1px solid {theme.border};
        border-radius: 30px;
    }}
    QFrame#surfaceCard, QFrame#surfaceCardWide {{
        background: {theme.panel_soft};
        border: 1px solid {theme.border};
        border-radius: 24px;
    }}
    QLabel#eyebrow {{
        color: {theme.accent_strong};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.2px;
    }}
    QLabel#heroTitle {{
        color: #2d2532;
        font-size: 26px;
        font-weight: 700;
    }}
    QLabel#heroSubtitle, QLabel#fieldHint, QLabel#microCopy {{
        color: #5f5567;
        font-size: 13px;
        line-height: 1.4em;
    }}
    QLabel#fieldTitle {{
        color: #302938;
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#surfaceHeading {{
        color: {theme.accent_strong};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    QLabel#statusPill {{
        background: {theme.accent};
        color: {theme.accent_strong};
        border: 1px solid {theme.border};
        border-radius: 15px;
        padding: 6px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#statusText {{
        color: {theme.accent_strong};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#formLabel {{
        color: #51495b;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }}
    QLineEdit#controlInput, QComboBox#controlInput {{
        background: rgba(255, 253, 249, 0.92);
        color: #2c2532;
        border: 1px solid {theme.border};
        border-radius: 18px;
        padding: 8px 14px;
        min-height: 18px;
    }}
    QTextEdit#draftSurface, QTextEdit#resultSurface, QTextEdit#promptSurface {{
        color: #2c2532;
        border-radius: 22px;
        padding: 14px;
        border: 1px solid rgba(107, 95, 120, 0.12);
        selection-background-color: {theme.accent};
    }}
    QTextEdit#draftSurface {{
        background: {theme.draft_surface};
    }}
    QTextEdit#resultSurface {{
        background: {theme.result_surface};
    }}
    QTextEdit#promptSurface {{
        background: rgba(255, 253, 249, 0.92);
    }}
    QSpinBox#controlInput {{
        background: rgba(255, 253, 249, 0.92);
        color: #2c2532;
        border: 1px solid {theme.border};
        border-radius: 16px;
        padding: 6px 10px;
        min-height: 18px;
    }}
    QPushButton {{
        border-radius: 16px;
        padding: 8px 14px;
        border: 1px solid {theme.border};
        background: rgba(255, 253, 249, 0.85);
        color: #2c2532;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(255, 255, 255, 0.98);
    }}
    QPushButton:pressed {{
        background: rgba(227, 220, 236, 0.98);
        border: 1px solid {theme.accent_strong};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton#primaryButton {{
        background: {theme.accent_strong};
        color: white;
        border: 1px solid {theme.accent_strong};
    }}
    QPushButton#primaryButton:hover {{
        background: {theme.accent_strong};
    }}
    QPushButton#primaryButton:pressed {{
        background: {theme.accent_strong};
        border: 1px solid {theme.accent_strong};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton#ghostButton {{
        background: transparent;
        color: {theme.accent_strong};
    }}
    QPushButton#ghostButton:pressed {{
        background: rgba(255, 255, 255, 0.38);
        border: 1px solid {theme.accent_strong};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QCheckBox {{
        color: #51495b;
        spacing: 8px;
        font-weight: 600;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 1px solid {theme.border};
        background: rgba(255, 253, 249, 0.85);
    }}
    QCheckBox::indicator:checked {{
        background: {theme.accent_strong};
        border: 1px solid {theme.accent_strong};
    }}
    QScrollArea, QSplitter {{
        background: transparent;
        border: none;
    }}
    QSplitter::handle {{
        background: transparent;
        width: 10px;
        height: 10px;
    }}
    """


def build_shell_stylesheet(active_theme: TabTheme) -> str:
    return f"""
    QMainWindow {{
        background: #f7f4ef;
    }}
    QWidget#shellRoot {{
        background: #f7f4ef;
    }}
    QTabWidget::pane {{
        border: none;
        top: 0px;
        background: transparent;
    }}
    QTabBar {{
        background: transparent;
    }}
    QTabBar::tab {{
        background: rgba(255, 255, 255, 0.68);
        color: #71657d;
        border: 1px solid rgba(194, 182, 209, 0.35);
        border-radius: 18px;
        padding: 10px 18px;
        margin-right: 8px;
        min-width: 120px;
        font-size: 13px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {active_theme.panel};
        color: #2d2532;
        border: 1px solid {active_theme.border};
    }}
    QTabBar::tab:hover {{
        background: rgba(255, 255, 255, 0.96);
    }}
    """


class PromptEditor(QWidget):
    def __init__(
        self,
        field_id: FieldId,
        theme: TabTheme,
        field_label: str,
        helper_text: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.field_id = field_id
        self.theme = theme
        self.setObjectName("pageRoot")
        self.setStyleSheet(build_page_stylesheet(theme))

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        card = make_card("fieldCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(4)

        title = QLabel(f"Base Prompt for {field_label}")
        title.setObjectName("fieldTitle")
        title_column.addWidget(title)

        hint = QLabel(helper_text)
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        title_column.addWidget(hint)
        header.addLayout(title_column, 1)

        order_column = QVBoxLayout()
        order_column.setSpacing(4)
        order_label = QLabel("Generation Order")
        order_label.setObjectName("formLabel")
        order_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        order_column.addWidget(order_label)
        self.order_input = QSpinBox()
        self.order_input.setObjectName("controlInput")
        self.order_input.setMinimum(0)
        self.order_input.setMaximum(99)
        self.order_input.setSpecialValueText("Skip")
        self.order_input.setMinimumWidth(96)
        order_column.addWidget(self.order_input)
        header.addLayout(order_column)
        layout.addLayout(header)

        editor_label = QLabel("Prompt Body")
        editor_label.setObjectName("surfaceHeading")
        layout.addWidget(editor_label)

        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("promptSurface")
        self.text_edit.setPlaceholderText(
            "Use {{input}}, earlier field tags like {{description}}, reference tags like {{char_personality}}, and {{if_input}} blocks."
        )
        self.text_edit.setMinimumHeight(190)
        layout.addWidget(self.text_edit)

        outer_layout.addWidget(card)

    def set_value(self, text: str, order: int) -> None:
        self.text_edit.setPlainText(text)
        self.order_input.setValue(max(0, order))

    def template(self) -> PromptTemplate | None:
        text = self.text_edit.toPlainText().strip()
        order = self.order_input.value()
        if not text or order <= 0:
            return None
        validate_prompt_text(text)
        return PromptTemplate(field=self.field_id, text=text, order=order)


class PromptSetTab(QWidget):
    prompt_set_requested = pyqtSignal(str)
    prompt_set_saved = pyqtSignal(object)

    def __init__(
        self,
        prompt_repository: PromptRepository,
        theme: TabTheme,
        title: str,
        subtitle: str,
        field_labels: dict[FieldId, str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.prompt_repository = prompt_repository
        self.theme = theme
        self.title = title
        self.subtitle = subtitle
        self.field_labels = field_labels or {}
        self.editors: dict[FieldId, PromptEditor] = {}
        self.setObjectName("pageRoot")
        self.setStyleSheet(build_page_stylesheet(theme))
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        root.addWidget(page_scroll)

        page = QWidget()
        page.setObjectName("pageRoot")
        page_scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(28, 28, 28, 24)
        page_layout.setSpacing(18)

        hero = make_card("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 26, 24)
        hero_layout.setSpacing(8)

        eyebrow = QLabel("Prompt Library")
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel(self.title)
        title.setObjectName("heroTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(self.subtitle)
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)
        page_layout.addWidget(hero)

        controls = make_card("controlCard")
        top = QHBoxLayout(controls)
        top.setContentsMargins(24, 20, 24, 20)
        top.setSpacing(12)

        top.addWidget(self._form_label("Prompt Set Name"))
        self.name_input = QLineEdit()
        self.name_input.setObjectName("controlInput")
        self.name_input.setPlaceholderText("Create or rename this prompt set...")
        top.addWidget(self.name_input, 1)

        top.addWidget(self._form_label("Load Set"))
        self.load_combo = QComboBox()
        self.load_combo.setObjectName("controlInput")
        top.addWidget(self.load_combo)

        refresh_button = self._button("Refresh")
        refresh_button.clicked.connect(self.refresh_prompt_sets)
        top.addWidget(refresh_button)

        load_button = self._button("Load")
        load_button.clicked.connect(
            lambda: self.prompt_set_requested.emit(self.load_combo.currentText())
        )
        top.addWidget(load_button)

        clear_button = self._button("Clear Fields")
        clear_button.clicked.connect(self.clear_fields)
        top.addWidget(clear_button)

        save_button = self._button("Save Prompt Set", primary=True)
        save_button.clicked.connect(self._save_prompt_set)
        top.addWidget(save_button)
        page_layout.addWidget(controls)

        container = QWidget()
        container.setObjectName("pageRoot")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        for field_id in FieldId.ui_order():
            editor = PromptEditor(
                field_id=field_id,
                theme=self.theme,
                field_label=display_label(field_id, self.field_labels),
                helper_text=PROMPT_FIELD_HINTS[field_id],
            )
            self.editors[field_id] = editor
            container_layout.addWidget(editor)

        container_layout.addStretch()
        page_layout.addWidget(container)
        page_layout.addStretch()

    def _button(self, text: str, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("primaryButton" if primary else "")
        return button

    def _form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def refresh_prompt_sets(self) -> None:
        names = self.prompt_repository.list_names()
        current = self.load_combo.currentText()
        self.load_combo.clear()
        self.load_combo.addItems(names)
        if current in names:
            self.load_combo.setCurrentText(current)

    def load_prompt_set(self, prompt_set: PromptSet) -> None:
        self.name_input.setText(prompt_set.name)
        self.load_combo.setCurrentText(prompt_set.name)
        for field_id in FieldId.ui_order():
            template = prompt_set.templates.get(field_id)
            if template:
                self.editors[field_id].set_value(template.text, template.order)
            else:
                self.editors[field_id].set_value("", 0)

    def _save_prompt_set(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Error", "Enter a prompt set name first.")
            return

        prompt_set = PromptSet(name=name)
        try:
            for field_id in FieldId.ui_order():
                template = self.editors[field_id].template()
                if template:
                    prompt_set.templates[field_id] = template
            if not prompt_set.templates:
                raise RuntimeError("Add at least one prompt before saving.")
            if not prompt_set.validate():
                raise RuntimeError("Prompt dependencies are invalid for the chosen order.")
            self.prompt_repository.save(prompt_set)
        except Exception as exc:
            QMessageBox.warning(self, "Save Error", str(exc))
            return

        self.refresh_prompt_sets()
        self.prompt_set_saved.emit(prompt_set)

    def clear_fields(self) -> None:
        self.name_input.clear()
        for editor in self.editors.values():
            editor.set_value("", 0)


class GenerationField(QWidget):
    generate_requested = pyqtSignal(object)
    cascade_requested = pyqtSignal(object)

    def __init__(
        self,
        field_id: FieldId,
        theme: TabTheme,
        field_label: str,
        helper_text: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.field_id = field_id
        self.theme = theme
        self.setObjectName("pageRoot")
        self.setStyleSheet(build_page_stylesheet(theme))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = make_card("fieldCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(12)

        title_column = QVBoxLayout()
        title_column.setSpacing(4)
        title = QLabel(field_label)
        title.setObjectName("fieldTitle")
        title_column.addWidget(title)

        hint = QLabel(helper_text)
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        title_column.addWidget(hint)
        header.addLayout(title_column, 1)

        generate_button = QPushButton("Generate")
        generate_button.setObjectName("ghostButton")
        generate_button.clicked.connect(lambda: self.generate_requested.emit(self.field_id))
        header.addWidget(generate_button)

        cascade_button = QPushButton("Generate From Here")
        cascade_button.setObjectName("primaryButton")
        cascade_button.clicked.connect(lambda: self.cascade_requested.emit(self.field_id))
        header.addWidget(cascade_button)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        input_card = make_card("surfaceCard")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(18, 16, 18, 18)
        input_layout.setSpacing(10)
        input_label = QLabel("Direction")
        input_label.setObjectName("surfaceHeading")
        input_layout.addWidget(input_label)
        self.input_edit = QTextEdit()
        self.input_edit.setObjectName("draftSurface")
        self.input_edit.setPlaceholderText(field_id.input_placeholder)
        self.input_edit.setMinimumHeight(140)
        input_layout.addWidget(self.input_edit)
        splitter.addWidget(input_card)

        output_card = make_card("surfaceCardWide")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(18, 16, 18, 18)
        output_layout.setSpacing(10)
        output_label = QLabel("Output")
        output_label.setObjectName("surfaceHeading")
        output_layout.addWidget(output_label)
        self.output_edit = QTextEdit()
        self.output_edit.setObjectName("resultSurface")
        self.output_edit.setMinimumHeight(200)
        output_layout.addWidget(self.output_edit)
        splitter.addWidget(output_card)

        splitter.setSizes([410, 670])
        layout.addWidget(splitter)
        outer.addWidget(card)

    def input_text(self) -> str:
        return self.input_edit.toPlainText()

    def output_text(self) -> str:
        return self.output_edit.toPlainText()

    def set_output(self, text: str) -> None:
        self.output_edit.setPlainText(text)

    def set_input(self, text: str) -> None:
        self.input_edit.setPlainText(text)


class GenerationTab(QWidget):
    prompt_set_requested = pyqtSignal(str)

    def __init__(
        self,
        prompt_repository: PromptRepository,
        card_repository: CharacterRepository,
        generation_engine: GenerationEngine,
        theme: TabTheme,
        title: str,
        subtitle: str,
        entity_name: str = "Character",
        enable_reference: bool = False,
        reference_repository: CharacterRepository | None = None,
        field_labels: dict[FieldId, str] | None = None,
        paths: AppPaths | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.prompt_repository = prompt_repository
        self.card_repository = card_repository
        self.reference_repository = reference_repository
        self.generation_engine = generation_engine
        self.paths = paths or AppPaths()
        self.theme = theme
        self.title = title
        self.subtitle = subtitle
        self.entity_name = entity_name
        self.enable_reference = enable_reference
        self.field_labels = field_labels or {}
        self.entity_name_lower = entity_name.lower()
        self.current_prompt_set: PromptSet | None = None
        self.current_card = CharacterCard()
        self.loaded_reference_card: CharacterCard | None = None
        self.fields: dict[FieldId, GenerationField] = {}
        self.reference_combo: QComboBox | None = None
        self.reference_text_edit: QTextEdit | None = None
        self.reference_status_label: QLabel | None = None
        self.setObjectName("pageRoot")
        self.setStyleSheet(build_page_stylesheet(theme))
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        root.addWidget(page_scroll)

        page = QWidget()
        page.setObjectName("pageRoot")
        page_scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(28, 28, 28, 24)
        page_layout.setSpacing(18)

        hero = make_card("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 26, 24)
        hero_layout.setSpacing(8)

        eyebrow = QLabel(f"{self.entity_name} Workflow")
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel(self.title)
        title.setObjectName("heroTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(self.subtitle)
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)
        page_layout.addWidget(hero)

        controls_card = make_card("controlCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(24, 20, 24, 20)
        controls_layout.setSpacing(16)

        file_row = QHBoxLayout()
        file_row.setSpacing(12)
        file_row.addWidget(self._form_label("File Name"))
        self.file_name_input = QLineEdit()
        self.file_name_input.setObjectName("controlInput")
        self.file_name_input.setPlaceholderText(f"Save this {self.entity_name_lower} as...")
        file_row.addWidget(self.file_name_input, 1)

        file_row.addWidget(self._form_label(f"Load {self.entity_name}"))
        self.load_combo = QComboBox()
        self.load_combo.setObjectName("controlInput")
        file_row.addWidget(self.load_combo)

        refresh_characters = QPushButton("Refresh")
        refresh_characters.clicked.connect(self.refresh_characters)
        file_row.addWidget(refresh_characters)

        file_row.addWidget(self._form_label("Save as"))
        self.save_format_combo = QComboBox()
        self.save_format_combo.setObjectName("controlInput")
        self.save_format_combo.addItems(SAVE_FORMATS)
        file_row.addWidget(self.save_format_combo)

        save_button = QPushButton(f"Save {self.entity_name}")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_character)
        file_row.addWidget(save_button)
        controls_layout.addLayout(file_row)

        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(12)
        prompt_row.addWidget(self._form_label("Prompt Set"))
        self.prompt_set_combo = QComboBox()
        self.prompt_set_combo.setObjectName("controlInput")
        prompt_row.addWidget(self.prompt_set_combo)

        refresh_prompts = QPushButton("Refresh")
        refresh_prompts.clicked.connect(self.refresh_prompt_sets)
        prompt_row.addWidget(refresh_prompts)

        load_prompt_button = QPushButton("Use Prompt Set")
        load_prompt_button.clicked.connect(
            lambda: self.prompt_set_requested.emit(self.prompt_set_combo.currentText())
        )
        prompt_row.addWidget(load_prompt_button)

        self.direct_name_checkbox = QCheckBox("Use Name Direction As Final Name")
        prompt_row.addWidget(self.direct_name_checkbox)
        prompt_row.addStretch()
        controls_layout.addLayout(prompt_row)
        page_layout.addWidget(controls_card)

        if self.enable_reference:
            page_layout.addWidget(self._build_reference_card())

        action_row = QHBoxLayout()
        generate_all_button = QPushButton("Generate All")
        generate_all_button.setObjectName("primaryButton")
        generate_all_button.clicked.connect(self.generate_all)
        action_row.addWidget(generate_all_button)

        clear_inputs_button = QPushButton("Clear Inputs")
        clear_inputs_button.clicked.connect(self.clear_inputs)
        action_row.addWidget(clear_inputs_button)

        clear_button = QPushButton("Clear Outputs")
        clear_button.clicked.connect(self.clear_outputs)
        action_row.addWidget(clear_button)

        action_row.addStretch()
        self.current_prompt_label = QLabel("No prompt set loaded")
        self.current_prompt_label.setObjectName("statusPill")
        action_row.addWidget(self.current_prompt_label)
        page_layout.addLayout(action_row)

        container = QWidget()
        container.setObjectName("pageRoot")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        for field_id in FieldId.ui_order():
            field_widget = GenerationField(
                field_id=field_id,
                theme=self.theme,
                field_label=display_label(field_id, self.field_labels),
                helper_text=FIELD_HINTS[field_id],
            )
            field_widget.generate_requested.connect(self.generate_single_field)
            field_widget.cascade_requested.connect(self.generate_from_field)
            self.fields[field_id] = field_widget
            container_layout.addWidget(field_widget)

        container_layout.addStretch()
        page_layout.addWidget(container)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusText")
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        page_layout.addWidget(self.status_label)
        page_layout.addStretch()

    def _build_reference_card(self) -> QFrame:
        card = make_card("referenceCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(4)
        title = QLabel("Reference Character")
        title.setObjectName("fieldTitle")
        title_column.addWidget(title)

        helper = QLabel(
            "Load a saved card, open an external card file, or paste context below. This becomes the working {{char}} reference."
        )
        helper.setObjectName("heroSubtitle")
        helper.setWordWrap(True)
        title_column.addWidget(helper)
        header.addLayout(title_column, 1)

        self.reference_status_label = QLabel("No reference loaded")
        self.reference_status_label.setObjectName("statusPill")
        header.addWidget(self.reference_status_label)
        layout.addLayout(header)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(self._form_label("Saved Character"))

        self.reference_combo = QComboBox()
        self.reference_combo.setObjectName("controlInput")
        controls.addWidget(self.reference_combo, 1)

        refresh_references = QPushButton("Refresh")
        refresh_references.clicked.connect(self.refresh_reference_characters)
        controls.addWidget(refresh_references)

        load_reference_button = QPushButton("Load Saved")
        load_reference_button.clicked.connect(
            lambda: self.load_reference_character(
                self.reference_combo.currentText() if self.reference_combo else ""
            )
        )
        controls.addWidget(load_reference_button)

        open_reference_button = QPushButton("Open File...")
        open_reference_button.clicked.connect(self.open_reference_file)
        controls.addWidget(open_reference_button)
        layout.addLayout(controls)

        surface = make_card("surfaceCard")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(18, 16, 18, 18)
        surface_layout.setSpacing(10)

        heading = QLabel("Reference Context")
        heading.setObjectName("surfaceHeading")
        surface_layout.addWidget(heading)

        self.reference_text_edit = QTextEdit()
        self.reference_text_edit.setObjectName("draftSurface")
        self.reference_text_edit.setPlaceholderText(
            "Paste a character card description here, or load a saved character card above."
        )
        self.reference_text_edit.setMinimumHeight(190)
        surface_layout.addWidget(self.reference_text_edit)

        note = QLabel(
            "You can keep the loaded card as-is, paste extra canon, or trim it down to only the details that should shape the persona."
        )
        note.setObjectName("microCopy")
        note.setWordWrap(True)
        surface_layout.addWidget(note)

        layout.addWidget(surface)
        return card

    def _form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def refresh_characters(self) -> None:
        names = self.card_repository.list_names()
        current = self.load_combo.currentText()
        self.load_combo.clear()
        self.load_combo.addItems(names)
        if current in names:
            self.load_combo.setCurrentText(current)

    def refresh_reference_characters(self) -> None:
        if not self.reference_repository or not self.reference_combo:
            return
        names = self.reference_repository.list_names()
        current = self.reference_combo.currentText()
        self.reference_combo.clear()
        self.reference_combo.addItems(names)
        if current in names:
            self.reference_combo.setCurrentText(current)

    def refresh_prompt_sets(self) -> None:
        names = self.prompt_repository.list_names()
        current = self.prompt_set_combo.currentText()
        self.prompt_set_combo.clear()
        self.prompt_set_combo.addItems(names)
        if current in names:
            self.prompt_set_combo.setCurrentText(current)

    def set_available_prompt_sets(self, names: list[str]) -> None:
        current = self.prompt_set_combo.currentText()
        self.prompt_set_combo.clear()
        self.prompt_set_combo.addItems(names)
        if current in names:
            self.prompt_set_combo.setCurrentText(current)

    def set_current_prompt_set(self, prompt_set: PromptSet) -> None:
        self.current_prompt_set = prompt_set
        self.prompt_set_combo.setCurrentText(prompt_set.name)
        self.current_prompt_label.setText(f"Prompt Set: {prompt_set.name}")

    def load_character(self, name: str) -> None:
        if not name:
            return
        try:
            self.current_card = self.card_repository.load(name)
        except Exception as exc:
            QMessageBox.warning(self, "Load Error", str(exc))
            return

        self.file_name_input.setText(self.current_card.name)
        for field_id in FieldId.ui_order():
            self.fields[field_id].set_output(self.current_card.fields.get(field_id, ""))
        self.set_status(f"Loaded {self.entity_name_lower}: {self.current_card.name}")

    def load_reference_character(self, name: str) -> None:
        if not name or not self.reference_repository:
            return
        try:
            reference_card = self.reference_repository.load(name)
        except Exception as exc:
            QMessageBox.warning(self, "Reference Load Error", str(exc))
            return
        self._apply_reference_card(reference_card, name)

    def open_reference_file(self) -> None:
        if not self.reference_repository:
            return

        start_dir = str(self.reference_repository.directory)
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Reference Character",
            start_dir,
            "Character Cards (*.json *.png);;All Files (*)",
        )
        if not selected_path:
            return

        try:
            reference_card = self.reference_repository.load(selected_path)
        except Exception as exc:
            QMessageBox.warning(self, "Reference Load Error", str(exc))
            return
        self._apply_reference_card(reference_card, Path(selected_path).name)

    def _apply_reference_card(self, card: CharacterCard, source_name: str) -> None:
        self.loaded_reference_card = card
        if self.reference_status_label:
            self.reference_status_label.setText(f"Reference: {source_name}")
        if self.reference_text_edit:
            self.reference_text_edit.setPlainText(serialize_reference_card(card))
        self.set_status(f"Loaded reference character: {source_name}")

    def save_character(self) -> None:
        card = self._collect_card()
        if not card.name.strip():
            QMessageBox.warning(
                self,
                "Save Error",
                f"Enter a file name or generate a {self.entity_name_lower} name first.",
            )
            return
        try:
            file_path = self.card_repository.save(card, self.save_format_combo.currentText())
        except Exception as exc:
            QMessageBox.warning(self, "Save Error", str(exc))
            return
        self.current_card = card
        self.refresh_characters()
        self.set_status(f"Saved {self.entity_name_lower} to {file_path.name}")

    def clear_outputs(self) -> None:
        self.current_card = CharacterCard()
        for field_id in FieldId.ui_order():
            self.fields[field_id].set_output("")
        self.set_status("Cleared outputs")

    def clear_inputs(self) -> None:
        self.file_name_input.clear()
        for field_id in FieldId.ui_order():
            self.fields[field_id].set_input("")

        if self.enable_reference:
            self.loaded_reference_card = None
            if self.reference_text_edit:
                self.reference_text_edit.clear()
            if self.reference_status_label:
                self.reference_status_label.setText("No reference loaded")

        self.set_status("Cleared input fields")

    def generate_all(self) -> None:
        if not self.current_prompt_set:
            QMessageBox.warning(self, "Generation Error", "Load a prompt set first.")
            return
        if not self._ensure_reference_ready():
            return
        ordered_fields = self.current_prompt_set.ordered_fields()
        if not ordered_fields:
            QMessageBox.warning(
                self, "Generation Error", "This prompt set has no ordered fields."
            )
            return
        self.generate_from_field(ordered_fields[0])

    def generate_single_field(self, field_id: FieldId) -> None:
        if not self.current_prompt_set:
            QMessageBox.warning(self, "Generation Error", "Load a prompt set first.")
            return
        if not self._ensure_reference_ready():
            return
        inputs = self._collect_inputs()
        outputs = self._collect_outputs()
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            content = self.generation_engine.generate_field(
                prompt_set=self.current_prompt_set,
                field_id=field_id,
                inputs=inputs,
                outputs=outputs,
                direct_name=self.direct_name_checkbox.isChecked(),
                extra_context=self._reference_context(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Generation Error", str(exc))
            self.set_status(f"Error generating {display_label(field_id, self.field_labels).lower()}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.fields[field_id].set_output(content)
        if field_id == FieldId.NAME and not self.file_name_input.text().strip():
            self.file_name_input.setText(content.strip())
        self.set_status(f"Generated {display_label(field_id, self.field_labels).lower()}")

    def generate_from_field(self, field_id: FieldId) -> None:
        if not self.current_prompt_set:
            QMessageBox.warning(self, "Generation Error", "Load a prompt set first.")
            return
        if not self._ensure_reference_ready():
            return
        inputs = self._collect_inputs()
        outputs = self._collect_outputs()
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            generated = self.generation_engine.generate_from(
                prompt_set=self.current_prompt_set,
                start_field=field_id,
                inputs=inputs,
                outputs=outputs,
                direct_name=self.direct_name_checkbox.isChecked(),
                extra_context=self._reference_context(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Generation Error", str(exc))
            self.set_status(
                f"Error generating from {display_label(field_id, self.field_labels).lower()}"
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        for generated_field, content in generated.items():
            self.fields[generated_field].set_output(content)
        if FieldId.NAME in generated and not self.file_name_input.text().strip():
            self.file_name_input.setText(generated[FieldId.NAME].strip())
        self.set_status(
            f"Generated {len(generated)} field(s) from {display_label(field_id, self.field_labels).lower()}"
        )

    def _ensure_reference_ready(self) -> bool:
        if not self.enable_reference:
            return True
        reference_text = (
            self.reference_text_edit.toPlainText().strip() if self.reference_text_edit else ""
        )
        if reference_text or self.loaded_reference_card:
            return True
        QMessageBox.warning(
            self,
            "Reference Required",
            "Load or paste a reference character before generating a persona match.",
        )
        return False

    def _collect_inputs(self) -> dict[FieldId, str]:
        return {field_id: widget.input_text() for field_id, widget in self.fields.items()}

    def _collect_outputs(self) -> dict[FieldId, str]:
        return {field_id: widget.output_text() for field_id, widget in self.fields.items()}

    def _reference_context(self) -> dict[str, str]:
        context = {
            "reference": "",
            "reference_notes": "",
            "char_card": "",
            "intimacy_reference": "",
            "kink_reference": "",
            "romance_reference": load_reference_bundle(
                self.paths.romance_references_dir
            ),
            "seduction_reference": load_reference_bundle(
                self.paths.seduction_references_dir
            ),
            "explicit_dialogue_reference": load_reference_bundle(
                self.paths.explicit_dialogue_references_dir
            ),
            "narrative_pov_reference": load_reference_bundle(
                self.paths.narrative_pov_references_dir
            ),
            "character_psychology_reference": load_reference_bundle(
                self.paths.character_psychology_references_dir
            ),
            "character_romance_craft_reference": load_reference_bundle(
                self.paths.character_romance_craft_references_dir
            ),
            "setting_scaffolds_reference": load_reference_bundle(
                self.paths.setting_scaffolds_references_dir
            ),
            "lorebook_export_reference": load_reference_bundle(
                self.paths.lorebook_export_references_dir
            ),
            "prompt_validation_reference": load_reference_bundle(
                self.paths.prompt_validation_references_dir
            ),
            "specialized_nsfw_reference": load_reference_bundle(
                self.paths.specialized_nsfw_references_dir
            ),
            "worldbuilding_dynamic_lore_reference": load_reference_bundle(
                self.paths.worldbuilding_dynamic_lore_references_dir
            ),
        }

        if self.enable_reference:
            context["intimacy_reference"] = load_reference_bundle(
                self.paths.intimacy_references_dir
            )
            context["kink_reference"] = load_reference_bundle(
                self.paths.kink_references_dir
            )

        reference_text = (
            self.reference_text_edit.toPlainText().strip() if self.reference_text_edit else ""
        )
        if reference_text:
            context["reference"] = reference_text
            context["reference_notes"] = reference_text
            context["char_card"] = reference_text

        if not self.loaded_reference_card:
            for field_id in FieldId.ui_order():
                context[f"char_{field_id.value}"] = ""
            return context

        reference_name = (
            self.loaded_reference_card.fields.get(FieldId.NAME, "").strip()
            or self.loaded_reference_card.name.strip()
        )
        context["char_name"] = reference_name
        for field_id in FieldId.ui_order():
            value = self.loaded_reference_card.fields.get(field_id, "")
            if field_id == FieldId.NAME:
                value = reference_name
            context[f"char_{field_id.value}"] = value
        return context

    def _collect_card(self) -> CharacterCard:
        outputs = self._collect_outputs()
        generated_name = outputs.get(FieldId.NAME, "").strip()
        file_name = self.file_name_input.text().strip() or generated_name
        return CharacterCard(
            name=file_name,
            fields=outputs,
            image_data=self.current_card.image_data,
            alternate_greetings=list(self.current_card.alternate_greetings),
            tags=list(self.current_card.tags),
            creator=self.current_card.creator,
            version=self.current_card.version,
            created_at=self.current_card.created_at,
            modified_at=datetime.now(),
        )

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)


class TropeWorkspaceTab(QWidget):
    def __init__(
        self,
        paths: AppPaths,
        theme: TabTheme,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.theme = theme
        self.validator = CharacterCardValidator()
        self.prompt_mapper = LLMPromptMapper(self.validator)
        self.mode_switcher = TropeModeSwitcher()
        self.png_metadata_engine = PNGMetadataEngine()
        self.last_import_source_path: Path | None = None
        self.current_state = self._default_state()
        self.current_mode = "CHARACTER_CARD_V3"
        self.metric_widgets: dict[str, QWidget] = {}
        self.migration_worker: AsyncMigrationWorker | None = None
        self.repo_parser_worker: RepoAssetParserWorker | None = None
        self.setObjectName("pageRoot")
        self.setStyleSheet(build_page_stylesheet(theme))
        self._build_ui()
        self.sync_weights_interface()

    def _default_state(self) -> dict:
        return {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": str(uuid.uuid4()),
            "name": "",
            "description": "",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "system_prompt": "",
            "creator": "",
            "version": "main",
            "group_tags": ["Trope-Engine"],
            "assets": [],
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Ugly",
                    "current_phase": 1,
                    "weights": {
                        "lie_active": False,
                        "lie_count": 0,
                        "angst_meter": 0,
                        "distance_locked": False,
                    },
                    "origin_context": {
                        "environment_type": "",
                        "incident_summary": "",
                        "spark_token": "",
                        "unbreakable_tether": "",
                    },
                    "dialogue_nodes": {
                        "phase_4_breaking_point": {
                            "activation_condition": "romantic_tension >= 4",
                            "dialogue_payload": "",
                            "action_prompt": "",
                        },
                        "phase_5_hangover_crisis": {
                            "if_player_lied": "",
                            "if_player_honest": "",
                        },
                    },
                }
            },
        }

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        root.addWidget(page_scroll)

        page = QWidget()
        page.setObjectName("pageRoot")
        page_scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(28, 28, 28, 24)
        page_layout.setSpacing(18)

        hero = make_card("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 26, 24)
        hero_layout.setSpacing(8)

        eyebrow = QLabel("Trope Engine")
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("CCV3 Trope Workspace")
        title.setObjectName("heroTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Build Character Card V3 trope-engine wrappers with live relationship weights, archival anchors, and runtime script hooks. Export stays in wrapper form while runtime state continues to live separately."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)
        page_layout.addWidget(hero)

        controls = make_card("controlCard")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(24, 20, 24, 20)
        controls_layout.setSpacing(12)

        import_button = QPushButton("Import Card (.json)")
        import_button.clicked.connect(self.trigger_import)
        controls_layout.addWidget(import_button)

        export_button = QPushButton("Export Compliant V3")
        export_button.setObjectName("primaryButton")
        export_button.clicked.connect(self.trigger_export)
        controls_layout.addWidget(export_button)

        migrate_button = QPushButton("Migrate Folder")
        migrate_button.clicked.connect(self.execute_automated_folder_migration_flow)
        controls_layout.addWidget(migrate_button)

        index_repo_button = QPushButton("Index Repo")
        index_repo_button.clicked.connect(self.execute_repo_asset_indexing_flow)
        controls_layout.addWidget(index_repo_button)

        regenerate_id_button = QPushButton("Regenerate ID")
        regenerate_id_button.clicked.connect(self.regenerate_asset_id)
        controls_layout.addWidget(regenerate_id_button)

        controls_layout.addStretch()
        self.mode_label = QLabel("ASSET MODE: NATIVE CCV3")
        self.mode_label.setObjectName("statusPill")
        controls_layout.addWidget(self.mode_label)
        self.validation_label = QLabel("Waiting for valid trope data")
        self.validation_label.setObjectName("statusPill")
        controls_layout.addWidget(self.validation_label)
        page_layout.addWidget(controls)

        self.migration_progress = QSpinBox()
        self.migration_progress.setObjectName("controlInput")
        self.migration_progress.setRange(0, 100)
        self.migration_progress.setSuffix("%")
        self.migration_progress.setReadOnly(True)
        self.migration_progress.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.migration_progress.setValue(0)
        controls_layout.addWidget(self.migration_progress)

        self.drop_zone = TropeDragDropZone(
            "Drag & Drop Card Asset Here\n(.json data or .png character cards)"
        )
        self.drop_zone.file_dropped_signal.connect(self.process_import_path)
        page_layout.addWidget(self.drop_zone)

        workspace = QHBoxLayout()
        workspace.setSpacing(16)

        column_one = self._build_core_profile_group()
        workspace.addWidget(column_one, 1)

        column_two = self._build_trope_group()
        workspace.addWidget(column_two, 1)

        column_three = self._build_runtime_group()
        workspace.addWidget(column_three, 1)

        page_layout.addLayout(workspace)
        page_layout.addStretch()

    def _build_core_profile_group(self) -> QFrame:
        card = make_card("fieldCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        sprite_heading = QLabel("Character Sprite Preview")
        sprite_heading.setObjectName("surfaceHeading")
        layout.addWidget(sprite_heading)

        self.sprite_manager = TropeSpriteDisplayManager(240, 240, parent=card)
        layout.addWidget(self.sprite_manager, alignment=Qt.AlignmentFlag.AlignHCenter)

        form = QFormLayout()
        form.setSpacing(12)

        self.input_asset_id = QLineEdit()
        self.input_asset_id.setObjectName("controlInput")
        form.addRow(self._form_label("Asset ID"), self.input_asset_id)

        self.input_name = QLineEdit()
        self.input_name.setObjectName("controlInput")
        form.addRow(self._form_label("Character Name"), self.input_name)

        self.input_description = QTextEdit()
        self.input_description.setObjectName("draftSurface")
        self.input_description.setMaximumHeight(120)
        form.addRow(self._form_label("System Description"), self.input_description)

        self.input_personality = QTextEdit()
        self.input_personality.setObjectName("draftSurface")
        self.input_personality.setMaximumHeight(110)
        form.addRow(self._form_label("Personality / Archetype"), self.input_personality)

        self.input_scenario = QTextEdit()
        self.input_scenario.setObjectName("draftSurface")
        self.input_scenario.setMaximumHeight(90)
        form.addRow(self._form_label("Scenario"), self.input_scenario)

        self.input_first_mes = QTextEdit()
        self.input_first_mes.setObjectName("draftSurface")
        self.input_first_mes.setMaximumHeight(110)
        form.addRow(self._form_label("First Message"), self.input_first_mes)

        self.input_mes_example = QTextEdit()
        self.input_mes_example.setObjectName("draftSurface")
        self.input_mes_example.setMaximumHeight(110)
        form.addRow(self._form_label("Message Example / Body Cue"), self.input_mes_example)

        self.input_group_tags = QLineEdit()
        self.input_group_tags.setObjectName("controlInput")
        self.input_group_tags.setPlaceholderText("Trope-Engine, Rivals, Academia")
        form.addRow(self._form_label("Group Tags"), self.input_group_tags)

        layout.addLayout(form)
        return card

    def _build_trope_group(self) -> QFrame:
        card = make_card("fieldCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        selectors_layout = QFormLayout()
        selectors_layout.setSpacing(12)
        self.combo_bucket = QComboBox()
        self.combo_bucket.setObjectName("controlInput")
        for bucket_key in _visible_bucket_keys():
            self.combo_bucket.addItem(_display_bucket_label(bucket_key), bucket_key)
        self.combo_bucket.currentTextChanged.connect(self._handle_bucket_selection)
        selectors_layout.addRow(self._form_label("Engine Bucket"), self.combo_bucket)

        self.combo_subgroup = QComboBox()
        self.combo_subgroup.setObjectName("controlInput")
        self.combo_subgroup.currentTextChanged.connect(
            self._handle_subgroup_selection
        )
        selectors_layout.addRow(self._form_label("Engine Group"), self.combo_subgroup)

        self.combo_engine = QComboBox()
        self.combo_engine.setObjectName("controlInput")
        self.combo_engine.currentTextChanged.connect(self._handle_engine_selection)
        selectors_layout.addRow(self._form_label("Engine Type"), self.combo_engine)

        self.combo_phase = QComboBox()
        self.combo_phase.setObjectName("controlInput")
        self.combo_phase.addItems([f"Phase {index}" for index in range(1, 7)])
        selectors_layout.addRow(self._form_label("Current Phase"), self.combo_phase)
        layout.addLayout(selectors_layout)

        weights_heading = QLabel("Relationship Weights")
        weights_heading.setObjectName("surfaceHeading")
        layout.addWidget(weights_heading)

        self.scroll_weights = QScrollArea()
        self.scroll_weights.setWidgetResizable(True)
        self.weights_container = QWidget()
        self.weights_form = QFormLayout(self.weights_container)
        self.weights_form.setSpacing(12)
        self.scroll_weights.setWidget(self.weights_container)
        layout.addWidget(self.scroll_weights)

        anchors_group = QGroupBox("Archival Memory Anchors")
        anchors_layout = QFormLayout(anchors_group)
        anchors_layout.setSpacing(12)

        self.input_environment = QLineEdit()
        self.input_environment.setObjectName("controlInput")
        anchors_layout.addRow(
            self._form_label("Environment Type"), self.input_environment
        )

        self.input_token = QLineEdit()
        self.input_token.setObjectName("controlInput")
        anchors_layout.addRow(self._form_label("Core Memory Token"), self.input_token)

        self.input_incident = QTextEdit()
        self.input_incident.setObjectName("draftSurface")
        self.input_incident.setMaximumHeight(90)
        anchors_layout.addRow(
            self._form_label("Incident Summary"), self.input_incident
        )

        self.input_tether = QLineEdit()
        self.input_tether.setObjectName("controlInput")
        anchors_layout.addRow(
            self._form_label("Unbreakable Tether"), self.input_tether
        )

        layout.addWidget(anchors_group)
        return card

    def _build_runtime_group(self) -> QFrame:
        card = make_card("fieldCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        scripts_form = QFormLayout()
        scripts_form.setSpacing(12)

        self.input_p4_condition = QLineEdit()
        self.input_p4_condition.setObjectName("controlInput")
        self.input_p4_condition.setReadOnly(True)
        self.input_p4_condition.setToolTip(
            "Catalog-driven. This Phase 4 trigger is derived from the selected engine and is not edited here."
        )
        scripts_form.addRow(
            self._form_label("P4 Activation Condition (Catalog-Driven)"),
            self.input_p4_condition,
        )

        self.input_p4_payload = QTextEdit()
        self.input_p4_payload.setObjectName("draftSurface")
        self.input_p4_payload.setMaximumHeight(90)
        scripts_form.addRow(
            self._form_label("P4 Dialogue Line"), self.input_p4_payload
        )

        self.input_p4_action = QLineEdit()
        self.input_p4_action.setObjectName("controlInput")
        scripts_form.addRow(
            self._form_label("P4 Action Cue"), self.input_p4_action
        )

        self.input_p5_lied = QLineEdit()
        self.input_p5_lied.setObjectName("controlInput")
        scripts_form.addRow(
            self._form_label("P5 If Player Lied"), self.input_p5_lied
        )

        self.input_p5_honest = QLineEdit()
        self.input_p5_honest.setObjectName("controlInput")
        scripts_form.addRow(
            self._form_label("P5 If Player Honest"), self.input_p5_honest
        )
        layout.addLayout(scripts_form)

        json_heading = QLabel("Live Compiled CCV3 JSON")
        json_heading.setObjectName("surfaceHeading")
        layout.addWidget(json_heading)

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setObjectName("resultSurface")
        self.terminal_output.setStyleSheet(
            "font-family: Menlo, 'SF Mono', 'Courier New', monospace; "
            "font-size: 11px; background-color: #1e1e1e; color: #9fe870; border-radius: 18px; padding: 12px;"
        )
        self.terminal_output.setMinimumHeight(220)
        layout.addWidget(self.terminal_output)

        prompt_heading = QLabel("Runtime Prompt Preview")
        prompt_heading.setObjectName("surfaceHeading")
        layout.addWidget(prompt_heading)

        self.prompt_preview = QTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setObjectName("resultSurface")
        self.prompt_preview.setMinimumHeight(220)
        layout.addWidget(self.prompt_preview)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self._bind_input_change_listeners()
        self._populate_bucket_browser("Meet-Ugly")
        return card

    def _form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def _bind_input_change_listeners(self) -> None:
        line_edits = [
            self.input_asset_id,
            self.input_name,
            self.input_group_tags,
            self.input_environment,
            self.input_token,
            self.input_tether,
            self.input_p4_action,
            self.input_p5_lied,
            self.input_p5_honest,
        ]
        for widget in line_edits:
            widget.textChanged.connect(self.compile_ui_to_json)

        text_edits = [
            self.input_description,
            self.input_personality,
            self.input_scenario,
            self.input_first_mes,
            self.input_mes_example,
            self.input_incident,
            self.input_p4_payload,
        ]
        for widget in text_edits:
            widget.textChanged.connect(self.compile_ui_to_json)

        self.combo_phase.currentIndexChanged.connect(self.compile_ui_to_json)

    def _populate_bucket_browser(self, target_engine: str | None = None) -> None:
        engine_type = _canonical_visible_engine(
            target_engine or _combo_data(self.combo_engine) or "Meet-Ugly"
        )
        bucket_match = bucket_for_engine(engine_type)
        fallback_bucket = _combo_data(self.combo_bucket) or _visible_bucket_keys()[0]
        bucket_key = bucket_match[0] if bucket_match else fallback_bucket
        subgroup_name = (
            bucket_match[1]
            if bucket_match
            else (_visible_subgroup_names(bucket_key)[0] if _visible_subgroup_names(bucket_key) else "")
        )

        blockers = [
            QSignalBlocker(self.combo_bucket),
            QSignalBlocker(self.combo_subgroup),
            QSignalBlocker(self.combo_engine),
        ]

        bucket_index = _find_combo_data(self.combo_bucket, bucket_key)
        if bucket_index >= 0:
            self.combo_bucket.setCurrentIndex(bucket_index)

        self.combo_subgroup.clear()
        for subgroup in _visible_subgroup_names(bucket_key):
            self.combo_subgroup.addItem(subgroup, subgroup)
        subgroup_index = _find_combo_data(self.combo_subgroup, subgroup_name)
        if subgroup_index < 0 and self.combo_subgroup.count():
            subgroup_index = 0
        if subgroup_index >= 0:
            self.combo_subgroup.setCurrentIndex(subgroup_index)

        active_subgroup = _combo_data(self.combo_subgroup)
        self.combo_engine.clear()
        engine_names = _visible_engine_names(bucket_key, active_subgroup)
        if (
            engine_type
            and engine_type not in engine_names
            and engine_type in ENGINE_OPTION_ORDER
            and engine_type not in SUPERSEDED_SAFE_EQUIVALENTS
        ):
            engine_names = [engine_type, *engine_names]
        for engine_name in engine_names:
            self.combo_engine.addItem(engine_name, engine_name)
        engine_index = _find_combo_data(self.combo_engine, engine_type)
        if engine_index < 0 and self.combo_engine.count():
            engine_index = 0
        if engine_index >= 0:
            self.combo_engine.setCurrentIndex(engine_index)

        del blockers

    def _handle_bucket_selection(self) -> None:
        bucket_key = _combo_data(self.combo_bucket)
        subgroups = _visible_subgroup_names(bucket_key)
        target_subgroup = subgroups[0] if subgroups else ""
        target_engine = (
            _visible_engine_names(bucket_key, target_subgroup)[0]
            if target_subgroup and _visible_engine_names(bucket_key, target_subgroup)
            else None
        )
        self._populate_bucket_browser(target_engine)
        self.sync_weights_interface()

    def _handle_subgroup_selection(self) -> None:
        bucket_key = _combo_data(self.combo_bucket)
        subgroup_name = _combo_data(self.combo_subgroup)
        engines = _visible_engine_names(bucket_key, subgroup_name)
        target_engine = engines[0] if engines else None
        self._populate_bucket_browser(target_engine)
        self.sync_weights_interface()

    def _handle_engine_selection(self) -> None:
        self.sync_weights_interface()

    def set_selected_engine(self, engine_type: str) -> None:
        self._populate_bucket_browser(_canonical_visible_engine(engine_type))
        self.sync_weights_interface()

    def _engine_weight_keys(self, engine_type: str) -> list[str]:
        return engine_weight_keys(engine_type)

    def sync_weights_interface(self) -> None:
        while self.weights_form.count():
            child = self.weights_form.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.metric_widgets.clear()
        engine_type = _combo_data(self.combo_engine)
        weights = self.current_state["extensions"]["trope_engine"]["weights"]

        for key in self._engine_weight_keys(engine_type):
            if key in ENGINE_BOOLEAN_WEIGHT_KEYS:
                checkbox = QCheckBox()
                checkbox.setChecked(bool(weights.get(key, False)))
                checkbox.stateChanged.connect(self.compile_ui_to_json)
                self.weights_form.addRow(
                    self._form_label(key.replace("_", " ").title()), checkbox
                )
                self.metric_widgets[key] = checkbox
                continue

            if key == "lie_count":
                line_edit = QLineEdit(str(weights.get(key, 0)))
                line_edit.setObjectName("controlInput")
                line_edit.setMaximumWidth(72)
                line_edit.textChanged.connect(self.compile_ui_to_json)
                self.weights_form.addRow(self._form_label("Total Lie Count"), line_edit)
                self.metric_widgets[key] = line_edit
                continue

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 5)
            slider.setValue(int(weights.get(key, 0)))
            value_label = QLabel(f"{slider.value()}/5")
            value_label.setObjectName("microCopy")
            slider.valueChanged.connect(
                lambda value, label=value_label: label.setText(f"{value}/5")
            )
            slider.valueChanged.connect(self.compile_ui_to_json)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(value_label)
            self.weights_form.addRow(
                self._form_label(key.replace("_", " ").title()), row_widget
            )
            self.metric_widgets[key] = slider

        self.compile_ui_to_json()

    def compile_ui_to_json(self) -> None:
        state = self.current_state
        state["id"] = self.input_asset_id.text().strip() or state.get("id") or str(
            uuid.uuid4()
        )
        state["name"] = self.input_name.text().strip()
        state["description"] = self.input_description.toPlainText().strip()
        state["personality"] = self.input_personality.toPlainText().strip()
        state["scenario"] = self.input_scenario.toPlainText().strip()
        state["first_mes"] = self.input_first_mes.toPlainText().strip()
        state["mes_example"] = self.input_mes_example.toPlainText().strip()
        state["group_tags"] = self._parse_group_tags(self.input_group_tags.text())

        trope_engine = state["extensions"]["trope_engine"]
        trope_engine["engine_type"] = _combo_data(self.combo_engine)
        trope_engine["current_phase"] = self.combo_phase.currentIndex() + 1
        trope_engine["origin_context"]["environment_type"] = (
            self.input_environment.text().strip()
        )
        trope_engine["origin_context"]["spark_token"] = self.input_token.text().strip()
        trope_engine["origin_context"]["incident_summary"] = (
            self.input_incident.toPlainText().strip()
        )
        trope_engine["origin_context"]["unbreakable_tether"] = (
            self.input_tether.text().strip()
        )

        catalog_trigger = phase_four_activation_condition(trope_engine["engine_type"])
        if self.input_p4_condition.text() != catalog_trigger:
            blocker = QSignalBlocker(self.input_p4_condition)
            self.input_p4_condition.setText(catalog_trigger)
            del blocker

        phase_4 = trope_engine["dialogue_nodes"]["phase_4_breaking_point"]
        phase_4["activation_condition"] = catalog_trigger
        phase_4["dialogue_payload"] = self.input_p4_payload.toPlainText().strip()
        phase_4["action_prompt"] = self.input_p4_action.text().strip()

        phase_5 = trope_engine["dialogue_nodes"]["phase_5_hangover_crisis"]
        phase_5["if_player_lied"] = self.input_p5_lied.text().strip()
        phase_5["if_player_honest"] = self.input_p5_honest.text().strip()

        weights = trope_engine["weights"]
        for key, widget in self.metric_widgets.items():
            if isinstance(widget, QCheckBox):
                weights[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                try:
                    weights[key] = max(0, int(widget.text() or 0))
                except ValueError:
                    weights[key] = 0
            elif isinstance(widget, QSlider):
                weights[key] = widget.value()

        self.input_asset_id.setText(state["id"])
        self.terminal_output.setPlainText(
            json.dumps(state, indent=2, ensure_ascii=False)
        )
        self._refresh_runtime_preview()

    def _refresh_runtime_preview(self) -> None:
        try:
            prompt = self.prompt_mapper.compile_system_prompt(self.current_state)
        except Exception as exc:
            self.validation_label.setText("Needs validation")
            self.prompt_preview.setPlainText(f"[VALIDATION WARNING]\n{exc}")
            self.status_label.setText(
                "The wrapper is editable, but it does not yet compile into a valid runtime prompt."
            )
            return

        self.validation_label.setText("Runtime prompt valid")
        self.prompt_preview.setPlainText(prompt)
        self.status_label.setText(
            "This trope card validates cleanly and can feed the runtime prompt pipeline."
        )

    def regenerate_asset_id(self) -> None:
        self.input_asset_id.setText(str(uuid.uuid4()))
        self.compile_ui_to_json()

    def trigger_import(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Trope Card",
            str(self.paths.characters_dir),
            "Character Cards (*.json *.png);;JSON Files (*.json);;PNG Files (*.png);;All Files (*)",
        )
        if not selected_path:
            return

        self.process_import_path(selected_path)

    def process_import_path(self, selected_path: str) -> None:
        try:
            path = Path(selected_path)
            if path.suffix.lower() == ".png":
                parsed = self.png_metadata_engine.extract_card_data(path.read_bytes())
            elif path.suffix.lower() == ".json":
                with open(selected_path, "r", encoding="utf-8") as handle:
                    parsed = json.load(handle)
            else:
                raise ValueError("Unsupported file type. Import expects a .json or .png card.")
            self.execute_polymorphic_import(parsed, source_path=path)
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", str(exc))
            return

        self.status_label.setText(
            f"Imported trope workspace card from {Path(selected_path).name}"
        )

    def execute_polymorphic_import(
        self, raw_json_payload: dict, source_path: Path | None = None
    ) -> None:
        detected_type, normalized_payload = self.mode_switcher.identify_and_normalize_payload(
            raw_json_payload
        )
        if detected_type == "ENGINE_STATE_CARD":
            export_state = deepcopy(normalized_payload)
        else:
            export_state = self._normalized_export_state(normalized_payload)
        self.last_import_source_path = source_path
        self.current_mode = detected_type
        self.current_state = export_state
        self._apply_mode_presentation(detected_type)
        self.hydrate_ui_fields()
        self._refresh_sprite_preview(source_path)

    def _apply_mode_presentation(self, detected_type: str) -> None:
        self._set_core_profile_locked(detected_type == "ENGINE_STATE_CARD")
        if detected_type == "CHARACTER_CARD_V2":
            self.mode_label.setText("ASSET MODE: V2 UPGRADE")
            self.status_label.setText(
                "Mode switch: Character Card V2 detected and auto-upgraded into the CCV3 workspace."
            )
        elif detected_type == "CHARACTER_CARD_V3":
            self.mode_label.setText("ASSET MODE: NATIVE CCV3")
            self.status_label.setText(
                "Mode switch: Native CCV3 card loaded cleanly."
            )
        elif detected_type == "ENGINE_STATE_CARD":
            self.mode_label.setText("LIVE SESSION STATE ACTIVE")
            self.status_label.setText(
                "Mode switch: Runtime session snapshot loaded. Core asset fields are locked so you can inspect live weights without mutating the source profile."
            )

    def _set_core_profile_locked(self, locked: bool) -> None:
        self.input_asset_id.setReadOnly(locked)
        self.input_name.setReadOnly(locked)
        self.input_description.setReadOnly(locked)
        self.input_personality.setReadOnly(locked)
        self.input_scenario.setReadOnly(locked)
        self.input_first_mes.setReadOnly(locked)
        self.input_mes_example.setReadOnly(locked)
        self.input_group_tags.setReadOnly(locked)

    def hydrate_ui_fields(self) -> None:
        state = deepcopy(self.current_state)
        trope_engine = state.get("extensions", {}).get("trope_engine", {})

        blockers = [
            QSignalBlocker(self.input_asset_id),
            QSignalBlocker(self.input_name),
            QSignalBlocker(self.input_description),
            QSignalBlocker(self.input_personality),
            QSignalBlocker(self.input_scenario),
            QSignalBlocker(self.input_first_mes),
            QSignalBlocker(self.input_mes_example),
            QSignalBlocker(self.input_group_tags),
            QSignalBlocker(self.combo_bucket),
            QSignalBlocker(self.combo_subgroup),
            QSignalBlocker(self.combo_engine),
            QSignalBlocker(self.combo_phase),
            QSignalBlocker(self.input_environment),
            QSignalBlocker(self.input_token),
            QSignalBlocker(self.input_incident),
            QSignalBlocker(self.input_tether),
            QSignalBlocker(self.input_p4_condition),
            QSignalBlocker(self.input_p4_payload),
            QSignalBlocker(self.input_p4_action),
            QSignalBlocker(self.input_p5_lied),
            QSignalBlocker(self.input_p5_honest),
        ]

        self.input_asset_id.setText(str(state.get("id", "")))
        self.input_name.setText(state.get("name", ""))
        self.input_description.setPlainText(state.get("description", ""))
        self.input_personality.setPlainText(state.get("personality", ""))
        self.input_scenario.setPlainText(state.get("scenario", ""))
        self.input_first_mes.setPlainText(state.get("first_mes", ""))
        self.input_mes_example.setPlainText(state.get("mes_example", ""))
        self.input_group_tags.setText(", ".join(state.get("group_tags", [])))

        self._populate_bucket_browser(trope_engine.get("engine_type", "Meet-Ugly"))

        phase = int(trope_engine.get("current_phase", 1))
        self.combo_phase.setCurrentIndex(max(0, min(5, phase - 1)))

        origin = trope_engine.get("origin_context", {})
        self.input_environment.setText(origin.get("environment_type", ""))
        self.input_token.setText(origin.get("spark_token", ""))
        self.input_incident.setPlainText(origin.get("incident_summary", ""))
        self.input_tether.setText(origin.get("unbreakable_tether", ""))

        phase_4 = trope_engine.get("dialogue_nodes", {}).get(
            "phase_4_breaking_point", {}
        )
        self.input_p4_condition.setText(phase_4.get("activation_condition", ""))
        self.input_p4_payload.setPlainText(phase_4.get("dialogue_payload", ""))
        self.input_p4_action.setText(phase_4.get("action_prompt", ""))

        phase_5 = trope_engine.get("dialogue_nodes", {}).get(
            "phase_5_hangover_crisis", {}
        )
        self.input_p5_lied.setText(phase_5.get("if_player_lied", ""))
        self.input_p5_honest.setText(phase_5.get("if_player_honest", ""))

        del blockers
        self.sync_weights_interface()

    def _refresh_sprite_preview(self, source_path: Path | None = None) -> None:
        preview_source = source_path or self.last_import_source_path
        if preview_source is None:
            self.sprite_manager.load_sprite_from_card_payload(self.current_state)
            return
        self.sprite_manager.load_sprite_from_card_payload(
            self.current_state,
            preview_source,
        )

    def trigger_export(self) -> None:
        try:
            export_state = self._normalized_export_state()
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", str(exc))
            return

        suggested_name = export_state.get("name", "").strip() or "unnamed_trope_card"
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Compliant V3 Card",
            str(self.paths.characters_dir / f"{suggested_name}_ccv3_card.json"),
            "JSON Files (*.json)",
        )
        if not selected_path:
            return

        with open(selected_path, "w", encoding="utf-8") as handle:
            json.dump(export_state, handle, indent=2, ensure_ascii=False)

        self.current_state = export_state
        self.hydrate_ui_fields()
        self.status_label.setText(f"Exported trope workspace card to {Path(selected_path).name}")

    def execute_automated_folder_migration_flow(self) -> None:
        if self.repo_parser_worker and self.repo_parser_worker.isRunning():
            self.repo_parser_worker.is_cancelled = True
            self.status_label.setText("Repo inventory scan cancellation requested.")
            return
        if self.migration_worker and self.migration_worker.isRunning():
            self.migration_worker.is_cancelled = True
            self.status_label.setText("Database migration cancellation requested.")
            return

        selected_source_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Legacy Character Cards Folder Database Source",
            str(self.paths.characters_dir),
        )
        if not selected_source_directory:
            return

        selected_output_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Cleansed CCV3 Production Folder Target Location",
            selected_source_directory,
        )
        if not selected_output_directory:
            return

        self.terminal_output.clear()
        self.migration_progress.setValue(0)
        self.migration_worker = AsyncMigrationWorker(
            selected_source_directory,
            selected_output_directory,
            create_backups=True,
            parent=self,
        )
        self.migration_worker.progress_tick.connect(self.migration_progress.setValue)
        self.migration_worker.log_output.connect(self.terminal_output.append)
        self.migration_worker.task_complete.connect(
            self.handle_migration_task_finalization
        )
        self.migration_worker.start()
        self.status_label.setText(
            "Database migration loop engaged. Processing file streams asynchronously."
        )

    def execute_repo_asset_indexing_flow(self) -> None:
        if self.migration_worker and self.migration_worker.isRunning():
            self.migration_worker.is_cancelled = True
            self.status_label.setText("Database migration cancellation requested.")
            return
        if self.repo_parser_worker and self.repo_parser_worker.isRunning():
            self.repo_parser_worker.is_cancelled = True
            self.status_label.setText("Repo inventory scan cancellation requested.")
            return

        selected_source_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Root App Repository Source Folder",
            str(self.paths.root),
        )
        if not selected_source_directory:
            return

        selected_output_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Compilation Ledger Save Directory Location",
            selected_source_directory,
        )
        if not selected_output_directory:
            return

        self.terminal_output.clear()
        self.migration_progress.setValue(0)
        self.repo_parser_worker = RepoAssetParserWorker(
            selected_source_directory,
            selected_output_directory,
            parent=self,
        )
        self.repo_parser_worker.progress_update.connect(self.migration_progress.setValue)
        self.repo_parser_worker.log_stream.connect(self.terminal_output.append)
        self.repo_parser_worker.parsing_complete.connect(
            self.handle_repo_asset_indexing_finalization
        )
        self.repo_parser_worker.start()
        self.status_label.setText(
            "Repo-wide asset scan engaged. Parsing repository contents asynchronously."
        )

    def handle_migration_task_finalization(self, report: dict) -> None:
        status = report.get("status", "COMPLETED")
        if status == "COMPLETED":
            self.migration_progress.setValue(100)
            self.terminal_output.append(
                "\n[DATABASE MIGRATION PROCESS FINALIZED SUCCESS]\n"
                f"- Total File Objects Scanned: {report['total_files_scanned']}\n"
                f"- Successful CCV3 Conversions Executed: {report['successful_upgrades']}\n"
                f"- Malformed Files Skipped / Failed: {report['failed_parses']}\n"
                f"- Structural Lore Knowledge Chunks Compiled: {report['lore_nodes_compiled']}\n"
                "Backup data images (.bak) generated inside source directories."
            )
            self.status_label.setText(
                "Database batch migration operations completed successfully."
            )
        elif status == "CANCELLED":
            self.status_label.setText("Database migration was cancelled.")
        elif status == "EMPTY":
            self.status_label.setText("No valid character or worldbook files were discovered.")
        else:
            self.status_label.setText("Database migration finished with failures.")

    def handle_repo_asset_indexing_finalization(self, report: dict) -> None:
        status = report.get("status", "SUCCESS")
        if status == "SUCCESS":
            self.migration_progress.setValue(100)
            self.terminal_output.append(
                "\n[REPO ASSET INVENTORY LEDGER GENERATED SUCCESSFULLY]\n"
                f"- Inventory Ledger Document Written To: {report['ledger_path']}\n"
                f"- Native Flat Spec CCV3 Profiles Discovered: {report['v3_count']}\n"
                f"- Legacy Spec V2 Cards Segmented: {report['v2_count']}\n"
                f"- Legacy Spec V1 Profile Elements Catalogued: {report['v1_count']}\n"
                f"- Structured Worldbook Databases Located: {report['wb_count']}\n"
                f"- Unmapped / Corrupted Files Isolated: {report['fail_count']} assets."
            )
            self.status_label.setText("Repo-wide asset inventory completed successfully.")
        elif status == "CANCELLED":
            self.status_label.setText("Repo-wide asset inventory was cancelled.")
        elif status == "EMPTY":
            self.status_label.setText("Target folder contains zero valid card assets.")
        else:
            self.status_label.setText("Repo-wide asset inventory finished with failures.")

    def _normalized_export_state(self, payload: dict | None = None) -> dict:
        working = deepcopy(payload or self.current_state)
        canonical = extract_trope_engine_card(working)
        result = self.validator.validate_card_json(canonical)
        if not result.success:
            raise RuntimeError("; ".join(result.errors))

        normalized = result.normalized_card or {}
        wrapped = wrap_trope_engine_card_as_v3(normalized)
        wrapped["id"] = str(working.get("id") or wrapped.get("id") or uuid.uuid4())
        wrapped["name"] = working.get("name", wrapped.get("name", ""))
        wrapped["description"] = working.get(
            "description", wrapped.get("description", "")
        )
        wrapped["personality"] = working.get(
            "personality", wrapped.get("personality", "")
        )
        wrapped["scenario"] = working.get("scenario", wrapped.get("scenario", ""))
        wrapped["first_mes"] = working.get("first_mes", wrapped.get("first_mes", ""))
        wrapped["mes_example"] = working.get(
            "mes_example", wrapped.get("mes_example", "")
        )
        wrapped["system_prompt"] = working.get(
            "system_prompt", wrapped.get("system_prompt", "")
        )
        wrapped["creator"] = working.get("creator", wrapped.get("creator", ""))
        wrapped["version"] = working.get("version", wrapped.get("version", "main"))
        wrapped["assets"] = list(working.get("assets", wrapped.get("assets", [])))
        wrapped["group_tags"] = self._parse_group_tags(
            ", ".join(working.get("group_tags", []))
            if isinstance(working.get("group_tags"), list)
            else str(working.get("group_tags", ""))
        )
        return wrapped

    def _parse_group_tags(self, raw_text: str) -> list[str]:
        tags = [tag.strip() for tag in raw_text.split(",") if tag.strip()]
        return tags or ["Trope-Engine"]


class SessionStateWorkspaceTab(QWidget):
    def __init__(
        self,
        paths: AppPaths,
        storage_controller: TropeStorageController,
        theme: TabTheme,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.storage_controller = storage_controller
        self.io_controller = StateIOController(storage_controller, paths)
        self.theme = theme
        self.png_metadata_engine = PNGMetadataEngine()
        self.state_card = EngineStateCard(
            card_id="vance_v3_template", engine_type="Meet-Ugly"
        )
        self.slider_widgets: dict[str, QWidget] = {}
        self.current_session_path: Path | None = None
        self.sync_hook = TelemetrySyncHook(check_interval_seconds=1.0)
        self.sync_hook.state_mutated_signal.connect(self.handle_external_telemetry_reload)
        self.sync_hook.access_error_signal.connect(self.handle_telemetry_error)
        self.cache_sync_worker: CacheSyncManagerWorker | None = None
        self.telemetry_system = self._initialize_telemetry_system()
        self.setObjectName("pageRoot")
        self.setStyleSheet(build_page_stylesheet(theme))
        self._build_ui()
        self.cache_sync_worker = self._initialize_cache_sync_manager()
        self.rebuild_dynamic_slider_grid()
        self.refresh_session_list()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        root.addWidget(page_scroll)

        page = QWidget()
        page.setObjectName("pageRoot")
        page_scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(28, 28, 28, 24)
        page_layout.setSpacing(18)

        hero = make_card("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 26, 24)
        hero_layout.setSpacing(8)

        eyebrow = QLabel("Runtime Sessions")
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Engine State Editor")
        title.setObjectName("heroTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Inspect and override live `EngineStateCard` saves without touching the immutable source card. This workspace is for volatile metrics, phase state, chat history, and hot-reload telemetry."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)
        page_layout.addWidget(hero)

        controls = make_card("controlCard")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(24, 20, 24, 20)
        controls_layout.setSpacing(12)

        controls_layout.addWidget(self._form_label("Saved Session"))
        self.session_combo = QComboBox()
        self.session_combo.setObjectName("controlInput")
        controls_layout.addWidget(self.session_combo, 1)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_session_list)
        controls_layout.addWidget(refresh_button)

        load_button = QPushButton("Load Saved")
        load_button.clicked.connect(self.load_selected_session)
        controls_layout.addWidget(load_button)

        open_button = QPushButton("Open File...")
        open_button.clicked.connect(self.load_state_from_disk)
        controls_layout.addWidget(open_button)

        new_button = QPushButton("New Session")
        new_button.clicked.connect(self.reset_session)
        controls_layout.addWidget(new_button)

        save_button = QPushButton("Force Save")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_state_to_disk)
        controls_layout.addWidget(save_button)

        exposure_button = QPushButton("Exposure -> Secret")
        exposure_button.clicked.connect(
            lambda: self.trigger_external_catalyst_plot_twist_flow(
                "Secret-Relationship"
            )
        )
        controls_layout.addWidget(exposure_button)

        cold_feet_button = QPushButton("Cold Feet -> Runaway")
        cold_feet_button.clicked.connect(
            lambda: self.trigger_external_catalyst_plot_twist_flow(
                "Runaway-Fiance"
            )
        )
        controls_layout.addWidget(cold_feet_button)

        controls_layout.addStretch()
        self.sync_status_label = QLabel("Telemetry idle")
        self.sync_status_label.setObjectName("statusPill")
        controls_layout.addWidget(self.sync_status_label)
        page_layout.addWidget(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        metadata_card = make_card("fieldCard")
        metadata_layout = QVBoxLayout(metadata_card)
        metadata_layout.setContentsMargins(24, 20, 24, 24)
        metadata_layout.setSpacing(14)

        sprite_heading = QLabel("Linked Character Sprite")
        sprite_heading.setObjectName("surfaceHeading")
        metadata_layout.addWidget(sprite_heading)

        self.sprite_manager = TropeSpriteDisplayManager(220, 220, parent=metadata_card)
        metadata_layout.addWidget(
            self.sprite_manager, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        metadata_form = QFormLayout()
        metadata_form.setSpacing(12)

        self.label_session_id = QLabel("")
        self.label_session_id.setObjectName("statusPill")
        metadata_form.addRow(self._form_label("Session"), self.label_session_id)

        self.input_card_id = QLineEdit()
        self.input_card_id.setObjectName("controlInput")
        metadata_form.addRow(self._form_label("Linked Card Asset ID"), self.input_card_id)

        self.combo_bucket = QComboBox()
        self.combo_bucket.setObjectName("controlInput")
        for bucket_key in _visible_bucket_keys():
            self.combo_bucket.addItem(_display_bucket_label(bucket_key), bucket_key)
        self.combo_bucket.currentTextChanged.connect(self._handle_bucket_selection)
        metadata_form.addRow(self._form_label("Engine Bucket"), self.combo_bucket)

        self.combo_subgroup = QComboBox()
        self.combo_subgroup.setObjectName("controlInput")
        self.combo_subgroup.currentTextChanged.connect(
            self._handle_subgroup_selection
        )
        metadata_form.addRow(self._form_label("Engine Group"), self.combo_subgroup)

        self.combo_engine = QComboBox()
        self.combo_engine.setObjectName("controlInput")
        self.combo_engine.currentTextChanged.connect(self.handle_engine_mutation)
        metadata_form.addRow(self._form_label("Active Trope Engine"), self.combo_engine)

        self.combo_phase = QComboBox()
        self.combo_phase.setObjectName("controlInput")
        self.combo_phase.addItems([f"Phase {i}: Active Node" for i in range(1, 7)])
        self.combo_phase.currentIndexChanged.connect(self.sync_ui_to_model_state)
        metadata_form.addRow(self._form_label("Current Story Phase"), self.combo_phase)
        metadata_layout.addLayout(metadata_form)
        left_layout.addWidget(metadata_card)

        weights_card = make_card("fieldCard")
        weights_layout = QVBoxLayout(weights_card)
        weights_layout.setContentsMargins(24, 20, 24, 24)
        weights_layout.setSpacing(12)
        weights_heading = QLabel("Active Variable Sliders Hub")
        weights_heading.setObjectName("surfaceHeading")
        weights_layout.addWidget(weights_heading)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.sliders_widget_container = QWidget()
        self.sliders_form_layout = QFormLayout(self.sliders_widget_container)
        self.sliders_form_layout.setSpacing(12)
        self.scroll_area.setWidget(self.sliders_widget_container)
        weights_layout.addWidget(self.scroll_area)
        left_layout.addWidget(weights_card, 1)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        chat_card = make_card("fieldCard")
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(24, 20, 24, 24)
        chat_layout.setSpacing(12)
        chat_heading = QLabel("Active Conversation Backlog")
        chat_heading.setObjectName("surfaceHeading")
        chat_layout.addWidget(chat_heading)

        self.chat_viewport = QTextEdit()
        self.chat_viewport.setReadOnly(True)
        self.chat_viewport.setObjectName("resultSurface")
        self.chat_viewport.setStyleSheet(
            "background-color: #0f172a; color: #e2e8f0; font-size: 12px; border-radius: 18px; padding: 12px;"
        )
        self.chat_viewport.setMinimumHeight(220)
        chat_layout.addWidget(self.chat_viewport)

        injection_row = QHBoxLayout()
        self.inject_role_combo = QComboBox()
        self.inject_role_combo.setObjectName("controlInput")
        self.inject_role_combo.addItems(["user", "character"])
        injection_row.addWidget(self.inject_role_combo)

        self.input_inject_msg = QLineEdit()
        self.input_inject_msg.setObjectName("controlInput")
        self.input_inject_msg.setPlaceholderText(
            "Simulate a data turn message entry injection..."
        )
        injection_row.addWidget(self.input_inject_msg, 1)

        inject_button = QPushButton("Inject Turn")
        inject_button.clicked.connect(self.execute_mock_message_injection)
        injection_row.addWidget(inject_button)
        chat_layout.addLayout(injection_row)
        right_layout.addWidget(chat_card, 2)

        json_card = make_card("fieldCard")
        json_layout = QVBoxLayout(json_card)
        json_layout.setContentsMargins(24, 20, 24, 24)
        json_layout.setSpacing(12)
        json_heading = QLabel("JSON Live Serialization Cache")
        json_heading.setObjectName("surfaceHeading")
        json_layout.addWidget(json_heading)

        self.json_terminal = QTextEdit()
        self.json_terminal.setReadOnly(True)
        self.json_terminal.setObjectName("resultSurface")
        self.json_terminal.setStyleSheet(
            "font-family: Menlo, 'SF Mono', 'Courier New', monospace; "
            "font-size: 11px; background-color: #1a1a1a; color: #38bdf8; border-radius: 18px; padding: 12px;"
        )
        self.json_terminal.setMinimumHeight(260)
        json_layout.addWidget(self.json_terminal)

        directive_heading = QLabel("Catalyst Directive Override")
        directive_heading.setObjectName("surfaceHeading")
        json_layout.addWidget(directive_heading)

        self.directive_terminal = QTextEdit()
        self.directive_terminal.setReadOnly(True)
        self.directive_terminal.setObjectName("resultSurface")
        self.directive_terminal.setStyleSheet(
            "font-family: Menlo, 'SF Mono', 'Courier New', monospace; "
            "font-size: 11px; background-color: #111827; color: #f8fafc; border-radius: 18px; padding: 12px;"
        )
        self.directive_terminal.setMinimumHeight(140)
        json_layout.addWidget(self.directive_terminal)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)
        json_layout.addWidget(self.status_label)
        right_layout.addWidget(json_card, 3)
        splitter.addWidget(right_panel)

        splitter.setSizes([540, 740])
        page_layout.addWidget(splitter, 1)

        self._bind_input_change_listeners()
        self._populate_bucket_browser(self.state_card.engine_type)
        self.hydrate_ui_from_save_state()

    def _form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def _bind_input_change_listeners(self) -> None:
        self.input_card_id.textChanged.connect(self.sync_ui_to_model_state)
        self.input_card_id.textChanged.connect(self.refresh_sprite_preview_from_linked_card)

    def _initialize_telemetry_system(self) -> TropeTelemetrySystem:
        telemetry_system = TropeTelemetrySystem(
            websocket_server_url=os.environ.get("CHARACTERGEN_TELEMETRY_WS_URL"),
        )
        telemetry_system.start_background_dispatcher()
        return telemetry_system

    def _initialize_cache_sync_manager(self) -> CacheSyncManagerWorker | None:
        backend_api_url = os.environ.get("CHARACTERGEN_SYNC_API_URL", "").strip()
        if not backend_api_url:
            return None

        try:
            worker = CacheSyncManagerWorker(
                backend_api_url=backend_api_url,
                sync_interval_seconds=3.0,
                parent=self,
            )
        except ModuleNotFoundError as exc:
            self.status_label.setText(str(exc))
            return None
        worker.sync_success_signal.connect(
            self.handle_asynchronous_cache_hydration_patch
        )
        worker.network_fault_signal.connect(self.handle_cache_sync_fault)
        worker.start_sync_daemon()
        self.status_label.setText(
            "Network cache synchronization manager hook successfully engaged."
        )
        return worker

    def _engine_weight_keys(self, engine_type: str) -> list[str]:
        return engine_weight_keys(engine_type)

    def _populate_bucket_browser(self, target_engine: str | None = None) -> None:
        engine_type = _canonical_visible_engine(
            target_engine or _combo_data(self.combo_engine) or "Meet-Ugly"
        )
        bucket_match = bucket_for_engine(engine_type)
        fallback_bucket = _combo_data(self.combo_bucket) or _visible_bucket_keys()[0]
        bucket_key = bucket_match[0] if bucket_match else fallback_bucket
        subgroup_name = (
            bucket_match[1]
            if bucket_match
            else (_visible_subgroup_names(bucket_key)[0] if _visible_subgroup_names(bucket_key) else "")
        )

        blockers = [
            QSignalBlocker(self.combo_bucket),
            QSignalBlocker(self.combo_subgroup),
            QSignalBlocker(self.combo_engine),
        ]

        bucket_index = _find_combo_data(self.combo_bucket, bucket_key)
        if bucket_index >= 0:
            self.combo_bucket.setCurrentIndex(bucket_index)

        self.combo_subgroup.clear()
        for subgroup in _visible_subgroup_names(bucket_key):
            self.combo_subgroup.addItem(subgroup, subgroup)
        subgroup_index = _find_combo_data(self.combo_subgroup, subgroup_name)
        if subgroup_index < 0 and self.combo_subgroup.count():
            subgroup_index = 0
        if subgroup_index >= 0:
            self.combo_subgroup.setCurrentIndex(subgroup_index)

        active_subgroup = _combo_data(self.combo_subgroup)
        self.combo_engine.clear()
        engine_names = _visible_engine_names(bucket_key, active_subgroup)
        if (
            engine_type
            and engine_type not in engine_names
            and engine_type in ENGINE_OPTION_ORDER
            and engine_type not in SUPERSEDED_SAFE_EQUIVALENTS
        ):
            engine_names = [engine_type, *engine_names]
        for engine_name in engine_names:
            self.combo_engine.addItem(engine_name, engine_name)
        engine_index = _find_combo_data(self.combo_engine, engine_type)
        if engine_index < 0 and self.combo_engine.count():
            engine_index = 0
        if engine_index >= 0:
            self.combo_engine.setCurrentIndex(engine_index)

        del blockers

    def _handle_bucket_selection(self) -> None:
        bucket_key = _combo_data(self.combo_bucket)
        subgroups = _visible_subgroup_names(bucket_key)
        target_subgroup = subgroups[0] if subgroups else ""
        target_engine = (
            _visible_engine_names(bucket_key, target_subgroup)[0]
            if target_subgroup and _visible_engine_names(bucket_key, target_subgroup)
            else None
        )
        self._populate_bucket_browser(target_engine)
        self.handle_engine_mutation(_combo_data(self.combo_engine))

    def _handle_subgroup_selection(self) -> None:
        bucket_key = _combo_data(self.combo_bucket)
        subgroup_name = _combo_data(self.combo_subgroup)
        engines = _visible_engine_names(bucket_key, subgroup_name)
        target_engine = engines[0] if engines else None
        self._populate_bucket_browser(target_engine)
        self.handle_engine_mutation(_combo_data(self.combo_engine))

    def set_selected_engine(self, engine_type: str) -> None:
        canonical_engine = _canonical_visible_engine(engine_type)
        self._populate_bucket_browser(canonical_engine)
        self.handle_engine_mutation(canonical_engine)

    def refresh_session_list(self) -> None:
        session_ids = self.storage_controller.list_session_ids()
        current = self.session_combo.currentText()
        self.session_combo.clear()
        self.session_combo.addItems(session_ids)
        if current in session_ids:
            self.session_combo.setCurrentText(current)
        elif self.state_card.session_id in session_ids:
            self.session_combo.setCurrentText(self.state_card.session_id)

    def reset_session(self) -> None:
        self.stop_telemetry_monitor()
        self.state_card = EngineStateCard(
            card_id=self.input_card_id.text().strip() or "vance_v3_template",
            engine_type=_combo_data(self.combo_engine) or "Meet-Ugly",
        )
        self.current_session_path = None
        self.hydrate_ui_from_save_state()
        self.refresh_session_list()
        self.status_label.setText("Started a new volatile runtime session.")

    def load_selected_session(self) -> None:
        session_id = self.session_combo.currentText().strip()
        if not session_id:
            return
        try:
            session_path = self.storage_controller.session_path(session_id)
            self.state_card = self.io_controller.hydrate_state_card_from_disk(
                session_path
            )
        except Exception as exc:
            QMessageBox.warning(self, "Session Load Error", str(exc))
            return
        self.current_session_path = self.storage_controller.session_path(session_id)
        self.hydrate_ui_from_save_state()
        self.start_telemetry_monitor(self.current_session_path)
        self.status_label.setText(f"Loaded runtime session: {session_id}")

    def load_state_from_disk(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Active Runtime State Save File",
            str(self.paths.runtime_saves_dir),
            "JSON Files (*.json);;All Files (*)",
        )
        if not selected_path:
            return

        try:
            self.state_card = self.io_controller.hydrate_state_card_from_disk(
                selected_path
            )
        except Exception as exc:
            QMessageBox.warning(self, "Hydration Failure", str(exc))
            return

        self.current_session_path = Path(selected_path)
        self.hydrate_ui_from_save_state()
        self.start_telemetry_monitor(self.current_session_path)
        self.status_label.setText(
            f"Imported runtime state from {Path(selected_path).name}"
        )

    def save_state_to_disk(self) -> None:
        self.sync_ui_to_model_state()
        default_target = self.current_session_path or (
            self.io_controller.save_dir / f"{self.state_card.session_id}.json"
        )
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Active Runtime Session Progress",
            str(default_target),
            "JSON Files (*.json)",
        )
        if not selected_path:
            return

        try:
            target_path = self.io_controller.compile_and_save_to_disk(
                self.state_card,
                selected_path,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Storage IO Error", str(exc))
            return

        self.current_session_path = target_path
        if target_path.parent == self.paths.runtime_saves_dir:
            self.refresh_session_list()
        self.start_telemetry_monitor(target_path)
        self.status_label.setText(f"Saved runtime session to {target_path.name}")

    def handle_engine_mutation(self, new_engine: str) -> None:
        self.state_card.engine_type = new_engine
        self._populate_bucket_browser(new_engine)
        self.rebuild_dynamic_slider_grid()

    def rebuild_dynamic_slider_grid(self) -> None:
        while self.sliders_form_layout.count():
            child = self.sliders_form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.slider_widgets.clear()
        weights_ref = self.state_card.weights
        for key in self._engine_weight_keys(self.state_card.engine_type):
            if key in ENGINE_BOOLEAN_WEIGHT_KEYS:
                checkbox = QCheckBox()
                checkbox.setChecked(bool(weights_ref.get(key, False)))
                checkbox.stateChanged.connect(self.sync_ui_to_model_state)
                self.sliders_form_layout.addRow(
                    self._form_label(key.replace("_", " ").title()), checkbox
                )
                self.slider_widgets[key] = checkbox
                continue

            if key == "lie_count":
                line_edit = QLineEdit(str(weights_ref.get(key, 0)))
                line_edit.setObjectName("controlInput")
                line_edit.setMaximumWidth(72)
                line_edit.textChanged.connect(self.sync_ui_to_model_state)
                self.sliders_form_layout.addRow(
                    self._form_label("Total Lie Count"), line_edit
                )
                self.slider_widgets[key] = line_edit
                continue

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 5)
            slider.setValue(int(weights_ref.get(key, 0)))
            value_label = QLabel(f"{slider.value()}/5")
            value_label.setObjectName("microCopy")
            slider.valueChanged.connect(
                lambda value, label=value_label: label.setText(f"{value}/5")
            )
            slider.valueChanged.connect(self.sync_ui_to_model_state)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(value_label)
            self.sliders_form_layout.addRow(
                self._form_label(key.replace("_", " ").title()), row_widget
            )
            self.slider_widgets[key] = slider

        self.sync_ui_to_model_state()

    def sync_ui_to_model_state(self) -> None:
        self.state_card.card_id = self.input_card_id.text().strip()
        self.state_card.current_phase = self.combo_phase.currentIndex() + 1
        self.state_card.last_updated = datetime.now().timestamp()

        for key, widget in self.slider_widgets.items():
            if isinstance(widget, QCheckBox):
                self.state_card.weights[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                try:
                    self.state_card.weights[key] = max(0, int(widget.text() or 0))
                except ValueError:
                    self.state_card.weights[key] = 0
            elif isinstance(widget, QSlider):
                self.state_card.weights[key] = widget.value()

        self.refresh_chat_log_viewport()
        self.json_terminal.setPlainText(
            json.dumps(self.state_card.to_dict(), indent=2, ensure_ascii=False)
        )
        self.label_session_id.setText(self.state_card.session_id)
        self._process_live_gameplay_turn_updates()

    def execute_mock_message_injection(self) -> None:
        text = self.input_inject_msg.text().strip()
        if not text:
            return

        role = self.inject_role_combo.currentText()
        self.storage_controller.append_chat_message(self.state_card, role, text)
        if role == "user":
            self.storage_controller.append_chat_message(
                self.state_card,
                "character",
                f"[Simulated response turn answering: '{text}']",
            )

        self.input_inject_msg.clear()
        self.sync_ui_to_model_state()
        self.status_label.setText("Injected a simulated runtime message turn.")

    def trigger_external_catalyst_plot_twist_flow(
        self,
        target_branch_destination: str,
    ) -> None:
        pivot_parser = TropeDynamicPivotParser()

        try:
            morphed_dict, prompt_override_directive = (
                pivot_parser.execute_catalyst_pivot(
                    active_session_dict=self.state_card.to_dict(),
                    target_branch=target_branch_destination,
                )
            )
        except Exception as exc:
            self.status_label.setText(f"Pivot exception: {exc}")
            return

        self.state_card = EngineStateCard.from_dict(morphed_dict)
        self.directive_terminal.setPlainText(prompt_override_directive)
        self.hydrate_ui_from_save_state()
        self.status_label.setText(
            f"Plot twist executed: converted to {target_branch_destination}."
        )

    def _process_live_gameplay_turn_updates(self) -> None:
        state_payload = deepcopy(self.state_card.to_dict())
        newly_unlocked = self.telemetry_system.evaluate_live_achievements(state_payload)
        if newly_unlocked:
            titles = ", ".join(item["title"] for item in newly_unlocked)
            self.status_label.setText(f"Achievement unlocked: {titles}")
        self.telemetry_system.queue_telemetry_stream_packet(state_payload)

    def refresh_chat_log_viewport(self) -> None:
        formatted: list[str] = []
        for turn in self.state_card.chat_history:
            role = turn.get("role", "user")
            label = "PLAYER" if role == "user" else "CHARACTER"
            color = "#a855f7" if role == "user" else "#38bdf8"
            content = turn.get("content", "")
            formatted.append(
                f"<b style='color:{color};'>{label}:</b> {content}<br>"
            )
        self.chat_viewport.setHtml("".join(formatted))

    def hydrate_ui_from_save_state(self) -> None:
        blockers = [
            QSignalBlocker(self.input_card_id),
            QSignalBlocker(self.combo_bucket),
            QSignalBlocker(self.combo_subgroup),
            QSignalBlocker(self.combo_engine),
            QSignalBlocker(self.combo_phase),
        ]

        self.label_session_id.setText(self.state_card.session_id)
        self.input_card_id.setText(self.state_card.card_id)

        self._populate_bucket_browser(self.state_card.engine_type)
        self.combo_phase.setCurrentIndex(max(0, min(5, self.state_card.current_phase - 1)))

        self.refresh_chat_log_viewport()
        del blockers
        self.rebuild_dynamic_slider_grid()
        self.refresh_sprite_preview_from_linked_card()

        if self.current_session_path:
            self.sync_status_label.setText(f"Watching {self.current_session_path.name}")
        else:
            self.sync_status_label.setText("Telemetry idle")

    def refresh_sprite_preview_from_linked_card(self) -> None:
        card_path = self._resolve_linked_card_path(self.input_card_id.text().strip())
        if card_path is None:
            self.sprite_manager.clear_viewport_canvas()
            return

        try:
            if card_path.suffix.lower() == ".png":
                payload = self.png_metadata_engine.extract_card_data(card_path.read_bytes())
            elif card_path.suffix.lower() == ".json":
                with card_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            else:
                self.sprite_manager.clear_viewport_canvas()
                return
        except Exception:
            self.sprite_manager.clear_viewport_canvas()
            return

        self.sprite_manager.load_sprite_from_card_payload(payload, card_path)

    def _resolve_linked_card_path(self, raw_card_id: str) -> Path | None:
        if not raw_card_id:
            return None

        candidate = Path(raw_card_id)
        candidates: list[Path] = []
        if candidate.is_absolute():
            candidates.append(candidate)
            if not candidate.suffix:
                candidates.extend(
                    [candidate.with_suffix(".png"), candidate.with_suffix(".json")]
                )
        else:
            base = self.paths.characters_dir / candidate
            if candidate.suffix:
                candidates.extend([base, base.with_suffix(".png"), base.with_suffix(".json")])
            else:
                candidates.extend([base.with_suffix(".png"), base.with_suffix(".json"), base])

        for resolved in candidates:
            if resolved.exists() and resolved.is_file():
                return resolved
        return None

    def start_telemetry_monitor(self, target_path: Path) -> None:
        self.sync_hook.stop_monitoring()
        self.sync_hook.set_target_filepath(target_path)
        self.sync_hook.start_monitoring()
        self.sync_status_label.setText(f"Watching {target_path.name}")

    def stop_telemetry_monitor(self) -> None:
        self.sync_hook.stop_monitoring()
        self.sync_status_label.setText("Telemetry idle")

    def handle_external_telemetry_reload(self, updated_data_dict: dict) -> None:
        self.state_card = EngineStateCard.from_dict(updated_data_dict)
        self.hydrate_ui_from_save_state()
        self.status_label.setText(
            f"Telemetry sync active: hot-reloaded {self.state_card.session_id}"
        )

    def handle_telemetry_error(self, message: str) -> None:
        self.status_label.setText(message)

    def handle_asynchronous_cache_hydration_patch(
        self,
        updated_session_data: dict,
        session_id: str,
    ) -> None:
        if self.state_card.session_id != session_id:
            return
        self.state_card = EngineStateCard.from_dict(updated_session_data)
        self.hydrate_ui_from_save_state()
        self.status_label.setText(
            f"Cache synchronized: session '{session_id}' hot-patched from remote host."
        )

    def handle_cache_sync_fault(self, message: str) -> None:
        self.status_label.setText(message)

    def shutdown(self) -> None:
        self.stop_telemetry_monitor()
        if self.cache_sync_worker is not None:
            self.cache_sync_worker.stop_sync_daemon()
        self.telemetry_system.shutdown()


class MainWindow(QMainWindow):
    def __init__(
        self,
        paths: AppPaths,
        settings: ApiSettings,
        character_prompt_repository: PromptRepository,
        persona_prompt_repository: PromptRepository,
        character_repository: CharacterRepository,
        persona_repository: CharacterRepository,
        generation_engine: GenerationEngine,
        storage_controller: TropeStorageController,
        logger: logging.Logger,
    ):
        super().__init__()
        self.paths = paths
        self.settings = settings
        self.character_prompt_repository = character_prompt_repository
        self.persona_prompt_repository = persona_prompt_repository
        self.character_repository = character_repository
        self.persona_repository = persona_repository
        self.generation_engine = generation_engine
        self.storage_controller = storage_controller
        self.logger = logger
        self.settings_store = QSettings("CharacterGen", "CharacterGeneratorClean")
        self.setWindowTitle("Character Generator")
        self.resize(1480, 980)
        self._build_ui()
        self._load_startup_state()
        self._restore_window_state()
        self._ensure_window_visible()

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("shellRoot")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(20, 18, 20, 18)
        shell_layout.setSpacing(14)

        shell_header = make_card("heroCard")
        shell_header.setStyleSheet(build_page_stylesheet(PERSONA_THEME))
        header_layout = QHBoxLayout(shell_header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(14)

        brand_column = QVBoxLayout()
        brand_column.setSpacing(2)
        eyebrow = QLabel("CharacterGen")
        eyebrow.setObjectName("eyebrow")
        brand_column.addWidget(eyebrow)
        title = QLabel("Character and Persona Studio")
        title.setObjectName("heroTitle")
        brand_column.addWidget(title)
        subtitle = QLabel(
            "Build cards, prompt systems, relationship-matched personas, and trope-engine wrappers in one local workspace."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        brand_column.addWidget(subtitle)
        header_layout.addLayout(brand_column, 1)

        future_pill = QLabel("Future-ready for World Building")
        future_pill.setObjectName("statusPill")
        header_layout.addWidget(future_pill)
        shell_layout.addWidget(shell_header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)

        self.character_prompt_tab = PromptSetTab(
            self.character_prompt_repository,
            theme=PROMPTS_THEME,
            title="Base Character Prompts",
            subtitle="Edit the templates that produce your main bot cards. Use this tab to control structure, ordering, and tone without touching saved cards.",
        )
        self.character_generation_tab = GenerationTab(
            self.character_prompt_repository,
            self.character_repository,
            self.generation_engine,
            paths=self.paths,
            theme=CHARACTER_THEME,
            title="Character Generation",
            subtitle="Build reader-facing cards and private character dossiers with a calmer, more deliberate writing workspace.",
            entity_name="Character",
        )
        self.persona_prompt_tab = PromptSetTab(
            self.persona_prompt_repository,
            theme=PROMPTS_THEME,
            title="Persona Match Prompts",
            subtitle="Tune the persona-building prompts separately so the user profile stays lean, playable, and matched to the loaded character.",
            field_labels=PERSONA_LABELS,
        )
        self.persona_generation_tab = GenerationTab(
            self.persona_prompt_repository,
            self.persona_repository,
            self.generation_engine,
            paths=self.paths,
            theme=PERSONA_THEME,
            title="Persona Match",
            subtitle="Load a source character, shape the matching user persona, and keep the output romantic, playable, and specific without overfeeding the bot.",
            entity_name="Persona",
            enable_reference=True,
            reference_repository=self.character_repository,
            field_labels=PERSONA_LABELS,
        )
        self.trope_workspace_tab = TropeWorkspaceTab(
            paths=self.paths,
            theme=WORLD_THEME,
        )
        self.session_state_tab = SessionStateWorkspaceTab(
            paths=self.paths,
            storage_controller=self.storage_controller,
            theme=CHARACTER_THEME,
        )

        self.tabs.addTab(self.character_prompt_tab, "Base Prompts")
        self.tabs.addTab(self.character_generation_tab, "Character Generation")
        self.tabs.addTab(self.persona_generation_tab, "Persona Match")
        self.tabs.addTab(self.trope_workspace_tab, "Trope Workspace")
        self.tabs.addTab(self.session_state_tab, "Session State")
        self.tabs.addTab(self.persona_prompt_tab, "Persona Prompts")
        self.tabs.setCurrentWidget(self.character_generation_tab)
        shell_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(shell)

        self._tab_themes = {
            0: PROMPTS_THEME,
            1: CHARACTER_THEME,
            2: PERSONA_THEME,
            3: WORLD_THEME,
            4: CHARACTER_THEME,
            5: PROMPTS_THEME,
        }
        self._apply_shell_theme(self.tabs.currentIndex())
        self.tabs.currentChanged.connect(self._apply_shell_theme)

        tab_bar = self.tabs.tabBar()
        tab_bar.setTabTextColor(0, QColor(PROMPTS_THEME.accent_strong))
        tab_bar.setTabTextColor(1, QColor(CHARACTER_THEME.accent_strong))
        tab_bar.setTabTextColor(2, QColor(PERSONA_THEME.accent_strong))
        tab_bar.setTabTextColor(3, QColor(WORLD_THEME.accent_strong))
        tab_bar.setTabTextColor(4, QColor(CHARACTER_THEME.accent_strong))
        tab_bar.setTabTextColor(5, QColor(PROMPTS_THEME.accent_strong))

        self.character_prompt_tab.prompt_set_requested.connect(self.load_character_prompt_set)
        self.character_prompt_tab.prompt_set_saved.connect(self.handle_character_prompt_set_saved)
        self.character_generation_tab.prompt_set_requested.connect(self.load_character_prompt_set)
        self.character_generation_tab.load_combo.currentTextChanged.connect(
            self.character_generation_tab.load_character
        )

        self.persona_prompt_tab.prompt_set_requested.connect(self.load_persona_prompt_set)
        self.persona_prompt_tab.prompt_set_saved.connect(self.handle_persona_prompt_set_saved)
        self.persona_generation_tab.prompt_set_requested.connect(self.load_persona_prompt_set)
        self.persona_generation_tab.load_combo.currentTextChanged.connect(
            self.persona_generation_tab.load_character
        )

    def _apply_shell_theme(self, index: int) -> None:
        theme = self._tab_themes.get(index, CHARACTER_THEME)
        self.setStyleSheet(build_shell_stylesheet(theme))

    def _load_startup_state(self) -> None:
        character_prompt_names = self.character_prompt_repository.list_names()
        persona_prompt_names = self.persona_prompt_repository.list_names()

        self.character_prompt_tab.refresh_prompt_sets()
        self.character_generation_tab.set_available_prompt_sets(character_prompt_names)
        self.character_generation_tab.refresh_characters()

        self.persona_prompt_tab.refresh_prompt_sets()
        self.persona_generation_tab.set_available_prompt_sets(persona_prompt_names)
        self.persona_generation_tab.refresh_characters()
        self.persona_generation_tab.refresh_reference_characters()
        self.session_state_tab.refresh_session_list()

        if character_prompt_names:
            initial = "Default" if "Default" in character_prompt_names else character_prompt_names[0]
            self.load_character_prompt_set(initial)

        if persona_prompt_names:
            initial = (
                "Default" if "Default" in persona_prompt_names else persona_prompt_names[0]
            )
            self.load_persona_prompt_set(initial)

    def load_character_prompt_set(self, name: str) -> None:
        self._load_prompt_set(
            name,
            self.character_prompt_repository,
            self.character_prompt_tab,
            self.character_generation_tab,
        )

    def load_persona_prompt_set(self, name: str) -> None:
        self._load_prompt_set(
            name,
            self.persona_prompt_repository,
            self.persona_prompt_tab,
            self.persona_generation_tab,
        )

    def _load_prompt_set(
        self,
        name: str,
        repository: PromptRepository,
        prompt_tab: PromptSetTab,
        generation_tab: GenerationTab,
    ) -> None:
        if not name:
            return
        try:
            prompt_set = repository.load(name)
        except Exception as exc:
            QMessageBox.warning(self, "Prompt Error", str(exc))
            return

        prompt_tab.load_prompt_set(prompt_set)
        generation_tab.set_current_prompt_set(prompt_set)
        generation_tab.set_status(f"Loaded prompt set: {prompt_set.name}")

    def handle_character_prompt_set_saved(self, prompt_set: PromptSet) -> None:
        self._handle_prompt_set_saved(
            prompt_set,
            self.character_prompt_repository,
            self.character_prompt_tab,
            self.character_generation_tab,
        )

    def handle_persona_prompt_set_saved(self, prompt_set: PromptSet) -> None:
        self._handle_prompt_set_saved(
            prompt_set,
            self.persona_prompt_repository,
            self.persona_prompt_tab,
            self.persona_generation_tab,
        )

    def _handle_prompt_set_saved(
        self,
        prompt_set: PromptSet,
        repository: PromptRepository,
        prompt_tab: PromptSetTab,
        generation_tab: GenerationTab,
    ) -> None:
        prompt_tab.refresh_prompt_sets()
        generation_tab.set_available_prompt_sets(repository.list_names())
        generation_tab.set_current_prompt_set(prompt_set)
        generation_tab.set_status(f"Saved prompt set: {prompt_set.name}")

    def _restore_window_state(self) -> None:
        geometry = self.settings_store.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _ensure_window_visible(self) -> None:
        frame = self.frameGeometry()
        center = frame.center()
        for screen in QApplication.screens():
            if screen.availableGeometry().contains(center):
                return
        primary = QApplication.primaryScreen()
        if not primary:
            return
        available = primary.availableGeometry()
        self.move(
            available.x() + max(0, (available.width() - self.width()) // 2),
            available.y() + max(0, (available.height() - self.height()) // 2),
        )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.settings_store.setValue("geometry", self.saveGeometry())
        self.session_state_tab.shutdown()
        super().closeEvent(event)


def build_main_window(logger: logging.Logger) -> MainWindow:
    paths = AppPaths()
    settings = load_runtime_settings(paths)
    character_prompt_repository = PromptRepository(paths)
    persona_prompt_repository = PromptRepository(
        paths, directory=paths.persona_prompt_sets_dir
    )
    character_repository = CharacterRepository(paths)
    persona_repository = CharacterRepository(paths, directory=paths.personas_dir)
    generation_engine = GenerationEngine(APIClient(settings))
    storage_controller = TropeStorageController(paths)
    return MainWindow(
        paths=paths,
        settings=settings,
        character_prompt_repository=character_prompt_repository,
        persona_prompt_repository=persona_prompt_repository,
        character_repository=character_repository,
        persona_repository=persona_repository,
        generation_engine=generation_engine,
        storage_controller=storage_controller,
        logger=logger,
    )
