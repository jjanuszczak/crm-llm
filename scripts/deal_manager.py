import argparse
import os
import sys
from datetime import date

from crm_manager_utils import link_for_path, load_display_name, replace_section, resolve_optional_record_path, resolve_record_path
from frontmatter_utils import load_frontmatter_file, slugify, write_frontmatter_file
from lead_manager import get_crm_data_path
from navigation_manager import record_mutation


VALID_COVERAGE_STATUS = {"active", "parked", "closed", "passed"}
VALID_SOURCES = {"manual", "referral", "workspace-discovery", "drive", "gmail"}

CRM_DATA_PATH = get_crm_data_path()
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")


def ensure_dirs():
    os.makedirs(DEALS_DIR, exist_ok=True)


def build_body(args):
    lines = [
        f"# **Deal: {args.name}**",
        "",
        "## **Executive Summary**",
        args.summary or "",
        "",
        "## **The Problem & Solution**",
        f"*   **Problem:** {args.problem or ''}",
        f"*   **Solution:** {args.solution or ''}",
        "",
        "## **Traction & Financials**",
        f"*   **Revenue/Users:** {args.revenue_or_users or ''}",
        f"*   **Burn Rate:** {args.burn_rate or ''}",
        f"*   **Previous Rounds:** {args.previous_rounds or ''}",
        "",
        "## **Investment Highlights (The \"Sell\")**",
        args.investment_highlights or "",
        "",
        "## **Due Diligence Checklist**",
        "- [ ] Pitch Deck Reviewed",
        "- [ ] Financial Model Validated",
        "- [ ] Founder Reference Check",
        "- [ ] Tech/Product Demo",
        "",
        "## **Brokerage Strategy**",
        f"*   **Ideal Investor Profile:** {args.ideal_investor_profile or ''}",
        f"*   **Target Clients:** {args.target_clients or ''}",
        "",
    ]
    return "\n".join(lines)


def normalize_links(paths):
    return [link_for_path(path, CRM_DATA_PATH) for path in paths if path]


def cmd_create(args):
    ensure_dirs()
    if args.coverage_status not in VALID_COVERAGE_STATUS:
        raise ValueError(f"Invalid coverage-status '{args.coverage_status}'.")
    if args.source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{args.source}'.")

    slug = slugify(args.name)
    file_path = os.path.join(DEALS_DIR, f"{slug}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Deal already exists: {file_path}")

    founder_paths = [resolve_record_path(CONTACTS_DIR, CRM_DATA_PATH, value, "Contact") for value in args.founder_contacts]
    account_paths = [resolve_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, value, "Account") for value in args.related_accounts]
    opportunity_paths = [resolve_record_path(OPPORTUNITIES_DIR, CRM_DATA_PATH, value, "Opportunity") for value in args.related_opportunities]

    today = date.today().strftime("%Y-%m-%d")
    frontmatter = {
        "id": f"deal-{slug}",
        "startup-name": args.name,
        "owner": args.owner,
        "sector": args.sector or "",
        "fundraising-stage": args.fundraising_stage or "",
        "coverage-status": args.coverage_status,
        "location": args.location or "",
        "traction-metrics": args.traction_metrics or "",
        "target-raise": args.target_raise,
        "currency": args.currency,
        "valuation-cap": args.valuation_cap,
        "pitch-deck-url": args.pitch_deck_url or "",
        "google-drive-url": args.google_drive_url or "",
        "founder-contacts": normalize_links(founder_paths),
        "related-accounts": normalize_links(account_paths),
        "related-opportunities": normalize_links(opportunity_paths),
        "source": args.source,
        "source-ref": args.source_ref or "",
        "date-sourced": today,
        "date-modified": today,
    }
    body = build_body(args)
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Deal",
        title=args.name,
        path=file_path,
        source=args.source,
        related=frontmatter["founder-contacts"] + frontmatter["related-accounts"] + frontmatter["related-opportunities"],
        details=f"fundraising-stage={args.fundraising_stage or ''}; coverage-status={args.coverage_status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def find_deal_path(identifier):
    return resolve_record_path(DEALS_DIR, CRM_DATA_PATH, identifier, "Deal")


