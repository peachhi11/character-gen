from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.core.config import PathConfig
from src.core.enums import FieldName
from src.core.models import CharacterData, PromptTemplate
from src.services.character_service import CharacterService
from src.services.prompt_service import PromptService


APP = QApplication.instance() or QApplication([])


class RuntimeSmokeTests(unittest.TestCase):
    def test_qapplication_can_start_offscreen(self) -> None:
        APP.processEvents()
        self.assertIsNotNone(APP)

    def test_character_json_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = PathConfig(base_dir=Path(tmp))
            service = CharacterService(paths)
            card = CharacterData(
                name="RuntimeSmoke",
                fields={FieldName.DESCRIPTION: "A short test character."},
            )

            saved_path = service.save(card)
            loaded = service.load(saved_path.name)

        self.assertEqual(loaded.name, "RuntimeSmoke")
        self.assertEqual(
            loaded.fields[FieldName.DESCRIPTION],
            "A short test character.",
        )

    def test_prompt_processing_uses_context_and_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_service = PromptService(PathConfig(base_dir=Path(tmp)))
            template = PromptTemplate(
                text="{{name}} meets {{input}}.",
                field=FieldName.SCENARIO,
                generation_order=2,
            )

            rendered = prompt_service.process_prompt(
                template,
                "a quiet library",
                {FieldName.NAME: "RuntimeSmoke"},
            )

        self.assertEqual(rendered, "RuntimeSmoke meets a quiet library.")


if __name__ == "__main__":
    unittest.main()
