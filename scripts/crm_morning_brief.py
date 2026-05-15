#!/usr/bin/env python3
"""Generate a sandbox-safe CRM morning brief from local vault data."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from frontmatter_utils import iter_markdown_files, load_frontmatter_file  # noqa: E402


MANILA = ZoneInfo("Asia/Manila")
OPEN_TASK_STATUSES = {"todo", "waiting"}
DONE_TASK_STATUSES = {"completed", "complete", "done", "cancelled", "canceled"}
RECORD_DIRS = ("Organizations", "Accounts", "Contacts", "Opportunities", "Leads", "Deal-Flow")


def resolve_crm_data_path() -> Path:
    env_value = os.getenv("CRM_DATA_PATH")
    if env_value:
        return _resolve_path(env_value)

    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("CRM_DATA_PATH="):
                return _resolve_path(line.split("=", 1)[1].strip().strip("\"'"))

    return PROJECT_ROOT / "crm-data"


def _resolve_path(value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def parse_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    if "T" in text:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(MANILA).date()
        except ValueError:
            return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(value):
    text = str(value or "").strip()
    if not text:
        return None
    if "T" not in text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(MANILA)
    except ValueError:
        return None


def wikilinks_from_text(value) -> list[str]:
    if isinstance(value, list):
        links = []
        for item in value:
            links.extend(wikilinks_from_text(item))
        return links
    return re.findall(r"\[\[([^\]]+)\]\]", str(value or ""))


def compact_title(frontmatter: dict, path: Path) -> str:
    for key in (
        "activity-name",
        "task-name",
        "opportunity-name",
        "organization-name",
        "full-name",
        "lead-name",
        "startup-name",
        "account-name",
        "title",
        "name",
    ):
        value = frontmatter.get(key)
        if value not in (None, "", []):
            return str(value)
    return path.stem


def load_records(crm_data_path: Path) -> dict[str, dict]:
    records = {}
    for directory in RECORD_DIRS + ("Activities", "Tasks"):
        base = crm_data_path / directory
        if not base.exists():
            continue
        for file_name in iter_markdown_files(str(base)):
            path = Path(file_name)
            frontmatter, body = load_frontmatter_file(str(path))
            rel = path.relative_to(crm_data_path).with_suffix("").as_posix()
            record = {
                "path": path,
                "rel": rel,
                "link": f"[[{rel}]]",
                "title": compact_title(frontmatter, path),
                "frontmatter": frontmatter,
                "body": body,
            }
            records[rel.lower()] = record
            records[Path(rel).name.lower()] = record
    return records


def record_for_link(records: dict[str, dict], link: str) -> dict | None:
    normalized = str(link or "").strip().strip("[]")
    if not normalized:
        return None
    return records.get(normalized.lower()) or records.get(Path(normalized).name.lower())


def event_date(event: dict) -> date | None:
    return parse_date(event.get("event_time") or event.get("date"))


def event_sort_key(event: dict):
    start = parse_datetime(event.get("event_time"))
    return start or datetime.combine(event_date(event) or date.min, datetime.min.time(), tzinfo=MANILA)


def load_cached_calendar_events(crm_data_path: Path, target_date: date) -> tuple[list[dict], str]:
    cache_path = crm_data_path / "staging" / "calendar_events_cache.json"
    if not cache_path.exists():
        return [], "no local Calendar cache"
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], "Calendar cache is unreadable"

    events = []
    for event in payload.get("events", []):
        if event.get("status") == "cancelled":
            continue
        if event_date(event) == target_date:
            events.append(event)
    generated_at = payload.get("generated_at") or "unknown time"
    return sorted(events, key=event_sort_key), f"local Calendar cache generated {generated_at}"


def load_activity_calendar_events(crm_data_path: Path, target_date: date) -> tuple[list[dict], str]:
    events = []
    base = crm_data_path / "Activities"
    if not base.exists():
        return [], "no local Activity directory"

    for file_name in iter_markdown_files(str(base)):
        path = Path(file_name)
        frontmatter, body = load_frontmatter_file(str(path))
        if parse_date(frontmatter.get("date")) != target_date:
            continue
        if str(frontmatter.get("source") or "").lower() != "calendar":
            continue
        rel = path.relative_to(crm_data_path).with_suffix("").as_posix()
        links = wikilinks_from_text(frontmatter.get("primary-parent")) + wikilinks_from_text(frontmatter.get("secondary-links")) + wikilinks_from_text(body)
        events.append(
            {
                "source_type": "calendar",
                "source_id": str(frontmatter.get("source-ref") or rel),
                "subject_or_title": compact_title(frontmatter, path),
                "event_time": str(frontmatter.get("date") or target_date.isoformat()),
                "body_text": body,
                "crm_activity": f"[[{rel}]]",
                "crm_links": dedupe(links),
            }
        )
    return sorted(events, key=event_sort_key), "local CRM Calendar activities"


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def find_activity_for_event(records: dict[str, dict], event: dict, target_date: date) -> dict | None:
    source_id = str(event.get("source_id") or "").strip()
    title = str(event.get("subject_or_title") or "").strip().lower()
    best = None
    for record in records.values():
        if not record["rel"].startswith("Activities/"):
            continue
        frontmatter = record["frontmatter"]
        if parse_date(frontmatter.get("date")) != target_date:
            continue
        haystack = "\n".join(
            [
                str(frontmatter.get("source-ref") or ""),
                str(frontmatter.get("source") or ""),
                record["title"],
                record["body"][:1000],
            ]
        ).lower()
        if source_id and source_id.lower() in haystack:
            return record
        if title and title == record["title"].lower():
            best = record
    return best


def enrich_event(event: dict, records: dict[str, dict], target_date: date) -> dict:
    activity = find_activity_for_event(records, event, target_date)
    links = list(event.get("crm_links") or [])
    if activity:
        links.extend(wikilinks_from_text(activity["frontmatter"].get("primary-parent")))
        links.extend(wikilinks_from_text(activity["frontmatter"].get("secondary-links")))
        links.extend(wikilinks_from_text(activity["body"]))
        event["crm_activity"] = activity["link"]

    resolved = []
    for link in dedupe(links):
        record = record_for_link(records, link)
        if record:
            resolved.append(record)

    event["resolved_context"] = prioritize_context(dedupe_records(resolved))
    return event


def dedupe_records(records: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for record in records:
        key = record["rel"].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def prioritize_context(records: list[dict]) -> list[dict]:
    order = {"Opportunities": 0, "Deal-Flow": 1, "Contacts": 2, "Accounts": 3, "Organizations": 4, "Leads": 5}
    return sorted(records, key=lambda record: (order.get(record["rel"].split("/", 1)[0], 99), record["title"]))[:5]


def summarize_event(event: dict) -> str:
    start = parse_datetime(event.get("event_time"))
    end = parse_datetime(event.get("end_time"))
    if start and end:
        time_text = f"{start:%H:%M}-{end:%H:%M}"
    elif start:
        time_text = f"{start:%H:%M}"
    else:
        time_text = "All day"

    title = str(event.get("subject_or_title") or "(untitled event)")
    bits = []
    if event.get("location"):
        bits.append(str(event["location"]))
    if event.get("crm_activity"):
        bits.append(event["crm_activity"])
    context = []
    for record in event.get("resolved_context", []):
        frontmatter = record["frontmatter"]
        detail = ""
        if record["rel"].startswith("Opportunities/"):
            stage = frontmatter.get("stage")
            probability = frontmatter.get("probability")
            detail = f"stage {stage}, {probability}%" if stage and probability not in ("", None) else f"stage {stage}" if stage else ""
        elif record["rel"].startswith("Contacts/"):
            detail = f"last contacted {frontmatter.get('last-contacted')}" if frontmatter.get("last-contacted") else ""
        elif record["rel"].startswith("Deal-Flow/"):
            detail = f"{frontmatter.get('fundraising-stage')} raise" if frontmatter.get("fundraising-stage") else ""
        context.append(f"{record['link']}{f' ({detail})' if detail else ''}")
    if context:
        bits.append("Context: " + "; ".join(context))
    return f"- {time_text} - {title}" + (f" - {' | '.join(bits)}" if bits else "")


def load_open_tasks(crm_data_path: Path, target_date: date) -> list[dict]:
    tasks = []
    base = crm_data_path / "Tasks"
    if not base.exists():
        return tasks
    for file_name in iter_markdown_files(str(base)):
        path = Path(file_name)
        frontmatter, _ = load_frontmatter_file(str(path))
        status = str(frontmatter.get("status") or "").lower()
        if status in DONE_TASK_STATUSES or status not in OPEN_TASK_STATUSES:
            continue
        due = parse_date(frontmatter.get("due-date"))
        if not due or due > target_date:
            continue
        rel = path.relative_to(crm_data_path).with_suffix("").as_posix()
        tasks.append(
            {
                "title": compact_title(frontmatter, path),
                "status": status,
                "priority": str(frontmatter.get("priority") or "").lower(),
                "due": due,
                "parent": str(frontmatter.get("primary-parent") or ""),
                "link": f"[[{rel}]]",
            }
        )
    return sorted(tasks, key=lambda item: (item["due"], item["status"] != "todo", item["priority"] != "high", item["title"]))


def task_line(task: dict) -> str:
    related = f" - {task['parent']}" if task["parent"] else ""
    return f"- {task['title']} ({task['due'].isoformat()}, {task['priority'] or 'normal'}){related}"


def task_section(tasks: list[dict], target_date: date, max_lines: int) -> list[str]:
    if not tasks:
        return ["No CRM tasks are due today or overdue."]

    lines = []
    due_today = [task for task in tasks if task["due"] == target_date]
    overdue_todo_high = [task for task in tasks if task["due"] < target_date and task["status"] == "todo" and task["priority"] == "high"]
    overdue_todo_other = [task for task in tasks if task["due"] < target_date and task["status"] == "todo" and task["priority"] != "high"]
    overdue_waiting = [task for task in tasks if task["due"] < target_date and task["status"] == "waiting"]

    groups = [
        ("Due today", due_today),
        ("Overdue todo - high urgency", overdue_todo_high),
        ("Overdue todo - medium/normal urgency", overdue_todo_other),
        ("Overdue waiting reviews", overdue_waiting),
    ]
    for heading, group in groups:
        lines.append(f"{heading}:")
        if not group:
            lines.append("- None")
            continue
        shown = group[:max_lines]
        lines.extend(task_line(task) for task in shown)
        if len(group) > len(shown):
            lines.append(f"- ... {len(group) - len(shown)} more")
    return lines


def build_brief(crm_data_path: Path, target_date: date, max_task_lines: int) -> str:
    records = load_records(crm_data_path)
    events, source_note = load_cached_calendar_events(crm_data_path, target_date)
    if not events:
        events, source_note = load_activity_calendar_events(crm_data_path, target_date)
    events = [enrich_event(event, records, target_date) for event in events]
    tasks = load_open_tasks(crm_data_path, target_date)

    lines = ["## Today's Google Calendar Events"]
    if events:
        lines.append(f"Source: {source_note}.")
        lines.extend(summarize_event(event) for event in events)
    else:
        lines.append(f"No locally cached Google Calendar events found for {target_date.isoformat()} ({source_note}).")

    lines.append("")
    lines.append("## CRM Tasks Due Today Or Overdue")
    lines.extend(task_section(tasks, target_date, max_task_lines))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local-only CRM morning brief.")
    parser.add_argument("--date", help="Brief date in YYYY-MM-DD. Defaults to today in Asia/Manila.")
    parser.add_argument("--crm-data-path", help="Override CRM data path.")
    parser.add_argument("--max-task-lines", type=int, default=8, help="Max lines per task urgency group.")
    args = parser.parse_args()

    target_date = parse_date(args.date) if args.date else datetime.now(MANILA).date()
    if target_date is None:
        parser.error("--date must be YYYY-MM-DD")

    crm_data_path = _resolve_path(args.crm_data_path) if args.crm_data_path else resolve_crm_data_path()
    print(build_brief(crm_data_path, target_date, max(1, args.max_task_lines)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
