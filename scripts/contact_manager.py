import argparse
import os
import sys
from datetime import date

from crm_manager_utils import (
    display_name,
    link_for_path,
    load_display_name,
    replace_section,
    resolve_optional_record_path,
    resolve_record_path,
)
from frontmatter_utils import load_frontmatter_file, parse_markdown_frontmatter, slugify, write_frontmatter_file
from lead_manager import get_crm_data_path
from navigation_manager import record_mutation


VALID_RELATIONSHIP_STATUS = {"active", "dormant", "archived"}
VALID_PRIORITY = {"high", "medium", "low"}
VALID_SOURCES = {"manual", "lead-conversion", "network", "conference", "cold-outreach", "gmail", "calendar", "referral", "linkedin"}

LOGIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
CONTACT_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "contact-template.md")
CRM_DATA_PATH = get_crm_data_path()
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")


def ensure_dirs():
    os.makedirs(CONTACTS_DIR, exist_ok=True)


def read_template():
    with open(CONTACT_TEMPLATE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def create_body(full_name, role, linked_entity_name, expertise, focus, insight_1, insight_2, hook_1, hook_2, email):
    rendered = read_template()
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = body.replace("{{Full Name}}", full_name)
    body = body.replace("{{Role}}", role or "")
    body = body.replace("{{Account Link or Deal Link}}", linked_entity_name or "")
    body = body.replace("{{Area 1, Area 2, Area 3}}", expertise or "")
    body = body.replace("{{Brief description of current professional focus}}", focus or "")
    body = body.replace("{{Detail}}", insight_1 or "", 1)
    body = body.replace("{{Detail}}", insight_2 or "", 1)
    body = body.replace('"...?"', hook_1 or "...?", 1)
    body = body.replace('"...?"', hook_2 or "...?", 1)
    body = body.replace("{{email}}", email or "")
    return body


def validate_args(args):
    if args.relationship_status not in VALID_RELATIONSHIP_STATUS:
        raise ValueError(f"Invalid relationship-status '{args.relationship_status}'.")
    if args.priority not in VALID_PRIORITY:
        raise ValueError(f"Invalid priority '{args.priority}'.")
    if args.source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{args.source}'.")


def cmd_create(args):
    ensure_dirs()
    validate_args(args)
    slug = slugify(args.name)
    file_path = os.path.join(CONTACTS_DIR, f"{slug}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Contact already exists: {file_path}")

    account_path = resolve_optional_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, args.account, "Account")
    deal_path = resolve_optional_record_path(DEALS_DIR, CRM_DATA_PATH, args.deal, "Deal")
    account_link = link_for_path(account_path, CRM_DATA_PATH) if account_path else ""
    deal_link = link_for_path(deal_path, CRM_DATA_PATH) if deal_path else ""
    linked_entity_name = ""
    if account_path:
        account_fm, _ = load_frontmatter_file(account_path)
        linked_entity_name = display_name(account_fm, account_path)
    elif deal_path:
        deal_fm, _ = load_frontmatter_file(deal_path)
        linked_entity_name = display_name(deal_fm, deal_path)

    today = date.today().strftime("%Y-%m-%d")
    frontmatter = {
        "id": f"contact-{slug}",
        "full-name": args.name,
        "nickname": args.nickname or args.name.split()[0],
        "owner": args.owner,
        "account": account_link,
        "deal": deal_link,
        "linkedin": args.linkedin or "",
        "email": args.email or "",
        "mobile": args.mobile or "",
        "source": args.source,
        "source-ref": args.source_ref or "",
        "relationship-status": args.relationship_status,
        "priority": args.priority,
        "last-contacted": args.last_contacted or today,
        "date-created": today,
        "date-modified": today,
    }
    body = create_body(
        args.name,
        args.role,
        linked_entity_name,
        args.expertise,
        args.focus,
        args.insight_1,
        args.insight_2,
        args.hook_1,
        args.hook_2,
        args.email,
    )
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Contact",
        title=args.name,
        path=file_path,
        source=args.source,
        related=[account_link, deal_link],
        details=f"relationship-status={args.relationship_status}; priority={args.priority}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def find_contact_path(identifier):
    return resolve_record_path(CONTACTS_DIR, CRM_DATA_PATH, identifier, "Contact")


