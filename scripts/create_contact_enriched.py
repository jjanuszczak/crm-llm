import argparse

import contact_manager
from enrichment_utils import collect_local_context, combine_notes, infer_last_contacted, join_paragraph, split_sentences, titles_for


def synthesize_role(args):
    external = combine_notes(args.drive_notes, args.web_notes)
    sentence = split_sentences(external, limit=1)
    return sentence[0] if sentence else ""


def synthesize_expertise(args, matches):
    parts = []
    if args.account:
        parts.append("Account-linked relationship")
    if args.deal:
        parts.append("Deal-linked relationship")
    if args.web_notes:
        parts.extend(split_sentences(args.web_notes, limit=2))
    return ", ".join(parts[:3])


def synthesize_focus(args):
    external = combine_notes(args.drive_notes, args.web_notes)
    sentences = split_sentences(external, limit=3)
    return sentences[1] if len(sentences) > 1 else ""


def synthesize_insights(matches):
    outputs = []
    activities = titles_for(matches, "Activities", 2)
    opportunities = titles_for(matches, "Opportunities", 2)
    if activities:
        outputs.append(f"Already appears in CRM activity context including {', '.join(activities)}.")
    if opportunities:
        outputs.append(f"Commercial context also touches {', '.join(opportunities)}.")
    while len(outputs) < 2:
        outputs.append("")
    return outputs[:2]


def synthesize_hooks(args, matches):
    hooks = []
    if args.account:
        hooks.append(f"Ask how current priorities are evolving inside {args.account}.")
    if args.deal:
        hooks.append(f"Discuss where {args.deal} stands now and what would materially change momentum.")
    activities = titles_for(matches, "Activities", 1)
    if activities and len(hooks) < 2:
        hooks.append(f"Use {activities[0]} as a reconnect anchor.")
    while len(hooks) < 2:
        hooks.append("")
    return hooks[:2]


def build_parser():
    parser = argparse.ArgumentParser(description="Create an enriched Contact record.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--nickname")
    parser.add_argument("--owner", default="john")
    parser.add_argument("--account")
    parser.add_argument("--deal")
    parser.add_argument("--linkedin")
    parser.add_argument("--email")
    parser.add_argument("--mobile")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--source-ref")
    parser.add_argument("--relationship-status", default="active")
    parser.add_argument("--priority", default="medium")
    parser.add_argument("--last-contacted")
    parser.add_argument("--role")
    parser.add_argument("--expertise")
    parser.add_argument("--focus")
    parser.add_argument("--insight-1")
    parser.add_argument("--insight-2")
    parser.add_argument("--hook-1")
    parser.add_argument("--hook-2")
    parser.add_argument("--drive-notes")
    parser.add_argument("--web-notes")
    parser.add_argument("--crm-query", nargs="*", default=[])
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    matches = collect_local_context([args.name, args.email, args.linkedin, args.account, args.deal, *args.crm_query])
    args.role = args.role or synthesize_role(args)
    args.expertise = args.expertise or synthesize_expertise(args, matches)
    args.focus = args.focus or synthesize_focus(args)
    insights = synthesize_insights(matches)
    args.insight_1 = args.insight_1 or insights[0]
    args.insight_2 = args.insight_2 or insights[1]
    hooks = synthesize_hooks(args, matches)
    args.hook_1 = args.hook_1 or hooks[0]
    args.hook_2 = args.hook_2 or hooks[1]
    args.last_contacted = args.last_contacted or infer_last_contacted(matches)
    contact_manager.cmd_create(args)


if __name__ == "__main__":
    main()
