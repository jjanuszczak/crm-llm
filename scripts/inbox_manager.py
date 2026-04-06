import argparse
import os
import sys
from datetime import date

from frontmatter_utils import (
    bucketed_record_path,
    dated_record_id,
    find_markdown_file,
    frontmatter_date_value,
    load_frontmatter_file,
    parse_markdown_frontmatter,
    serialize_frontmatter,
    slugify,
    write_frontmatter_file,
)
from lead_manager import get_crm_data_path, link_for
from navigation_manager import append_log_entry, rebuild_index, record_mutation


VALID_STATUSES = {"new", "processing", "processed", "ignored"}
VALID_SOURCES = {"manual", "gmail", "calendar", "voice", "inbox-forward"}
LOGIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
INBOX_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "inbox-template.md")
NOTE_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "note-template.md")
ACTIVITY_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "activity-template.md")

CRM_DATA_PATH = get_crm_data_path()
INBOX_DIR = os.path.join(CRM_DATA_PATH, "Inbox")
NOTES_DIR = os.path.join(CRM_DATA_PATH, "Notes")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
TASKS_DIR = os.path.join(CRM_DATA_PATH, "Tasks")
LEADS_DIR = os.path.join(CRM_DATA_PATH, "Leads")


def ensure_dirs():
    for directory in [INBOX_DIR, NOTES_DIR, ACTIVITIES_DIR, TASKS_DIR, LEADS_DIR]:
        os.makedirs(directory, exist_ok=True)


def render_template(path, replacements):
    with open(path, "r", encoding="utf-8") as handle:
        rendered = handle.read()
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def find_inbox_path(identifier):
    if os.path.isfile(identifier):
        return identifier

    candidate = os.path.join(INBOX_DIR, identifier)
    if os.path.exists(candidate):
        return candidate

    if not identifier.endswith(".md"):
        candidate_md = os.path.join(INBOX_DIR, f"{identifier}.md")
        if os.path.exists(candidate_md):
            return candidate_md

        slug_path = os.path.join(INBOX_DIR, f"{slugify(identifier)}.md")
        if os.path.exists(slug_path):
            return slug_path

    raise FileNotFoundError(f"Inbox item not found: {identifier}")


def create_inbox_item(args):
    ensure_dirs()
    if args.source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{args.source}'.")

    item_id = slugify(args.title)
    file_path = os.path.join(INBOX_DIR, f"{item_id}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Inbox item already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        INBOX_TEMPLATE_PATH,
        {
            "inbox-id": item_id,
            "Inbox Item Title": args.title,
            "Owner": args.owner,
            "manual | gmail | calendar | voice | inbox-forward": args.source,
            "Source Reference": args.source_ref or "",
            "YYYY-MM-DD": today,
        },
    )

    frontmatter, body = parse_markdown_frontmatter(rendered)
    body = body.replace("{{Paste or summarize the raw input here.}}", args.content or "")
    if args.processing_notes:
        body = body.replace("{{Optional AI or user notes about how this should be triaged.}}", args.processing_notes)

    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Inbox",
        title=args.title,
        path=file_path,
        source=args.source,
        details="created inbox capture",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def update_status(path, status):
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid inbox status '{status}'.")
    frontmatter, body = load_frontmatter_file(path)
    frontmatter["status"] = status
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(path, frontmatter, body)


def note_path(title, note_date):
    return bucketed_record_path(NOTES_DIR, note_date, f"{slugify(title)}.md")


def activity_path(title, activity_date):
    activity_id = dated_record_id(activity_date, title)
    return bucketed_record_path(ACTIVITIES_DIR, activity_date, f"{activity_id}.md")


