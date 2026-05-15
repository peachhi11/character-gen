from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .api import APIClient
from .cards import CharacterRepository
from .config import AppPaths, load_reference_bundle, load_runtime_settings
from .constants import FieldId
from .generation import GenerationEngine
from .models import PromptSet
from .prompts import PromptRepository, render_prompt


ALLOWED_UNRESOLVED_TAGS = frozenset({"char", "user"})
QUOTE_RE = re.compile(r'"[^"\n]*"')
MULTILINE_QUOTE_RE = re.compile(r'"[^"]*"')
SCENARIO_VAGUE_PATTERNS = (
    re.compile(r"\ba conversation about\b", re.I),
    re.compile(r"\ba discussion about\b", re.I),
    re.compile(r"\ba talk about\b", re.I),
    re.compile(r"\bthemes of\b", re.I),
)
SCENARIO_SETTING_MARKERS = (
    "office",
    "bar",
    "club",
    "archive",
    "safehouse",
    "apartment",
    "train",
    "hallway",
    "locker room",
    "car",
    "street",
    "kitchen",
    "hotel",
    "party",
    "hospital",
    "stadium",
    "campus",
    "rooftop",
)
SCENARIO_PRESSURE_MARKERS = (
    "after",
    "before",
    "because",
    "forced",
    "caught",
    "waiting",
    "deadline",
    "public",
    "threat",
    "clash",
    "argument",
    "interrupted",
    "returns",
    "reunion",
    "apology",
    "jealous",
)
SCENARIO_RELATIONAL_MARKERS = (
    "{{user}}",
    "{{char}}",
    "tension",
    "chemistry",
    "history",
    "attraction",
    "longing",
    "rivals",
    "friends",
    "ex",
    "apprentice",
    "partner",
    "lover",
)
USER_SPEAKER_LABEL_RE = re.compile(r"(?im)^\s*(?:{{user}}|you)\s*:")
USER_INTERIORITY_PATTERNS = (
    re.compile(r"\byou (?:feel|felt|think|thought|want|wanted|realize|realized|know|knew)\b", re.I),
    re.compile(r"\byour (?:heart|mind|thoughts|pulse) (?:raced|pounded|spiked|twisted|jumped)\b", re.I),
    re.compile(r"\bwithout (?:you|{{user}}) realizing\b", re.I),
    re.compile(r"\bunaware that you\b", re.I),
)
USER_ACTION_PATTERNS = (
    re.compile(
        r"\byou (?:say|said|reply|replied|respond|responded|whisper|whispered|murmur|murmured|"
        r"nod|nodded|shake|shook|step|stepped|move|moved|turn|turned|reach|reached|"
        r"flinch|flinched|hesitate|hesitated|look|looked|glance|glanced|swallow|swallowed)\b",
        re.I,
    ),
)
OMNISCIENT_DRIFT_PATTERNS = (
    re.compile(r"\b{{user}} (?:didn't|did not) know\b", re.I),
    re.compile(r"\byou (?:didn't|did not) know\b", re.I),
    re.compile(r"\b{{char}} (?:knew|knows) you (?:wanted|were about to|would)\b", re.I),
    re.compile(r"\b(?:he|she) (?:knew|knows) you (?:wanted|were about to|would)\b", re.I),
    re.compile(r"\b(?:she|he) could tell you (?:wanted|needed|were about to)\b", re.I),
    re.compile(r"\bbefore you could (?:answer|reply|react|say anything)\b", re.I),
)
SCENE_ACTION_MARKERS = (
    "door",
    "hall",
    "room",
    "desk",
    "office",
    "kitchen",
    "bar",
    "street",
    "air",
    "voice",
    "hand",
    "steps",
    "silence",
    "light",
    "phone",
    "glance",
    "breath",
)
BASE_SPEECH_CATEGORIES = (
    "[When he is flirting]",
    "[When he is possessive]",
    "[When he is dominant or sexually charged]",
    "[When he is soft]",
    "[When he is angry]",
    "[When he is jealous]",
    "[When he is being honest]",
    "[When he is performing in public]",
)
PERSONA_SPEECH_CATEGORIES = (
    "[When she is flirting]",
    "[When she is possessive]",
    "[When she is sexually charged]",
    "[When she is soft]",
    "[When she is angry]",
    "[When she is jealous]",
    "[When she is being honest]",
    "[When she is trying to act normal in public]",
)


