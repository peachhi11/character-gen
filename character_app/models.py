from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

from PIL import Image

from .constants import FieldId, is_supported_prompt_tag


@dataclass
class PromptTemplate:
    field: FieldId
    text: str
    order: int

    @property
    def required_fields(self) -> set[FieldId]:
        found: set[FieldId] = set()
        for tag in re.findall(r"{{(\w+)}}", self.text):
            if is_supported_prompt_tag(tag):
                continue
            try:
                found.add(FieldId(tag))
            except ValueError:
                continue
        return found


@dataclass
class PromptSet:
    name: str
    description: str = ""
    templates: dict[FieldId, PromptTemplate] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def ordered_fields(self) -> list[FieldId]:
        ordered = [
            template for template in self.templates.values() if template.order > 0
        ]
        ordered.sort(key=lambda template: template.order)
        return [template.field for template in ordered]

    def validate(self) -> bool:
        available: set[FieldId] = set()
        for field in self.ordered_fields():
            template = self.templates[field]
            if not template.required_fields.issubset(available):
                return False
            available.add(field)
        return True


@dataclass
class CharacterCard:
    name: str = ""
    fields: dict[FieldId, str] = field(
        default_factory=lambda: {field_id: "" for field_id in FieldId.ui_order()}
    )
    image_data: Image.Image | None = None
    alternate_greetings: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    creator: str = "Anonymous"
    version: str = "main"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def to_payload(self, template: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = template.copy() if template else {}
        data = dict(payload.get("data", {}))
        card_name = self.fields.get(FieldId.NAME, "").strip() or self.name
        data.update(
            {
                "name": card_name,
                "alternate_greetings": list(self.alternate_greetings),
                "tags": list(self.tags),
                "creator": self.creator,
                "character_version": self.version,
                "created_at": self.created_at.isoformat(),
                "modified_at": self.modified_at.isoformat(),
            }
        )
        for field_id in FieldId.ui_order():
            if field_id == FieldId.NAME:
                data[field_id.value] = card_name
            else:
                data[field_id.value] = self.fields.get(field_id, "")
        payload["data"] = data
        payload["spec"] = payload.get("spec", "chara_card_v2")
        payload["spec_version"] = payload.get("spec_version", "2.0")
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CharacterCard":
        data = payload.get("data", {})
        fields = {
            field_id: data.get(field_id.value, "") for field_id in FieldId.ui_order()
        }
        if not fields[FieldId.NAME].strip():
            fields[FieldId.NAME] = data.get("name", "")
        created_at = data.get("created_at")
        modified_at = data.get("modified_at")
        return cls(
            name=data.get("name", ""),
            fields=fields,
            alternate_greetings=list(data.get("alternate_greetings", [])),
            tags=list(data.get("tags", [])),
            creator=data.get("creator", "Anonymous"),
            version=data.get("character_version", "main"),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
            modified_at=datetime.fromisoformat(modified_at) if modified_at else datetime.now(),
        )
