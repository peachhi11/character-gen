from __future__ import annotations

import asyncio
import unittest

from character_app.runtime_state import EngineStateCard, TropeStorageController
from character_app.trope_morph_parser import TropeTransitionMorphParser
from character_app.trope_pooling_system import (
    MultiUserTropeSessionPool,
    TropeEventHookManager,
)
from character_app.trope_transition_parser import TropeTransitionParser


class AdvancedTropeRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = TropeStorageController(storage_directory=".")
        self.max_clamping_limit = 5
        self.min_clamping_limit = 0

    def test_second_chance_baggage_conversion_limits(self) -> None:
        session = EngineStateCard(
            card_id="second_chance_asset",
            engine_type="Second-Chance",
        )
        session.weights.update(
            {
                "past_breakup_baggage": 1,
                "protective_pride_shield": 2,
                "residual_heartbreak": 2,
                "angst_meter": 3,
            }
        )

        hurt_reduction_factor = 2
        reduced_hurt = session.weights["past_breakup_baggage"] - hurt_reduction_factor
        self.storage.modify_metric_weight(session, "past_breakup_baggage", reduced_hurt)
        self.storage.modify_metric_weight(
            session,
            "protective_pride_shield",
            session.weights["protective_pride_shield"] - 1,
        )

        self.assertEqual(session.weights["past_breakup_baggage"], 0)
        self.assertGreaterEqual(session.weights["past_breakup_baggage"], 0)
        self.assertEqual(session.weights["protective_pride_shield"], 1)

    def test_forbidden_romance_exposure_deadlock_prevention(self) -> None:
        session = EngineStateCard(
            card_id="forbidden_asset",
            engine_type="Forbidden-Romance",
        )
        session.weights.update(
            {
                "systemic_restraint": 5,
                "stolen_proximity": 3,
                "fear_of_exposure": 5,
                "angst_meter": 4,
                "distance_locked": True,
            }
        )

        is_isolated_room = True
        if is_isolated_room:
            self.storage.modify_metric_weight(
                session,
                "stolen_proximity",
                session.weights["stolen_proximity"] + 1,
            )
            self.storage.modify_metric_weight(
                session,
                "fear_of_exposure",
                session.weights["fear_of_exposure"] - 1,
            )

        self.assertEqual(session.weights["stolen_proximity"], 4)
        self.assertEqual(session.weights["fear_of_exposure"], 4)
        self.assertTrue(session.weights["distance_locked"])

    def test_fake_dating_transition_maps_into_forbidden_romance(self) -> None:
        mapped = TropeTransitionParser.transition_fake_dating_to_forbidden(
            {
                "performative_closeness": 4,
                "private_confusion": 3,
                "boundary_panic": 2,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
            }
        )

        self.assertEqual(mapped["systemic_restraint"], 3)
        self.assertEqual(mapped["stolen_proximity"], 4)
        self.assertEqual(mapped["fear_of_exposure"], 4)
        self.assertEqual(mapped["angst_meter"], 4)
        self.assertTrue(mapped["lie_active"])
        self.assertTrue(mapped["distance_locked"])

    def test_fake_dating_pool_trigger_advances_phase_four(self) -> None:
        session = EngineStateCard(
            card_id="fake_dating_asset",
            engine_type="Fake-Dating",
        )
        session.weights.update(
            {
                "performative_closeness": 4,
                "private_confusion": 3,
                "boundary_panic": 2,
                "lie_active": True,
                "lie_count": 1,
            }
        )
        pool = MultiUserTropeSessionPool(
            event_manager=TropeEventHookManager(),
            storage_controller=self.storage,
        )
        pool.register_user_session("user_alpha", session)

        updated = asyncio.run(
            pool.execute_metric_mutation(
                user_id="user_alpha",
                session_id=session.session_id,
                metric_key="private_confusion",
                new_value=4,
            )
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.current_phase, 4)
        self.assertEqual(updated.weights["private_confusion"], 4)

    def test_tortured_hero_pool_trigger_supports_inverse_threshold(self) -> None:
        session = EngineStateCard(
            card_id="tortured_hero_asset",
            engine_type="Tortured-Hero",
        )
        session.weights.update(
            {
                "internal_trauma": 5,
                "emotional_detachment": 2,
                "rescue_resistance": 3,
                "angst_meter": 4,
            }
        )
        pool = MultiUserTropeSessionPool(
            event_manager=TropeEventHookManager(),
            storage_controller=self.storage,
        )
        pool.register_user_session("user_alpha", session)

        updated = asyncio.run(
            pool.execute_metric_mutation(
                user_id="user_alpha",
                session_id=session.session_id,
                metric_key="emotional_detachment",
                new_value=1,
            )
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.current_phase, 4)
        self.assertEqual(updated.weights["emotional_detachment"], 1)

    def test_matchmaker_to_partner_best_friend_transformation_bounds(self) -> None:
        mock_active_session = {
            "session_id": "sess_wingman_9921",
            "card_id": "maya_v3_asset",
            "engine_type": "Matchmaker-Crush",
            "current_phase": 1,
            "weights": {
                "performative_guidance": 4,
                "proxy_resentment": 3,
                "internal_frictional_heat": 4,
                "angst_meter": 2,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            },
            "chat_history": [],
        }

        parser = TropeTransitionMorphParser()
        morphed_card, prompt_override = (
            parser.morph_matchmaker_to_partners_best_friend(mock_active_session)
        )

        self.assertEqual(morphed_card["engine_type"], "Partner-Best-Friend")
        self.assertEqual(morphed_card["current_phase"], 2)

        weights = morphed_card["weights"]
        self.assertEqual(weights["loyalty_guilt"], 4)
        self.assertEqual(weights["repressed_fixation"], 3)
        self.assertEqual(weights["forbidden_proximity"], 5)
        self.assertTrue(weights["lie_active"])
        self.assertEqual(weights["lie_count"], 1)
        self.assertIn("[TROPE SYSTEM CRITICAL TRANSITION", prompt_override)


if __name__ == "__main__":
    unittest.main()
