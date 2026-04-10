import argparse

import account_manager
from crm_manager_utils import display_name, resolve_record_path
from enrichment_utils import collect_local_context, combine_notes, infer_last_contacted, join_paragraph, titles_for
from frontmatter_utils import load_frontmatter_file
from lead_manager import get_crm_data_path


CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = f"{CRM_DATA_PATH}/Organizations"


def load_org_name(reference):
    path = resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, reference, "Organization")
    frontmatter, _body = load_frontmatter_file(path)
    return display_name(frontmatter, path)


def synthesize_summary(org_name, args, matches):
    parts = [f"Commercial relationship wrapper for {org_name}."]
    if args.relationship_stage:
        parts.append(f"Current relationship stage is `{args.relationship_stage}`.")
    activities = titles_for(matches, "Activities", 2)
    opportunities = titles_for(matches, "Opportunities", 2)
    if activities:
        parts.append(f"Recent relationship evidence includes {', '.join(activities)}.")
    if opportunities:
        parts.append(f"Commercial relevance is also reflected in {', '.join(opportunities)}.")
    parts.append(combine_notes(args.drive_notes, args.web_notes))
    return join_paragraph(parts)


def synthesize_lifecycle(args, matches):
    parts = []
    activities = titles_for(matches, "Activities", 3)
    tasks = titles_for(matches, "Tasks", 3)
    if activities:
        parts.append(f"Known lifecycle signals currently come from {', '.join(activities)}.")
    if tasks:
        parts.append(f"Execution tracking in the CRM includes {', '.join(tasks)}.")
    if args.source_lead:
        parts.append("This account also has explicit provenance from a lead or conversion path.")
    return join_paragraph(parts)


def synthesize_importance(org_name, matches):
    parts = [f"{org_name} matters as a durable commercial wrapper around the live relationship, not just as a static company identity record."]
    contacts = titles_for(matches, "Contacts", 3)
    opportunities = titles_for(matches, "Opportunities", 3)
    if contacts:
        parts.append(f"Relationship surface area already includes {', '.join(contacts)}.")
    if opportunities:
        parts.append(f"Commercial significance is reinforced by linked opportunities such as {', '.join(opportunities)}.")
    return join_paragraph(parts)


def synthesize_execution(matches):
    tasks = titles_for(matches, "Tasks", 4)
    activities = titles_for(matches, "Activities", 2)
    parts = []
    if tasks:
        parts.append(f"Active execution context to watch: {', '.join(tasks)}.")
    if activities:
        parts.append(f"Recent interaction evidence to anchor next steps: {', '.join(activities)}.")
    return join_paragraph(parts)


def synthesize_open_questions(matches):
    questions = []
    if not titles_for(matches, "Contacts", 1):
        questions.append("Which durable operating or decision-maker contacts should be linked to this account?")
    if not titles_for(matches, "Opportunities", 1):
        questions.append("Is there already a concrete opportunity that should be attached to this account?")
    if not questions:
        questions.append("What is the next material commercial milestone for this account?")
    return "\n".join(f"- {question}" for question in questions)


def build_parser():
    parser = argparse.ArgumentParser(description="Create an enriched Account record.")
    parser.add_argument("--organization", required=True)
    parser.add_argument("--owner", default="john")
    parser.add_argument("--relationship-stage", default="prospect")
    parser.add_argument("--strategic-importance", default="medium")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--source-ref")
    parser.add_argument("--source-lead")
    parser.add_argument("--last-contacted")
    parser.add_argument("--summary")
    parser.add_argument("--lifecycle")
    parser.add_argument("--importance-notes")
    parser.add_argument("--execution-notes")
    parser.add_argument("--open-questions")
    parser.add_argument("--drive-notes")
    parser.add_argument("--web-notes")
    parser.add_argument("--crm-query", nargs="*", default=[])
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    org_name = load_org_name(args.organization)
    matches = collect_local_context([org_name, args.organization, *args.crm_query])
    args.summary = args.summary or synthesize_summary(org_name, args, matches)
    args.lifecycle = args.lifecycle or synthesize_lifecycle(args, matches)
    args.importance_notes = args.importance_notes or synthesize_importance(org_name, matches)
    args.execution_notes = args.execution_notes or synthesize_execution(matches)
    args.open_questions = args.open_questions or synthesize_open_questions(matches)
    args.last_contacted = args.last_contacted or infer_last_contacted(matches)
    account_manager.cmd_create(args)


if __name__ == "__main__":
    main()
