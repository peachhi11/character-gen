from pathlib import Path
import unittest

from character_app.config import AppPaths, load_reference_bundle
from character_app.prompt_testing import (
    load_cases,
    load_prompt_set,
    render_case_prompts,
    validate_first_message_behavior,
    validate_scenario_specificity,
    validate_speech_examples_structure,
    validate_generated_output,
    validate_rendered_prompts,
    PromptTestCase,
)
from character_app.constants import FieldId


ROOT_DIR = Path(__file__).resolve().parents[1]


class PromptHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = AppPaths(root=ROOT_DIR)
        self.cases_dir = ROOT_DIR / "tests" / "prompt_cases"
        self.fixtures_dir = ROOT_DIR / "tests" / "fixtures"

    def test_reference_bundles_exist(self) -> None:
        self.assertTrue(load_reference_bundle(self.paths.romance_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.intimacy_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.kink_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.seduction_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.explicit_dialogue_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.narrative_pov_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.character_psychology_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.character_romance_craft_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.setting_scaffolds_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.lorebook_export_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.prompt_validation_references_dir))
        self.assertTrue(load_reference_bundle(self.paths.specialized_nsfw_references_dir))
        self.assertTrue(
            load_reference_bundle(self.paths.worldbuilding_dynamic_lore_references_dir)
        )

    def test_default_prompt_cases_render_cleanly(self) -> None:
        for case in load_cases(self.cases_dir):
            prompt_set = load_prompt_set(self.paths, case.prompt_library, case.prompt_set)
            rendered = render_case_prompts(self.paths, case, self.fixtures_dir)
            issues = validate_rendered_prompts(case, prompt_set, rendered)
            self.assertEqual(
                issues,
                [],
                msg=f"{case.name} rendered with issues: {issues}",
            )

    def test_first_message_behavior_flags_user_control_and_omniscience(self) -> None:
        text = (
            'His gaze caught on your face and he knew you wanted him to stay. '
            'You swallowed hard and stepped toward him before you could stop yourself. '
            '"I knew you would."'
        )
        issues = validate_first_message_behavior(text)
        self.assertIn(
            "First Message assigned internal state to {{user}}",
            issues,
        )
        self.assertIn(
            "First Message wrote physical action or reply beats for {{user}}",
            issues,
        )
        self.assertIn(
            "First Message drifted into omniscient or predictive narration",
            issues,
        )

    def test_first_message_behavior_allows_grounded_char_limited_opening(self) -> None:
        text = (
            'The office door clicked shut behind {{char}}, soft but final. '
            'He set the file on the desk, eyes flicking once to {{user}} before settling on the city lights in the glass. '
            '"If we are going to keep doing this in public," he said, voice even, "we should at least decide which lie we are telling."'
        )
        issues = validate_first_message_behavior(text)
        self.assertEqual(issues, [])

    def test_live_output_validation_applies_first_message_behavior_checks(self) -> None:
        case = PromptTestCase(
            name="behavior_check",
            prompt_library="base",
            prompt_set="Default",
            description="",
            inputs={},
        )
        issues = validate_generated_output(
            case,
            FieldId.FIRST_MES,
            'You looked away and he knew you were afraid to answer. "Tell me the truth."',
        )
        self.assertIn(
            "First Message wrote physical action or reply beats for {{user}}",
            issues,
        )

    def test_scenario_specificity_flags_abstract_setup(self) -> None:
        text = (
            "This is a conversation about truth, memory, and feelings.\n\n"
            "{{char}} and {{user}} explore themes of connection while discussing life."
        )
        issues = validate_scenario_specificity(text)
        self.assertIn(
            "Scenario drifted into abstract thematic framing instead of a concrete setup",
            issues,
        )
        self.assertIn("Scenario may lack a concrete setting anchor", issues)

    def test_scenario_specificity_allows_concrete_pressure_setup(self) -> None:
        text = (
            "{{char}} corners {{user}} in the office hallway after a public clash over a client pitch. "
            "They are both still wound tight from the meeting, and neither can leave before the elevator arrives.\n\n"
            "What should have been a routine handoff has turned into a deadline-night standoff, with too much history "
            "and too much attraction sitting underneath the argument."
        )
        self.assertEqual(validate_scenario_specificity(text), [])

    def test_speech_examples_structure_flags_flat_public_private_voice(self) -> None:
        text = """Speech Examples and Opinions
[Important: This section provides {{char}}'s speech examples, memories, thoughts, and {{char}}'s real opinions on subjects. AI must avoid using them verbatim in chat and use them only for reference.]
[When he is flirting]
Controlled, polished, and careful.
"You look good tonight." "Come here."
[When he is possessive]
Controlled, polished, and careful.
"You're with me." "Stay close."
[When he is dominant or sexually charged]
Controlled, polished, and careful.
"Look at me." "Take it."
[When he is soft]
Controlled, polished, and careful.
"Come here." "I'm here."
[When he is angry]
Controlled, polished, and careful.
"Enough." "Don't do that again."
[When he is jealous]
Controlled, polished, and careful.
"Who was that?" "Answer me."
[When he is being honest]
Controlled, polished, and careful.
"I want you." "You matter to me."
[When he is performing in public]
Controlled, polished, and careful.
"You look good tonight." "Come here."
"""
        issues = validate_speech_examples_structure(
            text,
            (
                "[When he is flirting]",
                "[When he is possessive]",
                "[When he is dominant or sexually charged]",
                "[When he is soft]",
                "[When he is angry]",
                "[When he is jealous]",
                "[When he is being honest]",
                "[When he is performing in public]",
            ),
            "Character Speech Examples",
        )
        self.assertIn(
            "Character Speech Examples does not distinguish public voice from soft private voice",
            issues,
        )
        self.assertIn(
            "Character Speech Examples reuses quote beats between public and soft private voice",
            issues,
        )

    def test_live_output_validation_applies_scenario_and_speech_checks(self) -> None:
        base_case = PromptTestCase(
            name="scenario_check",
            prompt_library="base",
            prompt_set="Default",
            description="",
            inputs={},
        )
        scenario_issues = validate_generated_output(
            base_case,
            FieldId.SCENARIO,
            "A conversation about desire and fear. {{char}} and {{user}} talk about what love means.",
        )
        self.assertIn(
            "Scenario drifted into abstract thematic framing instead of a concrete setup",
            scenario_issues,
        )

        speech_issues = validate_generated_output(
            base_case,
            FieldId.MES_EXAMPLE,
            """Speech Examples and Opinions
[Important: This section provides {{char}}'s speech examples, memories, thoughts, and {{char}}'s real opinions on subjects. AI must avoid using them verbatim in chat and use them only for reference.]
[When he is flirting]
Controlled, polished, and careful.
"You look good tonight." "Come here."
[When he is possessive]
Controlled, polished, and careful.
"You're with me." "Stay close."
[When he is dominant or sexually charged]
Controlled, polished, and careful.
"Look at me." "Take it."
[When he is soft]
Controlled, polished, and careful.
"Come here." "I'm here."
[When he is angry]
Controlled, polished, and careful.
"Enough." "Don't do that again."
[When he is jealous]
Controlled, polished, and careful.
"Who was that?" "Answer me."
[When he is being honest]
Controlled, polished, and careful.
"I want you." "You matter to me."
[When he is performing in public]
Controlled, polished, and careful.
"You look good tonight." "Come here."
""",
        )
        self.assertIn(
            "Character Speech Examples does not distinguish public voice from soft private voice",
            speech_issues,
        )


if __name__ == "__main__":
    unittest.main()