def cmd_update(args):
    path = find_contact_path(args.contact)
    frontmatter, body = load_frontmatter_file(path)

    if args.name:
        frontmatter["full-name"] = args.name
    if args.nickname is not None:
        frontmatter["nickname"] = args.nickname
    if args.account is not None:
        account_path = resolve_optional_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, args.account, "Account")
        frontmatter["account"] = link_for_path(account_path, CRM_DATA_PATH) if account_path else ""
    if args.deal is not None:
        deal_path = resolve_optional_record_path(DEALS_DIR, CRM_DATA_PATH, args.deal, "Deal")
        frontmatter["deal"] = link_for_path(deal_path, CRM_DATA_PATH) if deal_path else ""
    if args.linkedin is not None:
        frontmatter["linkedin"] = args.linkedin
    if args.email is not None:
        frontmatter["email"] = args.email
    if args.mobile is not None:
        frontmatter["mobile"] = args.mobile
    if args.source is not None:
        if args.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{args.source}'.")
        frontmatter["source"] = args.source
    if args.source_ref is not None:
        frontmatter["source-ref"] = args.source_ref
    if args.relationship_status is not None:
        if args.relationship_status not in VALID_RELATIONSHIP_STATUS:
            raise ValueError(f"Invalid relationship-status '{args.relationship_status}'.")
        frontmatter["relationship-status"] = args.relationship_status
    if args.priority is not None:
        if args.priority not in VALID_PRIORITY:
            raise ValueError(f"Invalid priority '{args.priority}'.")
        frontmatter["priority"] = args.priority
    if args.last_contacted:
        frontmatter["last-contacted"] = args.last_contacted
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")

    if args.professional_overview is not None:
        body = replace_section(body, "Professional Overview", args.professional_overview)
    if args.insights is not None:
        body = replace_section(body, 'Strategic Insights & "Little Known" Facts', args.insights)
    if args.hooks is not None:
        body = replace_section(body, "Engagement Hooks for Forging Connection", args.hooks)

    write_frontmatter_file(path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Contact",
        title=frontmatter.get("full-name", load_display_name(path)),
        path=path,
        source=frontmatter.get("source", ""),
        related=[frontmatter.get("account", ""), frontmatter.get("deal", "")],
        details="updated contact metadata/body",
        crm_data_path=CRM_DATA_PATH,
    )
    print(path)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Contact records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a Contact record.")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--nickname")
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--account")
    create_parser.add_argument("--deal")
    create_parser.add_argument("--linkedin")
    create_parser.add_argument("--email")
    create_parser.add_argument("--mobile")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--relationship-status", default="active")
    create_parser.add_argument("--priority", default="medium")
    create_parser.add_argument("--last-contacted")
    create_parser.add_argument("--role")
    create_parser.add_argument("--expertise")
    create_parser.add_argument("--focus")
    create_parser.add_argument("--insight-1")
    create_parser.add_argument("--insight-2")
    create_parser.add_argument("--hook-1")
    create_parser.add_argument("--hook-2")
    create_parser.set_defaults(func=cmd_create)

    update_parser = subparsers.add_parser("update", help="Update a Contact record.")
    update_parser.add_argument("contact")
    update_parser.add_argument("--name")
    update_parser.add_argument("--nickname")
    update_parser.add_argument("--account")
    update_parser.add_argument("--deal")
    update_parser.add_argument("--linkedin")
    update_parser.add_argument("--email")
    update_parser.add_argument("--mobile")
    update_parser.add_argument("--source")
    update_parser.add_argument("--source-ref")
    update_parser.add_argument("--relationship-status")
    update_parser.add_argument("--priority")
    update_parser.add_argument("--last-contacted")
    update_parser.add_argument("--professional-overview")
    update_parser.add_argument("--insights")
    update_parser.add_argument("--hooks")
    update_parser.set_defaults(func=cmd_update)

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
