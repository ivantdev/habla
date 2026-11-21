"""Entrada FastAPI de la plataforma local. Ejecución con un proceso."""

from contextlib import asynccontextmanager
from typing import Annotated
import asyncio
import sqlite3

from fastapi import FastAPI, Query, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException

from .audio import AudioStore
from .config import LOCAL_ORIGINS, Settings
from .contracts import (
    AttemptList, Catalog, Comparison, CreatePractice, ErrorEnvelope, HistoryPage, Operation,
    Practice, Report, RetryCommand, StateCommand, Status, AnchorAttempt,
)
from .errors import PlatformError, not_found
from .fixtures import CATALOG, REFERENCES, platform_examples
from .history import History
from .http_uploads import read_anchor
from .identity import seed_base_user
from .orchestration import Clock, Orchestrator
from .storage import PracticeStore, SimulationRecords, connect
from .ws import serve_stream


API = "/api/v1"


def error_response(error: PlatformError) -> JSONResponse:
    return JSONResponse(
        ErrorEnvelope(error=error.body()).model_dump(mode="json", exclude_none=True), status_code=error.status,
        headers={"Cache-Control": "no-store"},
    )


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or Settings.from_env()
        with connect(config.data_dir) as db:
            actor = seed_base_user(db)
            store = PracticeStore(db, actor)
            audio = AudioStore(db, config.data_dir, actor)
            records = SimulationRecords(db)
            orchestrator = Orchestrator(config, store, audio, records, clock or Clock())
            orchestrator.reconcile()
            app.state.orchestrator = orchestrator
            app.state.history = History(store, audio)

            async def maintain():
                while True:
                    for _ in range(20):
                        orchestrator.tick()
                        await asyncio.sleep(0.1)
                    orchestrator.retry_cleanup()

            maintenance = asyncio.create_task(maintain())
            try:
                yield
            finally:
                maintenance.cancel()
                await asyncio.gather(maintenance, return_exceptions=True)
                await orchestrator.stop()

    app = FastAPI(title="¡Habla!", version="1.0", lifespan=lifespan)

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.url.hostname not in {"localhost", "127.0.0.1"}:
            return error_response(PlatformError(400, "INVALID_HOST", "Usa la dirección local de ¡Habla!."))
        if (origin is not None or request.method not in {"GET", "HEAD"}) and origin not in LOCAL_ORIGINS:
            return error_response(PlatformError(403, "ORIGIN_FORBIDDEN", "El origen de la petición no está permitido."))
        response = await call_next(request)
        if request.url.path.startswith(API):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(PlatformError)
    async def domain_error(_request, error):
        return error_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, error):
        if any(item["type"] == "json_invalid" for item in error.errors()):
            return error_response(PlatformError(400, "INVALID_JSON", "La petición JSON está mal formada."))
        return error_response(PlatformError(422, "INVALID_REQUEST", "Revisa los campos de la petición."))

    @app.exception_handler(HTTPException)
    async def http_error(_request, error):
        if error.status_code == 404:
            return error_response(not_found())
        return error_response(PlatformError(error.status_code, "HTTP_ERROR", "No se pudo atender la petición."))

    @app.exception_handler(OSError)
    @app.exception_handler(sqlite3.Error)
    async def storage_error(_request, _error):
        return error_response(PlatformError(503, "STORAGE_UNAVAILABLE", "No se pudo acceder al almacenamiento local."))

    def services(request: Request) -> Orchestrator:
        orchestrator = request.app.state.orchestrator
        orchestrator.tick()
        return orchestrator

    @app.get(f"{API}/health")
    async def health(request: Request):
        config = services(request).settings
        return {"status": "ok", "contract_version": "1", "mode": config.mode,
                "simulation": True, "scenario": config.scenario}

    @app.get(f"{API}/dev/fixtures")
    async def fixtures():
        return platform_examples()

    @app.get(f"{API}/catalog", response_model=Catalog)
    async def catalog():
        return CATALOG

    @app.post(f"{API}/practices", response_model=Practice, status_code=201)
    async def create(request: Request, command: CreatePractice):
        return services(request).create(command)

    @app.get(f"{API}/practices/{{practice_id}}", response_model=Practice)
    async def practice(request: Request, practice_id: str):
        return services(request).store.get(practice_id)

    @app.post(f"{API}/practices/{{practice_id}}/start", response_model=Practice)
    async def start(request: Request, practice_id: str, command: StateCommand):
        return services(request).start(practice_id, command.state_version)

    @app.post(f"{API}/practices/{{practice_id}}/cancel", response_model=Operation, status_code=202)
    async def cancel(request: Request, practice_id: str, command: StateCommand):
        return services(request).cancel(practice_id, command.state_version)

    @app.post(f"{API}/practices/{{practice_id}}/retry", response_model=Operation, status_code=202)
    async def retry(request: Request, practice_id: str, command: RetryCommand):
        return services(request).retry(practice_id, command)

    @app.get(f"{API}/practices/{{practice_id}}/anchor-attempts", response_model=AttemptList)
    async def attempts(request: Request, practice_id: str):
        orchestrator = services(request)
        orchestrator.store.get(practice_id)
        return AttemptList(items=orchestrator.records.attempts(practice_id))

    @app.post(f"{API}/practices/{{practice_id}}/anchor-attempts", response_model=AnchorAttempt, status_code=202)
    async def attempt(request: Request, practice_id: str):
        orchestrator = services(request)
        orchestrator.check_anchor_phase(practice_id)
        upload = await read_anchor(request, orchestrator.settings)
        return orchestrator.submit_anchor(practice_id, *upload)

    @app.get(f"{API}/practices/{{practice_id}}/report", response_model=Report)
    async def report(request: Request, practice_id: str):
        store = services(request).store
        draft = store.published(store.get(practice_id))
        if draft is None:
            raise PlatformError(409, "REPORT_NOT_READY", "El informe aún no está publicado.")
        return draft.report

    @app.get(f"{API}/history", response_model=HistoryPage)
    async def history(
        request: Request, cursor: Annotated[str | None, Query(max_length=256)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        services(request)
        return request.app.state.history.page(limit, cursor)

    @app.get(f"{API}/comparisons", response_model=Comparison)
    async def comparisons(
        request: Request, left: Annotated[str, Query(max_length=128)], right: Annotated[str, Query(max_length=128)],
    ):
        services(request)
        return request.app.state.history.compare(left, right)

    @app.get(f"{API}/audio/{{audio_id}}")
    async def audio(request: Request, audio_id: str):
        orchestrator = services(request)
        item = orchestrator.audio.get(audio_id)
        view = orchestrator.store.get(item.asset.practice_id)
        if (
            view.status != Status.COMPLETED or not view.report_id or item.asset.source != "anchor"
            or item.asset.status != "available" or not item.path.is_file()
        ):
            raise not_found()
        return FileResponse(item.path, media_type=item.asset.media_type)

    @app.get(f"{API}/references/{{audio_id}}")
    async def reference(audio_id: str):
        if audio_id not in REFERENCES:
            raise not_found()
        return Response(REFERENCES[audio_id], media_type="audio/wav")

    @app.websocket(f"{API}/practices/{{practice_id}}/stream")
    async def stream(socket: WebSocket, practice_id: str):
        await serve_stream(socket, practice_id, socket.app.state.orchestrator)

    return app


app = create_app()
