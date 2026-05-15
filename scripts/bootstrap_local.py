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
TEMPLATE_PATH = DATA_DIR / "config" / "template.json"
DEFAULT_PROMPT_PATH = DATA_DIR / "base_prompts" / "Default.json"
DEFAULT_PERSONA_PROMPT_PATH = DATA_DIR / "persona_prompts" / "Default.json"
INTIMACY_REFERENCE_FILES = (
    "ageplayer.md",
    "bdsm_compatibility.md",
    "experimentalist.md",
    "non_monogamist.md",
    "submission_stewardship_and_surrender_logic.md",
)
KINK_REFERENCE_FILES = ("grounded_kinks.md",)
ROMANCE_REFERENCE_FILES = (
    "grounded_romance_tropes.md",
    "friends_to_lovers_route_engines.md",
    "enemies_to_lovers_route_engines.md",
    "forced_proximity_route_engines.md",
)
SEDUCTION_REFERENCE_FILES = ("robert_greene_seduction_archetypes.md",)
EXPLICIT_DIALOGUE_REFERENCE_FILES = (
    "grounded_explicit_dialogue.md",
    "scene_invitation_and_consent_opening_language.md",
    "pre_scene_negotiation_and_boundary_language.md",
    "hesitation_renegotiation_and_soft_no_language.md",
    "in_scene_reassurance_and_check_in_language.md",
    "submissive_to_dominant_reassurance_and_top_drop_language.md",
    "aftercare_and_repair_language.md",
    "debrief_and_next_day_processing_language.md",
    "protocol_ritual_and_everyday_power_exchange_language.md",
    "dominant_voice_variants_and_vulnerability_language.md",
    "submissive_voice_variants_and_public_mask_language.md",
    "humiliation_boundary_and_repair_language.md",
    "confession_dialogue_patterns.md",
    "hurt_comfort_and_protective_dialogue.md",
    "awkward_grumpy_and_restrained_affection_dialogue.md",
)
NARRATIVE_POV_REFERENCE_FILES = ("grounded_pov_lock_and_scene_flow.md",)
CHARACTER_PSYCHOLOGY_REFERENCE_FILES = (
    "grounded_character_psychology.md",
    "relationship_wounds_attachment_modes_and_power_dynamics.md",
    "typed_self_report_samples.md",
    "enneagram_behavior_use_note.md",
)
CHARACTER_ROMANCE_CRAFT_REFERENCE_FILES = (
    "character_engine_and_romance_craft.md",
    "charactergen_reference_governance.md",
    "story_writing_benchmark_scene_prose_notes.md",
    "beau_style_best_friend_route_dynamics.md",
    "restrained_wounded_ex_voice_pattern.md",
    "everyday_love_and_nonsexual_intimacy.md",
    "nonverbal_intimacy_and_body_language.md",
    "sensory_safety_reassurance_and_erotic_trust.md",
    "care_trust_and_attunement_in_power_exchange.md",
)
SETTING_SCAFFOLD_REFERENCE_FILES = (
    "grounded_setting_and_scene_scaffolds.md",
    "meet_cute_meet_ugly_and_chaotic_intro_engines.md",
)
LOREBOOK_EXPORT_REFERENCE_FILES = ("lorebook_export_rules.md",)
PROMPT_VALIDATION_REFERENCE_FILES = (
    "roleplay_bench_validation_reference.md",
    "deepdialogue_emotion_domain_testing_note.md",
    "bdsm_source_quality_and_anti-flattening_rules.md",
)
SPECIALIZED_NSFW_REFERENCE_FILES = (
    "nsfw_tag_normalization_rules.md",
    "normalized_nsfw_acts_and_dynamics.md",
)
WORLDBUILDING_DYNAMIC_LORE_REFERENCE_FILES = (
    "safe_sandbox_brain_scripts.md",
    "reactive_world_principles.md",
)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from character_app.config import AppPaths, load_runtime_settings, load_template_payload
from character_app.config import load_reference_bundle

PATHS = AppPaths(root=ROOT_DIR)
CONFIG_PATH = PATHS.config_path

REQUIRED_MODULES = {
    "PyQt6": "PyQt6",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "requests": "requests",
}

EXPECTED_PACKAGE_VERSIONS = {
    "PyQt6": "6.8.1",
    "PyQt6-Qt6": "6.8.2",
}


class BootstrapError(RuntimeError):
    """Raised when bootstrap verification fails."""


def log(message: str) -> None:
    print(f"[bootstrap] {message}")


