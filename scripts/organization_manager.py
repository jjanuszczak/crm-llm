import argparse
import os
import sys
from datetime import date

from frontmatter_utils import parse_markdown_frontmatter, slugify, write_frontmatter_file
from lead_manager import get_crm_data_path
from navigation_manager import record_mutation


LOGIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
ORGANIZATION_TEMPLATE_PATH = os.path.join(LOGIC_ROOT, "templates", "organization-template.md")
CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")


def ensure_dirs():
    os.makedirs(ORGANIZATIONS_DIR, exist_ok=True)


def render_template(path, replacements):
    with open(path, "r", encoding="utf-8") as handle:
        rendered = handle.read()
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def create_organization(args):
    ensure_dirs()
    org_id = slugify(args.name)
    file_path = os.path.join(ORGANIZATIONS_DIR, f"{org_id}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Organization already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        ORGANIZATION_TEMPLATE_PATH,
        {
            "organization-name": args.name,
            "Organization Name": args.name,
            "domain": args.domain or "",
            "Owner": args.owner,
            "Source Reference": args.source_ref or "",
            "manual | lead-conversion | referral | workspace-discovery": args.source,
            "URL": args.url or "",
            "String": "",
            "YYYY-MM-DD": today,
        },
    )

    frontmatter, body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = f"org-{org_id}"
    frontmatter["organization-name"] = args.name
    frontmatter["domain"] = args.domain or ""
    frontmatter["headquarters"] = args.headquarters or ""
    frontmatter["industry"] = args.industry or ""
    frontmatter["size"] = args.size
    frontmatter["url"] = args.url or ""
    frontmatter["organization-class"] = args.organization_class
    frontmatter["organization-subtype"] = args.organization_subtype or ""
    frontmatter["investment-mandate"] = args.investment_mandate
    frontmatter["check-size"] = args.check_size or ""
    frontmatter["last-contacted"] = today
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = body.replace("{{Core facts about the organization, what it does, and where it operates.}}", args.identity or "")
    body = body.replace("{{Positioning, ecosystem role, and relevant classification details.}}", args.market_context or "")
    body = body.replace("{{Observed interaction history, signal quality, and contact surface area.}}", args.relationship_signals or "")
    body = body.replace("{{Stable facts worth preserving independent of any single opportunity.}}", args.strategic_notes or "")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Organization",
        title=args.name,
        path=file_path,
        source=args.source,
        details=f"class={args.organization_class}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Organization records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create an organization record.")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--domain")
    create_parser.add_argument("--url")
    create_parser.add_argument("--headquarters")
    create_parser.add_argument("--industry")
    create_parser.add_argument("--size", type=int, default=0)
    create_parser.add_argument("--organization-class", default="other")
    create_parser.add_argument("--organization-subtype")
    create_parser.add_argument("--investment-mandate", nargs="*", default=[])
    create_parser.add_argument("--check-size")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--identity")
    create_parser.add_argument("--market-context")
    create_parser.add_argument("--relationship-signals")
    create_parser.add_argument("--strategic-notes")
    create_parser.set_defaults(func=create_organization)

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
