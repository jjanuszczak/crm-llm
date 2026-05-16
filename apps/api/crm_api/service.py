from __future__ import annotations

import base64
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

def find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "scripts" / "frontmatter_utils.py").exists():
            return candidate
    return Path(__file__).resolve().parents[3]


REPO_ROOT = find_repo_root()
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from frontmatter_utils import iter_markdown_files, load_frontmatter_file
from navigation_manager import display_name_from_link, first_sentence, normalize_link


PIPELINE_STAGES = [
    "New Lead",
    "Prospect",
    "Engaged Lead",
    "Qualified Lead",
    "Discovery Opportunity",
    "Qualified Opportunity",
    "Proposal",
    "Negotiation",
    "Deferred / Paused",
    "Closed Won",
    "Closed Lost",
]
PIPELINE_STAGE_GROUPS = {
    "lead-intake": {"New Lead", "Prospect", "Engaged Lead"},
    "conversion-ready": {"Qualified Lead"},
    "opportunity-execution": {"Discovery Opportunity", "Qualified Opportunity", "Proposal", "Negotiation"},
    "deferred-paused": {"Deferred / Paused"},
    "closed": {"Closed Won", "Closed Lost"},
}
CLOSED_PIPELINE_STAGES = {"Closed Won", "Closed Lost"}
PIPELINE_STAGE_ORDER = {stage: index for index, stage in enumerate(PIPELINE_STAGES)}
OPEN_TASK_STATUSES = {"todo", "waiting", "in-progress", "in_progress", "open"}


@dataclass
class CrmRecord:
    entity_type: str
    directory_name: str
    path: Path
    relative_path: str
    frontmatter: dict[str, Any]
    body: str

    @property
    def link(self) -> str:
        return f"[[{self.relative_path[:-3]}]]" if self.relative_path.endswith(".md") else f"[[{self.relative_path}]]"

    @property
    def link_target(self) -> str:
        return self.relative_path[:-3] if self.relative_path.endswith(".md") else self.relative_path


@dataclass
class PipelineItem:
    key: str
    record: CrmRecord
    record_type: str
    title: str
    native_stage: str
    normalized_stage: str
    person_or_contact: str = ""
    organization_or_account: str = ""
    priority_or_probability: str = ""
    priority_rank: int = 0
    latest_activity_date: str = ""
    next_motion: str = ""
    open_tasks: list[CrmRecord] = field(default_factory=list)
    overdue_tasks: list[CrmRecord] = field(default_factory=list)
    is_active: bool = True
    summary: str = ""

    @property
    def task_count(self) -> int:
        return len(self.open_tasks)

    @property
    def overdue_count(self) -> int:
        return len(self.overdue_tasks)

    @property
    def needs_attention(self) -> bool:
        return self.priority_rank >= 2 or bool(self.overdue_tasks)


@dataclass
class PipelineData:
    crm_data_path: Path
    columns: dict[str, list[PipelineItem]]
    items: list[PipelineItem]
    counts: dict[str, int]
    stage_counts: dict[str, int]


