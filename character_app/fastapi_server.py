from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from .api import APIClient
from .autosave_daemon import TropeAutosaveDaemon
from .cards import CharacterRepository
from .config import AppPaths, load_runtime_settings
from .db_sweep_pipeline import archive_stale_session_files
from .dialogue_triggers import DialogueTriggerEngine
from .live_chat_state import LiveChatLogAnalyzer
from .png_metadata_engine import PNGMetadataEngine
from .runtime_chat import RuntimeChatService
from .runtime_state import EngineStateCard, TropeStorageController
from .trope_dynamic_pivot import TropeDynamicPivotParser
from .trope_morph_parser import TropeTransitionMorphParser
from .trope_pooling_system import MultiUserTropeSessionPool, TropeEventHookManager


logger = logging.getLogger(__name__)


class ChatTurnRequest(BaseModel):
    session_id: str = Field(
        ..., description="Unique identifier for the active player session."
    )
    player_message: str = Field(..., description="The user's raw text input string.")
    ai_response: str | None = Field(
        default=None, description="The generated LLM completion string text output."
    )
    generate_model_response: bool = Field(
        default=False,
        description="When true, generate the character reply from the runtime prompt and chat history.",
    )
    card_payload: dict[str, Any] | None = Field(
        default=None,
        description="Optional engine-state payload or V2/V3 card payload to compile into the runtime system prompt.",
    )
    card_identifier: str | None = Field(
        default=None,
        description="Optional card file identifier or path used to load the source payload for runtime prompting.",
    )


class CreateSessionRequest(BaseModel):
    spec: Literal["chara_card_v3"] = Field(
        ..., description="The immutable Character Card V3 wrapper spec marker."
    )
    spec_version: Literal["3.0"] = Field(
        ..., description="The Character Card V3 schema version."
    )
    id: str = Field(
        ..., description="Unique global reference identifier of the template card."
    )
    name: str = Field(
        ..., description="Template character profile name."
    )
    extensions: dict[str, Any] = Field(
        ..., description="Wrapper extension mapping containing trope_engine."
    )


class EditorUpdateRequest(BaseModel):
    session_id: str = Field(..., description="Target runtime session container token.")
    metric_key: str = Field(
        ..., description="The specific weight key name string."
    )
    metric_value: Any = Field(
        ..., description="The target value configuration."
    )


class APIStatusResponse(BaseModel):
    status: str
    message: str
    session_id: str
    current_phase: int
    directive_signal: str | None = None
    ai_response: str | None = None
    trigger_action: str | None = None
    updated_weights: dict[str, Any]


class SessionStateResponse(BaseModel):
    status: str
    session_id: str
    card_id: str
    engine_type: str
    current_phase: int
    last_updated: float
    updated_weights: dict[str, Any]
    chat_history: list[dict[str, str]]


class SessionCreatedResponse(BaseModel):
    status: str
    message: str
    session_id: str
    card_id: str
    engine_type: str
    current_phase: int
    weights: dict[str, Any]


class TerminationResponse(BaseModel):
    status: str
    message: str
    session_id: str
    final_message_count: int


class PoolUpdateRequest(BaseModel):
    session_id: str = Field(..., description="Target session inside the user pool.")
    weight_key: str = Field(..., description="Metric key to mutate.")
    target_value: Any = Field(..., description="Target value for the metric mutation.")


class PoolUpdateResponse(BaseModel):
    status: str
    session_id: str
    current_phase: int
    weights: dict[str, Any]


class PoolStatusResponse(BaseModel):
    status: str
    active_sessions: dict[str, str]


class MorphRequest(BaseModel):
    session_id: str = Field(..., description="Target runtime session token.")


class PivotRequest(BaseModel):
    session_id: str = Field(..., description="Target runtime session token.")
    target_branch: Literal["Secret-Relationship", "Runaway-Fiance"] = Field(
        ...,
        description="Catalyst branch destination for a Fake-Relationship runtime session.",
    )


class MorphResponse(BaseModel):
    status: str
    message: str
    session_id: str
    engine_type: str
    current_phase: int
    injected_system_prompt_directive: str
    updated_weights: dict[str, Any]


