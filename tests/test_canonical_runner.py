import os
import sys
import unittest
from pathlib import Path


class CanonicalRunnerTest(unittest.TestCase):
    def test_tests_run_through_character_gen_venv(self):
        self.assertEqual(
            os.environ.get("CHARACTERGEN_TEST_RUNNER"),
            "1",
            "Run the full suite with ./test.sh so it always uses the "
            "CharacterGen virtual environment.",
        )

        expected_venv = os.environ.get("CHARACTERGEN_EXPECTED_VENV_DIR")
        self.assertTrue(
            expected_venv,
            "The canonical runner must set CHARACTERGEN_EXPECTED_VENV_DIR.",
        )
        self.assertEqual(Path(sys.prefix).resolve(), Path(expected_venv).resolve())

    def test_runtime_dependencies_import_from_venv(self):
        import PIL  # noqa: F401
        import PyQt6.QtWidgets  # noqa: F401
        import requests  # noqa: F401
        import yaml  # noqa: F401


if __name__ == "__main__":
    unittest.main()
