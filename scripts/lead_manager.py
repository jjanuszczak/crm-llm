import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

from frontmatter_utils import (
    bucketed_record_path,
    frontmatter_date_value,
    iter_markdown_files,
    load_frontmatter_file,
    serialize_frontmatter,
    write_frontmatter_file,
)


VALID_STATUSES = {"new", "prospect", "engaged", "qualified", "converted", "disqualified"}
TRANSITIONS = {
    "new": {"prospect", "engaged", "disqualified"},
    "prospect": {"engaged", "qualified", "disqualified"},
    "engaged": {"prospect", "qualified", "disqualified"},
    "qualified": {"engaged", "disqualified"},
    "disqualified": {"prospect", "engaged"},
}
SOURCE_CHOICES = {"manual", "gmail", "calendar", "inbox", "referral", "linkedin"}
PRIORITY_CHOICES = {"high", "medium", "low"}


def get_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return os.path.abspath(env_override)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logic_root = os.path.abspath(os.path.join(script_dir, "../"))
    env_path = os.path.join(logic_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    path = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.abspath(os.path.join(logic_root, path)) if not os.path.isabs(path) else path
    return os.getenv("CRM_DATA_PATH", os.getcwd())


CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
LEADS_DIR = os.path.join(CRM_DATA_PATH, "Leads")
CONVERTED_LEADS_DIR = os.path.join(LEADS_DIR, "Converted")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")
NOTES_DIR = os.path.join(CRM_DATA_PATH, "Notes")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
TASKS_DIR = os.path.join(CRM_DATA_PATH, "Tasks")
LOGIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
LEAD_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "lead-template.md")


def slugify(value):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip())
    return re.sub(r"-{2,}", "-", cleaned).strip("-") or "lead"


def ensure_leads_dir():
    os.makedirs(LEADS_DIR, exist_ok=True)


def ensure_core_dirs():
    for directory in [ORGANIZATIONS_DIR, LEADS_DIR, CONVERTED_LEADS_DIR, ACCOUNTS_DIR, CONTACTS_DIR, OPPORTUNITIES_DIR, NOTES_DIR, ACTIVITIES_DIR, TASKS_DIR]:
        os.makedirs(directory, exist_ok=True)


