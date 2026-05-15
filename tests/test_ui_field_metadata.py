from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types
import unittest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class _Signal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _SignalDescriptor:
    def __set_name__(self, owner, name) -> None:
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        signal = instance.__dict__.get(self.name)
        if signal is None:
            signal = _Signal()
            instance.__dict__[self.name] = signal
        return signal


def _pyqt_signal(*_args, **_kwargs):
    return _SignalDescriptor()


class _Size:
    def __init__(self, height: int = 24) -> None:
        self._height = height

    def height(self) -> int:
        return self._height


class _Margins:
    def top(self) -> int:
        return 0

    def bottom(self) -> int:
        return 0


class _DocumentLayout:
    def __init__(self) -> None:
        self.documentSizeChanged = _Signal()


class _Document:
    def __init__(self) -> None:
        self._layout = _DocumentLayout()

    def documentLayout(self) -> _DocumentLayout:
        return self._layout

    def size(self) -> _Size:
        return _Size()


class _Widget:
    def __init__(self, parent=None) -> None:
        self._parent = parent
        self._layout = None
        self._visible = True
        self._window_title = ""
        self.destroyed = _Signal()

    def parent(self):
        return self._parent

    def setLayout(self, layout) -> None:
        self._layout = layout
        layout._owner = self

    def layout(self):
        return self._layout

    def setVisible(self, visible: bool) -> None:
        self._visible = visible

    def isVisible(self) -> bool:
        return self._visible

    def show(self) -> None:
        self._visible = True

    def close(self) -> None:
        self._visible = False
        self.destroyed.emit()

    def findChildren(self, _cls):
        return []

    def setWindowTitle(self, title: str) -> None:
        self._window_title = title

    def windowTitle(self) -> str:
        return self._window_title

    def resize(self, *_args) -> None:
        return None

    def setWindowFlags(self, *_args) -> None:
        return None

    def setContentsMargins(self, *_args) -> None:
        return None

    def setSizePolicy(self, *_args) -> None:
        return None

    def setMinimumHeight(self, *_args) -> None:
        return None

    def setMaximumHeight(self, *_args) -> None:
        return None

    def updateGeometry(self) -> None:
        return None


class _Layout:
    def __init__(self, parent=None) -> None:
        self.items = []
        self._owner = None
        if parent is not None:
            parent.setLayout(self)

    def addWidget(self, widget) -> None:
        self.items.append(widget)

    def addLayout(self, layout) -> None:
        self.items.append(layout)

    def addStretch(self, *_args) -> None:
        self.items.append(("stretch", None))

    def addSpacing(self, value: int) -> None:
        self.items.append(("spacing", value))

    def setContentsMargins(self, *_args) -> None:
        return None

    def setSpacing(self, *_args) -> None:
        return None


class _VBoxLayout(_Layout):
    pass


class _HBoxLayout(_Layout):
    pass


class _Frame(_Widget):
    class Shape:
        HLine = "HLine"

    class Shadow:
        Sunken = "Sunken"

    def setFrameShape(self, *_args) -> None:
        return None

    def setFrameShadow(self, *_args) -> None:
        return None

    def setAcceptDrops(self, *_args) -> None:
        return None


