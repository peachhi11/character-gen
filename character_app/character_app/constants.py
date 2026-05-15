from __future__ import annotations

from enum import Enum


PASSTHROUGH_PROMPT_TAGS = frozenset(
    {
        "input",
        "if_input",
        "char",
        "user",
        "reference",
        "reference_notes",
        "char_card",
        "intimacy_reference",
        "kink_reference",
        "romance_reference",
        "seduction_reference",
        "explicit_dialogue_reference",
        "narrative_pov_reference",
        "character_psychology_reference",
        "character_romance_craft_reference",
        "setting_scaffolds_reference",
        "lorebook_export_reference",
        "prompt_validation_reference",
        "specialized_nsfw_reference",
        "worldbuilding_dynamic_lore_reference",
    }
)


class FieldId(str, Enum):
    NAME = "name"
    DESCRIPTION = "description"
    PERSONALITY = "personality"
    SCENARIO = "scenario"
    FIRST_MES = "first_mes"
    MES_EXAMPLE = "mes_example"

    @property
    def display_name(self) -> str:
        labels = {
            FieldId.NAME: "Name",
            FieldId.DESCRIPTION: "Description",
            FieldId.PERSONALITY: "Personality",
            FieldId.SCENARIO: "Scenario",
            FieldId.FIRST_MES: "First Message",
            FieldId.MES_EXAMPLE: "Speech Examples",
        }
        return labels[self]

    @property
    def input_placeholder(self) -> str:
        placeholders = {
            FieldId.NAME: "Enter name concept or direction...",
            FieldId.DESCRIPTION: "Enter description notes...",
            FieldId.PERSONALITY: "Enter personality direction...",
            FieldId.SCENARIO: "Enter scenario or relationship premise...",
            FieldId.FIRST_MES: "Enter opening-message direction...",
            FieldId.MES_EXAMPLE: "Enter speech-guide direction...",
        }
        return placeholders[self]

    @classmethod
    def ui_order(cls) -> list["FieldId"]:
        return [
            cls.NAME,
            cls.DESCRIPTION,
            cls.PERSONALITY,
            cls.SCENARIO,
            cls.FIRST_MES,
            cls.MES_EXAMPLE,
        ]


SAVE_FORMATS = ("json", "png")


def is_reference_field_tag(tag: str) -> bool:
    if not tag.startswith("char_"):
        return False
    try:
        FieldId(tag[len("char_") :])
    except ValueError:
        return False
    return True


def is_supported_prompt_tag(tag: str) -> bool:
    return tag in PASSTHROUGH_PROMPT_TAGS or is_reference_field_tag(tag)
