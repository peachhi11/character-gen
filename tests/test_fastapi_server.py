from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest

from fastapi.testclient import TestClient

from character_app.autosave_daemon import TropeAutosaveDaemon
from character_app.config import AppPaths
from character_app.fastapi_server import (
    _archive_old_session_files_once,
    _evict_idle_sessions_once,
    create_app,
)
from character_app.runtime_chat import RuntimeChatService
from character_app.runtime_state import EngineStateCard, TropeStorageController


class FakeAPIClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_chat(
        self,
        *,
        system_prompt: str,
        chat_history: list[dict[str, str]],
        user_message: str,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "chat_history": list(chat_history),
                "user_message": user_message,
            }
        )
        return "You are entirely too close to my desk."


class FastAPIServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.storage_controller = TropeStorageController(self.paths)
        self.autosave_daemon = TropeAutosaveDaemon(
            storage_controller=self.storage_controller,
            interval_turns=1,
        )
        self.fake_api_client = FakeAPIClient()
        self.runtime_chat_service = RuntimeChatService(self.fake_api_client)
        self.app = create_app(
            paths=self.paths,
            storage_controller=self.storage_controller,
            autosave_daemon=self.autosave_daemon,
            runtime_chat_service=self.runtime_chat_service,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _make_saved_session(self) -> EngineStateCard:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.weights["rivalry_heat"] = 3
        self.storage_controller.save_session_state(session)
        return session

    def _make_engine_card_payload(self) -> dict:
        return {
            "card_id": "vance_v3_asset",
            "metadata": {
                "name": "Julian Vance",
                "archetype": "The Academic Ice-Wall",
                "engine_type": "Meet-Ugly",
                "current_phase": 1,
            },
            "trope_engine_weights": {
                "rivalry_heat": 4,
                "repressed_desire": 2,
                "fear_of_loss": 3,
                "angst_meter": 1,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            },
            "origin_context": {
                "environment_type": "University Library Archives",
                "incident_summary": "Stole the final critical thesis textbook copy.",
                "spark_token": "The research notes with coffee stains.",
                "unbreakable_tether": "Assigned as co-authors on the publication.",
            },
            "dialogue_nodes": {
                "phase_1_baseline": {
                    "greeting": "Oh, look. The resident expert arrived.",
                    "body_language_descriptor": "They do not look up from their laptop, but their typing speed accelerates sharply.",
                },
                "phase_4_breaking_point": {
                    "activation_condition": "romantic_tension >= 4",
                    "dialogue_payload": "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
                    "action_prompt": "They step directly into your space.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "A tactical error. Let's forget it.",
                    "if_player_honest": "Even now? When there's nothing left to hide behind?",
                },
            },
        }

    def _make_v3_wrapper_payload(self) -> dict:
        return {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "vance_v3_production_asset",
            "name": "Julian Vance",
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Ugly",
                    "current_phase": 3,
                    "weights": {
                        "rivalry_heat": 9,
                        "repressed_desire": 1,
                        "angst_meter": 2,
                        "lie_active": False,
                        "lie_count": 0,
                        "distance_locked": False,
                    },
                }
            },
        }

    def test_create_session_creates_active_runtime_state_from_v3_wrapper(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/session/create",
                json=self._make_v3_wrapper_payload(),
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["card_id"], "vance_v3_production_asset")
        self.assertEqual(payload["engine_type"], "Meet-Ugly")
        self.assertEqual(payload["current_phase"], 3)
        self.assertEqual(payload["weights"]["rivalry_heat"], 5)
        self.assertIn(payload["session_id"], self.app.state.active_sessions)

    def test_create_session_with_user_header_registers_session_in_user_pool(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/session/create",
                json=self._make_v3_wrapper_payload(),
                headers={"X-User-Id": "account_uid_user_alpha_77A"},
            )

        self.assertEqual(response.status_code, 201)
        session_id = response.json()["session_id"]
        pooled = self.app.state.session_pool.get_session_context(
            user_id="account_uid_user_alpha_77A",
            session_id=session_id,
            touch=False,
        )
        self.assertIsNotNone(pooled)

    def test_create_session_rejects_missing_trope_engine_block(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/session/create",
                json={
                    "spec": "chara_card_v3",
                    "spec_version": "3.0",
                    "id": "broken_card",
                    "name": "Broken Card",
                    "extensions": {},
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("extensions.trope_engine", response.json()["detail"])

    def test_get_session_returns_saved_state(self) -> None:
        session = self._make_saved_session()

        with TestClient(self.app) as client:
            response = client.get(f"/api/session/{session.session_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_id"], session.session_id)
        self.assertEqual(payload["card_id"], "vance_v3_asset")
        self.assertIn("last_updated", payload)
        self.assertEqual(payload["updated_weights"]["rivalry_heat"], 3)

    def test_get_session_rehydrates_evicted_disk_state_back_into_ram(self) -> None:
        session = self._make_saved_session()
        self.app.state.active_sessions.pop(session.session_id, None)

        with TestClient(self.app) as client:
            response = client.get(f"/api/session/{session.session_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(session.session_id, self.app.state.active_sessions)
        self.assertEqual(response.json()["session_id"], session.session_id)

    def test_evict_idle_sessions_persists_and_removes_ram_cache_entry(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.chat_history.append({"role": "user", "content": "hello"})
        session.last_updated = time.time() - 4000
        self.app.state.active_sessions[session.session_id] = session

        evicted = _evict_idle_sessions_once(self.app, max_idle_seconds=1800)

        self.assertEqual(evicted, [session.session_id])
        self.assertNotIn(session.session_id, self.app.state.active_sessions)
        reloaded = self.storage_controller.load_session_state(session.session_id)
        self.assertEqual(reloaded.chat_history[0]["content"], "hello")

    def test_delete_session_saves_final_state_and_clears_ram(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.chat_history.extend(
            [
                {"role": "user", "content": "hello"},
                {"role": "character", "content": "hi"},
            ]
        )
        self.app.state.active_sessions[session.session_id] = session

        with TestClient(self.app) as client:
            response = client.delete(f"/api/session/{session.session_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["final_message_count"], 2)
        self.assertNotIn(session.session_id, self.app.state.active_sessions)
        reloaded = self.storage_controller.load_session_state(session.session_id)
        self.assertEqual(len(reloaded.chat_history), 2)

    def test_delete_session_returns_success_for_cold_disk_session(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.chat_history.append({"role": "user", "content": "persisted"})
        self.storage_controller.save_session_state(session)

        with TestClient(self.app) as client:
            response = client.delete(f"/api/session/{session.session_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["final_message_count"], 1)
        self.assertIn("already cold in RAM", payload["message"])

    def test_archive_old_session_files_once_zips_and_removes_cold_json(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        file_path = self.storage_controller.save_session_state(session)
        stale_time = time.time() - (9 * 86400)
        Path(file_path).touch()
        import os
        os.utime(file_path, (stale_time, stale_time))

        archived = _archive_old_session_files_once(self.app, max_age_days=7)

        self.assertEqual(archived, [Path(file_path).name])
        self.assertFalse(Path(file_path).exists())
        archive_dir = self.paths.runtime_saves_dir / "archives"
        archives = list(archive_dir.glob("archive_batch_*.zip"))
        self.assertTrue(archives)

    def test_pool_update_mutates_user_scoped_session_and_fires_phase_shift_event(self) -> None:
        with TestClient(self.app) as client:
            create_response = client.post(
                "/api/session/create",
                json=self._make_v3_wrapper_payload(),
                headers={"X-User-Id": "account_uid_user_alpha_77A"},
            )
            self.assertEqual(create_response.status_code, 201)
            session_id = create_response.json()["session_id"]

            response = client.post(
                "/api/pool/update",
                json={
                    "session_id": session_id,
                    "weight_key": "romantic_tension",
                    "target_value": 4,
                },
                headers={"X-User-Id": "account_uid_user_alpha_77A"},
            )
            self.assertEqual(response.status_code, 200)
            time.sleep(0.05)

        payload = response.json()
        self.assertEqual(payload["current_phase"], 4)
        self.assertEqual(payload["weights"]["romantic_tension"], 4)
        dispatched = self.app.state.event_hook_manager.dispatched_events
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0]["event_type"], "PHASE_SHIFT_BREAKING_POINT_4")
        self.assertEqual(dispatched[0]["user_id"], "account_uid_user_alpha_77A")

    def test_pool_update_rejects_cross_user_session_access(self) -> None:
        with TestClient(self.app) as client:
            create_response = client.post(
                "/api/session/create",
                json=self._make_v3_wrapper_payload(),
                headers={"X-User-Id": "user_A"},
            )
            self.assertEqual(create_response.status_code, 201)
            session_id = create_response.json()["session_id"]

            response = client.post(
                "/api/pool/update",
                json={
                    "session_id": session_id,
                    "weight_key": "romantic_tension",
                    "target_value": 4,
                },
                headers={"X-User-Id": "user_B"},
            )

        self.assertEqual(response.status_code, 404)

    def test_pool_status_returns_sync_tokens_for_active_sessions(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.weights["rivalry_heat"] = 4
        self.app.state.active_sessions[session.session_id] = session

        with TestClient(self.app) as client:
            response = client.get("/api/pool/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertIn(session.session_id, payload["active_sessions"])
        self.assertTrue(payload["active_sessions"][session.session_id])

    def test_morph_wingman_transitions_matchmaker_session_and_persists(self) -> None:
        session = EngineStateCard(
            card_id="maya_v3_asset",
            engine_type="Matchmaker-Crush",
        )
        session.weights.update(
            {
                "performative_guidance": 4,
                "proxy_resentment": 3,
                "internal_frictional_heat": 4,
                "angst_meter": 2,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
        )
        self.app.state.active_sessions[session.session_id] = session
        self.app.state.session_pool.register_user_session("user_alpha", session)

        with TestClient(self.app) as client:
            response = client.post(
                "/api/pool/morph-wingman",
                json={"session_id": session.session_id},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["engine_type"], "Partner-Best-Friend")
        self.assertEqual(payload["current_phase"], 2)
        self.assertEqual(payload["updated_weights"]["loyalty_guilt"], 4)
        self.assertEqual(payload["updated_weights"]["forbidden_proximity"], 5)
        self.assertTrue(payload["updated_weights"]["lie_active"])
        self.assertIn("CRACKED WINGMAN MASK", payload["injected_system_prompt_directive"])

        updated = self.app.state.active_sessions[session.session_id]
        self.assertEqual(updated.engine_type, "Partner-Best-Friend")
        pooled = self.app.state.session_pool.get_session_context(
            user_id="user_alpha",
            session_id=session.session_id,
            touch=False,
        )
        self.assertIs(updated, pooled)
        reloaded = self.storage_controller.load_session_state(session.session_id)
        self.assertEqual(reloaded.engine_type, "Partner-Best-Friend")

    def test_morph_wingman_rejects_non_matchmaker_session(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.app.state.active_sessions[session.session_id] = session

        with TestClient(self.app) as client:
            response = client.post(
                "/api/pool/morph-wingman",
                json={"session_id": session.session_id},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Expected input 'Matchmaker-Crush'", response.json()["detail"])

    def test_fake_relationship_pivot_route_transitions_to_secret_relationship(self) -> None:
        session = EngineStateCard(
            card_id="vance_v3_asset",
            engine_type="Fake-Relationship",
        )
        session.weights.update(
            {
                "performative_closeness": 5,
                "private_confusion": 4,
                "boundary_panic_heat": 4,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            }
        )
        self.app.state.active_sessions[session.session_id] = session
        self.app.state.session_pool.register_user_session("user_alpha", session)

        with TestClient(self.app) as client:
            response = client.post(
                "/api/pool/pivot-fake-relationship",
                json={
                    "session_id": session.session_id,
                    "target_branch": "Secret-Relationship",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["engine_type"], "Secret-Relationship")
        self.assertEqual(payload["current_phase"], 5)
        self.assertEqual(payload["updated_weights"]["fear_of_exposure"], 5)
        self.assertTrue(payload["updated_weights"]["distance_locked"])
        self.assertIn("SHATTERED COVER", payload["injected_system_prompt_directive"])

        updated = self.app.state.active_sessions[session.session_id]
        self.assertEqual(updated.engine_type, "Secret-Relationship")
        reloaded = self.storage_controller.load_session_state(session.session_id)
        self.assertEqual(reloaded.engine_type, "Secret-Relationship")

    def test_fake_relationship_pivot_route_rejects_wrong_source_engine(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.app.state.active_sessions[session.session_id] = session

        with TestClient(self.app) as client:
            response = client.post(
                "/api/pool/pivot-fake-relationship",
                json={
                    "session_id": session.session_id,
                    "target_branch": "Runaway-Fiance",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Expected input 'Fake-Relationship'", response.json()["detail"])

    def test_chat_turn_updates_state_and_queues_autosave(self) -> None:
        session = self._make_saved_session()
        session.weights["romantic_tension"] = 3
        self.storage_controller.save_session_state(session)

        with TestClient(self.app) as client:
            response = client.post(
                "/api/chat/turn",
                json={
                    "session_id": session.session_id,
                    "player_message": "I step closer, leaning directly over your desk to read the report files.",
                    "ai_response": "Julian freezes completely, their breath catching as they stare up at your lips.",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["directive_signal"], "FORCE_PHASE_4_BREAKING_POINT")
            self.assertEqual(payload["current_phase"], 4)
            self.assertEqual(payload["updated_weights"]["romantic_tension"], 4)
            time.sleep(0.2)

        reloaded = self.storage_controller.load_session_state(session.session_id)
        self.assertEqual(reloaded.current_phase, 4)
        self.assertEqual(reloaded.weights["romantic_tension"], 4)
        self.assertEqual(len(reloaded.chat_history), 2)

    def test_editor_update_clamps_and_saves(self) -> None:
        session = self._make_saved_session()

        with TestClient(self.app) as client:
            response = client.post(
                "/api/editor/update",
                json={
                    "session_id": session.session_id,
                    "metric_key": "rivalry_heat",
                    "metric_value": 9,
                },
            )
            self.assertEqual(response.status_code, 200)
            time.sleep(0.2)

        reloaded = self.storage_controller.load_session_state(session.session_id)
        self.assertEqual(reloaded.weights["rivalry_heat"], 5)

    def test_missing_session_returns_404(self) -> None:
        with TestClient(self.app) as client:
            response = client.get("/api/session/sess_missing")
        self.assertEqual(response.status_code, 404)

    def test_chat_turn_can_generate_response_from_runtime_prompt(self) -> None:
        session = self._make_saved_session()
        session.current_phase = 3
        session.weights["rivalry_heat"] = 5
        session.weights["lie_active"] = True
        self.storage_controller.save_session_state(session)

        with TestClient(self.app) as client:
            response = client.post(
                "/api/chat/turn",
                json={
                    "session_id": session.session_id,
                    "player_message": "Can you pass me that file? You're blocking the light.",
                    "generate_model_response": True,
                    "card_payload": self._make_engine_card_payload(),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ai_response"], "You are entirely too close to my desk.")
        self.assertEqual(len(self.fake_api_client.calls), 1)
        captured_prompt = self.fake_api_client.calls[0]["system_prompt"]
        self.assertIn("Trope Engine Variant: Meet-Ugly", captured_prompt)
        self.assertIn("Narrative Phase: 3/6", captured_prompt)
        self.assertIn("rivalry_heat: 5", captured_prompt)
        self.assertIn("[CRITICAL CONSTRAINT] 'lie_active' is true", captured_prompt)

    def test_chat_turn_can_load_card_payload_from_repository_by_session_card_id(self) -> None:
        session = self._make_saved_session()
        card_path = self.paths.characters_dir / f"{session.card_id}.json"
        card_path.write_text(
            json.dumps(self._make_engine_card_payload(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

        with TestClient(self.app) as client:
            response = client.post(
                "/api/chat/turn",
                json={
                    "session_id": session.session_id,
                    "player_message": "You keep acting like this is only about the report.",
                    "generate_model_response": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ai_response"], "You are entirely too close to my desk.")
        self.assertEqual(len(self.fake_api_client.calls), 1)

    def test_chat_turn_overrides_generated_response_when_phase_four_trigger_fires(self) -> None:
        session = self._make_saved_session()
        session.weights["romantic_tension"] = 3
        self.storage_controller.save_session_state(session)

        with TestClient(self.app) as client:
            response = client.post(
                "/api/chat/turn",
                json={
                    "session_id": session.session_id,
                    "player_message": "I step closer, my breath catching as I refuse to break eye contact.",
                    "generate_model_response": True,
                    "card_payload": self._make_engine_card_payload(),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["directive_signal"], "EXECUTE_PHASE_4_BREAKING_POINT")
        self.assertEqual(payload["current_phase"], 4)
        self.assertIn("I don't hate you.", payload["ai_response"])
        self.assertEqual(payload["trigger_action"], "They step directly into your space.")

    def test_chat_turn_overrides_with_phase_five_denial_response(self) -> None:
        session = self._make_saved_session()
        session.current_phase = 4
        session.weights["romantic_tension"] = 4
        self.storage_controller.save_session_state(session)

        with TestClient(self.app) as client:
            response = client.post(
                "/api/chat/turn",
                json={
                    "session_id": session.session_id,
                    "player_message": "It was a mistake, an accident, nothing. Forget it.",
                    "ai_response": "They go perfectly still.",
                    "card_payload": self._make_engine_card_payload(),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["directive_signal"],
            "EXECUTE_PHASE_5_HANGOVER_CRISIS_DENIAL",
        )
        self.assertEqual(payload["current_phase"], 5)
        self.assertIn("A tactical error.", payload["ai_response"])
        self.assertIn("emotional wall of absolute deniability", payload["ai_response"])
        self.assertEqual(
            payload["trigger_action"],
            "[The character pulls back, building an emotional wall of absolute deniability.]",
        )


if __name__ == "__main__":
    unittest.main()
