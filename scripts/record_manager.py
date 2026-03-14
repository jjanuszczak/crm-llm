import argparse
import os
import sys
from datetime import date

from frontmatter_utils import parse_markdown_frontmatter, write_frontmatter_file
from lead_manager import get_crm_data_path, slugify


LOGIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
NOTE_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "note-template.md")
ACTIVITY_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "activity-template.md")
VALID_PARENT_TYPES = {"lead", "contact", "account", "opportunity", "deal", "activity"}
VALID_ACTIVITY_TYPES = {"call", "email", "meeting", "analysis", "note-derived"}
VALID_ACTIVITY_STATUSES = {"completed", "scheduled", "cancelled"}

CRM_DATA_PATH = get_crm_data_path()
NOTES_DIR = os.path.join(CRM_DATA_PATH, "Notes")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")


def ensure_dirs():
    os.makedirs(NOTES_DIR, exist_ok=True)
    os.makedirs(ACTIVITIES_DIR, exist_ok=True)


def render_template(path, replacements):
    with open(path, "r", encoding="utf-8") as handle:
        rendered = handle.read()
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def parse_secondary_links(values):
    links = []
    for value in values or []:
        text = value.strip()
        if not text:
            continue
        if not (text.startswith("[[") and text.endswith("]]")):
            text = f"[[{text}]]"
        if text not in links:
            links.append(text)
    return links


def create_note(args):
    ensure_dirs()
    if args.primary_parent_type not in VALID_PARENT_TYPES:
        raise ValueError(f"Invalid primary-parent-type '{args.primary_parent_type}'.")

    note_id = slugify(args.title)
    file_path = os.path.join(NOTES_DIR, f"{note_id}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Note already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        NOTE_TEMPLATE_PATH,
        {
            "note-id": note_id,
            "Note Title": args.title,
            "Owner": args.owner,
            "lead | contact | account | opportunity | deal | activity": args.primary_parent_type,
            "Primary Parent": args.primary_parent,
            "Secondary Link 1": args.secondary_links[0] if args.secondary_links else args.primary_parent,
            "manual | inbox | gmail | calendar | ai-generated": args.source,
            "Source Reference": args.source_ref or "",
            "YYYY-MM-DD": today,
        },
    )
    frontmatter, body = parse_markdown_frontmatter(rendered)
    frontmatter["secondary-links"] = parse_secondary_links(args.secondary_links)
    body = body.replace("{{Durable background, interpretation, research, or strategic memory.}}", args.context or "")
    body = body.replace("{{Implication 1}}", args.implication_1 or "")
    body = body.replace("{{Implication 2}}", args.implication_2 or "")
    write_frontmatter_file(file_path, frontmatter, body)
    print(file_path)


def create_activity(args):
    ensure_dirs()
    if args.primary_parent_type not in VALID_PARENT_TYPES:
        raise ValueError(f"Invalid primary-parent-type '{args.primary_parent_type}'.")
    if args.activity_type not in VALID_ACTIVITY_TYPES:
        raise ValueError(f"Invalid activity-type '{args.activity_type}'.")
    if args.status not in VALID_ACTIVITY_STATUSES:
        raise ValueError(f"Invalid activity status '{args.status}'.")

    activity_id = slugify(args.title)
    file_path = os.path.join(ACTIVITIES_DIR, f"{activity_id}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Activity already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    activity_date = args.date or today
    rendered = render_template(
        ACTIVITY_TEMPLATE_PATH,
        {
            "activity-id": activity_id,
            "Activity Name": args.title,
            "call | email | meeting | analysis | note-derived": args.activity_type,
            "Owner": args.owner,
            "YYYY-MM-DD": activity_date,
            "opportunity | contact | account | lead | deal": args.primary_parent_type,
            "Primary Parent": args.primary_parent,
            "Secondary Link 1": args.secondary_links[0] if args.secondary_links else args.primary_parent,
            "manual | gmail | calendar | inbox": args.source,
            "Source Reference": args.source_ref or "",
            "email-link": args.email_link or "",
            "meeting-notes": args.meeting_notes or "",
        },
    )
    frontmatter, body = parse_markdown_frontmatter(rendered)
    frontmatter["status"] = args.status
    frontmatter["secondary-links"] = parse_secondary_links(args.secondary_links)
    body = body.replace("{{activity-name}}", args.title)
    body = body.replace("{{A brief (1-2 sentence) description of the purpose of this activity.}}", args.summary or "")
    body = body.replace("{{High-level results of the activity. What was achieved?}}", args.outcomes or "")
    body = body.replace("{{Comprehensive notes from the call, meeting, or analysis. Use bullet points for readability.}}", "")
    body = body.replace("{{How did the contact react? Enthusiastic, skeptical, neutral?}}", "")
    write_frontmatter_file(file_path, frontmatter, body)
    print(file_path)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage first-class Notes and Activities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    note_parser = subparsers.add_parser("create-note", help="Create a first-class Note record.")
    note_parser.add_argument("--title", required=True)
    note_parser.add_argument("--owner", default="john")
    note_parser.add_argument("--primary-parent-type", required=True)
    note_parser.add_argument("--primary-parent", required=True)
    note_parser.add_argument("--secondary-links", nargs="*", default=[])
    note_parser.add_argument("--source", default="manual")
    note_parser.add_argument("--source-ref")
    note_parser.add_argument("--context")
    note_parser.add_argument("--implication-1")
    note_parser.add_argument("--implication-2")
    note_parser.set_defaults(func=create_note)

    activity_parser = subparsers.add_parser("create-activity", help="Create a first-class Activity record.")
    activity_parser.add_argument("--title", required=True)
    activity_parser.add_argument("--activity-type", required=True)
    activity_parser.add_argument("--status", default="completed")
    activity_parser.add_argument("--owner", default="john")
    activity_parser.add_argument("--date")
    activity_parser.add_argument("--primary-parent-type", required=True)
    activity_parser.add_argument("--primary-parent", required=True)
    activity_parser.add_argument("--secondary-links", nargs="*", default=[])
    activity_parser.add_argument("--source", default="manual")
    activity_parser.add_argument("--source-ref")
    activity_parser.add_argument("--email-link")
    activity_parser.add_argument("--meeting-notes")
    activity_parser.add_argument("--summary")
    activity_parser.add_argument("--outcomes")
    activity_parser.set_defaults(func=create_activity)

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