def create_app(
    *,
    paths: AppPaths | None = None,
    storage_controller: TropeStorageController | None = None,
    chat_analyzer: LiveChatLogAnalyzer | None = None,
    autosave_daemon: TropeAutosaveDaemon | None = None,
    runtime_chat_service: RuntimeChatService | None = None,
    eviction_interval_seconds: int = 60,
    eviction_max_idle_seconds: int = 1800,
    archive_interval_hours: int = 24,
    archive_max_age_days: int = 7,
    analytics_url: str | None = None,
) -> FastAPI:
    resolved_paths = paths or AppPaths()
    resolved_storage = storage_controller or TropeStorageController(resolved_paths)
    resolved_analyzer = chat_analyzer or LiveChatLogAnalyzer()
    resolved_autosave = autosave_daemon or TropeAutosaveDaemon(
        storage_controller=resolved_storage,
        interval_turns=5,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_autosave.start()
        eviction_task = asyncio.create_task(
            _start_automated_eviction_loop(
                app,
                interval_seconds=eviction_interval_seconds,
                max_idle_seconds=eviction_max_idle_seconds,
            )
        )
        archive_task = asyncio.create_task(
            _start_database_archive_sweep_loop(
                app,
                interval_hours=archive_interval_hours,
                max_age_days=archive_max_age_days,
            )
        )
        try:
            yield
        finally:
            eviction_task.cancel()
            archive_task.cancel()
            try:
                await eviction_task
            except asyncio.CancelledError:
                pass
            try:
                await archive_task
            except asyncio.CancelledError:
                pass
            resolved_autosave.stop()

    app = FastAPI(
        title="Trope Engine Card Backend Pipeline",
        version="3.0.0",
        lifespan=lifespan,
    )

    app.state.paths = resolved_paths
    app.state.storage_controller = resolved_storage
    app.state.chat_analyzer = resolved_analyzer
    app.state.autosave_daemon = resolved_autosave
    app.state.runtime_chat_service = runtime_chat_service
    app.state.character_repository = CharacterRepository(resolved_paths)
    app.state.png_metadata_engine = PNGMetadataEngine()
    app.state.dialogue_trigger_engine = DialogueTriggerEngine()
    app.state.active_sessions: dict[str, EngineStateCard] = {}
    app.state.event_hook_manager = TropeEventHookManager(analytics_url)
    app.state.session_pool = MultiUserTropeSessionPool(
        event_manager=app.state.event_hook_manager,
        storage_controller=resolved_storage,
    )
    app.state.transition_morph_parser = TropeTransitionMorphParser()
    app.state.dynamic_pivot_parser = TropeDynamicPivotParser()

    @app.post(
        "/api/session/create",
        response_model=SessionCreatedResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_runtime_session(
        payload: CreateSessionRequest,
        x_user_id: str | None = Header(
            default=None,
            alias="X-User-Id",
            description="Optional user sandbox identifier for multi-user session pooling.",
        ),
    ) -> SessionCreatedResponse:
        trope_data = payload.extensions.get("trope_engine", {})
        if not isinstance(trope_data, dict) or not trope_data:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Validation Error: Input card is missing required "
                    "'extensions.trope_engine' parameters."
                ),
            )

        engine_type = trope_data.get("engine_type")
        if not isinstance(engine_type, str) or not engine_type.strip():
            raise HTTPException(
                status_code=400,
                detail="Validation Error: 'extensions.trope_engine.engine_type' must be a non-empty string.",
            )

        session = EngineStateCard(
            card_id=payload.id,
            engine_type=engine_type.strip(),
        )

        template_phase = trope_data.get("current_phase", 1)
        app.state.storage_controller.update_phase(session, template_phase)

        template_weights = trope_data.get("weights", {})
        if not isinstance(template_weights, dict):
            raise HTTPException(
                status_code=400,
                detail="Validation Error: 'extensions.trope_engine.weights' must be an object.",
            )

        for key, value in template_weights.items():
            if key not in session.weights:
                continue
            try:
                app.state.storage_controller.modify_metric_weight(
                    state_card=session,
                    key=key,
                    value=value,
                )
            except (KeyError, TypeError) as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation Error: {exc}",
                ) from exc

        app.state.active_sessions[session.session_id] = session
        if x_user_id:
            app.state.session_pool.register_user_session(x_user_id, session)

        return SessionCreatedResponse(
            status="SUCCESS",
            message=(
                "Volatile runtime session successfully compiled and cached away "
                "from template layer assets."
            ),
            session_id=session.session_id,
            card_id=session.card_id,
            engine_type=session.engine_type,
            current_phase=session.current_phase,
            weights=dict(session.weights),
        )

    @app.post(
        "/api/chat/turn",
        response_model=APIStatusResponse,
        status_code=status.HTTP_200_OK,
    )
    async def process_chat_turn(payload: ChatTurnRequest) -> APIStatusResponse:
        session = _resolve_session(app, payload.session_id)
        card_payload: dict[str, Any] | None = None

        ai_response = payload.ai_response
        if ai_response is None and payload.generate_model_response:
            card_payload = _resolve_card_payload(
                app,
                session=session,
                explicit_payload=payload.card_payload,
                explicit_identifier=payload.card_identifier,
            )
            runtime_chat_service = _resolve_runtime_chat_service(app)
            ai_response, _ = runtime_chat_service.generate_response(
                card_payload=card_payload,
                session=session,
                user_message=payload.player_message,
            )
        elif ai_response is None:
            raise HTTPException(
                status_code=400,
                detail="Either 'ai_response' must be provided or 'generate_model_response' must be true.",
            )

        current_state = dict(session.weights)
        current_state["current_phase"] = session.current_phase
        updated_state, directive_signal = app.state.chat_analyzer.analyze_message_turn(
            player_message=payload.player_message,
            ai_response=ai_response,
            current_state=current_state,
        )

        trigger_action: str | None = None
        trigger_signal = "CONTINUE_STANDARD_GENERATION"
        if card_payload is None:
            card_payload = _try_resolve_card_payload(
                app,
                session=session,
                explicit_payload=payload.card_payload,
                explicit_identifier=payload.card_identifier,
            )

        updated_weights = dict(updated_state)
        updated_phase = int(updated_weights.pop("current_phase", session.current_phase))

        if card_payload is not None:
            trigger_signal, trigger_payload = app.state.dialogue_trigger_engine.evaluate_all_active_triggers(
                card_payload,
                {
                    "current_phase": session.current_phase,
                    "weights": updated_weights,
                },
            )
            if trigger_payload is not None:
                ai_response = _compose_trigger_response(trigger_payload)
                trigger_action = trigger_payload.get("action")
                directive_signal = trigger_signal
                if trigger_signal == "EXECUTE_PHASE_4_BREAKING_POINT":
                    updated_phase = 4
                elif trigger_signal.startswith("EXECUTE_PHASE_5_"):
                    updated_phase = 5

        session.weights.update(updated_weights)
        app.state.storage_controller.update_phase(session, updated_phase)
        app.state.storage_controller.append_chat_message(
            session, "user", payload.player_message
        )
        app.state.storage_controller.append_chat_message(
            session, "character", ai_response
        )
        app.state.autosave_daemon.track_and_evaluate_message(session)

        return APIStatusResponse(
            status="SUCCESS",
            message="Chat log processed and relationship variables calculated.",
            session_id=session.session_id,
            current_phase=session.current_phase,
            directive_signal=directive_signal,
            ai_response=ai_response,
            trigger_action=trigger_action,
            updated_weights=dict(session.weights),
        )

    @app.post(
        "/api/editor/update",
        response_model=APIStatusResponse,
        status_code=status.HTTP_200_OK,
    )
    async def update_metric_via_editor(
        payload: EditorUpdateRequest,
    ) -> APIStatusResponse:
        session = _resolve_session(app, payload.session_id)

        try:
            session = app.state.storage_controller.modify_metric_weight(
                state_card=session,
                key=payload.metric_key,
                value=payload.metric_value,
            )
        except (KeyError, TypeError) as error_log:
            raise HTTPException(status_code=400, detail=str(error_log)) from error_log

        app.state.autosave_daemon.force_immediate_save(session)

        return APIStatusResponse(
            status="SUCCESS",
            message=f"Parameter metric '{payload.metric_key}' successfully updated via editor.",
            session_id=session.session_id,
            current_phase=session.current_phase,
            updated_weights=dict(session.weights),
        )

    @app.post(
        "/api/pool/update",
        response_model=PoolUpdateResponse,
        status_code=status.HTTP_200_OK,
    )
    async def update_pool_session_metric(
        payload: PoolUpdateRequest,
        x_user_id: str = Header(
            ...,
            alias="X-User-Id",
            description="Verified account user token ID.",
        ),
    ) -> PoolUpdateResponse:
        session = app.state.session_pool.get_session_context(
            user_id=x_user_id,
            session_id=payload.session_id,
            touch=True,
        )
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Resource Error: Requested pool session could not be verified.",
            )

        try:
            session = await app.state.session_pool.execute_metric_mutation(
                user_id=x_user_id,
                session_id=payload.session_id,
                metric_key=payload.weight_key,
                new_value=payload.target_value,
            )
        except (KeyError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Resource Error: Requested pool session could not be verified.",
            )

        return PoolUpdateResponse(
            status="SUCCESS",
            session_id=session.session_id,
            current_phase=session.current_phase,
            weights=dict(session.weights),
        )

    @app.get(
        "/api/pool/status",
        response_model=PoolStatusResponse,
        status_code=status.HTTP_200_OK,
    )
    async def get_pool_status() -> PoolStatusResponse:
        return PoolStatusResponse(
            status="SUCCESS",
            active_sessions={
                session_id: _session_sync_token(session)
                for session_id, session in app.state.active_sessions.items()
            },
        )

    @app.post(
        "/api/pool/morph-wingman",
        response_model=MorphResponse,
        status_code=status.HTTP_200_OK,
    )
    async def trigger_wingman_plot_twist_morph(
        payload: MorphRequest,
    ) -> MorphResponse:
        session = _resolve_session(app, payload.session_id, touch=False)

        try:
            morphed_dict, system_directive_prompt = (
                app.state.transition_morph_parser.morph_matchmaker_to_partners_best_friend(
                    session.to_dict()
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Internal conversion processor breakdown: {exc}",
            ) from exc

        morphed_session = EngineStateCard.from_dict(morphed_dict)
        app.state.active_sessions[payload.session_id] = morphed_session

        owner = app.state.session_pool.session_owners.get(payload.session_id)
        if owner:
            app.state.session_pool.register_user_session(owner, morphed_session)

        app.state.storage_controller.save_session_state(morphed_session)

        return MorphResponse(
            status="SUCCESS",
            message=(
                "Character card logic successfully migrated to forbidden relationship "
                "architecture variables."
            ),
            session_id=morphed_session.session_id,
            engine_type=morphed_session.engine_type,
            current_phase=morphed_session.current_phase,
            injected_system_prompt_directive=system_directive_prompt,
            updated_weights=dict(morphed_session.weights),
        )

    @app.post(
        "/api/pool/pivot-fake-relationship",
        response_model=MorphResponse,
        status_code=status.HTTP_200_OK,
    )
    async def trigger_fake_relationship_catalyst_pivot(
        payload: PivotRequest,
    ) -> MorphResponse:
        session = _resolve_session(app, payload.session_id, touch=False)

        try:
            morphed_dict, system_directive_prompt = (
                app.state.dynamic_pivot_parser.execute_catalyst_pivot(
                    session.to_dict(),
                    payload.target_branch,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Internal conversion processor breakdown: {exc}",
            ) from exc

        morphed_session = EngineStateCard.from_dict(morphed_dict)
        app.state.active_sessions[payload.session_id] = morphed_session

        owner = app.state.session_pool.session_owners.get(payload.session_id)
        if owner:
            app.state.session_pool.register_user_session(owner, morphed_session)

        app.state.storage_controller.save_session_state(morphed_session)

        return MorphResponse(
            status="SUCCESS",
            message=(
                "Character card logic successfully pivoted through the external "
                "plot catalyst branch."
            ),
            session_id=morphed_session.session_id,
            engine_type=morphed_session.engine_type,
            current_phase=morphed_session.current_phase,
            injected_system_prompt_directive=system_directive_prompt,
            updated_weights=dict(morphed_session.weights),
        )

    @app.get(
        "/api/session/{session_id}",
        response_model=SessionStateResponse,
        status_code=status.HTTP_200_OK,
    )
    async def get_session_state(session_id: str) -> SessionStateResponse:
        session = _resolve_session(app, session_id, touch=True)
        return SessionStateResponse(
            status="SUCCESS",
            session_id=session.session_id,
            card_id=session.card_id,
            engine_type=session.engine_type,
            current_phase=session.current_phase,
            last_updated=session.last_updated,
            updated_weights=dict(session.weights),
            chat_history=list(session.chat_history),
        )

    @app.delete(
        "/api/session/{session_id}",
        response_model=TerminationResponse,
        status_code=status.HTTP_200_OK,
    )
    async def terminate_active_session(session_id: str) -> TerminationResponse:
        active_sessions: dict[str, EngineStateCard] = app.state.active_sessions
        if session_id in active_sessions:
            session = active_sessions[session_id]
            message_count = len(session.chat_history)
            try:
                app.state.storage_controller.save_session_state(session)
                active_sessions.pop(session_id, None)
                app.state.session_pool.evict_session_from_all_pools(session_id)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=500,
                    detail=f"System error encountered during session teardown process: {exc}",
                ) from exc

            logger.info("Explicitly terminated session '%s'.", session_id)
            return TerminationResponse(
                status="SUCCESS",
                message="Active workspace session terminated successfully. Final progress committed to disk.",
                session_id=session_id,
                final_message_count=message_count,
            )

        try:
            cold_session = app.state.storage_controller.load_session_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Termination Error: Active session identifier '{session_id}' cannot be resolved.",
            ) from exc

        return TerminationResponse(
            status="SUCCESS",
            message="Session was already cold in RAM. Disk save file verified intact.",
            session_id=session_id,
            final_message_count=len(cold_session.chat_history),
        )

    return app


