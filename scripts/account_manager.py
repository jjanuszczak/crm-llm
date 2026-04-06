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
from frontmatter_utils import find_markdown_file, load_frontmatter_file, parse_markdown_frontmatter, slugify, write_frontmatter_file
from lead_manager import get_crm_data_path
from navigation_manager import record_mutation


VALID_RELATIONSHIP_STAGES = {"prospect", "engaged", "customer", "churned"}
VALID_STRATEGIC_IMPORTANCE = {"high", "medium", "low"}
VALID_SOURCES = {"manual", "lead-conversion", "referral", "workspace-discovery"}

LOGIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
ACCOUNT_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "account-template.md")
CRM_DATA_PATH = get_crm_data_path()
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
LEADS_DIR = os.path.join(CRM_DATA_PATH, "Leads")


def ensure_dirs():
    os.makedirs(ACCOUNTS_DIR, exist_ok=True)


def read_template():
    with open(ACCOUNT_TEMPLATE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def create_body(organization_name, summary, lifecycle, importance, execution_notes, open_questions):
    rendered = read_template()
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = body.replace("{{Organization Name}}", organization_name)
    body = body.replace("{{Current commercial relationship summary and what matters now.}}", summary or "")
    body = body.replace("{{Why this account is in the pipeline, current stage, and recent progress.}}", lifecycle or "")
    body = body.replace("{{Why this organization matters commercially or strategically over time.}}", importance or "")
    body = body.replace("{{Active constraints, stakeholder dynamics, and next-step framing.}}", execution_notes or "")
    body = body.replace("{{What still needs to be learned or validated.}}", open_questions or "")
    return body


def validate_args(args):
    if args.relationship_stage not in VALID_RELATIONSHIP_STAGES:
        raise ValueError(f"Invalid relationship-stage '{args.relationship_stage}'.")
    if args.strategic_importance not in VALID_STRATEGIC_IMPORTANCE:
        raise ValueError(f"Invalid strategic-importance '{args.strategic_importance}'.")
    if args.source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{args.source}'.")


def cmd_create(args):
    ensure_dirs()
    validate_args(args)
    organization_path = resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, args.organization, "Organization")
    organization_fm, _organization_body = load_frontmatter_file(organization_path)
    organization_name = display_name(organization_fm, organization_path)
    lead_path = resolve_optional_record_path(LEADS_DIR, CRM_DATA_PATH, args.source_lead, "Lead")
    slug = slugify(organization_name)
    file_path = os.path.join(ACCOUNTS_DIR, f"{slug}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Account already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    frontmatter = {
        "id": f"acct-{slug}",
        "organization": link_for_path(organization_path, CRM_DATA_PATH),
        "owner": args.owner,
        "relationship-stage": args.relationship_stage,
        "stage": args.relationship_stage,
        "strategic-importance": args.strategic_importance,
        "source": args.source,
        "source-ref": args.source_ref or "",
        "source-lead": link_for_path(lead_path, CRM_DATA_PATH) if lead_path else "",
        "last-contacted": args.last_contacted or today,
        "date-created": today,
        "date-modified": today,
    }
    body = create_body(
        organization_name,
        args.summary,
        args.lifecycle,
        args.importance_notes,
        args.execution_notes,
        args.open_questions,
    )
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Account",
        title=organization_name,
        path=file_path,
        source=args.source,
        related=[frontmatter["organization"], frontmatter["source-lead"]],
        details=f"relationship-stage={args.relationship_stage}; strategic-importance={args.strategic_importance}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def find_account_path(identifier):
    return resolve_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, identifier, "Account")


def cmd_update(args):
    path = find_account_path(args.account)
    frontmatter, body = load_frontmatter_file(path)
    if args.organization:
        organization_path = resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, args.organization, "Organization")
        frontmatter["organization"] = link_for_path(organization_path, CRM_DATA_PATH)
    if args.relationship_stage:
        if args.relationship_stage not in VALID_RELATIONSHIP_STAGES:
            raise ValueError(f"Invalid relationship-stage '{args.relationship_stage}'.")
        frontmatter["relationship-stage"] = args.relationship_stage
        frontmatter["stage"] = args.relationship_stage
    if args.strategic_importance:
        if args.strategic_importance not in VALID_STRATEGIC_IMPORTANCE:
            raise ValueError(f"Invalid strategic-importance '{args.strategic_importance}'.")
        frontmatter["strategic-importance"] = args.strategic_importance
    if args.source:
        if args.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{args.source}'.")
        frontmatter["source"] = args.source
    if args.source_ref is not None:
        frontmatter["source-ref"] = args.source_ref
    if args.source_lead is not None:
        lead_path = resolve_optional_record_path(LEADS_DIR, CRM_DATA_PATH, args.source_lead, "Lead")
        frontmatter["source-lead"] = link_for_path(lead_path, CRM_DATA_PATH) if lead_path else ""
    if args.last_contacted:
        frontmatter["last-contacted"] = args.last_contacted
    today = date.today().strftime("%Y-%m-%d")
    frontmatter["date-modified"] = today

    if args.summary is not None:
        body = replace_section(body, "Relationship Summary", args.summary)
    if args.lifecycle is not None:
        body = replace_section(body, "Relationship Lifecycle", args.lifecycle)
    if args.importance_notes is not None:
        body = replace_section(body, "Strategic Importance", args.importance_notes)
    if args.execution_notes is not None:
        body = replace_section(body, "Execution Notes", args.execution_notes)
    if args.open_questions is not None:
        body = replace_section(body, "Open Questions", args.open_questions)

    write_frontmatter_file(path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Account",
        title=load_display_name(path),
        path=path,
        source=frontmatter.get("source", ""),
        related=[frontmatter.get("organization", ""), frontmatter.get("source-lead", "")],
        details="updated account metadata/body",
        crm_data_path=CRM_DATA_PATH,
    )
    print(path)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Account records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create an Account linked to an Organization.")
    create_parser.add_argument("--organization", required=True)
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--relationship-stage", default="prospect")
    create_parser.add_argument("--strategic-importance", default="medium")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--source-lead")
    create_parser.add_argument("--last-contacted")
    create_parser.add_argument("--summary")
    create_parser.add_argument("--lifecycle")
    create_parser.add_argument("--importance-notes")
    create_parser.add_argument("--execution-notes")
    create_parser.add_argument("--open-questions")
    create_parser.set_defaults(func=cmd_create)

    update_parser = subparsers.add_parser("update", help="Update an Account record.")
    update_parser.add_argument("account")
    update_parser.add_argument("--organization")
    update_parser.add_argument("--relationship-stage")
    update_parser.add_argument("--strategic-importance")
    update_parser.add_argument("--source")
    update_parser.add_argument("--source-ref")
    update_parser.add_argument("--source-lead")
    update_parser.add_argument("--last-contacted")
    update_parser.add_argument("--summary")
    update_parser.add_argument("--lifecycle")
    update_parser.add_argument("--importance-notes")
    update_parser.add_argument("--execution-notes")
    update_parser.add_argument("--open-questions")
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