@dataclass
class PromptTestCase:
    name: str
    prompt_library: str
    prompt_set: str
    description: str
    inputs: dict[FieldId, str]
    reference_card_path: str | None = None
    reference_text: str = ""
    direct_name: bool = False

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "PromptTestCase":
        inputs = {
            FieldId(field_name): value
            for field_name, value in payload.get("inputs", {}).items()
            if value is not None
        }
        return cls(
            name=payload["name"],
            prompt_library=payload["prompt_library"],
            prompt_set=payload.get("prompt_set", "Default"),
            description=payload.get("description", ""),
            inputs=inputs,
            reference_card_path=payload.get("reference_card_path"),
            reference_text=payload.get("reference_text", ""),
            direct_name=bool(payload.get("direct_name", False)),
        )


def load_cases(cases_dir: Path) -> list[PromptTestCase]:
    cases: list[PromptTestCase] = []
    for file_path in sorted(cases_dir.glob("*.json")):
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        cases.append(PromptTestCase.from_payload(payload))
    return cases


def get_prompt_repository(paths: AppPaths, prompt_library: str) -> PromptRepository:
    if prompt_library == "base":
        return PromptRepository(paths)
    if prompt_library == "persona":
        return PromptRepository(paths, directory=paths.persona_prompt_sets_dir)
    raise RuntimeError(f"Unsupported prompt library: {prompt_library}")


def load_prompt_set(paths: AppPaths, prompt_library: str, prompt_set_name: str) -> PromptSet:
    return get_prompt_repository(paths, prompt_library).load(prompt_set_name)


def build_reference_context(
    paths: AppPaths,
    case: PromptTestCase,
    fixtures_root: Path,
) -> dict[str, str]:
    context = {
        "reference": case.reference_text.strip(),
        "reference_notes": case.reference_text.strip(),
        "char_card": case.reference_text.strip(),
        "intimacy_reference": load_reference_bundle(paths.intimacy_references_dir),
        "kink_reference": load_reference_bundle(paths.kink_references_dir),
        "romance_reference": load_reference_bundle(paths.romance_references_dir),
        "seduction_reference": load_reference_bundle(paths.seduction_references_dir),
        "explicit_dialogue_reference": load_reference_bundle(
            paths.explicit_dialogue_references_dir
        ),
        "narrative_pov_reference": load_reference_bundle(
            paths.narrative_pov_references_dir
        ),
        "character_psychology_reference": load_reference_bundle(
            paths.character_psychology_references_dir
        ),
        "character_romance_craft_reference": load_reference_bundle(
            paths.character_romance_craft_references_dir
        ),
        "setting_scaffolds_reference": load_reference_bundle(
            paths.setting_scaffolds_references_dir
        ),
        "lorebook_export_reference": load_reference_bundle(
            paths.lorebook_export_references_dir
        ),
        "prompt_validation_reference": load_reference_bundle(
            paths.prompt_validation_references_dir
        ),
        "specialized_nsfw_reference": load_reference_bundle(
            paths.specialized_nsfw_references_dir
        ),
        "worldbuilding_dynamic_lore_reference": load_reference_bundle(
            paths.worldbuilding_dynamic_lore_references_dir
        ),
    }

    if not case.reference_card_path:
        for field_id in FieldId.ui_order():
            context[f"char_{field_id.value}"] = ""
        context["char_name"] = ""
        return context

    card_path = fixtures_root / case.reference_card_path
    repository = CharacterRepository(paths, directory=card_path.parent)
    card = repository.load(str(card_path))
    reference_name = card.fields.get(FieldId.NAME, "").strip() or card.name.strip()
    context["char_name"] = reference_name
    if not context["reference"]:
        context["reference"] = serialize_reference_card(card)
        context["reference_notes"] = context["reference"]
        context["char_card"] = context["reference"]
    for field_id in FieldId.ui_order():
        value = card.fields.get(field_id, "")
        if field_id == FieldId.NAME:
            value = reference_name
        context[f"char_{field_id.value}"] = value
    return context


def serialize_reference_card(card) -> str:
    lines = [f"Name: {card.fields.get(FieldId.NAME, '').strip() or card.name.strip()}"]
    for field_id in FieldId.ui_order():
        if field_id == FieldId.NAME:
            continue
        value = card.fields.get(field_id, "").strip()
        if value:
            lines.append(f"{field_id.display_name}:")
            lines.append(value)
    return "\n".join(lines).strip()


def unresolved_tags(text: str) -> set[str]:
    return set(re.findall(r"{{(\w+)}}", text))


