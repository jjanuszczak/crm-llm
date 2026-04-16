import argparse
import os
import sys
from datetime import date

from crm_manager_utils import link_for_path, load_display_name, replace_section, resolve_optional_record_path, resolve_record_path
from frontmatter_utils import bucketed_record_path, dated_record_id, find_markdown_file, load_frontmatter_file, write_frontmatter_file
from lead_manager import get_crm_data_path
from navigation_manager import record_mutation


VALID_STATUSES = {"todo", "waiting", "completed", "in-progress", "blocked", "done", "canceled"}
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_PARENT_TYPES = {"lead", "contact", "account", "opportunity", "deal"}
VALID_SOURCES = {"manual", "activity", "inbox", "gmail", "calendar"}

CRM_DATA_PATH = get_crm_data_path()
TASKS_DIR = os.path.join(CRM_DATA_PATH, "Tasks")
LEADS_DIR = os.path.join(CRM_DATA_PATH, "Leads")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")


def ensure_dirs():
    os.makedirs(TASKS_DIR, exist_ok=True)


def normalize_status(value):
    if value == "done":
        return "completed"
    return value


def parent_dir_for_type(parent_type):
    return {
        "lead": LEADS_DIR,
        "contact": CONTACTS_DIR,
        "account": ACCOUNTS_DIR,
        "opportunity": OPPORTUNITIES_DIR,
        "deal": DEALS_DIR,
    }[parent_type]


def cmd_create(args):
    ensure_dirs()
    status = normalize_status(args.status)
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{args.status}'.")
    if args.priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority '{args.priority}'.")
    if args.primary_parent_type not in VALID_PARENT_TYPES:
        raise ValueError(f"Invalid primary-parent-type '{args.primary_parent_type}'.")
    if args.source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{args.source}'.")

    parent_path = resolve_record_path(
        parent_dir_for_type(args.primary_parent_type),
        CRM_DATA_PATH,
        args.primary_parent,
        args.primary_parent_type.title(),
    )
    task_id = dated_record_id(args.due_date, args.name)
    existing_path = find_markdown_file(TASKS_DIR, task_id)
    if existing_path:
        raise FileExistsError(f"Task already exists: {existing_path}")

    account_path = resolve_optional_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, args.account, "Account")
    contact_path = resolve_optional_record_path(CONTACTS_DIR, CRM_DATA_PATH, args.contact, "Contact")
    opportunity_path = resolve_optional_record_path(OPPORTUNITIES_DIR, CRM_DATA_PATH, args.opportunity, "Opportunity")
    lead_path = resolve_optional_record_path(LEADS_DIR, CRM_DATA_PATH, args.lead, "Lead")

    if args.primary_parent_type == "account" and not account_path:
        account_path = parent_path
    if args.primary_parent_type == "contact" and not contact_path:
        contact_path = parent_path
    if args.primary_parent_type == "opportunity" and not opportunity_path:
        opportunity_path = parent_path
    if args.primary_parent_type == "lead" and not lead_path:
        lead_path = parent_path

    file_path = bucketed_record_path(TASKS_DIR, args.due_date, f"{task_id}.md")
    today = date.today().strftime("%Y-%m-%d")
    frontmatter = {
        "id": task_id,
        "task-name": args.name,
        "status": status,
        "priority": args.priority,
        "owner": args.owner,
        "due-date": args.due_date,
        "date-created": today,
        "date-modified": today,
        "primary-parent-type": args.primary_parent_type,
        "primary-parent": link_for_path(parent_path, CRM_DATA_PATH),
        "account": link_for_path(account_path, CRM_DATA_PATH) if account_path else "",
        "contact": link_for_path(contact_path, CRM_DATA_PATH) if contact_path else "",
        "opportunity": link_for_path(opportunity_path, CRM_DATA_PATH) if opportunity_path else "",
        "lead": link_for_path(lead_path, CRM_DATA_PATH) if lead_path else "",
        "type": args.type,
        "source": args.source,
        "source-ref": args.source_ref or "",
        "google-task-id": args.google_task_id or "",
        "google-task-list-id": args.google_task_list_id or "",
        "email-link": args.email_link or "",
        "meeting-notes": args.meeting_notes or "",
    }
    body = "\n".join(
        [
            f"# **Task: {args.name}**",
            "",
            "## **Description**",
            args.description or "",
            "",
            "## **Context & Background**",
            args.context or "",
            "",
            "## **Notes / Updates**",
            f"*   {args.notes or ''}",
            "",
            "## **Outcome / Completion Notes**",
            args.outcome or "",
            "",
        ]
    )
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Task",
        title=args.name,
        path=file_path,
        source=args.source,
        related=[frontmatter["primary-parent"], frontmatter["account"], frontmatter["contact"], frontmatter["opportunity"], frontmatter["lead"]],
        details=f"status={status}; priority={args.priority}; due-date={args.due_date}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def find_task_path(identifier):
    return resolve_record_path(TASKS_DIR, CRM_DATA_PATH, identifier, "Task")


