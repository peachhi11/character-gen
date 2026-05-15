from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re

from .config import AppPaths
from .constants import FieldId, is_supported_prompt_tag
from .models import PromptSet, PromptTemplate


class PromptRepository:
    def __init__(self, paths: AppPaths, directory: Path | None = None):
        self.paths = paths
        self.directory = directory or self.paths.prompt_sets_dir
        self.paths.ensure_directories()

    def list_names(self) -> list[str]:
        self.directory.mkdir(parents=True, exist_ok=True)
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def load(self, name: str) -> PromptSet:
        file_path = self.directory / f"{name}.json"
        with file_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        templates: dict[FieldId, PromptTemplate] = {}
        prompts = raw.get("prompts", {})
        orders = raw.get("orders", {})
        for key, value in prompts.items():
            try:
                field_id = FieldId(key)
            except ValueError:
                continue
            prompt_text = value.get("text", "")
            validate_prompt_text(prompt_text)
            templates[field_id] = PromptTemplate(
                field=field_id,
                text=prompt_text,
                order=int(orders.get(key, 0)),
            )

        prompt_set = PromptSet(
            name=raw.get("name", name),
            description=raw.get("description", ""),
            templates=templates,
            created_at=datetime.fromisoformat(
                raw.get("created_at", datetime.now().isoformat())
            ),
            modified_at=datetime.fromisoformat(
                raw.get("modified_at", datetime.now().isoformat())
            ),
        )
        if not prompt_set.validate():
            raise RuntimeError(f"Prompt set '{name}' has invalid field dependencies")
        return prompt_set

    def save(self, prompt_set: PromptSet) -> None:
        prompt_set.modified_at = datetime.now()
        payload = {
            "name": prompt_set.name,
            "description": prompt_set.description,
            "created_at": prompt_set.created_at.isoformat(),
            "modified_at": prompt_set.modified_at.isoformat(),
            "prompts": {},
            "orders": {},
        }
        for field_id in FieldId.ui_order():
            template = prompt_set.templates.get(field_id)
            if not template:
                continue
            payload["prompts"][field_id.value] = {
                "text": template.text,
                "required_fields": [value.value for value in sorted(template.required_fields, key=lambda item: item.value)],
                "conditional_tags": [],
            }
            payload["orders"][field_id.value] = template.order

        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / f"{prompt_set.name}.json"
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)

    def create_empty(self, name: str, description: str = "") -> PromptSet:
        return PromptSet(name=name, description=description)


def validate_prompt_text(prompt_text: str) -> None:
    if prompt_text.count("{{if_input}}") != prompt_text.count("{{/if_input}}"):
        raise RuntimeError("Mismatched {{if_input}} tags")
    for tag in re.findall(r"{{(\w+)}}", prompt_text):
        if is_supported_prompt_tag(tag):
            continue
        FieldId(tag)


def render_prompt(
    template: PromptTemplate,
    input_text: str,
    outputs: dict[FieldId, str],
    extra_context: dict[str, str] | None = None,
) -> str:
    rendered = template.text

    if input_text.strip():
        rendered = re.sub(
            r"{{if_input}}(.*?){{/if_input}}",
            r"\1",
            rendered,
            flags=re.DOTALL,
        )
    else:
        rendered = re.sub(
            r"{{if_input}}.*?{{/if_input}}",
            "",
            rendered,
            flags=re.DOTALL,
        )

    rendered = rendered.replace("{{input}}", input_text)
    for field_id, value in outputs.items():
        rendered = rendered.replace(f"{{{{{field_id.value}}}}}", value)
    for key, value in (extra_context or {}).items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered.strip()
