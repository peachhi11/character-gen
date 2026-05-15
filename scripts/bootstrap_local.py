#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
from importlib.metadata import version as package_version
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "bootstrap_assets"


REQUIRED_MODULES = {
    "PyQt6.QtWidgets": "PyQt6",
    "PIL": "Pillow",
    "requests": "requests",
    "yaml": "PyYAML",
}

EXPECTED_PACKAGE_VERSIONS = {
    "PyQt6": "6.8.1",
    "PyQt6-Qt6": "6.8.2",
}


class BootstrapError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[bootstrap] {message}")


def copy_if_missing(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    if not source.exists():
        raise BootstrapError(f"Missing bootstrap asset: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    log(f"seeded {destination.relative_to(ROOT_DIR)}")


def ensure_directories() -> None:
    for path in (
        DATA_DIR / "characters",
        DATA_DIR / "base_prompts",
        DATA_DIR / "config",
        DATA_DIR / "logs",
        ROOT_DIR / "logs",
    ):
        path.mkdir(parents=True, exist_ok=True)


def ensure_seed_files() -> None:
    copy_if_missing(
        ASSETS_DIR / "config" / "config.example.yaml",
        DATA_DIR / "config" / "config.yaml",
    )
    copy_if_missing(
        ASSETS_DIR / "config" / "template.json",
        DATA_DIR / "config" / "template.json",
    )
    if not any((DATA_DIR / "base_prompts").glob("*.json")):
        copy_if_missing(
            ASSETS_DIR / "base_prompts" / "Default.json",
            DATA_DIR / "base_prompts" / "Default.json",
        )


def verify_python() -> None:
    version = sys.version_info
    if (version.major, version.minor) not in {(3, 11), (3, 14)}:
        raise BootstrapError(
            "Python 3.11 or 3.14 is required, "
            f"found {version.major}.{version.minor}.{version.micro}"
        )
    log(f"python {version.major}.{version.minor}.{version.micro}")


def verify_dependencies() -> None:
    for module_name, package_name in REQUIRED_MODULES.items():
        importlib.import_module(module_name)
        log(f"import-ok {module_name}")
        if package_name in EXPECTED_PACKAGE_VERSIONS:
            expected = EXPECTED_PACKAGE_VERSIONS[package_name]
            actual = package_version(package_name)
            if actual != expected:
                raise BootstrapError(
                    f"{package_name} must be {expected}, found {actual}"
                )


def verify_qt_smoke() -> None:
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.processEvents()
    log("qt-ok QApplication")


def verify_seed_files() -> None:
    config_path = DATA_DIR / "config" / "config.yaml"
    template_path = DATA_DIR / "config" / "template.json"
    prompt_path = DATA_DIR / "base_prompts" / "Default.json"

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if "API_URL" not in config:
        raise BootstrapError("data/config/config.yaml is missing API_URL")

    template = json.loads(template_path.read_text(encoding="utf-8"))
    if template.get("spec") != "chara_card_v2":
        raise BootstrapError("data/config/template.json is not a v2 card template")

    prompts = json.loads(prompt_path.read_text(encoding="utf-8"))
    if "prompts" not in prompts or "orders" not in prompts:
        raise BootstrapError("data/base_prompts/Default.json is missing prompt data")

    log("seed-files-ok")


def verify_service_smoke() -> None:
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    from src.core.config import PathConfig
    from src.core.enums import FieldName
    from src.core.models import CharacterData, PromptTemplate
    from src.services.character_service import CharacterService
    from src.services.prompt_service import PromptService

    with TemporaryDirectory() as tmp:
        paths = PathConfig(base_dir=Path(tmp))
        character_service = CharacterService(paths)
        prompt_service = PromptService(paths)

        card = CharacterData(
            name="RuntimeSmoke",
            fields={FieldName.DESCRIPTION: "A short test character."},
        )
        saved_path = character_service.save(card)
        loaded = character_service.load(saved_path.name)
        if loaded.name != "RuntimeSmoke":
            raise BootstrapError("Character save/load smoke test failed")

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
        if rendered != "RuntimeSmoke meets a quiet library.":
            raise BootstrapError("Prompt processing smoke test failed")

    log("services-ok")


def run_bootstrap(*, smoke_test: bool) -> None:
    verify_python()
    ensure_directories()
    ensure_seed_files()
    verify_dependencies()
    verify_qt_smoke()
    verify_seed_files()
    if smoke_test:
        verify_service_smoke()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare CharacterGen locally.")
    parser.add_argument("--prepare", action="store_true", help="prepare runtime files")
    parser.add_argument("--verify", action="store_true", help="verify runtime files")
    parser.add_argument("--smoke-test", action="store_true", help="run service smoke checks")
    return parser.parse_args()


def main() -> int:
    _args = parse_args()
    try:
        run_bootstrap(smoke_test=_args.smoke_test)
    except Exception as exc:
        print(f"[bootstrap] failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
