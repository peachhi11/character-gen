from __future__ import annotations

import unittest

from character_app.legacy_v1_parser import LegacyV1CardParser


class LegacyV1ParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = LegacyV1CardParser()

    def test_upgrades_rival_profile_to_v3_meet_ugly(self) -> None:
        payload = """
        {
          "name": "Rival Analyst",
          "description": "An incredibly arrogant, high-friction data engineer. They hate losing.",
          "personality": "Sarcastic, fiercely competitive, defensive about their output metrics.",
          "scenario": "Trapped late working inside the local data server room layout.",
          "first_mes": "Step away from that monitor. You're messing up my pipeline code configurations."
        }
        """

        upgraded = self.parser.parse_and_upgrade_v1(payload)

        self.assertEqual(upgraded["spec"], "chara_card_v3")
        self.assertEqual(
            upgraded["extensions"]["trope_engine"]["engine_type"], "Meet-Ugly"
        )
        self.assertIn("rivalry_heat", upgraded["extensions"]["trope_engine"]["weights"])

    def test_upgrades_neutral_profile_to_v3_meet_cute(self) -> None:
        payload = """
        {
          "name": "Neighborhood Friend",
          "description": "Warm, approachable, always nearby.",
          "personality": "Soft-spoken and dependable.",
          "scenario": "A familiar morning coffee stop."
        }
        """

        upgraded = self.parser.parse_and_upgrade_v1(payload)

        self.assertEqual(
            upgraded["extensions"]["trope_engine"]["engine_type"], "Meet-Cute"
        )
        self.assertIn(
            "platonic_trust", upgraded["extensions"]["trope_engine"]["weights"]
        )


if __name__ == "__main__":
    unittest.main()
