from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from character_app.db_migration_manager import TropeDatabaseMigrationManager


class TropeDatabaseMigrationManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_dir = self.root / "legacy_database_vault"
        self.output_dir = self.root / "upgraded_production_vault"
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_batch_migrates_nested_v2_cards_and_creates_backup(self) -> None:
        nested = self.source_dir / "subcategory"
        nested.mkdir(parents=True, exist_ok=True)
        source_path = nested / "maya_v2.json"
        source_path.write_text(
            json.dumps(
                {
                    "spec": "chara_card_v2",
                    "data": {
                        "name": "Maya Lin (Legacy Spec Asset)",
                        "description": "Maya is a childhood friend character template parameters profile...",
                        "personality": "Playful, sarcastic, fiercely protective",
                        "first_mes": "Hey, put the other earbud back in before I throw this pillow.",
                    },
                }
            ),
            encoding="utf-8",
        )

        manager = TropeDatabaseMigrationManager(create_backups=True)
        report = manager.batch_migrate_directory(self.source_dir, self.output_dir)

        migrated = self.output_dir / "subcategory" / "maya_v2.json"
        payload = json.loads(migrated.read_text(encoding="utf-8"))

        self.assertEqual(report["total_files_scanned"], 1)
        self.assertEqual(report["successful_upgrades"], 1)
        self.assertEqual(payload["spec"], "chara_card_v3")
        self.assertEqual(payload["name"], "Maya Lin (Legacy Spec Asset)")
        self.assertIn(
            "Automated-Database-Migration-V3", payload["group_tags"]
        )
        self.assertTrue(source_path.with_suffix(".json.bak").exists())

    def test_batch_uses_existing_trope_extension_when_present(self) -> None:
        source_path = self.source_dir / "julian.json"
        source_path.write_text(
            json.dumps(
                {
                    "spec": "chara_card_v2",
                    "data": {
                        "name": "Julian",
                        "description": "An academic rival.",
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
                                    "environment_type": "Lecture Hall",
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
                    },
                }
            ),
            encoding="utf-8",
        )

        manager = TropeDatabaseMigrationManager(create_backups=False)
        manager.batch_migrate_directory(self.source_dir, self.output_dir)

        migrated = json.loads(
            (self.output_dir / "julian.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            migrated["extensions"]["trope_engine"]["engine_type"], "Meet-Ugly"
        )
        self.assertEqual(
            migrated["extensions"]["trope_engine"]["weights"]["rivalry_heat"], 4
        )

    def test_batch_copies_non_v2_json_when_output_directory_differs(self) -> None:
        source_path = self.source_dir / "existing_v3.json"
        source_path.write_text(
            json.dumps(
                {
                    "spec": "chara_card_v3",
                    "spec_version": "3.0",
                    "id": "v3_existing",
                    "name": "Existing V3",
                    "extensions": {"trope_engine": {"engine_type": "Meet-Cute"}},
                }
            ),
            encoding="utf-8",
        )

        manager = TropeDatabaseMigrationManager(create_backups=False)
        report = manager.batch_migrate_directory(self.source_dir, self.output_dir)

        copied = self.output_dir / "existing_v3.json"
        self.assertTrue(copied.exists())
        self.assertEqual(report["successful_upgrades"], 0)

    def test_batch_counts_malformed_json_as_failure(self) -> None:
        source_path = self.source_dir / "broken.json"
        source_path.write_text("{ not valid json", encoding="utf-8")

        manager = TropeDatabaseMigrationManager(create_backups=False)
        report = manager.batch_migrate_directory(self.source_dir, self.output_dir)

        self.assertEqual(report["total_files_scanned"], 1)
        self.assertEqual(report["failed_parses"], 1)

    def test_batch_extracts_worldbook_entries_into_compiled_output(self) -> None:
        source_path = self.source_dir / "legacy_worldbook.entries"
        source_path.write_text(
            json.dumps(
                {
                    "entries": {
                        "a1": {
                            "keys": ["academy", "archives"],
                            "content": "The archive basement closes at midnight.",
                        },
                        "a2": {
                            "key": "julian, rival",
                            "entry": "Julian keeps annotated copies of everything.",
                        },
                    }
                }
            ),
            encoding="utf-8",
        )

        manager = TropeDatabaseMigrationManager(create_backups=False)
        report = manager.batch_migrate_directory(self.source_dir, self.output_dir)

        compiled = list(self.output_dir.glob("compiled_worldbook_*.json"))
        self.assertEqual(report["lore_nodes_compiled"], 2)
        self.assertEqual(len(compiled), 1)
        payload = json.loads(compiled[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["spec"], "worldbook_v1")
        self.assertEqual(len(payload["entries"]), 2)

    def test_batch_deduces_fake_dating_when_contract_language_is_present(self) -> None:
        source_path = self.source_dir / "public_contract.json"
        source_path.write_text(
            json.dumps(
                {
                    "spec": "chara_card_v2",
                    "data": {
                        "name": "Avery",
                        "description": "A fake date contract for publicity that starts to feel too real.",
                        "personality": "Sharp, charming, and panicked in private.",
                        "scenario": "They have to sell the script at every public gala.",
                        "first_mes": "Smile. They're watching.",
                    },
                }
            ),
            encoding="utf-8",
        )

        manager = TropeDatabaseMigrationManager(create_backups=False)
        manager.batch_migrate_directory(self.source_dir, self.output_dir)

        migrated = json.loads(
            (self.output_dir / "public_contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            migrated["extensions"]["trope_engine"]["engine_type"], "Fake-Dating"
        )
        self.assertEqual(
            migrated["extensions"]["trope_engine"]["dialogue_nodes"][
                "phase_4_breaking_point"
            ]["activation_condition"],
            "private_confusion >= 4",
        )


if __name__ == "__main__":
    unittest.main()
