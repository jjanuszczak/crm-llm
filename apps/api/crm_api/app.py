from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from .service import PIPELINE_STAGE_GROUPS, PIPELINE_STAGES, CrmRecord, PipelineData, PipelineItem, load_item_detail, load_pipeline


app = FastAPI(title="CRM Logic API", description="Read-only API for the markdown-backed CRM.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/pipeline")
def pipeline(
    record_type: str = Query("all"),
    stage: str = Query("all"),
    active_only: bool = Query(True),
    attention_only: bool = Query(False),
    lifecycle_group: str = Query("all"),
) -> dict[str, Any]:
    try:
        return serialize_pipeline(load_pipeline(record_type, stage, active_only, attention_only, lifecycle_group))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/records/{item_key}")
def record_detail(item_key: str) -> dict[str, Any]:
    try:
        return serialize_detail(load_item_detail(item_key))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def serialize_pipeline(data: PipelineData) -> dict[str, Any]:
    return {
        "crm_data_path": str(data.crm_data_path),
        "stages": PIPELINE_STAGES,
        "stage_groups": {key: sorted(value) for key, value in PIPELINE_STAGE_GROUPS.items()},
        "counts": data.counts,
        "stage_counts": data.stage_counts,
        "columns": {
            stage: [serialize_pipeline_item(item) for item in data.columns.get(stage, [])]
            for stage in PIPELINE_STAGES
        },
        "items": [serialize_pipeline_item(item) for item in data.items],
    }


def serialize_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "item": serialize_pipeline_item(detail["item"]),
        "record": serialize_record(detail["record"]),
        "summary": detail.get("summary", ""),
        "tasks": [serialize_record(task) for task in detail.get("tasks", [])],
        "activities": [serialize_record(activity) for activity in detail.get("activities", [])],
        "links": detail.get("links", []),
        "frontmatter": [{"key": key, "value": value} for key, value in detail.get("frontmatter", [])],
    }


def serialize_pipeline_item(item: PipelineItem) -> dict[str, Any]:
    return {
        "key": item.key,
        "record_type": item.record_type,
        "title": item.title,
        "native_stage": item.native_stage,
        "normalized_stage": item.normalized_stage,
        "person_or_contact": item.person_or_contact,
        "organization_or_account": item.organization_or_account,
        "priority_or_probability": item.priority_or_probability,
        "priority_rank": item.priority_rank,
        "latest_activity_date": item.latest_activity_date,
        "next_motion": item.next_motion,
        "task_count": item.task_count,
        "overdue_count": item.overdue_count,
        "needs_attention": item.needs_attention,
        "is_active": item.is_active,
        "summary": item.summary,
        "record": serialize_record(item.record, include_body=False),
    }


def serialize_record(record: CrmRecord, include_body: bool = True) -> dict[str, Any]:
    payload = {
        "entity_type": record.entity_type,
        "directory_name": record.directory_name,
        "relative_path": record.relative_path,
        "link": record.link,
        "link_target": record.link_target,
        "frontmatter": stringify_values(record.frontmatter),
    }
    if include_body:
        payload["body"] = record.body
    return payload


def stringify_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): stringify_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stringify_values(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