def _resolve_session(
    app: FastAPI,
    session_id: str,
    *,
    touch: bool = False,
) -> EngineStateCard:
    active_sessions: dict[str, EngineStateCard] = app.state.active_sessions
    if session_id in active_sessions:
        session = active_sessions[session_id]
        if touch:
            session.last_updated = time.time()
        return session

    try:
        session = app.state.storage_controller.load_session_state(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Active session identifier context '{session_id}' not found.",
        ) from exc

    if touch:
        session.last_updated = time.time()
    active_sessions[session_id] = session
    return session


def _resolve_runtime_chat_service(app: FastAPI) -> RuntimeChatService:
    service = app.state.runtime_chat_service
    if service is None:
        settings = load_runtime_settings(app.state.paths)
        service = RuntimeChatService(APIClient(settings))
        app.state.runtime_chat_service = service
    return service


def _resolve_card_payload(
    app: FastAPI,
    *,
    session: EngineStateCard,
    explicit_payload: dict[str, Any] | None,
    explicit_identifier: str | None,
) -> dict[str, Any]:
    if explicit_payload is not None:
        return explicit_payload

    identifier = explicit_identifier or session.card_id
    repository: CharacterRepository = app.state.character_repository
    path = _resolve_payload_path(repository, identifier)
    if path.suffix.lower() == ".png":
        return app.state.png_metadata_engine.extract_card_data(path.read_bytes())
    return repository.load_json_payload(path)


