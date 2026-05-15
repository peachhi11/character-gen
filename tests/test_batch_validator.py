from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from character_app.batch_validator import (
    VALID_ENGINES,
    BatchValidatorDashboardUI,
    scan_schema_directory,
)
from character_app.card_format_conversion import wrap_trope_engine_card_as_v3
from character_app.engine_state_card_tropes import (
    BUCKET_SUBGROUP_AVAILABLE_PRESETS,
    NO_PRESET_YET_ENGINE_TYPES,
    bucket_for_engine,
)
from character_app.engine_state_card_presets import build_engine_state_card
from character_app.trope_engine_catalog import ENGINE_OPTION_ORDER


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


class BatchValidatorCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scan_schema_directory_reports_pass_fail_and_corruption(self) -> None:
        (self.root / "valid.json").write_text(
            json.dumps(
                wrap_trope_engine_card_as_v3(
                    build_engine_state_card("Blind-Date-Mixup")
                )
            ),
            encoding="utf-8",
        )
        (self.root / "invalid.json").write_text(
            json.dumps(
                {
                    "spec": "chara_card_v3",
                    "name": "Broken Profile",
                    "extensions": {"trope_engine": {"engine_type": "Blind-Date-Mixup"}},
                }
            ),
            encoding="utf-8",
        )
        (self.root / "broken.json").write_text("{ bad json", encoding="utf-8")

        report, logs = scan_schema_directory(str(self.root), VALID_ENGINES)

        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual(report["scanned"], 3)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(report["failed_validation"], 1)
        self.assertEqual(report["corrupted"], 1)
        self.assertTrue(any("[PASS]" in line for line in logs))
        self.assertTrue(any("[FAIL VALIDATION]" in line for line in logs))
        self.assertTrue(any("[MALFORMED STREAM]" in line for line in logs))

    def test_scan_schema_directory_returns_empty_when_no_json_exists(self) -> None:
        (self.root / "README.md").write_text("nothing here", encoding="utf-8")

        report, logs = scan_schema_directory(str(self.root), VALID_ENGINES)

        self.assertEqual(report["status"], "EMPTY")
        self.assertTrue(any("zero .json data records" in line for line in logs))

    def test_scan_schema_directory_can_report_cancelled(self) -> None:
        for index in range(3):
            (self.root / f"valid_{index}.json").write_text(
                json.dumps(
                    wrap_trope_engine_card_as_v3(
                        build_engine_state_card("Blind-Date-Mixup", card_id=f"card_{index}")
                    )
                ),
                encoding="utf-8",
            )

        calls = 0

        def cancel_check() -> bool:
            nonlocal calls
            calls += 1
            return calls > 1

        from character_app.batch_validator import _scan_directory_impl

        report, logs = _scan_directory_impl(
            str(self.root),
            VALID_ENGINES,
            cancel_check=cancel_check,
        )

        self.assertEqual(report["status"], "CANCELLED")
        self.assertEqual(report["scanned"], 1)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(report["failed_validation"], 0)
        self.assertEqual(report["corrupted"], 0)
        self.assertTrue(any("[SYSTEM CANCEL]" in line for line in logs))

    def test_bucketed_taxonomy_maps_recent_engine_families(self) -> None:
        self.assertEqual(
            bucket_for_engine("Babysitter"),
            ("WORKPLACE", "Services (Domestic)"),
        )
        self.assertEqual(
            bucket_for_engine("Love-Letter-Lunacy"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Coffee-Shop-Regular"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Strangers-to-Lovers"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Blank-Page"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Routine-Synchronicity"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Opaque-Inversion"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Rebound-Infatuation"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Lost-Found"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Screwball-Comedy"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Partners-In-Crime"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("One-Sided-Cute"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Institutional-Rivalry"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Mistaken-Identity"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Cage-Match-Entry"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Two-Ships-Passing"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Double-Booking"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Digital-Seek"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Wrong-Table"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Enclosed-Transit"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Critical-Intersect"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Cosmic-Anchor"),
            ("MODERN_REALITY", "First Meet"),
        )
        self.assertEqual(
            bucket_for_engine("Vacation-Countdown"),
            ("MODERN_REALITY", "Travel"),
        )
        self.assertEqual(
            bucket_for_engine("Billionaire-Playboy"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Prank-Paranoia"),
            ("MODERN_REALITY", "Everyday"),
        )
        self.assertEqual(
            bucket_for_engine("Twenty-Five-Benchmark"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Ten-Year-Void"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Adult-Strangers-Shift"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Climax-Reconnect"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Foundling-Track"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Coach-Athlete"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Cross-Campus"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Probation-Alliance"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Benchwarmer-Hustle"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Rival-Captains"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Shared-Roots"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Repeating-Intersect"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Sports-Roommate"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Corporate-Playmaker"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Charitable-Proxy"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Algorithmic-Drive"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Lineage-Shield"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Retainer-Date"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Starlet-Shield"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Older-Hero-Younger-Heroine"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Older-Heroine-Younger-Hero"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Grumpy-Veteran-Rookie"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Crown-Advisor"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Century-Void"),
            ("MODERN_REALITY", "Social"),
        )
        self.assertEqual(
            bucket_for_engine("Platonic-Denial"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Guardian-Ward"),
            ("RELATIONSHIPS", "Family"),
        )
        self.assertEqual(
            bucket_for_engine("Taboo-Betrayal"),
            ("RELATIONSHIPS", "Family"),
        )
        self.assertEqual(
            bucket_for_engine("Matchmaker-Crush"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Himbo-Earnest"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Legal-Lock-in"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Ancestral-Lock"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Martyr-Shield-Pact"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Betrayal-Grovel"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Blackmail-Date"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Jilted-Bride"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Cynical-Setup"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Group-Exposure"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Loyalty-Breakdown"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Bar-Tab-Wager"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Engineered-Trap"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Extorted-Target"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Undercover-Predator"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Proxy-Collapse"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Undercover-Sabotage"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Calculated-Sabotage"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Cynical-Wager"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Dare-Repentance"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Overt-Obsession"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Broken-Wingman"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Transactional-Truce"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Martyr-Shield-Crisis"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Public-Cover-Breach"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Proxy-Voice"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Ex-Best-Friend"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Erased-Barrier"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Accidental-Adultery"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Ghost-Marriage"),
            ("RELATIONSHIPS", "Betrayal"),
        )
        self.assertEqual(
            bucket_for_engine("Marital-Sham"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Second-Chance"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Accidental-Pregnancy"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Arranged-Marriage"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Ancestral-Truce"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Altar-Flight"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Runaway-Fiance"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Preserved-Grief"),
            ("RELATIONSHIPS", "Commitment"),
        )
        self.assertEqual(
            bucket_for_engine("Secret-Lovechild"),
            ("RELATIONSHIPS", "Family"),
        )
        self.assertEqual(
            bucket_for_engine("Bully-Romance"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Fake-Dating"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Fake-Relationship"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Forbidden-Romance"),
            ("RELATIONSHIPS", "Situationship"),
        )
        self.assertEqual(
            bucket_for_engine("Best-Friend-Triangle"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("Harem-Friends"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("MMF-Triad"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("MFM-Triad"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("MFF-Triad"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("Polyamory-Love"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("Tug-of-War-Triangle"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("Sovereign-Selection"),
            ("RELATIONSHIPS", "Poly"),
        )
        self.assertEqual(
            bucket_for_engine("Sibling-Partner"),
            ("RELATIONSHIPS", "Family"),
        )
        self.assertEqual(
            bucket_for_engine("Silver-Fox-Executive"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Collateral-Debt"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Boardroom-Betrayal"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Enemies-Boardroom"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Non-Disclosure-Mask"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Mentorship-Breach"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Hostile-Takeover"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Liquidation-Trap"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Legal-Mentorship"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Sandbox-Grudge"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Sandbox-Enemy"),
            ("WORKPLACE", "Corporate"),
        )
        self.assertEqual(
            bucket_for_engine("Underworld-High-Stakes"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Pack-Commander"),
            ("DARK", "Supernatural"),
        )
        self.assertEqual(
            bucket_for_engine("Sanctuary-Refuge"),
            ("DARK", "Supernatural"),
        )
        self.assertEqual(
            bucket_for_engine("Instinct-Override"),
            ("DARK", "Supernatural"),
        )
        self.assertEqual(
            bucket_for_engine("Bloodline-Obligation"),
            ("DARK", "Supernatural"),
        )
        self.assertEqual(
            bucket_for_engine("Grounding-Anchor"),
            ("DARK", "Supernatural"),
        )
        self.assertEqual(
            bucket_for_engine("Stripper-Performance"),
            ("DARK", "NSFW/Explicit"),
        )
        self.assertEqual(
            bucket_for_engine("Bondage-Restraint"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Luxury-Confinement"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Ransom-Bargain"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Corrupt-Detective"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Wiretap-Crisis"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Deep-Cover-Trap"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Blood-Truce"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Mafia-Syndicate"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Cartel-Isolation"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Witness-Protection"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Suburban-Mask"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Preserved-Identity"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Flight-Crisis"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("Guilt-Ridden-Anchor"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertEqual(
            bucket_for_engine("DDLG-Exchange"),
            ("DARK", "NSFW/Explicit"),
        )
        self.assertEqual(
            bucket_for_engine("Tactical-Infatuation"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Honeymoon-Trap"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Orphan-Pact"),
            ("DARK", "Underworld"),
        )
        self.assertEqual(
            bucket_for_engine("Instant-Castaway"),
            ("DARK", "Captivity/Protective"),
        )
        self.assertIn("Services (Domestic)", BUCKET_SUBGROUP_AVAILABLE_PRESETS["WORKPLACE"])
        self.assertIn("Babysitter", BUCKET_SUBGROUP_AVAILABLE_PRESETS["WORKPLACE"]["Services (Domestic)"])
        self.assertNotIn("Babysitter", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("First-Sight", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Meet-Crazy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Meet-Cute", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Meet-Ugly", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Strangers-to-Lovers", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Blank-Page", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Routine-Synchronicity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Opaque-Inversion", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Rebound-Infatuation", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Lost-Found", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cosmic-Anchor", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Opaque-Interlude", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Screwball-Comedy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Partners-In-Crime", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("One-Sided-Cute", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Institutional-Rivalry", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Mistaken-Identity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cage-Match-Entry", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Two-Ships-Passing", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Double-Booking", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Digital-Seek", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Wrong-Table", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Enclosed-Transit", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Critical-Intersect", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Volatile-Relapse", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("One-Night-Stand", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Legal-Lock-in", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Tactical-Infatuation", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Orphan-Pact", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Instant-Castaway", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Prank-Date", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cynical-Setup", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Group-Exposure", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Loyalty-Breakdown", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Bar-Tab-Wager", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Engineered-Trap", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Extorted-Target", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Undercover-Predator", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Prank-Paranoia", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Undercover-Sabotage", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Public-Cover-Breach", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Proxy-Voice", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Forced-Proximity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Friends-Benefits", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Hate-to-Love", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Hostile-Friction", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("No-Feelings", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Blackmail-Date", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Jilted-Bride", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Calculated-Sabotage", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cynical-Wager", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Altar-Flight", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Dare-Repentance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Overt-Obsession", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Collateral-Debt", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Preserved-Grief", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Broken-Wingman", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Transactional-Truce", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Martyr-Shield-Crisis", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ex-Best-Friend", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Sibling-Partner", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Guilt-Ridden-Anchor", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Erased-Barrier", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Boardroom-Betrayal", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Accidental-Adultery", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ghost-Marriage", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Second-Chance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Accidental-Pregnancy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Secret-Lovechild", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Marital-Sham", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Arranged-Marriage", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ancestral-Truce", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Preserved-Identity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Honeymoon-Trap", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Flight-Crisis", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Runaway-Fiance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("High-School-Sweethearts", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Childhood-Pact", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Twenty-Five-Benchmark", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ten-Year-Void", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Adult-Strangers-Shift", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Climax-Reconnect", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Foundling-Track", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Coach-Athlete", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cross-Campus", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Probation-Alliance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Benchwarmer-Hustle", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Rival-Captains", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Shared-Roots", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Sports-Roommate", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Sandbox-Enemy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Sandbox-Grudge", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Repeating-Intersect", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ancestral-Lock", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Martyr-Shield-Pact", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Jock-Tutor", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Roommate-Romance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Shared-Utility-Boundary", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Love-Neighbor", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Childhood-Reunion", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Friends-Lovers", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("New-Old-Flame", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ugly-Duckling", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Coffee-Shop-Regular", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Vacation-Countdown", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Platonic-Denial", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Matchmaker-Crush", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Relationship-Coach", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Secret-Relationship", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Tortured-Hero", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Unconscious-Bleed", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Instructional-Proximity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Martyr-Shield", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Best-Friend-Triangle", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Partner-Best-Friend", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Harem-Friends", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("MMF-Triad", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("MFM-Triad", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("MFF-Triad", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Polyamory-Love", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Side-Car-Jealousy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Tug-of-War-Triangle", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Sovereign-Selection", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Profile-Conflict", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Contractual-Heartbreak", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Flirt-Coach", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Proxy-Collapse", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Billionaire-Playboy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Boardroom-Parity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Clinical-Consult", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Co-Counsel", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Corporate-Playmaker", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Non-Disclosure-Mask", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Charitable-Proxy", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Algorithmic-Drive", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Lineage-Shield", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Hostile-Takeover", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Liquidation-Trap", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Luxury-Confinement", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Retainer-Date", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Starlet-Shield", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Age-Gap", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Older-Hero-Younger-Heroine", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Older-Heroine-Younger-Hero", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Grumpy-Veteran-Rookie", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Guardian-Ward", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Taboo-Betrayal", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Silver-Fox-Executive", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Mentorship-Breach", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Legal-Mentorship", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Enemies-Boardroom", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Crown-Advisor", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Century-Void", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Himbo-Earnest", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Soft-Alpha", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Pure-Devotion", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Earnest-Hustle", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Radiant-Optimizer", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Soft-Sanctuary", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Chivalric-Code", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("BDSM-Exchange", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Bondage-Restraint", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Captive-Captor", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Academic-Rivals", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Band-Brothers", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Mafia-Crime", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Mafia-Syndicate", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Street-Biker", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Bratva-Enforcer", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Corrupt-Detective", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Wiretap-Crisis", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Deep-Cover-Trap", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Blood-Truce", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cartel-Isolation", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Underworld-Medic", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Syndicate-Fixer", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Mob-Informant", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cyber-Hacker", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Rescue-Romance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("DDLG-Exchange", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Escort-Transaction", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Stockholm-Syndrome", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Collateral-Bride", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Bodyguard-Captivity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Bodyguard-Protection", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Caretaker-Infiltration", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Amnesia-Haven", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Vigilante-Justice", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Castaway-Survival", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Witness-Protection", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Suburban-Mask", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Inverted-Captivity", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Indentured-Servitude", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Ransom-Bargain", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Sex-Club", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Virgin-Auction", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Stripper-Performance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("The-Bet", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Bully-Romance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Fake-Dating", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Fake-Relationship", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Forbidden-Romance", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Boss-Employee", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Cooking-Show", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Doctor-Patient", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Lawyer-Client", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Office-Benefits", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Office-Rivals", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Step-Sibling", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Teacher-Parent", NO_PRESET_YET_ENGINE_TYPES)
        self.assertNotIn("Teacher-Student", NO_PRESET_YET_ENGINE_TYPES)
        self.assertEqual(
            [name for name in ENGINE_OPTION_ORDER if bucket_for_engine(name) is None],
            [],
        )

    def test_build_engine_state_card_supports_safe_professional_subset(self) -> None:
        for engine_type in (
            "Band-Brothers",
            "Friends-Lovers",
            "Partner-Best-Friend",
            "Academic-Rivals",
            "Boardroom-Parity",
            "Clinical-Consult",
            "Co-Counsel",
            "Cooking-Show",
            "Office-Benefits",
            "Office-Rivals",
            "Pack-Commander",
            "Sanctuary-Refuge",
            "Instinct-Override",
            "Bloodline-Obligation",
            "Grounding-Anchor",
            "Shared-Utility-Boundary",
            "Teacher-Parent",
        ):
            card = build_engine_state_card(engine_type)
            self.assertEqual(card["metadata"]["engine_type"], engine_type)

    def test_build_engine_state_card_reports_superseded_safe_equivalent_cleanly(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "intentionally superseded by safe equivalent 'Academic-Rivals'",
        ):
            build_engine_state_card("Teacher-Student")


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class BatchValidatorUITests(unittest.TestCase):
    def setUp(self) -> None:
        self.window = BatchValidatorDashboardUI()

    def tearDown(self) -> None:
        self.window.deleteLater()

    def test_dashboard_defaults_to_current_valid_engine_registry(self) -> None:
        self.assertIn("Teacher-Student", self.window.schema_registry)
        self.assertIn("Friends-Benefits", self.window.schema_registry)
        self.assertIn("Hostile-Friction", self.window.schema_registry)
        self.assertIn("Second-Chance", self.window.schema_registry)
        self.assertIn("Blind-Date-Mixup", self.window.schema_registry)
        self.assertIn("Workplace-Romance", self.window.schema_registry)
        self.assertIn("Underworld-High-Stakes", self.window.schema_registry)

    def test_handle_completion_renders_cancelled_summary_without_forcing_full_progress(self) -> None:
        self.window.progress_bar.setValue(42)
        self.window.run_btn.setText("ABORT VALIDATION PROCESS")
        self.window.run_btn.setEnabled(False)

        self.window.handle_completion(
            {
                "status": "CANCELLED",
                "scanned": 2,
                "passed": 1,
                "failed_validation": 1,
                "corrupted": 0,
            }
        )

        self.assertEqual(self.window.progress_bar.value(), 42)
        self.assertEqual(self.window.run_btn.text(), "ENGAGE SCHEMA VALIDATION RUN")
        self.assertTrue(self.window.run_btn.isEnabled())
        self.assertIn("AUDIT CANCELLED", self.window.console.toPlainText())

    def test_toggle_validation_disables_abort_button_until_worker_returns(self) -> None:
        self.window.target_folder = tempfile.gettempdir()

        class DummySignal:
            def connect(self, _callback) -> None:
                return None

        class DummyWorker:
            def __init__(self) -> None:
                self.progress_update = DummySignal()
                self.log_output = DummySignal()
                self.validation_complete = DummySignal()
                self.is_cancelled = False

            def isRunning(self) -> bool:
                return True

        self.window.worker = DummyWorker()

        self.window.toggle_validation()

        self.assertTrue(self.window.worker.is_cancelled)
        self.assertFalse(self.window.run_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
