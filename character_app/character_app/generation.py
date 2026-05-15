from __future__ import annotations

from .api import APIClient
from .constants import FieldId
from .models import PromptSet
from .prompts import render_prompt


class GenerationEngine:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def generate_field(
        self,
        prompt_set: PromptSet,
        field_id: FieldId,
        inputs: dict[FieldId, str],
        outputs: dict[FieldId, str],
        direct_name: bool = False,
        extra_context: dict[str, str] | None = None,
    ) -> str:
        if field_id == FieldId.NAME and direct_name and inputs.get(FieldId.NAME, "").strip():
            return inputs[FieldId.NAME].strip()

        template = prompt_set.templates.get(field_id)
        if not template:
            raise RuntimeError(f"No prompt template for {field_id.display_name}")

        missing = [
            required.display_name
            for required in template.required_fields
            if not outputs.get(required, "").strip()
        ]
        if missing:
            raise RuntimeError(
                f"{field_id.display_name} depends on missing fields: {', '.join(sorted(missing))}"
            )

        prompt = render_prompt(
            template,
            inputs.get(field_id, ""),
            outputs,
            extra_context=extra_context,
        )
        return self.api_client.generate(prompt)

    def generate_from(
        self,
        prompt_set: PromptSet,
        start_field: FieldId,
        inputs: dict[FieldId, str],
        outputs: dict[FieldId, str],
        direct_name: bool = False,
        extra_context: dict[str, str] | None = None,
    ) -> dict[FieldId, str]:
        ordered_fields = prompt_set.ordered_fields()
        if start_field not in ordered_fields:
            raise RuntimeError(f"{start_field.display_name} is not in the prompt order")

        start_index = ordered_fields.index(start_field)
        generated: dict[FieldId, str] = {}
        working_outputs = dict(outputs)
        for field_id in ordered_fields[start_index:]:
            content = self.generate_field(
                prompt_set=prompt_set,
                field_id=field_id,
                inputs=inputs,
                outputs=working_outputs,
                direct_name=direct_name,
                extra_context=extra_context,
            )
            working_outputs[field_id] = content
            generated[field_id] = content
        return generated