def create_note_from_inbox(frontmatter, parent_type, parent_name):
    note_id = f"{frontmatter['id']}-note"
    title = frontmatter["title"]
    note_date = frontmatter_date_value(frontmatter, "captured-at", "date-created") or date.today().strftime("%Y-%m-%d")
    existing_path = find_markdown_file(NOTES_DIR, slugify(title))
    if existing_path:
        return existing_path
    file_path = note_path(title, note_date)

    rendered = render_template(
        NOTE_TEMPLATE_PATH,
        {
            "note-id": note_id,
            "Note Title": title,
            "Owner": frontmatter.get("owner", "john"),
            "lead | contact | account | opportunity | deal | activity": parent_type,
            "Primary Parent": parent_name,
            "Secondary Link 1": parent_name,
            "manual | inbox | gmail | calendar | ai-generated": "inbox",
            "Source Reference": frontmatter.get("id", ""),
            "YYYY-MM-DD": note_date,
        },
    )
    note_frontmatter, note_body = parse_markdown_frontmatter(rendered)
    note_frontmatter["secondary-links"] = []
    note_body = note_body.replace("{{Durable background, interpretation, research, or strategic memory.}}", "Created from Inbox processing.")
    write_frontmatter_file(file_path, note_frontmatter, note_body)
    return file_path


def create_activity_from_inbox(frontmatter, parent_type, parent_name):
    title = frontmatter["title"]
    activity_date = frontmatter_date_value(frontmatter, "captured-at", "date-created") or date.today().strftime("%Y-%m-%d")
    activity_id = dated_record_id(activity_date, title)
    existing_path = find_markdown_file(ACTIVITIES_DIR, activity_id)
    if existing_path:
        return existing_path
    file_path = activity_path(title, activity_date)

    rendered = render_template(
        ACTIVITY_TEMPLATE_PATH,
        {
            "activity-id": activity_id,
            "Activity Name": title,
            "call | email | meeting | analysis | note-derived": "note-derived",
            "Owner": frontmatter.get("owner", "john"),
            "YYYY-MM-DD": activity_date,
            "opportunity | contact | account | lead | deal": parent_type,
            "Primary Parent": parent_name,
            "Secondary Link 1": parent_name,
            "manual | gmail | calendar | inbox": "inbox",
            "Source Reference": frontmatter.get("id", ""),
            "email-link": "",
            "meeting-notes": "",
        },
    )
    activity_frontmatter, activity_body = parse_markdown_frontmatter(rendered)
    activity_frontmatter["secondary-links"] = []
    activity_body = activity_body.replace("{{A brief (1-2 sentence) description of the purpose of this activity.}}", "Created from Inbox processing.")
    activity_body = activity_body.replace("{{activity-name}}", title)
    write_frontmatter_file(file_path, activity_frontmatter, activity_body)
    return file_path


def create_task_from_inbox(frontmatter, opportunity_name=""):
    title = frontmatter["title"]
    today = date.today().strftime("%Y-%m-%d")
    task_id = dated_record_id(today, title)
    existing_path = find_markdown_file(TASKS_DIR, task_id)
    if existing_path:
        return existing_path
    file_path = bucketed_record_path(TASKS_DIR, today, f"{task_id}.md")
    opportunity_link = link_for("Opportunities", slugify(opportunity_name)) if opportunity_name else ""
    content = (
        "---\n"
        f'id: "{task_id}"\n'
        f'task-name: "{title}"\n'
        "status: todo\n"
        "priority: medium\n"
        f'owner: "{frontmatter.get("owner", "john")}"\n'
        f"due-date: {today}\n"
        f"date-created: {today}\n"
        f"date-modified: {today}\n"
        f'primary-parent-type: "{"opportunity" if opportunity_link else "lead"}"\n'
        f'primary-parent: "{opportunity_link or link_for("Leads", slugify(title))}"\n'
        'account: ""\n'
        'contact: ""\n'
        f'opportunity: "{opportunity_link}"\n'
        f'lead: "{link_for("Leads", slugify(title)) if not opportunity_link else ""}"\n'
        "type: follow-up\n"
        'source: "inbox"\n'
        f'source-ref: "{frontmatter.get("id", "")}"\n'
        'email-link: ""\n'
        'meeting-notes: ""\n'
        "---\n\n"
        f"# **Task: {title}**\n\n## **Description**\nCreated from Inbox processing.\n"
    )
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return file_path


