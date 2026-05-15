from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(env_path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = _strip_optional_quotes(value.strip())
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


@dataclass
class AppPaths:
    root: Path = field(default_factory=lambda: PROJECT_ROOT)

    def __post_init__(self) -> None:
        self.data_dir = self.root / "data"
        self.characters_dir = self.data_dir / "characters"
        self.runtime_saves_dir = self.data_dir / "runtime_saves"
        self.prompt_sets_dir = self.data_dir / "base_prompts"
        self.personas_dir = self.data_dir / "personas"
        self.persona_prompt_sets_dir = self.data_dir / "persona_prompts"
        self.references_dir = self.data_dir / "references"
        self.intimacy_references_dir = self.references_dir / "intimacy_archetypes"
        self.kink_references_dir = self.references_dir / "kink_taxonomy"
        self.romance_references_dir = self.references_dir / "romance_tropes"
        self.seduction_references_dir = self.references_dir / "seduction_archetypes"
        self.explicit_dialogue_references_dir = self.references_dir / "explicit_dialogue"
        self.narrative_pov_references_dir = self.references_dir / "narrative_pov"
        self.character_psychology_references_dir = (
            self.references_dir / "character_psychology"
        )
        self.character_romance_craft_references_dir = (
            self.references_dir / "character_romance_craft"
        )
        self.setting_scaffolds_references_dir = (
            self.references_dir / "setting_scaffolds"
        )
        self.lorebook_export_references_dir = self.references_dir / "lorebook_export"
        self.prompt_validation_references_dir = self.references_dir / "prompt_validation"
        self.specialized_nsfw_references_dir = (
            self.references_dir / "specialized_nsfw"
        )
        self.worldbuilding_dynamic_lore_references_dir = (
            self.references_dir / "worldbuilding_dynamic_lore"
        )
        self.config_dir = self.data_dir / "config"
        self.logs_dir = self.root / "logs"
        self.env_path = self.root / ".env"
        self.config_path = self.config_dir / "config.yaml"
        self.template_path = self.config_dir / "template.json"

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.characters_dir,
            self.runtime_saves_dir,
            self.prompt_sets_dir,
            self.personas_dir,
            self.persona_prompt_sets_dir,
            self.references_dir,
            self.intimacy_references_dir,
            self.kink_references_dir,
            self.romance_references_dir,
            self.seduction_references_dir,
            self.explicit_dialogue_references_dir,
            self.narrative_pov_references_dir,
            self.character_psychology_references_dir,
            self.character_romance_craft_references_dir,
            self.setting_scaffolds_references_dir,
            self.lorebook_export_references_dir,
            self.prompt_validation_references_dir,
            self.specialized_nsfw_references_dir,
            self.worldbuilding_dynamic_lore_references_dir,
            self.config_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_reference_bundle(directory: Path) -> str:
    if not directory.exists():
        return ""

    sections: list[str] = []
    for file_path in sorted(directory.glob("*.md")):
        text = file_path.read_text(encoding="utf-8").strip()
        if text:
            sections.append(text)
    return "\n\n".join(sections).strip()


@dataclass
class ApiSettings:
    url: str
    model: str | None
    key: str | None
    max_tokens: int = 2048
    temperature: float = 1.0
    top_p: float = 0.95
    timeout: int = 420
    max_retries: int = 3
    retry_delay: int = 1


def load_runtime_settings(paths: AppPaths) -> ApiSettings:
    paths.ensure_directories()
    load_env_file(paths.env_path)

    if not paths.config_path.exists():
        raise RuntimeError(f"Missing config file: {paths.config_path}")

    with paths.config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise RuntimeError("Config file must parse to a mapping")

    generation = raw.get("generation", {})
    if not isinstance(generation, dict):
        generation = {}

    url = _first_non_empty(os.getenv("CHARACTERGEN_API_URL"), raw.get("API_URL"))
    model = _first_non_empty(
        os.getenv("CHARACTERGEN_API_MODEL"),
        os.getenv("OPENROUTER_MODEL"),
        raw.get("API_MODEL"),
    )
    key = _first_non_empty(
        os.getenv("CHARACTERGEN_API_KEY"),
        os.getenv("OPENROUTER_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        raw.get("API_KEY"),
    )

    if not url:
        raise RuntimeError("API_URL is required in data/config/config.yaml")

    return ApiSettings(
        url=url,
        model=model,
        key=key,
        max_tokens=int(generation.get("max_tokens", 2048)),
        temperature=float(generation.get("temperature", 1.0)),
        top_p=float(generation.get("top_p", 0.95)),
        timeout=int(generation.get("timeout", 420)),
        max_retries=int(generation.get("max_retries", 3)),
        retry_delay=int(generation.get("retry_delay", 1)),
    )


def load_template_payload(paths: AppPaths) -> dict[str, Any]:
    if not paths.template_path.exists():
        return {
            "data": {},
            "spec": "chara_card_v2",
            "spec_version": "2.0",
        }

    import json

    with paths.template_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