def resolve_crm_data_path() -> Path:
    env_path = os.getenv("CRM_DATA_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("CRM_DATA_PATH="):
                raw_value = line.split("=", 1)[1].strip().strip('"').strip("'")
                candidate = Path(raw_value).expanduser()
                if not candidate.is_absolute():
                    candidate = REPO_ROOT / candidate
                return candidate.resolve()

    return (REPO_ROOT / "crm-data").resolve()


def load_pipeline(
    record_type: str = "all",
    stage: str = "all",
    active_only: bool = True,
    attention_only: bool = False,
    lifecycle_group: str = "all",
) -> PipelineData:
    crm_data_path = resolve_crm_data_path()
    if not crm_data_path.exists():
        raise FileNotFoundError(f"CRM_DATA_PATH does not exist: {crm_data_path}")

    records = load_records(crm_data_path)
    tasks = records.get("Tasks", [])
    activities = records.get("Activities", [])
    items = [
        build_lead_item(record, crm_data_path, tasks, activities)
        for record in records.get("Leads", [])
    ] + [
        build_opportunity_item(record, crm_data_path, tasks, activities)
        for record in records.get("Opportunities", [])
    ]

    items = [item for item in items if item.title]
    if record_type in {"lead", "opportunity"}:
        items = [item for item in items if item.record_type == record_type]
    if stage in PIPELINE_STAGES:
        items = [item for item in items if item.normalized_stage == stage]
    if lifecycle_group in PIPELINE_STAGE_GROUPS:
        group_stages = PIPELINE_STAGE_GROUPS[lifecycle_group]
        items = [item for item in items if item.normalized_stage in group_stages]
    if active_only:
        items = [item for item in items if item.is_active and item.normalized_stage not in CLOSED_PIPELINE_STAGES]
    if attention_only:
        items = [item for item in items if item.needs_attention]

    items.sort(key=sort_key)
    columns = {name: [] for name in PIPELINE_STAGES}
    for item in items:
        columns.setdefault(item.normalized_stage, []).append(item)

    return PipelineData(
        crm_data_path=crm_data_path,
        columns=columns,
        items=items,
        counts={
            "total": len(items),
            "leads": sum(1 for item in items if item.record_type == "lead"),
            "opportunities": sum(1 for item in items if item.record_type == "opportunity"),
            "attention": sum(1 for item in items if item.needs_attention),
            "overdue": sum(len(item.overdue_tasks) for item in items),
        },
        stage_counts={name: len(columns.get(name, [])) for name in PIPELINE_STAGES},
    )


def load_item_detail(item_key: str) -> dict[str, Any]:
    crm_data_path = resolve_crm_data_path()
    relative_path = decode_key(item_key)
    if not relative_path.startswith(("Leads/", "Opportunities/")):
        raise FileNotFoundError("Unsupported record type")

    record_path = (crm_data_path / relative_path).resolve()
    if not str(record_path).startswith(str(crm_data_path.resolve())) or not record_path.exists():
        raise FileNotFoundError(relative_path)

    records = load_records(crm_data_path)
    record = record_from_path(crm_data_path, record_path)
    tasks = open_tasks(related_tasks(record, records.get("Tasks", [])))
    activities = related_activities(record, records.get("Activities", []))
    links = linked_context(record, crm_data_path)

    item = (
        build_lead_item(record, crm_data_path, records.get("Tasks", []), records.get("Activities", []))
        if record.directory_name == "Leads"
        else build_opportunity_item(record, crm_data_path, records.get("Tasks", []), records.get("Activities", []))
    )
    return {
        "item": item,
        "record": record,
        "summary": item.summary or first_sentence(record.body),
        "tasks": sorted(tasks, key=lambda task: str(task.frontmatter.get("due-date") or ""))[:12],
        "activities": sorted(activities, key=lambda activity: str(activity.frontmatter.get("date") or ""), reverse=True)[:10],
        "links": links,
        "frontmatter": display_frontmatter(record.frontmatter),
    }


def load_records(crm_data_path: Path) -> dict[str, list[CrmRecord]]:
    directories = ["Leads", "Opportunities", "Contacts", "Accounts", "Organizations", "Activities", "Tasks", "Deal-Flow"]
    return {directory: load_directory(crm_data_path, directory) for directory in directories}


def load_directory(crm_data_path: Path, directory: str) -> list[CrmRecord]:
    directory_path = crm_data_path / directory
    records: list[CrmRecord] = []
    for path in iter_markdown_files(str(directory_path)) or []:
        record_path = Path(path)
        try:
            records.append(record_from_path(crm_data_path, record_path))
        except Exception:
            continue
    return records


def record_from_path(crm_data_path: Path, path: Path) -> CrmRecord:
    frontmatter, body = load_frontmatter_file(str(path))
    directory = path.relative_to(crm_data_path).parts[0]
    return CrmRecord(
        entity_type=directory.rstrip("s"),
        directory_name=directory,
        path=path,
        relative_path=path.relative_to(crm_data_path).as_posix(),
        frontmatter=frontmatter,
        body=body,
    )


def build_lead_item(record: CrmRecord, crm_data_path: Path, tasks: list[CrmRecord], activities: list[CrmRecord]) -> PipelineItem:
    native_stage = text(record.frontmatter.get("status") or "new").lower()
    record_tasks = related_tasks(record, tasks)
    overdue = overdue_open_tasks(record_tasks)
    return PipelineItem(
        key=encode_key(record.relative_path),
        record=record,
        record_type="lead",
        title=title_for(record),
        native_stage=native_stage or "new",
        normalized_stage=normalize_lead_stage(native_stage),
        person_or_contact=text(record.frontmatter.get("person-name")),
        organization_or_account=display_name(record.frontmatter.get("company-name"), crm_data_path),
        priority_or_probability=text(record.frontmatter.get("priority") or "medium"),
        priority_rank=priority_rank(record.frontmatter.get("priority")),
        latest_activity_date=latest_activity(record, activities),
        next_motion=next_lead_motion(native_stage),
        open_tasks=open_tasks(record_tasks),
        overdue_tasks=overdue,
        is_active=native_stage not in {"converted", "disqualified", "archived"},
        summary=extract_section(record.body, "Summary") or first_sentence(record.body),
    )


def build_opportunity_item(record: CrmRecord, crm_data_path: Path, tasks: list[CrmRecord], activities: list[CrmRecord]) -> PipelineItem:
    native_stage = text(record.frontmatter.get("stage") or "discovery").lower()
    record_tasks = related_tasks(record, tasks)
    overdue = overdue_open_tasks(record_tasks)
    probability = record.frontmatter.get("probability")
    return PipelineItem(
        key=encode_key(record.relative_path),
        record=record,
        record_type="opportunity",
        title=title_for(record),
        native_stage=native_stage or "discovery",
        normalized_stage=normalize_opportunity_stage(native_stage),
        person_or_contact=display_name(record.frontmatter.get("primary-contact"), crm_data_path),
        organization_or_account=display_name(record.frontmatter.get("organization") or record.frontmatter.get("account"), crm_data_path),
        priority_or_probability=f"{probability}%" if probability not in (None, "") else "",
        priority_rank=probability_rank(probability),
        latest_activity_date=latest_activity(record, activities),
        next_motion=next_opportunity_motion(native_stage),
        open_tasks=open_tasks(record_tasks),
        overdue_tasks=overdue,
        is_active=bool(record.frontmatter.get("is-active", True)) and native_stage not in {"closed-won", "closed-lost", "won", "lost"},
        summary=extract_section(record.body, "Executive Summary") or first_sentence(record.body),
    )


def normalize_lead_stage(stage: str) -> str:
    mapping = {
        "new": "New Lead",
        "prospect": "Prospect",
        "engaged": "Engaged Lead",
        "qualified": "Qualified Lead",
        "deferred": "Deferred / Paused",
        "converted": "Closed Won",
        "disqualified": "Closed Lost",
    }
    return mapping.get(stage, "New Lead")


def normalize_opportunity_stage(stage: str) -> str:
    mapping = {
        "new": "Discovery Opportunity",
        "prospect": "Discovery Opportunity",
        "discovery": "Discovery Opportunity",
        "qualification": "Qualified Opportunity",
        "qualified": "Qualified Opportunity",
        "proposal": "Proposal",
        "negotiation": "Negotiation",
        "paused": "Deferred / Paused",
        "closed-won": "Closed Won",
        "won": "Closed Won",
        "closed-lost": "Closed Lost",
        "lost": "Closed Lost",
    }
    return mapping.get(stage, "Discovery Opportunity")


def next_lead_motion(stage: str) -> str:
    mapping = {
        "new": "Add signal or move to prospect",
        "prospect": "Engage or defer",
        "engaged": "Qualify, defer, or disqualify",
        "qualified": "Convert to durable CRM records",
        "deferred": "Review waiting task",
        "converted": "Inspect converted records",
        "disqualified": "No action unless revived",
    }
    return mapping.get(stage, "Clarify lead status")


def next_opportunity_motion(stage: str) -> str:
    mapping = {
        "discovery": "Validate opportunity",
        "qualified": "Shape proposal",
        "proposal": "Advance to negotiation",
        "negotiation": "Close won, close lost, or pause",
        "paused": "Review waiting task",
        "closed-won": "Review outcome",
        "closed-lost": "Review loss reason",
    }
    return mapping.get(stage, "Clarify opportunity stage")


def related_tasks(record: CrmRecord, tasks: list[CrmRecord]) -> list[CrmRecord]:
    variants = link_variants(record)
    matched = []
    for task in tasks:
        values = [
            task.frontmatter.get("primary-parent"),
            task.frontmatter.get("opportunity"),
            task.frontmatter.get("lead"),
            task.frontmatter.get("contact"),
            task.frontmatter.get("account"),
        ]
        if any(normalized_link_value(value) in variants for value in values if value):
            matched.append(task)
    return matched


def related_activities(record: CrmRecord, activities: list[CrmRecord]) -> list[CrmRecord]:
    variants = link_variants(record)
    matched = []
    for activity in activities:
        links = [activity.frontmatter.get("primary-parent")]
        secondary = activity.frontmatter.get("secondary-links")
        if isinstance(secondary, list):
            links.extend(secondary)
        if any(normalized_link_value(value) in variants for value in links if value):
            matched.append(activity)
    return matched


def linked_context(record: CrmRecord, crm_data_path: Path) -> list[dict[str, str]]:
    keys = ["organization", "account", "primary-contact", "deal", "source-lead", "converted-organization", "converted-contact", "converted-account"]
    links = []
    seen = set()
    for key in keys:
        value = record.frontmatter.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            target = normalized_link_value(item)
            if not target or target in seen:
                continue
            seen.add(target)
            links.append({"label": display_name(item, crm_data_path), "target": target, "kind": target.split("/", 1)[0] if "/" in target else "Record"})
    return links


def latest_activity(record: CrmRecord, activities: list[CrmRecord]) -> str:
    dates = [str(activity.frontmatter.get("date") or "") for activity in related_activities(record, activities)]
    return max([value for value in dates if value], default="")


def open_tasks(tasks: list[CrmRecord]) -> list[CrmRecord]:
    return [task for task in tasks if text(task.frontmatter.get("status")).lower() in OPEN_TASK_STATUSES]


def overdue_open_tasks(tasks: list[CrmRecord]) -> list[CrmRecord]:
    today = date.today().strftime("%Y-%m-%d")
    return [
        task for task in open_tasks(tasks)
        if str(task.frontmatter.get("due-date") or "") and str(task.frontmatter.get("due-date")) < today
    ]


def link_variants(record: CrmRecord) -> set[str]:
    target = record.link_target
    basename = Path(target).name
    return {target, f"[[{target}]]", basename, f"[[{basename}]]"}


def normalized_link_value(value: Any) -> str:
    if not value:
        return ""
    normalized = normalize_link(value)
    return normalized[:-3] if normalized.endswith(".md") else normalized


def display_name(value: Any, crm_data_path: Path) -> str:
    if not value:
        return ""
    return display_name_from_link(value, str(crm_data_path))


def title_for(record: CrmRecord) -> str:
    candidates = {
        "Leads": ["lead-name", "name", "title"],
        "Opportunities": ["opportunity-name", "name", "title"],
        "Tasks": ["task-name", "title"],
        "Activities": ["activity-name", "title"],
    }.get(record.directory_name, ["title", "name"])
    for key in candidates:
        if record.frontmatter.get(key):
            return text(record.frontmatter.get(key))
    return Path(record.relative_path).stem.replace("-", " ")


def display_frontmatter(frontmatter: dict[str, Any]) -> list[tuple[str, str]]:
    hidden = {"id"}
    rows = []
    for key, value in frontmatter.items():
        if key in hidden or value in (None, "", [], {}):
            continue
        rows.append((key, ", ".join(map(str, value)) if isinstance(value, list) else str(value)))
    return rows


def extract_section(body: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+\**{re.escape(heading)}\**\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(body or "")
    if not match:
        return ""
    rest = body[match.end():]
    next_heading = re.search(r"^##\s+", rest, re.MULTILINE)
    section = rest[: next_heading.start()] if next_heading else rest
    return clean_markdown(section)


def clean_markdown(value: str) -> str:
    lines = []
    for raw in value.splitlines():
        line = re.sub(r"^\s*[-*]\s+", "", raw.strip())
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        if line:
            lines.append(line)
    return " ".join(lines)[:700]


def priority_rank(value: Any) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(text(value).lower(), 1)


def probability_rank(value: Any) -> int:
    try:
        probability = int(value)
    except (TypeError, ValueError):
        return 0
    if probability >= 75:
        return 3
    if probability >= 50:
        return 2
    if probability >= 25:
        return 1
    return 0


def sort_key(item: PipelineItem) -> tuple[int, int, str, str]:
    return (-item.overdue_count, -item.priority_rank, f"{PIPELINE_STAGE_ORDER.get(item.normalized_stage, 999):03d}", item.title.lower())


def encode_key(relative_path: str) -> str:
    return base64.urlsafe_b64encode(relative_path.encode("utf-8")).decode("ascii").rstrip("=")


def decode_key(key: str) -> str:
    padding = "=" * (-len(key) % 4)
    return base64.urlsafe_b64decode((key + padding).encode("ascii")).decode("utf-8")


def text(value: Any) -> str:
    return str(value or "").strip()