def _try_resolve_card_payload(
    app: FastAPI,
    *,
    session: EngineStateCard,
    explicit_payload: dict[str, Any] | None,
    explicit_identifier: str | None,
) -> dict[str, Any] | None:
    try:
        return _resolve_card_payload(
            app,
            session=session,
            explicit_payload=explicit_payload,
            explicit_identifier=explicit_identifier,
        )
    except HTTPException:
        return None


def _compose_trigger_response(trigger_payload: dict[str, str]) -> str:
    dialogue = trigger_payload.get("dialogue", "").strip()
    action = trigger_payload.get("action", "").strip()
    if dialogue and action:
        return f"{dialogue}\n\n{action}"
    return dialogue or action


def _resolve_payload_path(repository: CharacterRepository, identifier: str):
    from pathlib import Path

    if Path(identifier).is_absolute():
        path = Path(identifier)
        if path.exists():
            return path
        raise HTTPException(
            status_code=404,
            detail=f"Card payload source '{identifier}' could not be resolved.",
        )

    base = repository.directory / identifier
    if base.exists():
        return base
    if base.with_suffix(".json").exists():
        return base.with_suffix(".json")
    if base.with_suffix(".png").exists():
        return base.with_suffix(".png")
    raise HTTPException(
        status_code=404,
        detail=f"Card payload source '{identifier}' could not be resolved.",
    )