def cmd_update(args):
    path = find_deal_path(args.deal)
    frontmatter, body = load_frontmatter_file(path)

    if args.name:
        frontmatter["startup-name"] = args.name
    if args.sector is not None:
        frontmatter["sector"] = args.sector
    if args.fundraising_stage is not None:
        frontmatter["fundraising-stage"] = args.fundraising_stage
    if args.coverage_status is not None:
        if args.coverage_status not in VALID_COVERAGE_STATUS:
            raise ValueError(f"Invalid coverage-status '{args.coverage_status}'.")
        frontmatter["coverage-status"] = args.coverage_status
    if args.location is not None:
        frontmatter["location"] = args.location
    if args.traction_metrics is not None:
        frontmatter["traction-metrics"] = args.traction_metrics
    if args.target_raise is not None:
        frontmatter["target-raise"] = args.target_raise
    if args.currency is not None:
        frontmatter["currency"] = args.currency
    if args.valuation_cap is not None:
        frontmatter["valuation-cap"] = args.valuation_cap
    if args.pitch_deck_url is not None:
        frontmatter["pitch-deck-url"] = args.pitch_deck_url
    if args.google_drive_url is not None:
        frontmatter["google-drive-url"] = args.google_drive_url
    if args.source is not None:
        if args.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{args.source}'.")
        frontmatter["source"] = args.source
    if args.source_ref is not None:
        frontmatter["source-ref"] = args.source_ref
    if args.founder_contacts is not None:
        frontmatter["founder-contacts"] = normalize_links(
            [resolve_record_path(CONTACTS_DIR, CRM_DATA_PATH, value, "Contact") for value in args.founder_contacts]
        )
    if args.related_accounts is not None:
        frontmatter["related-accounts"] = normalize_links(
            [resolve_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, value, "Account") for value in args.related_accounts]
        )
    if args.related_opportunities is not None:
        frontmatter["related-opportunities"] = normalize_links(
            [resolve_record_path(OPPORTUNITIES_DIR, CRM_DATA_PATH, value, "Opportunity") for value in args.related_opportunities]
        )
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")

    if args.summary is not None:
        body = replace_section(body, "Executive Summary", args.summary)
    if args.problem is not None or args.solution is not None:
        section = "\n".join(
            [
                f"*   **Problem:** {args.problem if args.problem is not None else ''}",
                f"*   **Solution:** {args.solution if args.solution is not None else ''}",
            ]
        )
        body = replace_section(body, "The Problem & Solution", section)
    if any(value is not None for value in [args.revenue_or_users, args.burn_rate, args.previous_rounds]):
        section = "\n".join(
            [
                f"*   **Revenue/Users:** {args.revenue_or_users if args.revenue_or_users is not None else ''}",
                f"*   **Burn Rate:** {args.burn_rate if args.burn_rate is not None else ''}",
                f"*   **Previous Rounds:** {args.previous_rounds if args.previous_rounds is not None else ''}",
            ]
        )
        body = replace_section(body, "Traction & Financials", section)
    if args.investment_highlights is not None:
        body = replace_section(body, 'Investment Highlights (The "Sell")', args.investment_highlights)
    if args.ideal_investor_profile is not None or args.target_clients is not None:
        section = "\n".join(
            [
                f"*   **Ideal Investor Profile:** {args.ideal_investor_profile if args.ideal_investor_profile is not None else ''}",
                f"*   **Target Clients:** {args.target_clients if args.target_clients is not None else ''}",
            ]
        )
        body = replace_section(body, "Brokerage Strategy", section)

    write_frontmatter_file(path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Deal",
        title=frontmatter.get("startup-name", load_display_name(path)),
        path=path,
        source=frontmatter.get("source", ""),
        related=frontmatter.get("founder-contacts", []) + frontmatter.get("related-accounts", []) + frontmatter.get("related-opportunities", []),
        details="updated deal metadata/body",
        crm_data_path=CRM_DATA_PATH,
    )
    print(path)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Deal records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a Deal record in Deal-Flow/.")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--sector")
    create_parser.add_argument("--fundraising-stage")
    create_parser.add_argument("--coverage-status", default="active")
    create_parser.add_argument("--location")
    create_parser.add_argument("--traction-metrics")
    create_parser.add_argument("--target-raise", type=int, default=0)
    create_parser.add_argument("--currency", default="USD")
    create_parser.add_argument("--valuation-cap", type=int, default=0)
    create_parser.add_argument("--pitch-deck-url")
    create_parser.add_argument("--google-drive-url")
    create_parser.add_argument("--founder-contacts", nargs="*", default=[])
    create_parser.add_argument("--related-accounts", nargs="*", default=[])
    create_parser.add_argument("--related-opportunities", nargs="*", default=[])
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--summary")
    create_parser.add_argument("--problem")
    create_parser.add_argument("--solution")
    create_parser.add_argument("--revenue-or-users")
    create_parser.add_argument("--burn-rate")
    create_parser.add_argument("--previous-rounds")
    create_parser.add_argument("--investment-highlights")
    create_parser.add_argument("--ideal-investor-profile")
    create_parser.add_argument("--target-clients")
    create_parser.set_defaults(func=cmd_create)

    update_parser = subparsers.add_parser("update", help="Update a Deal record.")
    update_parser.add_argument("deal")
    update_parser.add_argument("--name")
    update_parser.add_argument("--sector")
    update_parser.add_argument("--fundraising-stage")
    update_parser.add_argument("--coverage-status")
    update_parser.add_argument("--location")
    update_parser.add_argument("--traction-metrics")
    update_parser.add_argument("--target-raise", type=int)
    update_parser.add_argument("--currency")
    update_parser.add_argument("--valuation-cap", type=int)
    update_parser.add_argument("--pitch-deck-url")
    update_parser.add_argument("--google-drive-url")
    update_parser.add_argument("--founder-contacts", nargs="*")
    update_parser.add_argument("--related-accounts", nargs="*")
    update_parser.add_argument("--related-opportunities", nargs="*")
    update_parser.add_argument("--source")
    update_parser.add_argument("--source-ref")
    update_parser.add_argument("--summary")
    update_parser.add_argument("--problem")
    update_parser.add_argument("--solution")
    update_parser.add_argument("--revenue-or-users")
    update_parser.add_argument("--burn-rate")
    update_parser.add_argument("--previous-rounds")
    update_parser.add_argument("--investment-highlights")
    update_parser.add_argument("--ideal-investor-profile")
    update_parser.add_argument("--target-clients")
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