def create_lead_from_inbox(frontmatter):
    lead_name = frontmatter["title"]
    file_path = os.path.join(LEADS_DIR, f"{slugify(lead_name)}.md")
    if os.path.exists(file_path):
        return file_path

    today = date.today().strftime("%Y-%m-%d")
    content = (
        "---\n"
        f'id: "{slugify(lead_name)}"\n'
        f'lead-name: "{lead_name}"\n'
        'status: "new"\n'
        f'owner: "{frontmatter.get("owner", "john")}"\n'
        'lead-source: "inbox"\n'
        'person-name: ""\n'
        'company-name: ""\n'
        'email: ""\n'
        'linkedin: ""\n'
        'priority: "medium"\n'
        f'source-ref: "{frontmatter.get("id", "")}"\n'
        f"date-created: {today}\n"
        f"date-modified: {today}\n"
        "---\n\n"
        f"# **Lead: {lead_name}**\n\n## **Summary**\nCreated from Inbox processing.\n"
    )
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return file_path


def process_inbox_item(args):
    ensure_dirs()
    path = find_inbox_path(args.item)
    frontmatter, body = load_frontmatter_file(path)
    outputs = []
    parent_type = args.primary_parent_type
    parent_name = args.primary_parent

    if "note" in args.outputs:
        if not parent_type or not parent_name:
            raise ValueError("Creating a note from Inbox requires --primary-parent-type and --primary-parent.")
        outputs.append(("note", create_note_from_inbox(frontmatter, parent_type, parent_name)))

    if "activity" in args.outputs:
        if not parent_type or not parent_name:
            raise ValueError("Creating an activity from Inbox requires --primary-parent-type and --primary-parent.")
        outputs.append(("activity", create_activity_from_inbox(frontmatter, parent_type, parent_name)))

    if "task" in args.outputs:
        outputs.append(("task", create_task_from_inbox(frontmatter, args.opportunity_name or "")))

    if "lead" in args.outputs:
        outputs.append(("lead", create_lead_from_inbox(frontmatter)))

    if args.delete_processed:
        os.remove(path)
        print(f"deleted: {path}")
        path_for_log = ""
        details = f"deleted processed inbox item; outputs={','.join(record_type for record_type, _ in outputs)}"
    else:
        update_status(path, "processed")
        print(f"processed: {path}")
        path_for_log = path
        details = f"processed inbox item; outputs={','.join(record_type for record_type, _ in outputs)}"

    for record_type, output_path in outputs:
        print(f"{record_type}: {output_path}")

    related = [output_path for _, output_path in outputs]
    append_log_entry(
        action="process",
        entity_type="Inbox",
        title=frontmatter.get("title", os.path.basename(path)),
        path=path_for_log,
        source=frontmatter.get("source", ""),
        related=related,
        details=details,
        crm_data_path=CRM_DATA_PATH,
    )
    rebuild_index(CRM_DATA_PATH)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage v4 Inbox items.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new inbox item.")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--content")
    create_parser.add_argument("--processing-notes")
    create_parser.set_defaults(func=create_inbox_item)

    process_parser = subparsers.add_parser("process", help="Process an inbox item into durable outputs.")
    process_parser.add_argument("item")
    process_parser.add_argument("--outputs", nargs="+", required=True, choices=["note", "activity", "task", "lead"])
    process_parser.add_argument("--primary-parent-type")
    process_parser.add_argument("--primary-parent")
    process_parser.add_argument("--opportunity-name")
    process_parser.add_argument("--delete-processed", action="store_true")
    process_parser.set_defaults(func=process_inbox_item)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:  # pragma: no cover - CLI errors
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
