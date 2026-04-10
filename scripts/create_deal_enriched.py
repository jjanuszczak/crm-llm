import argparse

import deal_manager
from enrichment_utils import collect_local_context, combine_notes, join_paragraph, split_sentences, titles_for


def synthesize_summary(args, matches):
    parts = []
    external = combine_notes(args.drive_notes, args.web_notes)
    if external:
        parts.append(" ".join(split_sentences(external, limit=3)))
    else:
        parts.append(f"{args.name} is being tracked as a live deal inventory record for potential fundraising or brokerage relevance.")
    activities = titles_for(matches, "Activities", 2)
    if activities:
        parts.append(f"Existing CRM context already includes {', '.join(activities)}.")
    return join_paragraph(parts)


def synthesize_problem(args):
    external = combine_notes(args.drive_notes, args.web_notes)
    return " ".join(split_sentences(external, limit=1)) if external else ""


def synthesize_solution(args):
    external = combine_notes(args.drive_notes, args.web_notes)
    sentences = split_sentences(external, limit=3)
    return sentences[1] if len(sentences) > 1 else ""


def synthesize_highlights(args, matches):
    parts = []
    if args.traction_metrics:
        parts.append(f"Traction signal already captured in frontmatter: {args.traction_metrics}.")
    opportunities = titles_for(matches, "Opportunities", 3)
    accounts = titles_for(matches, "Accounts", 3)
    if opportunities:
        parts.append(f"Linked commercial context exists through {', '.join(opportunities)}.")
    if accounts:
        parts.append(f"Relevant internal account context includes {', '.join(accounts)}.")
    external = combine_notes(args.drive_notes, args.web_notes)
    if external:
        parts.append(" ".join(split_sentences(external, limit=2)))
    return join_paragraph(parts)


def synthesize_investor_profile(args):
    if args.sector and args.location:
        return f"Investors interested in {args.sector} opportunities with relevance to {args.location}."
    if args.sector:
        return f"Investors interested in {args.sector} opportunities."
    return ""


def synthesize_target_clients(matches):
    accounts = titles_for(matches, "Accounts", 4)
    return ", ".join(accounts)


def build_parser():
    parser = argparse.ArgumentParser(description="Create an enriched Deal record.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--owner", default="john")
    parser.add_argument("--sector")
    parser.add_argument("--fundraising-stage")
    parser.add_argument("--coverage-status", default="active")
    parser.add_argument("--location")
    parser.add_argument("--traction-metrics")
    parser.add_argument("--target-raise", type=int, default=0)
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--valuation-cap", type=int, default=0)
    parser.add_argument("--pitch-deck-url")
    parser.add_argument("--google-drive-url")
    parser.add_argument("--founder-contacts", nargs="*", default=[])
    parser.add_argument("--related-accounts", nargs="*", default=[])
    parser.add_argument("--related-opportunities", nargs="*", default=[])
    parser.add_argument("--source", default="manual")
    parser.add_argument("--source-ref")
    parser.add_argument("--summary")
    parser.add_argument("--problem")
    parser.add_argument("--solution")
    parser.add_argument("--revenue-or-users")
    parser.add_argument("--burn-rate")
    parser.add_argument("--previous-rounds")
    parser.add_argument("--investment-highlights")
    parser.add_argument("--ideal-investor-profile")
    parser.add_argument("--target-clients")
    parser.add_argument("--drive-notes")
    parser.add_argument("--web-notes")
    parser.add_argument("--crm-query", nargs="*", default=[])
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    matches = collect_local_context(
        [args.name, *(args.founder_contacts or []), *(args.related_accounts or []), *(args.related_opportunities or []), *args.crm_query]
    )
    args.summary = args.summary or synthesize_summary(args, matches)
    args.problem = args.problem or synthesize_problem(args)
    args.solution = args.solution or synthesize_solution(args)
    args.investment_highlights = args.investment_highlights or synthesize_highlights(args, matches)
    args.ideal_investor_profile = args.ideal_investor_profile or synthesize_investor_profile(args)
    args.target_clients = args.target_clients or synthesize_target_clients(matches)
    deal_manager.cmd_create(args)


if __name__ == "__main__":
    main()