def _strip_quoted_dialogue(text: str) -> str:
    return MULTILINE_QUOTE_RE.sub(" ", text)


def validate_first_message_behavior(text: str) -> list[str]:
    issues: list[str] = []
    narration = _strip_quoted_dialogue(text)
    lowered = text.lower()

    if USER_SPEAKER_LABEL_RE.search(text):
        issues.append("First Message wrote explicit {{user}} dialogue/action labels")

    for pattern in USER_INTERIORITY_PATTERNS:
        if pattern.search(narration):
            issues.append("First Message assigned internal state to {{user}}")
            break

    for pattern in USER_ACTION_PATTERNS:
        if pattern.search(narration):
            issues.append("First Message wrote physical action or reply beats for {{user}}")
            break

    for pattern in OMNISCIENT_DRIFT_PATTERNS:
        if pattern.search(narration):
            issues.append("First Message drifted into omniscient or predictive narration")
            break

    if "you respond" in lowered or "your response" in lowered:
        issues.append("First Message over-resolved the interaction instead of leaving space")

    if len(text) < 80:
        issues.append("First Message is too thin to establish an active opening beat")
    elif not any(marker in lowered for marker in SCENE_ACTION_MARKERS):
        issues.append("First Message may be too abstract or static for scene play")

    return issues


def validate_scenario_specificity(text: str) -> list[str]:
    issues: list[str] = []
    lowered = text.lower()
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]

    if len(paragraphs) < 2:
        issues.append("Scenario is too compressed; it should read as an active setup, not a note")

    if any(pattern.search(text) for pattern in SCENARIO_VAGUE_PATTERNS):
        issues.append("Scenario drifted into abstract thematic framing instead of a concrete setup")

    if not any(marker in lowered for marker in SCENARIO_SETTING_MARKERS):
        issues.append("Scenario may lack a concrete setting anchor")

    if not any(marker in lowered for marker in SCENARIO_PRESSURE_MARKERS):
        issues.append("Scenario may lack an active pressure or complication")

    if not any(marker in lowered for marker in SCENARIO_RELATIONAL_MARKERS):
        issues.append("Scenario may lack clear relationship tension or shared context")

    return issues


def _extract_speech_sections(
    text: str,
    categories: tuple[str, ...],
) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for index, category in enumerate(categories):
        start = text.find(category)
        if start == -1:
            continue
        end = len(text)
        for next_category in categories[index + 1 :]:
            candidate = text.find(next_category, start + len(category))
            if candidate != -1:
                end = candidate
                break
        body = text[start + len(category) : end].strip()
        sections.append((category, body))
    return sections


