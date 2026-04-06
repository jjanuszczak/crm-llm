import argparse
import os
import re
from datetime import datetime
from urllib.parse import quote

from frontmatter_utils import iter_markdown_files, load_frontmatter_file


ENTITY_ORDER = [
    ("Organizations", "Organization"),
    ("Accounts", "Account"),
    ("Contacts", "Contact"),
    ("Leads", "Lead"),
    ("Opportunities", "Opportunity"),
    ("Activities", "Activity"),
    ("Notes", "Note"),
    ("Tasks", "Task"),
    ("Inbox", "Inbox"),
    ("Deal-Flow", "Deal"),
]
INDEX_FILE_NAME = "index.md"
LOG_FILE_NAME = "log.md"
MAX_RELATED_LINKS = 4
LINK_DISPLAY_CACHE = {}


def get_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return os.path.abspath(env_override)

    logic_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    env_path = os.path.join(logic_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.abspath(os.path.join(logic_root, value)) if not os.path.isabs(value) else value
    return os.getcwd()


def index_path(crm_data_path=None):
    return os.path.join(crm_data_path or get_crm_data_path(), INDEX_FILE_NAME)


def log_path(crm_data_path=None):
    return os.path.join(crm_data_path or get_crm_data_path(), LOG_FILE_NAME)


def rebuild_index(crm_data_path=None):
    crm_data_path = crm_data_path or get_crm_data_path()
    os.makedirs(crm_data_path, exist_ok=True)
    counts = {}
    lines = [
        "# CRM Index",
        "",
        "Generated from vault records. Read this first to locate relevant pages, then drill into linked records.",
        "",
        f"Generated: {timestamp_string()}",
        "",
    ]

    for directory_name, entity_type in ENTITY_ORDER:
        directory_path = os.path.join(crm_data_path, directory_name)
        records = collect_entity_records(crm_data_path, directory_name, entity_type, directory_path)
        counts[directory_name] = len(records)
        lines.append(f"## {directory_name}")
        lines.append("")
        if not records:
            lines.append("- No records.")
            lines.append("")
            continue
        for record in records:
            lines.append(render_index_entry(record))
        lines.append("")

    counts_line = " | ".join(f"{name}={counts[name]}" for name, _ in ENTITY_ORDER)
    lines.insert(5, f"Counts: {counts_line}")
    lines.insert(6, "")

    output_path = index_path(crm_data_path)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    return output_path


def append_log_entry(action, entity_type, title, path="", source="", related=None, details="", crm_data_path=None):
    crm_data_path = crm_data_path or get_crm_data_path()
    os.makedirs(crm_data_path, exist_ok=True)
    related = normalize_related_links(related or [], crm_data_path)
    lines = [f"## [{timestamp_string()}] {action} | {entity_type} | {sanitize_inline(title)}"]
    if path:
        lines.append(f"- path: {rel_to_vault(path, crm_data_path)}")
    if source:
        lines.append(f"- source: {sanitize_inline(source)}")
    if related:
        lines.append(f"- related: {', '.join(related)}")
    if details:
        lines.append(f"- details: {sanitize_inline(details)}")
    lines.append("")

    output_path = log_path(crm_data_path)
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return output_path


def record_mutation(action, entity_type, title, path="", source="", related=None, details="", crm_data_path=None):
    crm_data_path = crm_data_path or get_crm_data_path()
    append_log_entry(
        action=action,
        entity_type=entity_type,
        title=title,
        path=path,
        source=source,
        related=related,
        details=details,
        crm_data_path=crm_data_path,
    )
    rebuild_index(crm_data_path)


def collect_entity_records(crm_data_path, directory_name, entity_type, directory_path):
    records = []
    for file_path in iter_markdown_files(directory_path):
        frontmatter, body = load_frontmatter_file(file_path)
        record = {
            "entity_type": entity_type,
            "directory_name": directory_name,
            "path": file_path,
            "relative_path": rel_to_vault(file_path, crm_data_path),
            "crm_data_path": crm_data_path,
            "frontmatter": frontmatter,
            "body": body,
        }
        record["title"] = record_title(record)
        record["summary"] = record_summary(record)
        record["meta"] = record_meta(record)
        record["related"] = record_related(record, crm_data_path)
        records.append(record)
    return sorted(records, key=lambda item: (item["title"].lower(), item["relative_path"].lower()))


def render_index_entry(record):
    line = f"- [{escape_link_label(record['title'])}]({encode_link_target(record['relative_path'])})"
    summary = record["summary"]
    if summary:
        line += f" — {summary}"
    if record["meta"]:
        separator = "." if summary else " —"
        line += f"{separator} Meta: {', '.join(record['meta'])}"
    if record["related"]:
        separator = "." if (summary or record["meta"]) else " —"
        line += f"{separator} Links: {', '.join(record['related'])}"
    return line


def record_title(record):
    frontmatter = record["frontmatter"]
    directory_name = record["directory_name"]
    candidates = {
        "Organizations": ["organization-name"],
        "Accounts": ["organization", "account-name", "name"],
        "Contacts": ["full-name", "nickname"],
        "Leads": ["lead-name"],
        "Opportunities": ["opportunity-name"],
        "Activities": ["activity-name"],
        "Notes": ["title", "note-name"],
        "Tasks": ["task-name"],
        "Inbox": ["title"],
        "Deal-Flow": ["deal-name", "name", "title"],
    }.get(directory_name, ["title", "name"])
    for key in candidates:
        value = frontmatter.get(key)
        if value:
            if key in {"organization", "account", "deal", "primary-parent"}:
                return basename_from_link(value) or os.path.splitext(os.path.basename(record["path"]))[0]
            return str(value)
    return os.path.splitext(os.path.basename(record["path"]))[0]


def record_summary(record):
    frontmatter = record["frontmatter"]
    directory_name = record["directory_name"]
    body = record["body"]
    summary = {
        "Organizations": summary_from_parts(
            class_or_type(frontmatter.get("organization-class"), frontmatter.get("organization-subtype")),
            frontmatter.get("industry"),
            domain_phrase(frontmatter.get("domain")),
        ),
        "Accounts": summary_from_parts(
            stage_phrase(frontmatter.get("relationship-stage"), "relationship stage"),
            linked_phrase(frontmatter.get("organization"), "linked to", record["crm_data_path"]),
        ),
        "Contacts": summary_from_parts(
            status_phrase(frontmatter.get("relationship-status"), "relationship"),
            linked_phrase(frontmatter.get("account"), "linked to", record["crm_data_path"]),
            linked_phrase(frontmatter.get("deal"), "deal", record["crm_data_path"]),
        ),
        "Leads": summary_from_parts(
            stage_phrase(frontmatter.get("status"), "lead status"),
            frontmatter.get("person-name"),
            linked_phrase(frontmatter.get("company-name"), "at", record["crm_data_path"]) if frontmatter.get("company-name") else "",
        ),
        "Opportunities": summary_from_parts(
            frontmatter.get("opportunity-type"),
            stage_phrase(frontmatter.get("stage"), "stage"),
            linked_phrase(frontmatter.get("organization") or frontmatter.get("account"), "for", record["crm_data_path"]),
        ),
        "Activities": summary_from_parts(
            frontmatter.get("activity-type"),
            frontmatter.get("date"),
            linked_phrase(frontmatter.get("primary-parent"), "with", record["crm_data_path"]),
        ),
        "Notes": summary_from_parts(
            linked_phrase(frontmatter.get("primary-parent"), "about", record["crm_data_path"]),
            first_sentence(body),
        ),
        "Tasks": summary_from_parts(
            stage_phrase(frontmatter.get("status"), "status"),
            due_phrase(frontmatter.get("due-date")),
            linked_phrase(frontmatter.get("primary-parent"), "for", record["crm_data_path"]),
        ),
        "Inbox": summary_from_parts(
            source_phrase(frontmatter.get("source")),
            stage_phrase(frontmatter.get("status"), "status"),
        ),
        "Deal-Flow": summary_from_parts(
            frontmatter.get("stage") or frontmatter.get("status"),
            frontmatter.get("company-name") or frontmatter.get("sector"),
            first_sentence(body),
        ),
    }.get(directory_name, "")
    return sanitize_inline(summary or first_sentence(body) or "Summary unavailable.")


def record_meta(record):
    frontmatter = record["frontmatter"]
    directory_name = record["directory_name"]
    field_map = {
        "Organizations": ["organization-class", "industry", "last-contacted"],
        "Accounts": ["owner", "relationship-stage", "strategic-importance", "last-contacted"],
        "Contacts": ["owner", "priority", "relationship-status", "last-contacted"],
        "Leads": ["owner", "status", "priority", "lead-source"],
        "Opportunities": ["owner", "stage", "commercial-value", "close-date", "probability"],
        "Activities": ["owner", "activity-type", "status", "date"],
        "Notes": ["owner", "date-created", "date-modified"],
        "Tasks": ["owner", "status", "priority", "due-date"],
        "Inbox": ["owner", "status", "source", "captured-at", "date-created"],
        "Deal-Flow": ["owner", "stage", "status", "date-created"],
    }
    items = []
    for key in field_map.get(directory_name, []):
        value = frontmatter.get(key)
        if value in (None, "", [], {}):
            continue
        items.append(f"{key}={format_meta_value(value)}")
    return items


def record_related(record, crm_data_path):
    frontmatter = record["frontmatter"]
    directory_name = record["directory_name"]
    related = []
    relation_map = {
        "Organizations": [],
        "Accounts": ["organization"],
        "Contacts": ["account", "deal"],
        "Leads": ["converted-organization", "converted-contact", "converted-account", "converted-opportunities"],
        "Opportunities": ["organization", "account", "primary-contact", "deal", "source-lead"],
        "Activities": ["primary-parent", "secondary-links"],
        "Notes": ["primary-parent", "secondary-links"],
        "Tasks": ["primary-parent", "account", "contact", "opportunity", "lead"],
        "Inbox": [],
        "Deal-Flow": ["account", "contact", "organization"],
    }
    for key in relation_map.get(directory_name, []):
        value = frontmatter.get(key)
        if isinstance(value, list):
            related.extend(value)
        elif value:
            related.append(value)
    return normalize_related_links(related, crm_data_path)[:MAX_RELATED_LINKS]


def normalize_related_links(values, crm_data_path=None):
    related = []
    seen = set()
    for value in values:
        if not value:
            continue
        normalized = normalize_link(value, crm_data_path)
        if not normalized:
            continue
        wikilink = f"[[{normalized}]]"
        if wikilink in seen:
            continue
        seen.add(wikilink)
        related.append(wikilink)
    return related


def normalize_link(value, crm_data_path=None):
    text = str(value or "").strip()
    if not text:
        return ""
    crm_data_path = crm_data_path or get_crm_data_path()
    if text.endswith(".md"):
        candidate = text
        if not os.path.isabs(candidate):
            candidate = os.path.join(crm_data_path, candidate)
        if os.path.exists(candidate):
            relative = os.path.relpath(os.path.abspath(candidate), crm_data_path)
            return os.path.splitext(relative)[0]
    if text.startswith("[[") and text.endswith("]]"):
        return text[2:-2].strip()
    return text


def basename_from_link(value):
    normalized = normalize_link(value)
    if not normalized:
        return ""
    return os.path.basename(normalized)


def rel_to_vault(path, crm_data_path):
    return os.path.relpath(os.path.abspath(path), crm_data_path)


def class_or_type(primary, subtype):
    if primary and subtype:
        return f"{primary} ({subtype})"
    return primary or subtype or ""


def linked_phrase(value, prefix, crm_data_path=None):
    name = display_name_from_link(value, crm_data_path)
    return f"{prefix} {name}" if name else ""


def display_name_from_link(value, crm_data_path=None):
    normalized = normalize_link(value, crm_data_path)
    if not normalized:
        return ""
    crm_data_path = crm_data_path or get_crm_data_path()
    cache_key = (crm_data_path, normalized)
    if cache_key in LINK_DISPLAY_CACHE:
        return LINK_DISPLAY_CACHE[cache_key]

    candidate_path = os.path.join(crm_data_path, f"{normalized}.md")
    if os.path.exists(candidate_path):
        frontmatter, _body = load_frontmatter_file(candidate_path)
        directory_name = normalized.split("/", 1)[0] if "/" in normalized else ""
        display = title_from_frontmatter(directory_name, frontmatter)
    else:
        display = ""

    if not display:
        display = humanize_slug(os.path.basename(normalized))
    LINK_DISPLAY_CACHE[cache_key] = display
    return display


def title_from_frontmatter(directory_name, frontmatter):
    candidates = {
        "Organizations": ["organization-name"],
        "Accounts": ["organization", "account-name", "name"],
        "Contacts": ["full-name", "nickname"],
        "Leads": ["lead-name"],
        "Opportunities": ["opportunity-name"],
        "Activities": ["activity-name"],
        "Notes": ["title", "note-name"],
        "Tasks": ["task-name"],
        "Inbox": ["title"],
        "Deal-Flow": ["deal-name", "name", "title"],
    }.get(directory_name, ["title", "name"])
    for key in candidates:
        value = frontmatter.get(key)
        if value:
            if key in {"organization", "account", "deal", "primary-parent"}:
                return basename_from_link(value)
            return str(value)
    return ""


def humanize_slug(value):
    return str(value or "").replace("-", " ").strip()


def stage_phrase(value, label):
    return f"{label} {value}" if value else ""


def status_phrase(value, label):
    return f"{label} {value}" if value else ""


def due_phrase(value):
    return f"due {value}" if value else ""


def source_phrase(value):
    return f"source {value}" if value else ""


def domain_phrase(value):
    return f"domain {value}" if value else ""


def summary_from_parts(*parts):
    cleaned = []
    for part in parts:
        text = sanitize_inline(part)
        if text:
            cleaned.append(text)
    return "; ".join(cleaned)


def first_sentence(body):
    if not body:
        return ""
    for raw_line in body.splitlines():
        line = sanitize_inline(strip_markdown(raw_line))
        if not line:
            continue
        if line.startswith("{{") and line.endswith("}}"):
            continue
        fragments = re.split(r"(?<=[.!?])\s+", line)
        return fragments[0].strip()
    return ""


def strip_markdown(value):
    text = str(value or "").strip()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"^\*\*?(.*?)\*\*?$", r"\1", text)
    text = re.sub(r"^\*\s+", "", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text


def format_meta_value(value):
    if isinstance(value, list):
        return ",".join(sanitize_inline(item) for item in value if item not in (None, ""))
    return sanitize_inline(value)


def sanitize_inline(value):
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def escape_link_label(value):
    return str(value).replace("[", "\\[").replace("]", "\\]")


def encode_link_target(value):
    return quote(str(value), safe="/")


def timestamp_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_parser():
    parser = argparse.ArgumentParser(description="Manage CRM navigation artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild_parser = subparsers.add_parser("rebuild-index", help="Regenerate CRM index.md from vault records.")
    rebuild_parser.set_defaults(func=lambda _args: print(rebuild_index()))

    log_parser = subparsers.add_parser("append-log", help="Append a structured log entry to log.md.")
    log_parser.add_argument("--action", required=True)
    log_parser.add_argument("--entity-type", required=True)
    log_parser.add_argument("--title", required=True)
    log_parser.add_argument("--path")
    log_parser.add_argument("--source")
    log_parser.add_argument("--related", nargs="*", default=[])
    log_parser.add_argument("--details")
    log_parser.set_defaults(
        func=lambda args: print(
            append_log_entry(
                action=args.action,
                entity_type=args.entity_type,
                title=args.title,
                path=args.path or "",
                source=args.source or "",
                related=args.related,
                details=args.details or "",
            )
        )
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
