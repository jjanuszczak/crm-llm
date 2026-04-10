import argparse

import organization_manager
from enrichment_utils import (
    collect_local_context,
    combine_notes,
    infer_last_contacted,
    join_paragraph,
    summarize_roots,
    titles_for,
)


def synthesize_identity(args, matches):
    parts = []
    if any([args.organization_class, args.organization_subtype, args.industry, args.headquarters]):
        summary = f"{args.name}"
        descriptors = [value for value in [args.organization_subtype or args.organization_class, args.industry] if value]
        if descriptors:
            summary += f" is a {' / '.join(descriptors)}"
        if args.headquarters:
            summary += f" based in {args.headquarters}"
        if args.domain:
            summary += f" with domain {args.domain}"
        if args.url:
            summary += f" and official site {args.url}"
        parts.append(summary + ".")
    parts.append(combine_notes(args.web_notes, args.drive_notes))
    if not any(parts):
        snippets = [item["snippet"] for item in matches[:2] if item["snippet"]]
        if snippets:
            parts.append(" ".join(snippets))
    return join_paragraph(parts)


def synthesize_market_context(args, matches):
    parts = []
    if args.organization_class or args.organization_subtype:
        parts.append(
            f"Classified in the CRM as `{args.organization_class}`"
            + (f" with subtype `{args.organization_subtype}`." if args.organization_subtype else ".")
        )
    if args.investment_mandate or args.check_size:
        details = []
        if args.investment_mandate:
            details.append(f"investment mandate: {', '.join(args.investment_mandate)}")
        if args.check_size:
            details.append(f"check size: {args.check_size}")
        parts.append("Relevant market classification details include " + "; ".join(details) + ".")
    related = summarize_roots(matches)
    if related:
        parts.append(f"Existing CRM context touches this organization across {related}.")
    return join_paragraph(parts)


def synthesize_relationship_signals(matches):
    parts = []
    contacts = titles_for(matches, "Contacts")
    activities = titles_for(matches, "Activities")
    tasks = titles_for(matches, "Tasks")
    opportunities = titles_for(matches, "Opportunities")
    if contacts:
        parts.append(f"Known contact surface includes {', '.join(contacts)}.")
    if activities:
        parts.append(f"Observed interaction history includes {', '.join(activities)}.")
    if tasks:
        parts.append(f"Task-level relationship tracking includes {', '.join(tasks)}.")
    if opportunities:
        parts.append(f"Commercial context already exists through {', '.join(opportunities)}.")
    return join_paragraph(parts)


def synthesize_strategic_notes(matches, args):
    parts = []
    notes = titles_for(matches, "Notes")
    opportunities = titles_for(matches, "Opportunities")
    if notes:
        parts.append(f"Durable internal notes already exist via {', '.join(notes)}.")
    if opportunities:
        parts.append(f"Strategic relevance in the vault is currently reflected through {', '.join(opportunities)}.")
    if not parts and (args.web_notes or args.drive_notes):
        parts.append("Preserve the stable facts captured in the attached research and supporting materials.")
    return join_paragraph(parts)


def build_parser():
    parser = argparse.ArgumentParser(description="Create an enriched Organization record.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--owner", default="john")
    parser.add_argument("--domain")
    parser.add_argument("--url")
    parser.add_argument("--headquarters")
    parser.add_argument("--industry")
    parser.add_argument("--size", type=int, default=0)
    parser.add_argument("--organization-class", default="other")
    parser.add_argument("--organization-subtype")
    parser.add_argument("--investment-mandate", nargs="*", default=[])
    parser.add_argument("--check-size")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--source-ref")
    parser.add_argument("--identity")
    parser.add_argument("--market-context")
    parser.add_argument("--relationship-signals")
    parser.add_argument("--strategic-notes")
    parser.add_argument("--drive-notes")
    parser.add_argument("--web-notes")
    parser.add_argument("--crm-query", nargs="*", default=[])
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    matches = collect_local_context([args.name, args.domain, args.url, *args.crm_query])
    args.identity = args.identity or synthesize_identity(args, matches)
    args.market_context = args.market_context or synthesize_market_context(args, matches)
    args.relationship_signals = args.relationship_signals or synthesize_relationship_signals(matches)
    args.strategic_notes = args.strategic_notes or synthesize_strategic_notes(matches, args)
    args.last_contacted = infer_last_contacted(matches)
    organization_manager.create_organization(args)


if __name__ == "__main__":
    main()