def read_template():
    with open(LEAD_TEMPLATE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def render_template(template, replacements):
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def find_lead_path(identifier):
    path = Path(identifier)
    if path.is_file():
        return str(path)

    candidate = os.path.join(LEADS_DIR, identifier)
    if os.path.exists(candidate):
        return candidate

    if not identifier.endswith(".md"):
        candidate_md = os.path.join(LEADS_DIR, f"{identifier}.md")
        if os.path.exists(candidate_md):
            return candidate_md

        slug_path = os.path.join(LEADS_DIR, f"{slugify(identifier)}.md")
        if os.path.exists(slug_path):
            return slug_path

    raise FileNotFoundError(f"Lead not found: {identifier}")


def link_for(directory, name):
    return f"[[{directory}/{name}]]"


def extract_link_name(value):
    if not value:
        return ""
    text = str(value).strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text


def same_link(value, expected):
    return extract_link_name(value) == extract_link_name(expected)


def next_year_string():
    return str(date.today().year)


def validate_source(value):
    if value not in SOURCE_CHOICES:
        raise ValueError(f"Invalid lead-source '{value}'. Expected one of: {', '.join(sorted(SOURCE_CHOICES))}")
    return value


def validate_priority(value):
    if value not in PRIORITY_CHOICES:
        raise ValueError(f"Invalid priority '{value}'. Expected one of: {', '.join(sorted(PRIORITY_CHOICES))}")
    return value


def validate_transition(current, target):
    if target not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{target}'.")
    if current == target:
        return
    allowed = TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid transition: {current} -> {target}")


def validate_ready_for_qualification(frontmatter):
    missing = []
    if not frontmatter.get("person-name"):
        missing.append("person-name")
    if not frontmatter.get("company-name"):
        missing.append("company-name")
    return missing


def validate_ready_for_conversion(frontmatter):
    missing = validate_ready_for_qualification(frontmatter)
    if not frontmatter.get("status") == "qualified":
        missing.append("status=qualified")
    return missing


def cmd_create(args):
    ensure_core_dirs()
    validate_source(args.lead_source)
    validate_priority(args.priority)
    if args.status == "qualified":
        missing = []
        if not args.person_name:
            missing.append("person-name")
        if not args.company_name:
            missing.append("company-name")
        if missing:
            raise ValueError(
                "Lead cannot be created as qualified until required fields are populated: "
                + ", ".join(missing)
            )

    today = date.today().strftime("%Y-%m-%d")
    lead_id = slugify(args.name)
    file_name = f"{lead_id}.md"
    file_path = os.path.join(LEADS_DIR, file_name)
    if os.path.exists(file_path):
        raise FileExistsError(f"Lead already exists: {file_path}")

    template = read_template()
    rendered = render_template(
        template,
        {
            "lead-id": lead_id,
            "Lead Name": args.name,
            "Lead Status": args.status,
            "Owner": args.owner,
            "manual | gmail | calendar | inbox | referral | linkedin": args.lead_source,
            "Person Name": args.person_name or "",
            "Company Name": args.company_name or "",
            "Email Address": args.email or "",
            "LinkedIn URL": args.linkedin or "",
            "high | medium | low": args.priority,
            "Source Reference": args.source_ref or "",
            "YYYY-MM-DD": today,
            "Signal 1": "",
            "Signal 2": "",
            "Question 1": "",
            "Question 2": "",
        },
    )

    try:
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    print(file_path)


def set_status(file_path, target_status):
    frontmatter, body = load_frontmatter_file(file_path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {file_path}")

    current_status = frontmatter.get("status", "new")
    validate_transition(current_status, target_status)

    if target_status == "qualified":
        missing = validate_ready_for_qualification(frontmatter)
        if missing:
            raise ValueError(
                "Lead cannot move to qualified until required fields are populated: "
                + ", ".join(missing)
            )

    frontmatter["status"] = target_status
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)


def cmd_set_status(args):
    file_path = find_lead_path(args.lead)
    set_status(file_path, args.status)
    print(file_path)


def cmd_revive(args):
    file_path = find_lead_path(args.lead)
    frontmatter, body = load_frontmatter_file(file_path)
    if frontmatter.get("status") != "disqualified":
        raise ValueError("Only disqualified leads can be revived.")

    target_status = "engaged" if args.meaningful_two_way else "prospect"
    frontmatter["status"] = target_status
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    print(file_path)


def cmd_validate(args):
    file_path = find_lead_path(args.lead)
    frontmatter, _ = load_frontmatter_file(file_path)
    missing = validate_ready_for_qualification(frontmatter)
    if missing:
        print("missing:", ", ".join(missing))
        raise SystemExit(1)
    print("ready-for-qualification")


def importance_from_priority(value):
    if value in PRIORITY_CHOICES:
        return value
    return "medium"


def create_organization_record(company_name, source_lead):
    slug = slugify(company_name)
    file_path = os.path.join(ORGANIZATIONS_DIR, f"{slug}.md")
    if os.path.exists(file_path):
        return file_path

    today = date.today().strftime("%Y-%m-%d")
    frontmatter = {
        "id": f"org-{slug}",
        "organization-name": company_name,
        "domain": "",
        "headquarters": "",
        "industry": "",
        "size": 0,
        "url": "",
        "organization-class": "operating-company",
        "organization-subtype": "",
        "investment-mandate": [],
        "check-size": "",
        "last-contacted": today,
        "source": "lead-conversion",
        "source-ref": source_lead,
        "date-created": today,
        "date-modified": today,
    }
    body = f"# **Organization: {company_name}**\n\n## **Identity**\nCreated from lead conversion.\n"
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def create_account_record(company_name, owner, source_lead, strategic_importance="medium", organization_path=None):
    slug = slugify(company_name)
    file_path = os.path.join(ACCOUNTS_DIR, f"{slug}.md")
    if os.path.exists(file_path):
        return file_path

    today = date.today().strftime("%Y-%m-%d")
    organization_slug = os.path.splitext(os.path.basename(organization_path))[0] if organization_path else slug
    frontmatter = {
        "id": f"acct-{slug}",
        "organization": link_for("Organizations", organization_slug),
        "owner": owner or "john",
        "relationship-stage": "prospect",
        "strategic-importance": importance_from_priority(strategic_importance),
        "source": "lead-conversion",
        "source-ref": source_lead,
        "source-lead": source_lead,
        "last-contacted": today,
        "date-created": today,
        "date-modified": today,
    }
    body = f"# **Account Relationship: {company_name}**\n\n## **Relationship Summary**\nCreated from lead conversion.\n"
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def create_contact_record(person_name, account_name, lead_frontmatter):
    slug = slugify(person_name)
    file_path = os.path.join(CONTACTS_DIR, f"{slug}.md")
    if os.path.exists(file_path):
        return file_path

    today = date.today().strftime("%Y-%m-%d")
    nickname = person_name.split()[0] if person_name else ""
    lead_link = link_for("Leads", slugify(lead_frontmatter.get("lead-name", person_name)))
    frontmatter = {
        "id": slug,
        "full-name": person_name,
        "nickname": nickname,
        "owner": lead_frontmatter.get("owner", "john"),
        "account": link_for("Accounts", slugify(account_name)),
        "deal": "",
        "linkedin": lead_frontmatter.get("linkedin", ""),
        "email": lead_frontmatter.get("email", ""),
        "mobile": lead_frontmatter.get("phone", ""),
        "source": "lead-conversion",
        "source-ref": lead_link,
        "source-lead": lead_link,
        "relationship-status": "active",
        "priority": lead_frontmatter.get("priority", "medium"),
        "last-contacted": today,
        "date-created": today,
        "date-modified": today,
    }
    body = f"# **Profile: {person_name}**\n\n## **Professional Overview**\nCreated from lead conversion.\n"
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def create_opportunity_record(account_name, contact_name, source_lead, owner="john", opportunity_name=None, organization_path=None):
    account_slug = slugify(account_name)
    contact_slug = slugify(contact_name)
    year = next_year_string()
    computed_name = opportunity_name or f"{account_name} - Advisory - {year}"
    opportunity_slug = slugify(computed_name)
    file_path = os.path.join(OPPORTUNITIES_DIR, f"{opportunity_slug}.md")
    if os.path.exists(file_path):
        return file_path

    today = date.today().strftime("%Y-%m-%d")
    organization_slug = os.path.splitext(os.path.basename(organization_path))[0] if organization_path else account_slug
    frontmatter = {
        "id": opportunity_slug,
        "opportunity-name": computed_name,
        "owner": owner,
        "date-created": today,
        "date-modified": today,
        "account": link_for("Accounts", account_slug),
        "deal": "",
        "primary-contact": link_for("Contacts", contact_slug),
        "source-lead": source_lead,
        "organization": link_for("Organizations", organization_slug),
        "opportunity-type": "advisory",
        "is-active": True,
        "stage": "discovery",
        "commercial-value": 0,
        "close-date": today,
        "probability": 10,
        "product-service": "Advisory",
        "influencers": [],
        "source": "lead-conversion",
        "source-ref": source_lead,
        "lost-at-stage": "",
        "lost-reason": "",
        "lost-date": "",
    }
    body = f"# **Opportunity: {computed_name}**\n\n## **Executive Summary**\nCreated from lead conversion.\n"
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def copy_linked_records(directory, lead_link, source_type, new_primary_type, new_primary_link, secondary_links):
    if not os.path.exists(directory):
        return []

    copied = []
    for file_path in iter_markdown_files(directory):
        file_name = os.path.basename(file_path)
        frontmatter, body = load_frontmatter_file(file_path)
        if not frontmatter:
            continue

        matches_primary = (
            frontmatter.get("primary-parent-type") == source_type
            and same_link(frontmatter.get("primary-parent"), lead_link)
        )
        matches_secondary = any(same_link(link, lead_link) for link in frontmatter.get("secondary-links", []))
        if not (matches_primary or matches_secondary):
            continue

        cloned = dict(frontmatter)
        base_name = os.path.splitext(file_name)[0]
        cloned["id"] = f"{base_name}-converted-{slugify(new_primary_link)}"
        cloned["primary-parent-type"] = new_primary_type
        cloned["primary-parent"] = new_primary_link
        existing_secondary = [link for link in cloned.get("secondary-links", []) if not same_link(link, lead_link)]
        merged_secondary = []
        for link in existing_secondary + secondary_links + [lead_link]:
            if link and link not in merged_secondary and link != new_primary_link:
                merged_secondary.append(link)
        cloned["secondary-links"] = merged_secondary
        cloned["source-ref"] = frontmatter.get("source-ref") or lead_link
        cloned["date-modified"] = date.today().strftime("%Y-%m-%d")
        target_name = f"{base_name}-from-{slugify(extract_link_name(lead_link))}.md"
        record_date = frontmatter_date_value(frontmatter, "date", "due-date", "date-created", "date-modified") or date.today().strftime("%Y-%m-%d")
        target_path = bucketed_record_path(directory, record_date, target_name)
        write_frontmatter_file(target_path, cloned, body)
        copied.append(target_path)

    return copied


def move_open_tasks(lead_link, account_link, contact_link, opportunity_link):
    moved = []
    if not os.path.exists(TASKS_DIR):
        return moved

    for file_path in iter_markdown_files(TASKS_DIR):
        frontmatter, body = load_frontmatter_file(file_path)
        if not frontmatter:
            continue

        status = frontmatter.get("status")
        if status not in {"todo", "in-progress"}:
            continue

        linked_to_lead = same_link(frontmatter.get("lead"), lead_link)
        linked_to_primary_lead = (
            frontmatter.get("primary-parent-type") == "lead"
            and same_link(frontmatter.get("primary-parent"), lead_link)
        )
        if not (linked_to_lead or linked_to_primary_lead):
            continue

        frontmatter["account"] = account_link
        frontmatter["contact"] = contact_link
        frontmatter["opportunity"] = opportunity_link
        frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
        if linked_to_primary_lead:
            frontmatter["primary-parent-type"] = "opportunity"
            frontmatter["primary-parent"] = opportunity_link
        write_frontmatter_file(file_path, frontmatter, body)
        moved.append(file_path)
    return moved


def archive_converted_lead(file_path, frontmatter, body):
    os.makedirs(CONVERTED_LEADS_DIR, exist_ok=True)
    target_path = os.path.join(CONVERTED_LEADS_DIR, os.path.basename(file_path))
    write_frontmatter_file(target_path, frontmatter, body)
    os.remove(file_path)
    return target_path


def cmd_convert(args):
    ensure_core_dirs()
    if args.autonomous and not args.opportunity_name:
        raise ValueError("Autonomous conversion requires --opportunity-name so the specific opportunity is explicit.")

    file_path = find_lead_path(args.lead)
    frontmatter, body = load_frontmatter_file(file_path)
    missing = validate_ready_for_conversion(frontmatter)
    if missing:
        raise ValueError("Lead is not ready to convert: " + ", ".join(missing))

    lead_name = frontmatter.get("lead-name") or os.path.splitext(os.path.basename(file_path))[0]
    person_name = frontmatter.get("person-name")
    company_name = frontmatter.get("company-name")
    lead_link = link_for("Leads", os.path.splitext(os.path.basename(file_path))[0])

    organization_path = create_organization_record(company_name, lead_link)
    account_path = create_account_record(
        company_name,
        frontmatter.get("owner", "john"),
        lead_link,
        frontmatter.get("priority", "medium"),
        organization_path,
    )
    contact_path = create_contact_record(person_name, company_name, frontmatter)
    opportunity_path = create_opportunity_record(
        company_name,
        person_name,
        lead_link,
        frontmatter.get("owner", "john"),
        args.opportunity_name,
        organization_path,
    )

    organization_link = link_for("Organizations", os.path.splitext(os.path.basename(organization_path))[0])
    account_link = link_for("Accounts", os.path.splitext(os.path.basename(account_path))[0])
    contact_link = link_for("Contacts", os.path.splitext(os.path.basename(contact_path))[0])
    opportunity_link = link_for("Opportunities", os.path.splitext(os.path.basename(opportunity_path))[0])

    copied_notes = copy_linked_records(
        NOTES_DIR,
        lead_link,
        "lead",
        "opportunity",
        opportunity_link,
        [contact_link, account_link],
    )
    copied_activities = copy_linked_records(
        ACTIVITIES_DIR,
        lead_link,
        "lead",
        "opportunity",
        opportunity_link,
        [contact_link, account_link],
    )
    moved_tasks = move_open_tasks(lead_link, account_link, contact_link, opportunity_link)

    frontmatter["status"] = "converted"
    frontmatter["converted-organization"] = organization_link
    frontmatter["converted-contact"] = contact_link
    frontmatter["converted-account"] = account_link
    frontmatter["converted-opportunities"] = [opportunity_link]
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    archived_path = archive_converted_lead(file_path, frontmatter, body)

    print("archived-lead:", archived_path)
    print("organization:", organization_path)
    print("account:", account_path)
    print("contact:", contact_path)
    print("opportunity:", opportunity_path)
    print("copied-notes:", len(copied_notes))
    print("copied-activities:", len(copied_activities))
    print("moved-tasks:", len(moved_tasks))


def build_parser():
    parser = argparse.ArgumentParser(description="Manage v4 Lead records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new lead record.")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--status", default="new", choices=sorted(VALID_STATUSES - {"converted"}))
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--lead-source", default="manual")
    create_parser.add_argument("--person-name")
    create_parser.add_argument("--company-name")
    create_parser.add_argument("--email")
    create_parser.add_argument("--linkedin")
    create_parser.add_argument("--priority", default="medium")
    create_parser.add_argument("--source-ref")
    create_parser.set_defaults(func=cmd_create)

    status_parser = subparsers.add_parser("set-status", help="Set a lead status with transition validation.")
    status_parser.add_argument("lead")
    status_parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES - {"converted"}))
    status_parser.set_defaults(func=cmd_set_status)

    revive_parser = subparsers.add_parser("revive", help="Revive a disqualified lead.")
    revive_parser.add_argument("lead")
    revive_parser.add_argument("--meaningful-two-way", action="store_true")
    revive_parser.set_defaults(func=cmd_revive)

    validate_parser = subparsers.add_parser("validate-qualified", help="Check whether a lead is ready to be qualified.")
    validate_parser.add_argument("lead")
    validate_parser.set_defaults(func=cmd_validate)

    convert_parser = subparsers.add_parser("convert", help="Convert a qualified lead into Contact, Account, and Opportunity records.")
    convert_parser.add_argument("lead")
    convert_parser.add_argument("--opportunity-name")
    convert_parser.add_argument("--autonomous", action="store_true")
    convert_parser.set_defaults(func=cmd_convert)

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