class _Label(_Widget):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._text = text

    def setText(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def clear(self) -> None:
        self._text = ""

    def setAlignment(self, *_args) -> None:
        return None


class _TextEdit(_Widget):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._text = text
        self._placeholder = ""
        self._blocked = False
        self._document = _Document()
        self.textChanged = _Signal()

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder = text

    def placeholderText(self) -> str:
        return self._placeholder

    def setAcceptRichText(self, *_args) -> None:
        return None

    def document(self) -> _Document:
        return self._document

    def contentsMargins(self) -> _Margins:
        return _Margins()

    def setPlainText(self, text: str) -> None:
        self._text = text
        if not self._blocked:
            self.textChanged.emit()

    def toPlainText(self) -> str:
        return self._text

    def clear(self) -> None:
        self.setPlainText("")

    def blockSignals(self, blocked: bool) -> None:
        self._blocked = blocked

    def setReadOnly(self, *_args) -> None:
        return None

    def isReadOnly(self) -> bool:
        return False


class _PushButton(_Widget):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._text = text
        self.clicked = _Signal()

    def setToolTip(self, *_args) -> None:
        return None

    def setFixedWidth(self, *_args) -> None:
        return None

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text

    def setEnabled(self, *_args) -> None:
        return None


class _CheckBox(_Widget):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._text = text
        self._checked = False
        self.stateChanged = _Signal()

    def setChecked(self, checked: bool) -> None:
        self._checked = checked

    def isChecked(self) -> bool:
        return self._checked


class _LineEdit(_Widget):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._text = text
        self._placeholder = ""
        self.textChanged = _Signal()

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder = text

    def placeholderText(self) -> str:
        return self._placeholder

    def setFixedWidth(self, *_args) -> None:
        return None

    def setText(self, text: str) -> None:
        self._text = text
        self.textChanged.emit(text)

    def text(self) -> str:
        return self._text

    def clear(self) -> None:
        self.setText("")

    def setReadOnly(self, *_args) -> None:
        return None

    def isReadOnly(self) -> bool:
        return False


class _ComboBox(_Widget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items = []
        self._current = ""
        self.currentTextChanged = _Signal()

    def addItems(self, items) -> None:
        self._items.extend(items)
        if not self._current and self._items:
            self._current = self._items[0]

    def clear(self) -> None:
        self._items = []
        self._current = ""

    def currentText(self) -> str:
        return self._current

    def setCurrentText(self, text: str) -> None:
        self._current = text
        self.currentTextChanged.emit(text)


class _ScrollArea(_Widget):
    def setWidgetResizable(self, *_args) -> None:
        return None

    def setWidget(self, widget) -> None:
        self._widget = widget


class _Splitter(_Widget):
    def __init__(self, *_args, parent=None) -> None:
        super().__init__(parent)
        self.widgets = []

    def addWidget(self, widget) -> None:
        self.widgets.append(widget)

    def setSizes(self, *_args) -> None:
        return None


class _SpinBox(_Widget):
    pass


class _SpacerItem:
    def __init__(self, *_args, **_kwargs) -> None:
        return None


class _SizePolicy:
    class Policy:
        Expanding = "Expanding"
        Minimum = "Minimum"
        Fixed = "Fixed"
        Preferred = "Preferred"


class _FileDialog:
    @staticmethod
    def getOpenFileName(*_args, **_kwargs):
        return "", ""


class _MessageBox:
    last_warning = None

    class StandardButton:
        Yes = 1
        No = 2
        Cancel = 3

    @classmethod
    def warning(cls, parent, title: str, message: str) -> None:
        cls.last_warning = (parent, title, message)

    @classmethod
    def information(cls, *_args) -> None:
        return None

    @classmethod
    def critical(cls, *_args) -> None:
        return None

    @classmethod
    def question(cls, *_args):
        return cls.StandardButton.No


class _Qt:
    class Orientation:
        Horizontal = "horizontal"

    class WindowType:
        Window = "window"

    class AlignmentFlag:
        AlignRight = "align-right"


def _install_fake_pyqt() -> None:
    pyqt6 = types.ModuleType("PyQt6")
    qtwidgets = types.ModuleType("PyQt6.QtWidgets")
    qtcore = types.ModuleType("PyQt6.QtCore")

    qtwidgets.QWidget = _Widget
    qtwidgets.QFrame = _Frame
    qtwidgets.QVBoxLayout = _VBoxLayout
    qtwidgets.QHBoxLayout = _HBoxLayout
    qtwidgets.QTextEdit = _TextEdit
    qtwidgets.QPushButton = _PushButton
    qtwidgets.QLabel = _Label
    qtwidgets.QCheckBox = _CheckBox
    qtwidgets.QSplitter = _Splitter
    qtwidgets.QSpacerItem = _SpacerItem
    qtwidgets.QSizePolicy = _SizePolicy
    qtwidgets.QSpinBox = _SpinBox
    qtwidgets.QLineEdit = _LineEdit
    qtwidgets.QComboBox = _ComboBox
    qtwidgets.QFileDialog = _FileDialog
    qtwidgets.QMessageBox = _MessageBox
    qtwidgets.QScrollArea = _ScrollArea

    qtcore.Qt = _Qt
    qtcore.pyqtSignal = _pyqt_signal

    sys.modules["PyQt6"] = pyqt6
    sys.modules["PyQt6.QtWidgets"] = qtwidgets
    sys.modules["PyQt6.QtCore"] = qtcore


def _reload(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def _iter_layout_texts(node):
    if isinstance(node, _Label):
        yield node.text()
        return
    if isinstance(node, _Splitter):
        for widget in node.widgets:
            yield from _iter_layout_texts(widget)
        return
    if isinstance(node, _ScrollArea):
        if hasattr(node, "_widget"):
            yield from _iter_layout_texts(node._widget)
        return
    if isinstance(node, _Widget) and node.layout() is not None:
        yield from _iter_layout_texts(node.layout())
        return
    if isinstance(node, _Layout):
        for item in node.items:
            if isinstance(item, tuple):
                continue
            yield from _iter_layout_texts(item)


_install_fake_pyqt()

from src.core.enums import FieldName  # noqa: E402
from src.core.models import CharacterData, GenerationResult  # noqa: E402

common = _reload("src.ui.widgets.common")
field_widgets = _reload("src.ui.widgets.field_widgets")
base_prompt_widgets = _reload("src.ui.widgets.base_prompt_widgets")
generation_tab = _reload("src.ui.tabs.generation_tab")


class _CharacterServiceStub:
    def list_characters(self):
        return []

    def create_character(self, name: str) -> CharacterData:
        return CharacterData(name=name)


class _GenerationServiceStub:
    pass


class UiFieldMetadataTests(unittest.TestCase):
    def test_field_input_widget_uses_display_name_and_placeholder_text(self) -> None:
        widget = field_widgets.FieldInputWidget(FieldName.FIRST_MES)

        labels = list(_iter_layout_texts(widget))

        self.assertIn(FieldName.FIRST_MES.display_name, labels)
        self.assertEqual(
            widget.input.placeholderText(),
            FieldName.FIRST_MES.placeholder_text,
        )

    def test_base_prompt_widgets_follow_ui_order_and_display_name(self) -> None:
        widget = base_prompt_widgets.BasePromptWidget(FieldName.MES_EXAMPLE)
        container = base_prompt_widgets.BasePromptsContainer()

        labels = list(_iter_layout_texts(widget))

        self.assertIn(
            f"Base Prompt for {FieldName.MES_EXAMPLE.display_name}",
            labels,
        )
        self.assertEqual(
            list(container.prompt_widgets.keys()),
            FieldName.ui_order(),
        )

    def test_generation_tab_uses_ui_order_for_inputs_and_outputs(self) -> None:
        tab = generation_tab.GenerationTab(
            _CharacterServiceStub(),
            _GenerationServiceStub(),
        )

        labels = list(_iter_layout_texts(tab))

        self.assertEqual(list(tab.input_widgets.keys()), FieldName.ui_order())
        self.assertEqual(list(tab.output_texts.keys()), FieldName.ui_order())
        self.assertIn("First Message Output:", labels)
        self.assertIn("Speech Examples Output:", labels)

    def test_generation_callbacks_and_errors_use_display_names(self) -> None:
        tab = generation_tab.GenerationTab(
            _CharacterServiceStub(),
            _GenerationServiceStub(),
        )
        tab.current_character = CharacterData(name="Aster")

        callbacks = tab._create_callbacks()
        callbacks.on_start(FieldName.FIRST_MES)
        self.assertEqual(
            tab.status_bar.status_label.text(),
            "Generating first message...",
        )

        result = GenerationResult(
            field=FieldName.FIRST_MES,
            content="Hello there",
            attempts=2,
        )
        callbacks.on_result(FieldName.FIRST_MES, result)

        self.assertEqual(
            tab.output_texts[FieldName.FIRST_MES].toPlainText(),
            "Hello there",
        )
        self.assertEqual(
            tab.status_bar.status_label.text(),
            "Generated first message in 2 attempts",
        )

        tab._handle_generation_error(FieldName.MES_EXAMPLE, ValueError("boom"))
        self.assertEqual(
            tab.status_bar.status_label.text(),
            "Error generating speech examples",
        )
        self.assertEqual(
            _MessageBox.last_warning[2],
            "Error generating speech examples: boom",
        )


if __name__ == "__main__":
    unittest.main()