def validate_speech_examples_structure(
    text: str,
    categories: tuple[str, ...],
    label: str,
) -> list[str]:
    issues: list[str] = []
    sections = _extract_speech_sections(text, categories)
    if len(sections) != len(categories):
        issues.append(f"{label} is missing one or more required emotional categories")
        return issues

    guide_lines: dict[str, str] = {}
    quote_sets: dict[str, tuple[str, ...]] = {}

    for category, body in sections:
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if not lines:
            issues.append(f"{label} has an empty section for {category}")
            continue
        guide_line = lines[0]
        guide_lines[category] = guide_line
        quotes = tuple(QUOTE_RE.findall(body))
        quote_sets[category] = quotes

        if guide_line.startswith('"') and guide_line.endswith('"'):
            issues.append(f"{label} should start {category} with an unquoted guide line")
        if len(quotes) < 2:
            issues.append(f"{label} needs at least two quote examples in {category}")

    if len(set(line.lower() for line in guide_lines.values())) < max(4, len(categories) // 2):
        issues.append(f"{label} guide lines are too repetitive across emotional categories")

    public_category = next((cat for cat in categories if "public" in cat.lower()), None)
    soft_category = next((cat for cat in categories if "soft" in cat.lower()), None)
    honest_category = next((cat for cat in categories if "honest" in cat.lower()), None)
    if public_category and soft_category:
        public_guide = guide_lines.get(public_category, "").lower()
        soft_guide = guide_lines.get(soft_category, "").lower()
        if public_guide and soft_guide and public_guide == soft_guide:
            issues.append(f"{label} does not distinguish public voice from soft private voice")
        if quote_sets.get(public_category) and quote_sets.get(soft_category):
            if set(quote_sets[public_category]) & set(quote_sets[soft_category]):
                issues.append(f"{label} reuses quote beats between public and soft private voice")
    if public_category and honest_category:
        if guide_lines.get(public_category, "").strip().lower() == guide_lines.get(honest_category, "").strip().lower():
            issues.append(f"{label} does not distinguish public voice from honest private voice")

    return issues


def render_case_prompts(
    paths: AppPaths,
    case: PromptTestCase,
    fixtures_root: Path,
) -> dict[FieldId, str]:
    prompt_set = load_prompt_set(paths, case.prompt_library, case.prompt_set)
    rendered: dict[FieldId, str] = {}
    fake_outputs: dict[FieldId, str] = {}
    extra_context = build_reference_context(paths, case, fixtures_root)

    for field_id in prompt_set.ordered_fields():
        template = prompt_set.templates[field_id]
        rendered[field_id] = render_prompt(
            template,
            case.inputs.get(field_id, ""),
            fake_outputs,
            extra_context=extra_context,
        )
        if field_id == FieldId.NAME and case.direct_name and case.inputs.get(FieldId.NAME, "").strip():
            fake_outputs[field_id] = case.inputs[FieldId.NAME].strip()
        else:
            fake_outputs[field_id] = f"[stub output for {field_id.value} in {case.name}]"
    return rendered


def validate_rendered_prompts(
    case: PromptTestCase,
    prompt_set: PromptSet,
    rendered: dict[FieldId, str],
) -> list[str]:
    issues: list[str] = []
    expected_fields = set(prompt_set.ordered_fields())
    missing = expected_fields - set(rendered)
    if missing:
        issues.append(
            "Missing rendered fields: " + ", ".join(field.display_name for field in sorted(missing, key=lambda f: f.value))
        )

    for field_id, text in rendered.items():
        if not text.strip():
            issues.append(f"{field_id.display_name} rendered to empty text")
            continue
        tags = unresolved_tags(text) - ALLOWED_UNRESOLVED_TAGS
        if tags:
            issues.append(
                f"{field_id.display_name} left unresolved tags: " + ", ".join(sorted(tags))
            )
        if "{{/if_input}}" in text or "{{if_input}}" in text:
            issues.append(f"{field_id.display_name} still contains conditional markers")
        if case.prompt_library == "persona" and field_id == FieldId.PERSONALITY:
            if "{{intimacy_reference}}" in text or "{{kink_reference}}" in text:
                issues.append("Persona Personality did not absorb reference bundles")
        if field_id == FieldId.MES_EXAMPLE and "{{explicit_dialogue_reference}}" in text:
            issues.append(f"{field_id.display_name} did not absorb explicit dialogue reference")
        if (
            case.prompt_library == "base"
            and field_id in {FieldId.PERSONALITY, FieldId.FIRST_MES}
            and "{{narrative_pov_reference}}" in text
        ):
            issues.append(
                f"{field_id.display_name} did not absorb narrative POV reference"
            )
        if case.prompt_library == "base" and field_id == FieldId.SCENARIO:
            if "{{romance_reference}}" in text:
                issues.append("Character Scenario did not absorb romance reference")
        if case.prompt_library == "base" and field_id == FieldId.PERSONALITY:
            if "{{character_psychology_reference}}" in text:
                issues.append("Character Personality did not absorb psychology reference")
            if "{{character_romance_craft_reference}}" in text:
                issues.append("Character Personality did not absorb romance-craft reference")
            if "{{specialized_nsfw_reference}}" in text:
                issues.append("Character Personality did not absorb specialized-nsfw reference")
        if case.prompt_library == "base" and field_id == FieldId.SCENARIO:
            if "{{character_romance_craft_reference}}" in text:
                issues.append("Character Scenario did not absorb romance-craft reference")
            if "{{setting_scaffolds_reference}}" in text:
                issues.append("Character Scenario did not absorb setting-scaffold reference")
        if case.prompt_library == "base" and field_id == FieldId.FIRST_MES:
            if "{{character_romance_craft_reference}}" in text:
                issues.append("Character First Message did not absorb romance-craft reference")
            if "{{setting_scaffolds_reference}}" in text:
                issues.append("Character First Message did not absorb setting-scaffold reference")
        if case.prompt_library == "base" and field_id == FieldId.MES_EXAMPLE:
            if "{{character_psychology_reference}}" in text:
                issues.append("Character Speech Examples did not absorb psychology reference")
            if "{{prompt_validation_reference}}" in text:
                issues.append("Character Speech Examples did not absorb prompt-validation reference")
        if case.prompt_library == "persona" and field_id == FieldId.DESCRIPTION:
            if "{{character_romance_craft_reference}}" in text:
                issues.append("Persona Description did not absorb romance-craft reference")
        if case.prompt_library == "persona" and field_id == FieldId.PERSONALITY:
            if "{{character_psychology_reference}}" in text:
                issues.append("Persona Personality did not absorb psychology reference")
            if "{{character_romance_craft_reference}}" in text:
                issues.append("Persona Personality did not absorb romance-craft reference")
            if "{{specialized_nsfw_reference}}" in text:
                issues.append("Persona Personality did not absorb specialized-nsfw reference")
        if case.prompt_library == "persona" and field_id == FieldId.SCENARIO:
            if "{{character_romance_craft_reference}}" in text:
                issues.append("Persona Scenario did not absorb romance-craft reference")
            if "{{setting_scaffolds_reference}}" in text:
                issues.append("Persona Scenario did not absorb setting-scaffold reference")
        if case.prompt_library == "persona" and field_id == FieldId.MES_EXAMPLE:
            if "{{character_psychology_reference}}" in text:
                issues.append("Persona Speech Examples did not absorb psychology reference")
            if "{{prompt_validation_reference}}" in text:
                issues.append("Persona Speech Examples did not absorb prompt-validation reference")
    return issues


def validate_generated_output(
    case: PromptTestCase,
    field_id: FieldId,
    output_text: str,
) -> list[str]:
    issues: list[str] = []
    text = output_text.strip()
    if not text:
        return [f"{field_id.display_name} generated empty output"]

    if case.prompt_library == "persona" and field_id == FieldId.PERSONALITY:
        required_markers = [
            "> BASIC INFORMATION",
            "> APPEARANCE",
            "> CORE PERSONALITY",
            "> CONNECTIONS",
            "> DYNAMIC WITH CHAR",
            "> INTIMACY",
            "> SPEECH",
            "> POST HISTORY INSTRUCTIONS",
        ]
        for marker in required_markers:
            if marker not in text:
                issues.append(f"Persona Personality missing marker: {marker}")
        if "Family\n" not in text or "\nFriends\n" not in text or "\nOther\n" not in text:
            issues.append("Persona Personality missing structured Connections subsections")
    elif case.prompt_library == "persona" and field_id == FieldId.MES_EXAMPLE:
        if "Speech Examples and Opinions" not in text:
            issues.append("Persona Speech Examples missing heading")
        issues.extend(
            validate_speech_examples_structure(
                text,
                PERSONA_SPEECH_CATEGORIES,
                "Persona Speech Examples",
            )
        )
    elif case.prompt_library == "base" and field_id == FieldId.DESCRIPTION:
        for marker in [
            "Opening Quote:",
            "Page Hook:",
            "Character Overview:",
            "World and Lore:",
            "Who {{user}} Is:",
            "Story Hook:",
        ]:
            if marker not in text:
                issues.append(f"Character Description missing marker: {marker}")
    elif field_id == FieldId.SCENARIO:
        issues.extend(validate_scenario_specificity(text))
    elif case.prompt_library == "base" and field_id == FieldId.MES_EXAMPLE:
        issues.extend(
            validate_speech_examples_structure(
                text,
                BASE_SPEECH_CATEGORIES,
                "Character Speech Examples",
            )
        )
    elif case.prompt_library == "base" and field_id == FieldId.FIRST_MES:
        issues.extend(validate_first_message_behavior(text))

    banned_markers = ["using literature as foreplay", "omegaverse", "alpha-beta-omega"]
    lowered = text.lower()
    for marker in banned_markers:
        if marker in lowered:
            issues.append(f"{field_id.display_name} included banned drift marker: {marker}")
    return issues


def run_live_case(
    paths: AppPaths,
    case: PromptTestCase,
    fixtures_root: Path,
) -> tuple[dict[FieldId, str], list[str]]:
    settings = load_runtime_settings(paths)
    engine = GenerationEngine(APIClient(settings))
    prompt_set = load_prompt_set(paths, case.prompt_library, case.prompt_set)
    outputs: dict[FieldId, str] = {}
    extra_context = build_reference_context(paths, case, fixtures_root)
    issues: list[str] = []

    for field_id in prompt_set.ordered_fields():
        content = engine.generate_field(
            prompt_set=prompt_set,
            field_id=field_id,
            inputs=case.inputs,
            outputs=outputs,
            direct_name=case.direct_name,
            extra_context=extra_context,
        )
        outputs[field_id] = content
        issues.extend(validate_generated_output(case, field_id, content))
    return outputs, issues
