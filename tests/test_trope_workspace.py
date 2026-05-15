from __future__ import annotations

import base64
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from character_app.config import AppPaths
from character_app.trope_engine_catalog import phase_four_activation_condition
if QApplication is not None:
    from character_app.ui import TropeWorkspaceTab, WORLD_THEME


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class TropeWorkspaceTabTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.paths = AppPaths(root=Path(self.temp_dir.name))
        self.paths.ensure_directories()
        self.tab = TropeWorkspaceTab(paths=self.paths, theme=WORLD_THEME)

    def tearDown(self) -> None:
        self.tab.deleteLater()
        self.temp_dir.cleanup()

    def test_sync_weights_interface_switches_engine_specific_metrics(self) -> None:
        self.tab.set_selected_engine("Meet-Crazy")

        self.assertIn("chaotic_chemistry", self.tab.metric_widgets)
        self.assertIn("adrenaline_level", self.tab.metric_widgets)
        self.assertNotIn("rivalry_heat", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_fake_dating_metrics(self) -> None:
        self.tab.set_selected_engine("Fake-Dating")

        self.assertIn("performative_closeness", self.tab.metric_widgets)
        self.assertIn("private_confusion", self.tab.metric_widgets)
        self.assertIn("boundary_panic", self.tab.metric_widgets)
        self.assertNotIn("chaotic_chemistry", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_arranged_marriage_metrics(self) -> None:
        self.tab.set_selected_engine("Arranged-Marriage")

        self.assertIn("contractual_lock", self.tab.metric_widgets)
        self.assertIn("clinical_politeness", self.tab.metric_widgets)
        self.assertIn("undercurrent_fixation", self.tab.metric_widgets)
        self.assertNotIn("performative_closeness", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_tortured_hero_metrics(self) -> None:
        self.tab.set_selected_engine("Tortured-Hero")

        self.assertIn("internal_trauma", self.tab.metric_widgets)
        self.assertIn("emotional_detachment", self.tab.metric_widgets)
        self.assertIn("rescue_resistance", self.tab.metric_widgets)
        self.assertNotIn("clinical_politeness", self.tab.metric_widgets)

    def test_superseded_step_sibling_selection_maps_to_safe_equivalent_metrics(self) -> None:
        self.tab.set_selected_engine("Step-Sibling")

        self.assertEqual(self.tab.combo_engine.currentData(), "Shared-Utility-Boundary")
        self.assertIn("domestic_forced_proximity", self.tab.metric_widgets)
        self.assertIn("shared_structural_overhead", self.tab.metric_widgets)
        self.assertIn("boundary_play_heat", self.tab.metric_widgets)
        self.assertNotIn("rivalry_heat", self.tab.metric_widgets)

    def test_superseded_teacher_student_selection_maps_to_safe_equivalent_metrics(self) -> None:
        self.tab.set_selected_engine("Teacher-Student")

        self.assertEqual(self.tab.combo_engine.currentData(), "Academic-Rivals")
        self.assertIn("academic_risk_factor", self.tab.metric_widgets)
        self.assertIn("hidden_proximity", self.tab.metric_widgets)
        self.assertIn("evaluation_panic", self.tab.metric_widgets)
        self.assertNotIn("domestic_forced_proximity", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_bdsm_exchange_boolean_flag(self) -> None:
        self.tab.set_selected_engine("BDSM-Exchange")

        self.assertIn("power_exchange_heat", self.tab.metric_widgets)
        self.assertIn("consent_restraint", self.tab.metric_widgets)
        self.assertIn("aftercare_safety", self.tab.metric_widgets)
        self.assertIn("safeword_breached", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_friends_benefits_metrics(self) -> None:
        self.tab.set_selected_engine("Friends-Benefits")

        self.assertIn("platonic_baseline_trust", self.tab.metric_widgets)
        self.assertIn("contractual_intimacy", self.tab.metric_widgets)
        self.assertIn("private_romantic_fixation", self.tab.metric_widgets)
        self.assertNotIn("academic_risk_factor", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_blind_date_mixup_metrics(self) -> None:
        self.tab.set_selected_engine("Blind-Date-Mixup")

        self.assertIn("identity_disorientation", self.tab.metric_widgets)
        self.assertIn("misdirected_spark", self.tab.metric_widgets)
        self.assertIn("embarrassed_curiosity", self.tab.metric_widgets)
        self.assertNotIn("platonic_baseline_trust", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_workplace_romance_metrics(self) -> None:
        self.tab.set_selected_engine("Workplace-Romance")

        self.assertIn("office_proximity", self.tab.metric_widgets)
        self.assertIn("professional_boundary", self.tab.metric_widgets)
        self.assertIn("career_risk", self.tab.metric_widgets)
        self.assertNotIn("identity_disorientation", self.tab.metric_widgets)

    def test_sync_weights_interface_supports_ust_slow_burn_metrics(self) -> None:
        self.tab.set_selected_engine("UST-Slow-Burn")

        self.assertIn("repressed_longing", self.tab.metric_widgets)
        self.assertIn("near_miss_heat", self.tab.metric_widgets)
        self.assertIn("restraint_fatigue", self.tab.metric_widgets)
        self.assertNotIn("office_proximity", self.tab.metric_widgets)

    def test_phase_four_condition_field_is_catalog_driven(self) -> None:
        self.tab.set_selected_engine("Meet-Ugly")

        self.assertTrue(self.tab.input_p4_condition.isReadOnly())
        self.assertEqual(
            self.tab.input_p4_condition.text(),
            phase_four_activation_condition("Meet-Ugly"),
        )
        self.assertIn("Catalog-driven", self.tab.input_p4_condition.toolTip())

    def test_engine_browser_tracks_bucket_and_group(self) -> None:
        self.tab.set_selected_engine("Babysitter")

        self.assertEqual(self.tab.combo_bucket.currentData(), "WORKPLACE")
        self.assertEqual(
            self.tab.combo_subgroup.currentData(),
            "Services (Domestic)",
        )
        self.assertEqual(self.tab.combo_engine.currentData(), "Babysitter")

    def test_compile_ui_to_json_refreshes_runtime_preview(self) -> None:
        self.tab.input_name.setText("Julian Vance")
        self.tab.input_description.setPlainText("An exacting academic rival.")
        self.tab.input_personality.setPlainText("The Academic Ice-Wall")
        self.tab.input_scenario.setPlainText("Late-night archive standoff.")
        self.tab.input_first_mes.setPlainText(
            "Oh, look. The resident expert arrived."
        )
        self.tab.input_mes_example.setPlainText(
            "They do not look up from their laptop, but their typing speed accelerates sharply."
        )
        self.tab.input_environment.setText("University Library Archives")
        self.tab.input_token.setText("The research notes with coffee stains.")
        self.tab.input_incident.setPlainText(
            "Stole the final critical thesis textbook copy."
        )
        self.tab.input_tether.setText(
            "Assigned as co-authors on the publication."
        )
        self.tab.input_p4_payload.setPlainText(
            "I don't hate you. I fight with you because it's the only time you look at me with absolute focus."
        )
        self.tab.input_p4_action.setText("They step directly into your space.")
        self.tab.input_p5_lied.setText("A tactical error. Let's forget it.")
        self.tab.input_p5_honest.setText(
            "Even now? When there's nothing left to hide behind?"
        )

        self.tab.compile_ui_to_json()

        self.assertIn('"spec": "chara_card_v3"', self.tab.terminal_output.toPlainText())
        self.assertIn(
            "[ROLEPLAY EMULATION ENGINE INSTRUCTIONS]",
            self.tab.prompt_preview.toPlainText(),
        )
        self.assertEqual(self.tab.validation_label.text(), "Runtime prompt valid")

    def test_execute_polymorphic_import_locks_core_fields_for_state_payload(self) -> None:
        payload = {
            "session_id": "sess_user_9921",
            "card_id": "julian_vance_v3",
            "engine_type": "Meet-Ugly",
            "current_phase": 4,
            "weights": {
                "rivalry_heat": 4,
                "repressed_desire": 3,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": True,
            },
            "chat_history": [],
        }

        self.tab.execute_polymorphic_import(payload)

        self.assertEqual(self.tab.mode_label.text(), "LIVE SESSION STATE ACTIVE")
        self.assertTrue(self.tab.input_name.isReadOnly())
        self.assertTrue(self.tab.input_description.isReadOnly())

    def test_trigger_import_can_read_png_wrapper_cards(self) -> None:
        from PIL import Image
        import io

        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "ccv3_fix_002_ugly",
            "name": "Julian Vance",
            "description": "An exacting academic rival.",
            "personality": "The Academic Ice-Wall",
            "scenario": "Late-night archive standoff.",
            "first_mes": "Oh, look. The resident expert arrived.",
            "mes_example": "They do not look up from their laptop.",
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Ugly",
                    "current_phase": 1,
                    "weights": {
                        "rivalry_heat": 4,
                        "repressed_desire": 1,
                        "angst_meter": 0,
                        "lie_active": False,
                        "lie_count": 0,
                        "distance_locked": False,
                    },
                    "origin_context": {
                        "environment_type": "Library",
                        "incident_summary": "Stole the last copy.",
                        "spark_token": "Coffee-stained notes.",
                        "unbreakable_tether": "Assigned co-authors.",
                    },
                    "dialogue_nodes": {
                        "phase_4_breaking_point": {
                            "activation_condition": "repressed_desire >= 4",
                            "dialogue_payload": "Look at me.",
                            "action_prompt": "They step into your space.",
                        },
                        "phase_5_hangover_crisis": {
                            "if_player_lied": "Let's forget it.",
                            "if_player_honest": "Even now?",
                        },
                    },
                }
            },
        }
        image = Image.new("RGBA", (64, 64), (255, 0, 0, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        png_path = self.paths.characters_dir / "wrapped_card.png"
        png_path.write_bytes(self.tab.png_metadata_engine.inject_card_data(buffer.getvalue(), payload))

        with patch(
            "character_app.ui.QFileDialog.getOpenFileName",
            return_value=(str(png_path), "PNG Files (*.png)"),
        ):
            self.tab.trigger_import()

        self.assertEqual(self.tab.input_name.text(), "Julian Vance")

    def test_process_import_path_can_read_json_cards(self) -> None:
        from PIL import Image

        image = Image.new("RGBA", (8, 8), (45, 128, 210, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "ccv3_fix_001_cute",
            "name": "Maya Lin",
            "description": "A childhood friend profile.",
            "personality": "Witty and protective.",
            "scenario": "Sharing old headphones.",
            "first_mes": "Put the earbud back in.",
            "mes_example": "She hides nerves behind humor.",
            "assets": [{"uri": f"data:image/png;base64,{encoded_image}"}],
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Cute",
                    "current_phase": 1,
                    "weights": {
                        "platonic_trust": 4,
                        "romantic_awareness": 1,
                        "fear_of_loss": 3,
                        "angst_meter": 0,
                        "lie_active": False,
                        "lie_count": 0,
                        "distance_locked": False,
                    },
                    "origin_context": {
                        "environment_type": "Treehouse",
                        "incident_summary": "Built a fort together.",
                        "spark_token": "A cracked keychain.",
                        "unbreakable_tether": "Years of shared routines.",
                    },
                    "dialogue_nodes": {
                        "phase_4_breaking_point": {
                            "activation_condition": "romantic_awareness >= 4",
                            "dialogue_payload": "Stop acting like this is normal.",
                            "action_prompt": "Her hand freezes over yours.",
                        },
                        "phase_5_hangover_crisis": {
                            "if_player_lied": "Let's pretend it was a weird night.",
                            "if_player_honest": "I don't want to go back.",
                        },
                    },
                }
            },
        }
        json_path = self.paths.characters_dir / "maya.json"
        json_path.write_text(__import__("json").dumps(payload), encoding="utf-8")

        self.tab.process_import_path(str(json_path))

        self.assertEqual(self.tab.input_name.text(), "Maya Lin")
        self.assertEqual(self.tab.mode_label.text(), "ASSET MODE: NATIVE CCV3")
        self.assertIsNotNone(self.tab.sprite_manager.image_canvas.pixmap())


if __name__ == "__main__":
    unittest.main()