def cmd_update(args):
    path = find_task_path(args.task)
    frontmatter, body = load_frontmatter_file(path)
    if args.status is not None:
        status = normalize_status(args.status)
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{args.status}'.")
        frontmatter["status"] = status
    if args.priority is not None:
        if args.priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{args.priority}'.")
        frontmatter["priority"] = args.priority
    if args.due_date is not None:
        frontmatter["due-date"] = args.due_date
    if args.source is not None:
        if args.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{args.source}'.")
        frontmatter["source"] = args.source
    if args.source_ref is not None:
        frontmatter["source-ref"] = args.source_ref
    if args.google_task_id is not None:
        frontmatter["google-task-id"] = args.google_task_id
    if args.google_task_list_id is not None:
        frontmatter["google-task-list-id"] = args.google_task_list_id
    if args.email_link is not None:
        frontmatter["email-link"] = args.email_link
    if args.meeting_notes is not None:
        frontmatter["meeting-notes"] = args.meeting_notes
    if args.account is not None:
        account_path = resolve_optional_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, args.account, "Account")
        frontmatter["account"] = link_for_path(account_path, CRM_DATA_PATH) if account_path else ""
    if args.contact is not None:
        contact_path = resolve_optional_record_path(CONTACTS_DIR, CRM_DATA_PATH, args.contact, "Contact")
        frontmatter["contact"] = link_for_path(contact_path, CRM_DATA_PATH) if contact_path else ""
    if args.opportunity is not None:
        opportunity_path = resolve_optional_record_path(OPPORTUNITIES_DIR, CRM_DATA_PATH, args.opportunity, "Opportunity")
        frontmatter["opportunity"] = link_for_path(opportunity_path, CRM_DATA_PATH) if opportunity_path else ""
    if args.lead is not None:
        lead_path = resolve_optional_record_path(LEADS_DIR, CRM_DATA_PATH, args.lead, "Lead")
        frontmatter["lead"] = link_for_path(lead_path, CRM_DATA_PATH) if lead_path else ""
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")

    if args.description is not None:
        body = replace_section(body, "Description", args.description)
    if args.context is not None:
        body = replace_section(body, "Context & Background", args.context)
    if args.notes is not None:
        body = replace_section(body, "Notes / Updates", args.notes)
    if args.outcome is not None:
        body = replace_section(body, "Outcome / Completion Notes", args.outcome)

    write_frontmatter_file(path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Task",
        title=frontmatter.get("task-name", load_display_name(path)),
        path=path,
        source=frontmatter.get("source", ""),
        related=[frontmatter.get("primary-parent", ""), frontmatter.get("account", ""), frontmatter.get("contact", ""), frontmatter.get("opportunity", ""), frontmatter.get("lead", "")],
        details="updated task metadata/body",
        crm_data_path=CRM_DATA_PATH,
    )
    print(path)


def cmd_set_status(args):
    path = find_task_path(args.task)
    frontmatter, body = load_frontmatter_file(path)
    status = normalize_status(args.status)
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{args.status}'.")
    frontmatter["status"] = status
    if args.review_date:
        frontmatter["due-date"] = args.review_date
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    if args.notes is not None:
        body = replace_section(body, "Notes / Updates", args.notes)
    if args.outcome is not None:
        body = replace_section(body, "Outcome / Completion Notes", args.outcome)
    write_frontmatter_file(path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Task",
        title=frontmatter.get("task-name", load_display_name(path)),
        path=path,
        source=frontmatter.get("source", ""),
        related=[frontmatter.get("primary-parent", "")],
        details=f"set status to {status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(path)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Task records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a Task record.")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--status", default="todo")
    create_parser.add_argument("--priority", default="medium")
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--due-date", required=True)
    create_parser.add_argument("--primary-parent-type", required=True)
    create_parser.add_argument("--primary-parent", required=True)
    create_parser.add_argument("--account")
    create_parser.add_argument("--contact")
    create_parser.add_argument("--opportunity")
    create_parser.add_argument("--lead")
    create_parser.add_argument("--type", default="follow-up")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--google-task-id")
    create_parser.add_argument("--google-task-list-id")
    create_parser.add_argument("--email-link")
    create_parser.add_argument("--meeting-notes")
    create_parser.add_argument("--description")
    create_parser.add_argument("--context")
    create_parser.add_argument("--notes")
    create_parser.add_argument("--outcome")
    create_parser.set_defaults(func=cmd_create)

    update_parser = subparsers.add_parser("update", help="Update a Task record.")
    update_parser.add_argument("task")
    update_parser.add_argument("--status")
    update_parser.add_argument("--priority")
    update_parser.add_argument("--due-date")
    update_parser.add_argument("--account")
    update_parser.add_argument("--contact")
    update_parser.add_argument("--opportunity")
    update_parser.add_argument("--lead")
    update_parser.add_argument("--source")
    update_parser.add_argument("--source-ref")
    update_parser.add_argument("--google-task-id")
    update_parser.add_argument("--google-task-list-id")
    update_parser.add_argument("--email-link")
    update_parser.add_argument("--meeting-notes")
    update_parser.add_argument("--description")
    update_parser.add_argument("--context")
    update_parser.add_argument("--notes")
    update_parser.add_argument("--outcome")
    update_parser.set_defaults(func=cmd_update)

    status_parser = subparsers.add_parser("set-status", help="Update only the task status and optional review date.")
    status_parser.add_argument("task")
    status_parser.add_argument("--status", required=True)
    status_parser.add_argument("--review-date")
    status_parser.add_argument("--notes")
    status_parser.add_argument("--outcome")
    status_parser.set_defaults(func=cmd_set_status)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
