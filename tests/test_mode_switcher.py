from __future__ import annotations

import unittest

from character_app.mode_switcher import TropeModeSwitcher


class TropeModeSwitcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.switcher = TropeModeSwitcher()

    def test_identifies_and_upgrades_v2_payload(self) -> None:
        payload = {
            "spec": "chara_card_v2",
            "data": {
                "name": "Maya Lin (Legacy)",
                "description": "Maya is your childhood friend character prompt details...",
                "extensions": {
                    "trope_engine": {
                        "engine_type": "Meet-Cute",
                        "weights": {
                            "platonic_trust": 4,
                            "romantic_awareness": 1,
                            "angst_meter": 0,
                            "lie_active": False,
                            "lie_count": 0,
                            "distance_locked": False,
                        },
                    }
                },
            },
        }

        detected, normalized = self.switcher.identify_and_normalize_payload(payload)

        self.assertEqual(detected, "CHARACTER_CARD_V2")
        self.assertEqual(normalized["spec"], "chara_card_v3")
        self.assertEqual(
            normalized["extensions"]["trope_engine"]["engine_type"],
            "Meet-Cute",
        )

    def test_identifies_native_v3_payload(self) -> None:
        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "ccv3_test",
            "name": "Julian Vance",
            "extensions": {"trope_engine": {"engine_type": "Meet-Ugly"}},
        }

        detected, normalized = self.switcher.identify_and_normalize_payload(payload)

        self.assertEqual(detected, "CHARACTER_CARD_V3")
        self.assertEqual(normalized["id"], "ccv3_test")

    def test_identifies_engine_state_payload_and_rehydrates_preview(self) -> None:
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

        detected, normalized = self.switcher.identify_and_normalize_payload(payload)

        self.assertEqual(detected, "ENGINE_STATE_CARD")
        self.assertEqual(normalized["spec"], "chara_card_v3")
        self.assertEqual(
            normalized["name"], "State Preview Session: sess_user_9921"
        )
        self.assertTrue(
            normalized["extensions"]["trope_engine"]["weights"]["distance_locked"]
        )


if __name__ == "__main__":
    unittest.main()
