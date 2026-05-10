from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from apps.api.crm_api.service import PIPELINE_STAGES, load_item_detail, load_pipeline


APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="CRM Pipeline Command Center")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    record_type: str = Query("all"),
    stage: str = Query("all"),
    active_only: bool = Query(True),
    attention_only: bool = Query(False),
) -> HTMLResponse:
    try:
        pipeline = load_pipeline(record_type, stage, active_only, attention_only)
    except FileNotFoundError as exc:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": str(exc)},
            status_code=500,
        )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "pipeline": pipeline,
            "stages": PIPELINE_STAGES,
            "filters": {
                "record_type": record_type,
                "stage": stage,
                "active_only": active_only,
                "attention_only": attention_only,
            },
        },
    )


@app.get("/pipeline", response_class=HTMLResponse)
def pipeline_partial(
    request: Request,
    record_type: str = Query("all"),
    stage: str = Query("all"),
    active_only: bool = Query(True),
    attention_only: bool = Query(False),
) -> HTMLResponse:
    try:
        pipeline = load_pipeline(record_type, stage, active_only, attention_only)
    except FileNotFoundError as exc:
        return templates.TemplateResponse(request, "error_panel.html", {"message": str(exc)}, status_code=500)
    return templates.TemplateResponse(request, "pipeline.html", {"pipeline": pipeline, "stages": PIPELINE_STAGES})


@app.get("/records/{item_key}", response_class=HTMLResponse)
def record_detail(request: Request, item_key: str) -> HTMLResponse:
    try:
        detail = load_item_detail(item_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(request, "detail_drawer.html", detail)
