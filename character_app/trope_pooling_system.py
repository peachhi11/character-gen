from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from .runtime_state import EngineStateCard, TropeStorageController
from .trope_engine_catalog import phase_four_trigger_satisfied


logger = logging.getLogger(__name__)

GLOBAL_PHASE_FOUR_TRIGGER_KEYS = frozenset({"romantic_tension"})


class TropeEventHookManager:
    def __init__(self, remote_analytics_url: str | None = None) -> None:
        self.analytics_url = remote_analytics_url
        self.dispatched_events: list[dict[str, Any]] = []

    async def dispatch_telemetry_event(
        self,
        *,
        event_type: str,
        user_id: str,
        session_id: str,
        current_weights: dict[str, Any],
    ) -> None:
        payload = {
            "event_id": f"evt_{int(time.time())}_{session_id[:4]}",
            "event_type": event_type,
            "timestamp": time.time(),
            "user_id": user_id,
            "session_id": session_id,
            "metrics_snapshot": dict(current_weights),
        }
        self.dispatched_events.append(payload)
        logger.info(
            "Hook triggered -> type='%s' user='%s' session='%s'",
            event_type,
            user_id,
            session_id,
        )

        if not self.analytics_url:
            return

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.analytics_url,
                    json=payload,
                    timeout=2.0,
                )
                if response.status_code != 200:
                    logger.warning(
                        "Remote analytics endpoint rejected hook payload with code %s",
                        response.status_code,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to broadcast event webhook payload: %s", exc)


class MultiUserTropeSessionPool:
    def __init__(
        self,
        *,
        event_manager: TropeEventHookManager,
        storage_controller: TropeStorageController,
    ) -> None:
        self.user_pools: dict[str, dict[str, EngineStateCard]] = {}
        self.session_owners: dict[str, str] = {}
        self.event_manager = event_manager
        self.storage_controller = storage_controller

    def register_user_session(self, user_id: str, session_card: EngineStateCard) -> None:
        previous_owner = self.session_owners.get(session_card.session_id)
        if previous_owner and previous_owner != user_id:
            self.evict_session_from_pool(previous_owner, session_card.session_id)

        self.user_pools.setdefault(user_id, {})[session_card.session_id] = session_card
        self.session_owners[session_card.session_id] = user_id
        logger.info(
            "Registered session '%s' under user sandbox '%s'.",
            session_card.session_id,
            user_id,
        )

    def get_session_context(
        self,
        *,
        user_id: str,
        session_id: str,
        touch: bool = True,
    ) -> EngineStateCard | None:
        session = self.user_pools.get(user_id, {}).get(session_id)
        if session is not None and touch:
            session.last_updated = time.time()
        return session

    def evict_session_from_pool(self, user_id: str, session_id: str) -> bool:
        if user_id not in self.user_pools or session_id not in self.user_pools[user_id]:
            return False

        del self.user_pools[user_id][session_id]
        self.session_owners.pop(session_id, None)
        if not self.user_pools[user_id]:
            del self.user_pools[user_id]
        return True

    def evict_session_from_all_pools(self, session_id: str) -> list[str]:
        owner = self.session_owners.get(session_id)
        if owner is None:
            return []
        removed = self.evict_session_from_pool(owner, session_id)
        return [owner] if removed else []

    async def execute_metric_mutation(
        self,
        *,
        user_id: str,
        session_id: str,
        metric_key: str,
        new_value: Any,
    ) -> EngineStateCard | None:
        session = self.get_session_context(
            user_id=user_id,
            session_id=session_id,
            touch=True,
        )
        if session is None:
            return None

        old_phase = session.current_phase
        self._assign_weight_value(session, metric_key, new_value)

        current_value = session.weights.get(metric_key)
        if old_phase < 4 and (
            (
                metric_key in GLOBAL_PHASE_FOUR_TRIGGER_KEYS
                and isinstance(current_value, int)
                and current_value >= 4
            )
            or phase_four_trigger_satisfied(
                session.engine_type,
                session.weights,
                metric_key=metric_key,
            )
        ):
            self.storage_controller.update_phase(session, 4)
            asyncio.create_task(
                self.event_manager.dispatch_telemetry_event(
                    event_type="PHASE_SHIFT_BREAKING_POINT_4",
                    user_id=user_id,
                    session_id=session_id,
                    current_weights=session.weights,
                )
            )

        return session

    def _assign_weight_value(
        self,
        session: EngineStateCard,
        metric_key: str,
        new_value: Any,
    ) -> None:
        if metric_key in session.weights:
            self.storage_controller.modify_metric_weight(
                state_card=session,
                key=metric_key,
                value=new_value,
            )
            return

        if isinstance(new_value, bool):
            session.weights[metric_key] = new_value
            session.last_updated = time.time()
            return

        try:
            int_value = int(new_value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"Value modifier for metric key '{metric_key}' must cast to numerical integer formats."
            ) from exc

        session.weights[metric_key] = max(0, min(5, int_value))
        session.last_updated = time.time()
