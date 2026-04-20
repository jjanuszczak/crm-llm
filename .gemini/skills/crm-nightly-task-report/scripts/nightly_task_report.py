#!/usr/bin/env python3
import argparse
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[4]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from frontmatter_utils import iter_markdown_files, load_frontmatter_file  # noqa: E402


EXCLUDED_STATUSES = {"complete", "completed", "done", "canceled", "cancelled"}
STATUS_LABELS = {
    "todo": "You Owe Action",
    "waiting": "Waiting / Review",
}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "": 3}
STATUS_ORDER = {"todo": 0, "waiting": 1}


def resolve_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return Path(env_override).expanduser().resolve()

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("CRM_DATA_PATH="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                path = Path(value).expanduser()
                return (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path.resolve()

    return (PROJECT_ROOT / "crm-data").resolve()


def parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def clean(value):
    return "" if value in (None, []) else str(value).strip()


def task_sort_key(task):
    return (
        STATUS_ORDER.get(task["status"], 9),
        PRIORITY_ORDER.get(task["priority"], 9),
        task["due_date"],
        task["name"].lower(),
    )


def collect_tasks(crm_data_path, report_date, days):
    tasks_dir = crm_data_path / "Tasks"
    horizon = report_date + timedelta(days=days)
    overdue = []
    upcoming = []

    for file_path in iter_markdown_files(str(tasks_dir)):
        frontmatter, _ = load_frontmatter_file(file_path)
        due_date = parse_date(frontmatter.get("due-date"))
        if due_date is None or due_date > horizon:
            continue

        status = clean(frontmatter.get("status")).lower()
        if status in EXCLUDED_STATUSES:
            continue

        task = {
            "name": clean(frontmatter.get("task-name")) or Path(file_path).stem,
            "status": status or "unknown",
            "priority": clean(frontmatter.get("priority")).lower(),
            "due_date": due_date,
            "parent": clean(frontmatter.get("primary-parent")),
            "path": Path(file_path),
        }

        if due_date < report_date:
            overdue.append(task)
        else:
            upcoming.append(task)

    return sorted(overdue, key=task_sort_key), sorted(upcoming, key=task_sort_key)


def render_task(task, include_date=False):
    priority = task["priority"] or "no-priority"
    prefix = f"{task['due_date'].isoformat()} | " if include_date else ""
    parent = f" - {task['parent']}" if task["parent"] else ""
    return f"- {prefix}{priority} {task['status']}: {task['name']}{parent}"


def render_status_group(title, tasks, include_date=False):
    lines = [f"## {title}", ""]
    if not tasks:
        lines.extend(["No tasks.", ""])
        return lines

    by_status = defaultdict(list)
    for task in tasks:
        by_status[task["status"]].append(task)

    for status in sorted(by_status, key=lambda value: STATUS_ORDER.get(value, 9)):
        label = STATUS_LABELS.get(status, status.title())
        lines.extend([f"### {label}", ""])
        for task in sorted(by_status[status], key=task_sort_key):
            lines.append(render_task(task, include_date=include_date))
        lines.append("")

    return lines


def render_upcoming(upcoming):
    lines = ["## Upcoming", ""]
    if not upcoming:
        lines.extend(["No tasks due in the report window.", ""])
        return lines

    by_date = defaultdict(list)
    for task in upcoming:
        by_date[task["due_date"]].append(task)

    for due_date in sorted(by_date):
        lines.extend([f"### {due_date.isoformat()}", ""])
        for task in sorted(by_date[due_date], key=task_sort_key):
            lines.append(render_task(task))
        lines.append("")

    return lines


def top_execution_cluster(overdue, upcoming, limit=7):
    candidates = [
        task for task in overdue + upcoming
        if task["status"] == "todo" and task["priority"] == "high"
    ]
    candidates = sorted(candidates, key=lambda task: (task["due_date"], task["name"].lower()))
    return candidates[:limit]


def render_report(report_date, days, overdue, upcoming, crm_data_path):
    horizon = report_date + timedelta(days=days)
    lines = [
        "---",
        f"report-date: {report_date.isoformat()}",
        "type: nightly-task-report",
        "status: final",
        f"crm-data-path: {crm_data_path}",
        f"window-start: {report_date.isoformat()}",
        f"window-end: {horizon.isoformat()}",
        "---",
        "",
        f"# Nightly Task Report: {report_date.isoformat()}",
        "",
        f"Window: overdue plus tasks due from {report_date.isoformat()} through {horizon.isoformat()}.",
        f"Open items found: {len(overdue)} overdue, {len(upcoming)} upcoming.",
        "",
    ]

    cluster = top_execution_cluster(overdue, upcoming)
    lines.extend(["## Top Execution Cluster", ""])
    if cluster:
        lines.extend(render_task(task, include_date=True) for task in cluster)
    else:
        lines.append("No high-priority todo tasks in the report window.")
    lines.append("")

    lines.extend(render_status_group("Overdue", overdue))
    lines.extend(render_upcoming(upcoming))
    return "\n".join(lines).rstrip() + "\n"


def parse_args():
    parser = argparse.ArgumentParser(description="Create a CRM nightly task report.")
    parser.add_argument("--date", help="Report date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--days", type=int, default=3, help="Number of upcoming days after the report date to include.")
    parser.add_argument("--output-dir", help="Directory for the Markdown report. Defaults to CRM_DATA_PATH/Reports.")
    return parser.parse_args()


def main():
    args = parse_args()
    report_date = parse_date(args.date) if args.date else date.today()
    if report_date is None:
        raise ValueError("--date must use YYYY-MM-DD")
    if args.days < 0:
        raise ValueError("--days must be non-negative")

    crm_data_path = resolve_crm_data_path()
    overdue, upcoming = collect_tasks(crm_data_path, report_date, args.days)

    output_dir = Path(args.output_dir) if args.output_dir else crm_data_path / "Reports"
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{report_date.isoformat()}-nightly-task-report.md"
    output_path.write_text(render_report(report_date, args.days, overdue, upcoming, crm_data_path), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