async def _start_automated_eviction_loop(
    app: FastAPI,
    *,
    interval_seconds: int = 60,
    max_idle_seconds: int = 1800,
) -> None:
    logger.info("Asynchronous Memory Eviction Loop engaged.")
    try:
        while True:
            await asyncio.sleep(max(1, int(interval_seconds)))
            _evict_idle_sessions_once(
                app,
                max_idle_seconds=max(1, int(max_idle_seconds)),
            )
    except asyncio.CancelledError:
        logger.info("Asynchronous Memory Eviction Loop cancelled.")
        raise


def _evict_idle_sessions_once(
    app: FastAPI,
    *,
    max_idle_seconds: int,
) -> list[str]:
    current_time = time.time()
    active_sessions: dict[str, EngineStateCard] = app.state.active_sessions
    eviction_targets: list[str] = []

    for session_id, session in list(active_sessions.items()):
        idle_duration = current_time - float(session.last_updated)
        if idle_duration > max_idle_seconds:
            eviction_targets.append(session_id)

    evicted: list[str] = []
    for session_id in eviction_targets:
        session = active_sessions.get(session_id)
        if session is None:
            continue
        try:
            snapshot = EngineStateCard.from_dict(deepcopy(session.to_dict()))
            app.state.storage_controller.save_session_state(snapshot)
            active_sessions.pop(session_id, None)
            app.state.session_pool.evict_session_from_all_pools(session_id)
            evicted.append(session_id)
            logger.info("Evicted idle session '%s' to disk cache.", session_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to evict idle session '%s': %s", session_id, exc)

    return evicted


async def _start_database_archive_sweep_loop(
    app: FastAPI,
    *,
    interval_hours: int = 24,
    max_age_days: int = 7,
) -> None:
    logger.info("Asynchronous Database Sweep and Archival Pipeline engaged.")
    try:
        while True:
            await asyncio.sleep(max(1, int(interval_hours)) * 3600)
            _archive_old_session_files_once(
                app,
                max_age_days=max(1, int(max_age_days)),
            )
    except asyncio.CancelledError:
        logger.info("Asynchronous Database Sweep and Archival Pipeline cancelled.")
        raise


def _archive_old_session_files_once(
    app: FastAPI,
    *,
    max_age_days: int,
) -> list[str]:
    report = archive_stale_session_files(
        app.state.storage_controller.storage_directory,
        max_age_days=max_age_days,
        active_session_ids=set(app.state.active_sessions.keys()),
    )
    for file_name in report.archived_files:
        logger.info("Archived cold session save '%s'.", file_name)
    for failed in report.failed_files:
        logger.error(
            "Failed to archive session save '%s': %s",
            Path(failed["file_path"]).name,
            failed["error"],
        )
    return report.archived_files


app = create_app()


def _session_sync_token(session: EngineStateCard) -> str:
    payload = json.dumps(session.to_dict(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
