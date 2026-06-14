"""Local FastAPI app for the browser UI."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.model_catalog import MODEL_CHOICES, QUALITY_PROFILES
from app.remix_runner import (
    RemixRequest,
    create_plan,
    list_runs,
    load_plan,
    preflight_status,
    run_live,
    user_error_message,
)
from app.services import styles

app = FastAPI(title="ShortsMoneyPrinter", version="0.1.0")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = PROJECT_ROOT / "web" / "dist"
WEB_INDEX = WEB_DIST / "index.html"


class StartRequest(BaseModel):
    max_cost: float = Field(gt=0)


# Tracks runs with a live worker so a second start can't race on the same files.
_active_runs: set[str] = set()
_active_lock = threading.Lock()

# Close an idle event stream after this many seconds with no plan changes.
_STREAM_IDLE_TIMEOUT = 1800


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if WEB_INDEX.exists():
        return HTMLResponse(WEB_INDEX.read_text(encoding="utf-8"))
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>ShortsMoneyPrinter</title>
            <style>
              body {
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                background: #f7f7f4;
                color: #202124;
                font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              }
              main {
                width: min(560px, calc(100vw - 32px));
                background: #fff;
                border: 1px solid #d9ddd6;
                border-radius: 8px;
                padding: 24px;
              }
              code {
                background: #f0f4f3;
                border-radius: 4px;
                padding: 2px 5px;
              }
            </style>
          </head>
          <body>
            <main>
              <h1>ShortsMoneyPrinter</h1>
              <p>The React UI has not been built yet.</p>
              <p>Run <code>cd web && npm install && npm run build</code>, then restart <code>smp serve</code>.</p>
              <p>The API is still available under <code>/api</code>.</p>
            </main>
          </body>
        </html>
        """
    )


@app.get("/assets/{path:path}")
def web_assets(path: str) -> FileResponse:
    asset = (WEB_DIST / "assets" / path).resolve()
    asset_root = (WEB_DIST / "assets").resolve()
    if not asset.is_file() or asset_root not in asset.parents:
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(asset)


@app.get("/vite.svg")
def vite_svg() -> FileResponse:
    asset = WEB_DIST / "vite.svg"
    if not asset.exists():
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(asset)


@app.post("/api/runs/plan")
def api_plan(request: RemixRequest):
    try:
        return create_plan(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=user_error_message(exc)) from exc


@app.post("/api/runs/{run_id}/start")
def api_start(run_id: str, request: StartRequest):
    try:
        load_plan(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    with _active_lock:
        if run_id in _active_runs:
            raise HTTPException(status_code=409, detail="run already in progress")
        _active_runs.add(run_id)

    def _worker() -> None:
        try:
            run_live(run_id, request.max_cost)
        except Exception:
            pass
        finally:
            with _active_lock:
                _active_runs.discard(run_id)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return {"run_id": run_id, "status": "running"}


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str):
    try:
        return load_plan(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/runs/{run_id}/events")
def api_events(run_id: str):
    def stream():
        last = ""
        idle = 0
        while True:
            try:
                plan = load_plan(run_id)
            except FileNotFoundError:
                yield "event: error\ndata: unknown run\n\n"
                return
            except Exception:
                yield "event: error\ndata: could not read run state\n\n"
                return
            payload = plan.model_dump_json()
            if payload != last:
                yield f"data: {payload}\n\n"
                last = payload
                idle = 0
            else:
                # Comment line: keeps proxies alive and surfaces client disconnects
                # (the next yield raises GeneratorExit once the browser is gone).
                yield ": keepalive\n\n"
                idle += 1
            if plan.status in {"done", "failed"}:
                return
            if idle >= _STREAM_IDLE_TIMEOUT:
                yield "event: error\ndata: stream timed out\n\n"
                return
            time.sleep(1.0)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/runs/{run_id}/final.mp4")
def api_final(run_id: str):
    try:
        plan = load_plan(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not plan.final_path or not Path(plan.final_path).exists():
        raise HTTPException(status_code=404, detail="final video is not ready")
    return FileResponse(plan.final_path, media_type="video/mp4", filename=f"{run_id}.mp4")


@app.get("/api/runs/{run_id}/source.mp4")
def api_source(run_id: str):
    try:
        plan = load_plan(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not plan.source_path or not Path(plan.source_path).exists():
        raise HTTPException(status_code=404, detail="source video is not ready")
    return FileResponse(plan.source_path, media_type="video/mp4", filename=f"{run_id}-source.mp4")


@app.get("/api/runs")
def api_list_runs():
    return list_runs()


@app.get("/api/preflight")
def api_preflight():
    return preflight_status()


@app.get("/api/models")
def api_models():
    return [QUALITY_PROFILES[key].to_api() for key in MODEL_CHOICES]


@app.get("/api/styles")
def api_styles():
    return [
        {"key": key, "label": styles.get(key).label, "kids": styles.get(key).kids}
        for key in styles.keys()
    ]


@app.get("/{path:path}", response_model=None)
def web_fallback(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="not found")
    requested = (WEB_DIST / path).resolve()
    if WEB_DIST.resolve() in requested.parents and requested.is_file():
        return FileResponse(requested)
    if WEB_INDEX.exists():
        return HTMLResponse(WEB_INDEX.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="web UI has not been built")