def ensure_directories() -> None:
    for path in (
        DATA_DIR / "characters",
        DATA_DIR / "base_prompts",
        DATA_DIR / "personas",
        DATA_DIR / "persona_prompts",
        DATA_DIR / "references" / "intimacy_archetypes",
        DATA_DIR / "references" / "kink_taxonomy",
        DATA_DIR / "references" / "romance_tropes",
        DATA_DIR / "references" / "seduction_archetypes",
        DATA_DIR / "references" / "explicit_dialogue",
        DATA_DIR / "references" / "narrative_pov",
        DATA_DIR / "references" / "character_psychology",
        DATA_DIR / "references" / "character_romance_craft",
        DATA_DIR / "references" / "setting_scaffolds",
        DATA_DIR / "references" / "lorebook_export",
        DATA_DIR / "references" / "prompt_validation",
        DATA_DIR / "references" / "specialized_nsfw",
        DATA_DIR / "references" / "worldbuilding_dynamic_lore",
        DATA_DIR / "config",
        DATA_DIR / "logs",
        ROOT_DIR / "logs",
    ):
        path.mkdir(parents=True, exist_ok=True)


def copy_if_missing(source: Path, destination: Path) -> None:
    if destination.exists():
        return

    if not source.exists():
        raise BootstrapError(f"Missing bootstrap asset: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    log(f"seeded {destination.relative_to(ROOT_DIR)}")


def ensure_seed_files() -> None:
    copy_if_missing(
        ASSETS_DIR / "config" / "config.example.yaml",
        CONFIG_PATH,
    )
    copy_if_missing(
        ASSETS_DIR / "config" / "template.json",
        TEMPLATE_PATH,
    )

    prompt_files = sorted((DATA_DIR / "base_prompts").glob("*.json"))
    if not prompt_files:
        copy_if_missing(
            ASSETS_DIR / "base_prompts" / "Default.json",
            DEFAULT_PROMPT_PATH,
        )

    persona_prompt_files = sorted((DATA_DIR / "persona_prompts").glob("*.json"))
    if not persona_prompt_files:
        copy_if_missing(
            ASSETS_DIR / "persona_prompts" / "Default.json",
            DEFAULT_PERSONA_PROMPT_PATH,
        )

    for file_name in INTIMACY_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "intimacy_archetypes" / file_name,
            DATA_DIR / "references" / "intimacy_archetypes" / file_name,
        )
    for file_name in KINK_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "kink_taxonomy" / file_name,
            DATA_DIR / "references" / "kink_taxonomy" / file_name,
        )
    for file_name in ROMANCE_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "romance_tropes" / file_name,
            DATA_DIR / "references" / "romance_tropes" / file_name,
        )
    for file_name in SEDUCTION_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "seduction_archetypes" / file_name,
            DATA_DIR / "references" / "seduction_archetypes" / file_name,
        )
    for file_name in EXPLICIT_DIALOGUE_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "explicit_dialogue" / file_name,
            DATA_DIR / "references" / "explicit_dialogue" / file_name,
        )
    for file_name in NARRATIVE_POV_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "narrative_pov" / file_name,
            DATA_DIR / "references" / "narrative_pov" / file_name,
        )
    for file_name in CHARACTER_PSYCHOLOGY_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "character_psychology" / file_name,
            DATA_DIR / "references" / "character_psychology" / file_name,
        )
    for file_name in CHARACTER_ROMANCE_CRAFT_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "character_romance_craft" / file_name,
            DATA_DIR / "references" / "character_romance_craft" / file_name,
        )
    for file_name in SETTING_SCAFFOLD_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "setting_scaffolds" / file_name,
            DATA_DIR / "references" / "setting_scaffolds" / file_name,
        )
    for file_name in LOREBOOK_EXPORT_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "lorebook_export" / file_name,
            DATA_DIR / "references" / "lorebook_export" / file_name,
        )
    for file_name in PROMPT_VALIDATION_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "prompt_validation" / file_name,
            DATA_DIR / "references" / "prompt_validation" / file_name,
        )
    for file_name in SPECIALIZED_NSFW_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "specialized_nsfw" / file_name,
            DATA_DIR / "references" / "specialized_nsfw" / file_name,
        )
    for file_name in WORLDBUILDING_DYNAMIC_LORE_REFERENCE_FILES:
        copy_if_missing(
            ASSETS_DIR / "references" / "worldbuilding_dynamic_lore" / file_name,
            DATA_DIR / "references" / "worldbuilding_dynamic_lore" / file_name,
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
    missing = []
    for module_name, package_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        raise BootstrapError(
            "Missing Python packages: " + ", ".join(sorted(missing))
        )

    log("python dependencies import cleanly")

    for package_name, expected_version in EXPECTED_PACKAGE_VERSIONS.items():
        installed_version = package_version(package_name)
        if installed_version != expected_version:
            raise BootstrapError(
                f"{package_name} must be {expected_version}, found {installed_version}"
            )

    log("pinned package versions match")


def verify_qt_runtime() -> None:
    try:
        from PyQt6.QtCore import QLibraryInfo
    except Exception as exc:
        raise BootstrapError(f"Qt runtime probe failed: {exc}") from exc

    plugins_path = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    platforms_path = plugins_path / "platforms"
    if not plugins_path.exists():
        raise BootstrapError(f"Qt plugins path missing: {plugins_path}")
    if not platforms_path.exists():
        raise BootstrapError(f"Qt platforms path missing: {platforms_path}")
    if not any(platforms_path.glob("libq*.dylib")):
        raise BootstrapError(f"No Qt platform plugins found in {platforms_path}")
    log("qt plugin assets present")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise BootstrapError(f"Missing config file: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise BootstrapError("Config file must parse to a mapping")

    return data


def verify_config() -> None:
    try:
        config = load_runtime_settings(PATHS)
    except Exception as exc:
        raise BootstrapError(str(exc)) from exc

    if config.key:
        log(f"config ok for {config.url} ({config.model or 'no model'})")
    else:
        log(f"config ok for {config.url}")


def verify_template() -> None:
    if not TEMPLATE_PATH.exists():
        raise BootstrapError(f"Missing template file: {TEMPLATE_PATH}")

    template = load_template_payload(PATHS)

    if template.get("spec") != "chara_card_v2":
        raise BootstrapError("template.json is missing spec=chara_card_v2")

    if "data" not in template or not isinstance(template["data"], dict):
        raise BootstrapError("template.json is missing its data payload")

    log("template.json parses correctly")


def verify_prompt_assets() -> None:
    from character_app.prompts import PromptRepository

    repositories = (
        ("data/base_prompts", PromptRepository(PATHS)),
        (
            "data/persona_prompts",
            PromptRepository(PATHS, directory=PATHS.persona_prompt_sets_dir),
        ),
    )

    verified: list[str] = []
    for label, repository in repositories:
        prompt_sets = repository.list_names()
        if not prompt_sets:
            raise BootstrapError(f"No prompt sets found in {label}")

        target = "Default" if "Default" in prompt_sets else prompt_sets[0]
        prompt_set = repository.load(target)
        if not prompt_set.templates:
            raise BootstrapError(f"Prompt set '{target}' has no templates")
        verified.append(f"{label}:{target}")

    log("prompt assets ok (" + ", ".join(verified) + ")")


def verify_reference_assets() -> None:
    intimacy_bundle = load_reference_bundle(PATHS.intimacy_references_dir)
    if not intimacy_bundle:
        raise BootstrapError(
            f"No intimacy reference files found in {PATHS.intimacy_references_dir}"
        )
    missing_intimacy = [
        file_name
        for file_name in INTIMACY_REFERENCE_FILES
        if not (PATHS.intimacy_references_dir / file_name).exists()
    ]
    if missing_intimacy:
        raise BootstrapError(
            "Missing intimacy reference files: " + ", ".join(sorted(missing_intimacy))
        )

    kink_bundle = load_reference_bundle(PATHS.kink_references_dir)
    if not kink_bundle:
        raise BootstrapError(
            f"No kink reference files found in {PATHS.kink_references_dir}"
        )
    missing_kinks = [
        file_name
        for file_name in KINK_REFERENCE_FILES
        if not (PATHS.kink_references_dir / file_name).exists()
    ]
    if missing_kinks:
        raise BootstrapError(
            "Missing kink reference files: " + ", ".join(sorted(missing_kinks))
        )
    romance_bundle = load_reference_bundle(PATHS.romance_references_dir)
    if not romance_bundle:
        raise BootstrapError(
            f"No romance reference files found in {PATHS.romance_references_dir}"
        )
    missing_romance = [
        file_name
        for file_name in ROMANCE_REFERENCE_FILES
        if not (PATHS.romance_references_dir / file_name).exists()
    ]
    if missing_romance:
        raise BootstrapError(
            "Missing romance reference files: " + ", ".join(sorted(missing_romance))
        )

    seduction_bundle = load_reference_bundle(PATHS.seduction_references_dir)
    if not seduction_bundle:
        raise BootstrapError(
            f"No seduction reference files found in {PATHS.seduction_references_dir}"
        )
    missing_seduction = [
        file_name
        for file_name in SEDUCTION_REFERENCE_FILES
        if not (PATHS.seduction_references_dir / file_name).exists()
    ]
    if missing_seduction:
        raise BootstrapError(
            "Missing seduction reference files: " + ", ".join(sorted(missing_seduction))
        )
    explicit_dialogue_bundle = load_reference_bundle(
        PATHS.explicit_dialogue_references_dir
    )
    if not explicit_dialogue_bundle:
        raise BootstrapError(
            "No explicit dialogue reference files found in "
            f"{PATHS.explicit_dialogue_references_dir}"
        )
    missing_explicit_dialogue = [
        file_name
        for file_name in EXPLICIT_DIALOGUE_REFERENCE_FILES
        if not (PATHS.explicit_dialogue_references_dir / file_name).exists()
    ]
    if missing_explicit_dialogue:
        raise BootstrapError(
            "Missing explicit dialogue reference files: "
            + ", ".join(sorted(missing_explicit_dialogue))
        )
    narrative_pov_bundle = load_reference_bundle(PATHS.narrative_pov_references_dir)
    if not narrative_pov_bundle:
        raise BootstrapError(
            "No narrative POV reference files found in "
            f"{PATHS.narrative_pov_references_dir}"
        )
    missing_narrative_pov = [
        file_name
        for file_name in NARRATIVE_POV_REFERENCE_FILES
        if not (PATHS.narrative_pov_references_dir / file_name).exists()
    ]
    if missing_narrative_pov:
        raise BootstrapError(
            "Missing narrative POV reference files: "
            + ", ".join(sorted(missing_narrative_pov))
        )
    extra_reference_sets = (
        (
            "character psychology",
            PATHS.character_psychology_references_dir,
            CHARACTER_PSYCHOLOGY_REFERENCE_FILES,
        ),
        (
            "character romance craft",
            PATHS.character_romance_craft_references_dir,
            CHARACTER_ROMANCE_CRAFT_REFERENCE_FILES,
        ),
        (
            "setting scaffolds",
            PATHS.setting_scaffolds_references_dir,
            SETTING_SCAFFOLD_REFERENCE_FILES,
        ),
        (
            "lorebook export",
            PATHS.lorebook_export_references_dir,
            LOREBOOK_EXPORT_REFERENCE_FILES,
        ),
        (
            "prompt validation",
            PATHS.prompt_validation_references_dir,
            PROMPT_VALIDATION_REFERENCE_FILES,
        ),
        (
            "specialized nsfw",
            PATHS.specialized_nsfw_references_dir,
            SPECIALIZED_NSFW_REFERENCE_FILES,
        ),
        (
            "worldbuilding dynamic lore",
            PATHS.worldbuilding_dynamic_lore_references_dir,
            WORLDBUILDING_DYNAMIC_LORE_REFERENCE_FILES,
        ),
    )
    for label, directory, required_files in extra_reference_sets:
        bundle = load_reference_bundle(directory)
        if not bundle:
            raise BootstrapError(f"No {label} reference files found in {directory}")
        missing = [
            file_name for file_name in required_files if not (directory / file_name).exists()
        ]
        if missing:
            raise BootstrapError(
                f"Missing {label} reference files: " + ", ".join(sorted(missing))
            )

    log(
        "reference assets ok (intimacy archetypes, kink taxonomy, romance tropes, seduction archetypes, explicit dialogue, narrative POV, character psychology, character romance craft, setting scaffolds, lorebook export, prompt validation, specialized nsfw, worldbuilding dynamic lore)"
    )


def verify_core_services() -> None:
    from character_app.cards import CharacterRepository
    from character_app.constants import FieldId
    from character_app.models import CharacterCard
    from character_app.ui import MainWindow

    _ = MainWindow

    with TemporaryDirectory(prefix="charactergen_bootstrap_") as temp_dir:
        temp_paths = AppPaths(root=Path(temp_dir))
        repositories = (
            (
                "character",
                CharacterRepository(temp_paths),
                "bootstrap-smoke-test-character",
            ),
            (
                "persona",
                CharacterRepository(temp_paths, directory=temp_paths.personas_dir),
                "bootstrap-smoke-test-persona",
            ),
        )
        for label, repository, name in repositories:
            card = CharacterCard(name=name)
            card.fields[FieldId.DESCRIPTION] = f"Smoke test {label} description"

            saved_path = repository.save(card)
            loaded = repository.load(saved_path.name)

            if loaded.name != card.name:
                raise BootstrapError(f"{label.title()} save/load smoke test failed")

    log("core services smoke test passed")


def run_prepare() -> None:
    ensure_directories()
    ensure_seed_files()


def run_verify() -> None:
    verify_python()
    verify_dependencies()
    verify_qt_runtime()
    verify_config()
    verify_template()
    verify_prompt_assets()
    verify_reference_assets()


def run_smoke_test() -> None:
    run_verify()
    verify_core_services()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and verify a local CharacterGen checkout."
    )
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not any((args.prepare, args.verify, args.smoke_test)):
        args.prepare = True
        args.verify = True

    try:
        if args.prepare:
            run_prepare()
        if args.verify:
            run_verify()
        if args.smoke_test:
            run_smoke_test()
    except BootstrapError as exc:
        log(f"error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
