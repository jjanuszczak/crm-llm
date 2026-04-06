import argparse
import os
import re
import sys
from datetime import date


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from frontmatter_utils import (  # noqa: E402
    bucketed_record_path,
    dated_record_id,
    find_markdown_file,
    frontmatter_date_value,
    iter_markdown_files,
    load_frontmatter_file,
    parse_markdown_frontmatter,
    serialize_frontmatter,
    slugify,
    write_frontmatter_file,
)
from lead_manager import get_crm_data_path  # noqa: E402
from navigation_manager import append_log_entry, rebuild_index, record_mutation  # noqa: E402


VALID_OPPORTUNITY_TYPES = {"advisory", "consulting", "financing", "hiring", "partnership", "other"}
RECOMMENDED_STAGES = {"discovery", "qualified", "proposal", "negotiation", "closed-won", "closed-lost"}
VALID_ACTIVITY_TYPES = {"call", "email", "meeting", "analysis", "note-derived"}
VALID_ACTIVITY_STATUSES = {"completed", "scheduled", "cancelled"}
VALID_TASK_STATUSES = {"todo", "in-progress", "blocked", "done", "canceled"}
VALID_TASK_PRIORITIES = {"high", "medium", "low"}

CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
LEADS_DIR = os.path.join(CRM_DATA_PATH, "Leads")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")
TASKS_DIR = os.path.join(CRM_DATA_PATH, "Tasks")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
NOTES_DIR = os.path.join(CRM_DATA_PATH, "Notes")

OPPORTUNITY_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "opportunity-template.md")
TASK_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "task-template.md")
ACTIVITY_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "activity-template.md")
NOTE_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "note-template.md")


def ensure_dirs():
    for directory in [OPPORTUNITIES_DIR, TASKS_DIR, ACTIVITIES_DIR, NOTES_DIR]:
        os.makedirs(directory, exist_ok=True)


def read_template(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def render_template(path, replacements):
    rendered = read_template(path)
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def normalize_reference(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2].strip()
    if text.endswith(".md"):
        text = text[:-3]
    return text.strip()


def link_target_for_path(path):
    relative = os.path.relpath(path, CRM_DATA_PATH)
    return os.path.splitext(relative)[0].replace(os.sep, "/")


def link_for_path(path):
    return f"[[{link_target_for_path(path)}]]"


def display_name(frontmatter, default_path):
    for key in [
        "organization-name",
        "full-name",
        "lead-name",
        "opportunity-name",
        "activity-name",
        "task-name",
        "title",
        "name",
    ]:
        value = frontmatter.get(key)
        if value:
            return str(value)
    return os.path.splitext(os.path.basename(default_path))[0]


def unique_list(values):
    deduped = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def resolve_record_path(base_dir, reference, label):
    if not reference:
        raise ValueError(f"{label} reference is required.")

    text = normalize_reference(reference)
    if os.path.isabs(text) and os.path.isfile(text):
        return text

    candidate = os.path.join(CRM_DATA_PATH, text)
    if os.path.isfile(candidate):
        return candidate
    if os.path.isfile(candidate + ".md"):
        return candidate + ".md"

    stem = os.path.basename(text)
    direct = os.path.join(base_dir, stem)
    if os.path.isfile(direct):
        return direct
    if os.path.isfile(direct + ".md"):
        return direct + ".md"

    found = find_markdown_file(base_dir, stem)
    if found:
        return found

    found = find_markdown_file(base_dir, slugify(stem))
    if found:
        return found

    raise FileNotFoundError(f"{label} not found: {reference}")


def resolve_optional_record_path(base_dir, reference, label):
    if not reference:
        return ""
    return resolve_record_path(base_dir, reference, label)


def resolve_contact_links(values):
    links = []
    paths = []
    for value in values or []:
        path = resolve_record_path(CONTACTS_DIR, value, "Contact")
        paths.append(path)
        links.append(link_for_path(path))
    return unique_list(links), unique_list(paths)


def parse_link_target(value):
    text = normalize_reference(value)
    return text


def load_opportunity(reference):
    path = resolve_record_path(OPPORTUNITIES_DIR, reference, "Opportunity")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def infer_organization_path(account_path):
    frontmatter, _body = load_frontmatter_file(account_path)
    organization_value = frontmatter.get("organization")
    if not organization_value:
        raise ValueError("Account is missing canonical organization link.")
    return resolve_record_path(ORGANIZATIONS_DIR, organization_value, "Organization")


def opportunity_related_links(frontmatter):
    related = [
        frontmatter.get("organization", ""),
        frontmatter.get("account", ""),
        frontmatter.get("primary-contact", ""),
        frontmatter.get("deal", ""),
        frontmatter.get("source-lead", ""),
    ]
    related.extend(frontmatter.get("influencers", []) or [])
    return unique_list(related)


def ensure_probability(value):
    if not 0 <= value <= 100:
        raise ValueError("Probability must be between 0 and 100.")
    return value


def ensure_opportunity_type(value):
    if value not in VALID_OPPORTUNITY_TYPES:
        raise ValueError(
            f"Invalid opportunity-type '{value}'. Expected one of: {', '.join(sorted(VALID_OPPORTUNITY_TYPES))}"
        )
    return value


def ensure_stage(value):
    if not value:
        raise ValueError("Stage is required.")
    return value


def summary_text(body):
    match = re.search(r"## \*\*Executive Summary\*\*\n(.*?)(?:\n## \*\*|\Z)", body, re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def replace_section(body, heading, content):
    pattern = re.compile(rf"(## \*\*{re.escape(heading)}\*\*\n)(.*?)(?=\n## \*\*|\Z)", re.DOTALL)
    if pattern.search(body):
        def _replace(match):
            section_body = content.strip()
            if section_body:
                return match.group(1) + section_body + "\n\n"
            return match.group(1) + "\n"

        return pattern.sub(_replace, body, count=1)
    if body and not body.endswith("\n"):
        body += "\n"
    return body + f"\n## **{heading}**\n{content.strip()}\n"


def render_next_steps(lines):
    cleaned = [line.strip() for line in lines if line and line.strip()]
    if not cleaned:
        cleaned = ["{{Next immediate action}}", "{{Follow-up task}}"]
    if len(cleaned) == 1:
        cleaned.append("{{Follow-up task}}")
    return "\n".join(f"{idx}.  {line}" for idx, line in enumerate(cleaned, start=1))


def build_opportunity_body(opportunity_name, primary_contact_name, summary, next_steps, influencers):
    rendered = render_template(
        OPPORTUNITY_TEMPLATE_PATH,
        {
            "opportunity-id": slugify(opportunity_name),
            "Account": opportunity_name.split(" - ")[0],
            "Product/Service": "Advisory",
            "YYYY": date.today().year,
            "Owner": "john",
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
            "Deal Name": "",
            "Contact Name": primary_contact_name,
            "Source Lead": "",
            "Organization Link": "",
            "advisory | consulting | financing | hiring | partnership | other": "advisory",
            "manual | lead-conversion | referral | workspace-discovery": "manual",
            "Source Reference": "",
            "opportunity-name": opportunity_name,
            "Primary Contact": primary_contact_name,
            "High-level overview of the deal, its strategic importance, and the current state of the relationship.": summary or "",
            "Next immediate action": next_steps[0] if next_steps else "{{Next immediate action}}",
            "Follow-up task": next_steps[1] if len(next_steps) > 1 else "{{Follow-up task}}",
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    if influencers:
        body = body.replace("*   **Influencers:** ", f"*   **Influencers:** {', '.join(influencers)}")
    body = replace_section(body, "Executive Summary", summary or "Created through crm-opportunity-manager.")
    body = replace_section(body, "Next Steps", render_next_steps(next_steps))
    return body


def render_task_content(task_name, owner, due_date, priority, description, context, primary_parent, account, contact, opportunity, source_ref):
    rendered = render_template(
        TASK_TEMPLATE_PATH,
        {
            "task-id": dated_record_id(due_date, task_name),
            "Task Name": task_name,
            "todo | in-progress | blocked | done | canceled": "todo",
            "high | medium | low": priority,
            "Owner": owner,
            "YYYY-MM-DD": due_date,
            "lead | contact | account | opportunity | deal": "opportunity",
            "Primary Parent": primary_parent,
            "Account": account,
            "Contact": contact,
            "Opportunity": opportunity,
            "Lead": "",
            "manual | activity | inbox | gmail | calendar": "manual",
            "Source Reference": source_ref,
            "email-link": '""',
            "meeting-notes": '""',
            "task-name": task_name,
            "Clear, actionable description of what needs to be done.": description or "Created from opportunity workflow.",
            "Why is this task necessary? Reference recent activities or strategic shifts.": context,
            "Log progress or updates here.": "",
            "What was the result? If it leads to a new activity, link it here.": "",
        },
    )
    return parse_markdown_frontmatter(rendered)


def render_activity_content(title, activity_type, owner, activity_date, primary_parent, secondary_link, source_ref, summary, outcomes):
    rendered = render_template(
        ACTIVITY_TEMPLATE_PATH,
        {
            "activity-id": dated_record_id(activity_date, title),
            "Activity Name": title,
            "call | email | meeting | analysis | note-derived": activity_type,
            "Owner": owner,
            "YYYY-MM-DD": activity_date,
            "opportunity | contact | account | lead | deal": "opportunity",
            "Primary Parent": primary_parent,
            "Secondary Link 1": secondary_link or primary_parent,
            "manual | gmail | calendar | inbox": "manual",
            "Source Reference": source_ref,
            "email-link": "",
            "meeting-notes": "",
            "activity-name": title,
            "A brief (1-2 sentence) description of the purpose of this activity.": summary or "Created from opportunity workflow.",
            "High-level results of the activity. What was achieved?": outcomes or "",
            "Comprehensive notes from the call, meeting, or analysis. Use bullet points for readability.": "",
            "How did the contact react? Enthusiastic, skeptical, neutral?": "",
            "Specific tasks resulting from this activity with owners and deadlines.": "",
            "Date": activity_date,
        },
    )
    return parse_markdown_frontmatter(rendered)


def render_note_content(title, owner, primary_parent, secondary_link, source_ref, context, implication_1, implication_2):
    rendered = render_template(
        NOTE_TEMPLATE_PATH,
        {
            "note-id": slugify(title),
            "Note Title": title,
            "Owner": owner,
            "lead | contact | account | opportunity | deal | activity": "opportunity",
            "Primary Parent": primary_parent,
            "Secondary Link 1": secondary_link or primary_parent,
            "manual | inbox | gmail | calendar | ai-generated": "manual",
            "Source Reference": source_ref,
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
            "Durable background, interpretation, research, or strategic memory.": context or "",
            "Implication 1": implication_1 or "",
            "Implication 2": implication_2 or "",
        },
    )
    return parse_markdown_frontmatter(rendered)


def write_opportunity(path, frontmatter, body, action, details):
    write_frontmatter_file(path, frontmatter, body)
    record_mutation(
        action=action,
        entity_type="Opportunity",
        title=frontmatter.get("opportunity-name", os.path.splitext(os.path.basename(path))[0]),
        path=path,
        source=frontmatter.get("source", ""),
        related=opportunity_related_links(frontmatter),
        details=details,
        crm_data_path=CRM_DATA_PATH,
    )


def create_task_record(opportunity_path, opportunity_fm, task_name, due_date, priority, description, source_ref):
    if priority not in VALID_TASK_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'.")
    task_id = dated_record_id(due_date, task_name)
    existing_path = find_markdown_file(TASKS_DIR, task_id)
    if existing_path:
        raise FileExistsError(f"Task already exists: {existing_path}")

    file_path = bucketed_record_path(TASKS_DIR, due_date, f"{task_id}.md")
    frontmatter, body = render_task_content(
        task_name=task_name,
        owner=opportunity_fm.get("owner", "john"),
        due_date=due_date,
        priority=priority,
        description=description,
        context=f"Spawned from {opportunity_fm.get('opportunity-name', os.path.splitext(os.path.basename(opportunity_path))[0])}.",
        primary_parent=link_target_for_path(opportunity_path),
        account=parse_link_target(opportunity_fm.get("account", "")),
        contact=parse_link_target(opportunity_fm.get("primary-contact", "")),
        opportunity=link_target_for_path(opportunity_path),
        source_ref=source_ref,
    )
    today = date.today().strftime("%Y-%m-%d")
    frontmatter["status"] = "todo"
    frontmatter["primary-parent-type"] = "opportunity"
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today
    frontmatter["lead"] = ""
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def create_activity_record(opportunity_path, opportunity_fm, title, activity_type, activity_date, status, summary, outcomes, source_ref):
    if activity_type not in VALID_ACTIVITY_TYPES:
        raise ValueError(f"Invalid activity-type '{activity_type}'.")
    if status not in VALID_ACTIVITY_STATUSES:
        raise ValueError(f"Invalid activity status '{status}'.")

    activity_id = dated_record_id(activity_date, title)
    existing_path = find_markdown_file(ACTIVITIES_DIR, activity_id)
    if existing_path:
        raise FileExistsError(f"Activity already exists: {existing_path}")

    file_path = bucketed_record_path(ACTIVITIES_DIR, activity_date, f"{activity_id}.md")
    frontmatter, body = render_activity_content(
        title=title,
        activity_type=activity_type,
        owner=opportunity_fm.get("owner", "john"),
        activity_date=activity_date,
        primary_parent=link_target_for_path(opportunity_path),
        secondary_link=parse_link_target(opportunity_fm.get("primary-contact", "")) or parse_link_target(opportunity_fm.get("account", "")),
        source_ref=source_ref,
        summary=summary,
        outcomes=outcomes,
    )
    frontmatter["status"] = status
    frontmatter["primary-parent-type"] = "opportunity"
    frontmatter["secondary-links"] = unique_list(
        [
            opportunity_fm.get("primary-contact", ""),
            opportunity_fm.get("account", ""),
            opportunity_fm.get("organization", ""),
        ]
    )
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def create_note_record(opportunity_path, opportunity_fm, title, context, implication_1, implication_2, source_ref):
    note_id = slugify(title)
    existing_path = find_markdown_file(NOTES_DIR, note_id)
    if existing_path:
        raise FileExistsError(f"Note already exists: {existing_path}")

    today = date.today().strftime("%Y-%m-%d")
    file_path = bucketed_record_path(NOTES_DIR, today, f"{note_id}.md")
    frontmatter, body = render_note_content(
        title=title,
        owner=opportunity_fm.get("owner", "john"),
        primary_parent=link_target_for_path(opportunity_path),
        secondary_link=parse_link_target(opportunity_fm.get("account", "")) or parse_link_target(opportunity_fm.get("primary-contact", "")),
        source_ref=source_ref,
        context=context,
        implication_1=implication_1,
        implication_2=implication_2,
    )
    frontmatter["primary-parent-type"] = "opportunity"
    frontmatter["secondary-links"] = unique_list(
        [
            opportunity_fm.get("account", ""),
            opportunity_fm.get("primary-contact", ""),
            opportunity_fm.get("organization", ""),
        ]
    )
    write_frontmatter_file(file_path, frontmatter, body)
    return file_path


def cmd_create(args):
    ensure_dirs()
    ensure_opportunity_type(args.opportunity_type)
    ensure_probability(args.probability)
    ensure_stage(args.stage)

    account_path = resolve_record_path(ACCOUNTS_DIR, args.account, "Account")
    contact_path = resolve_record_path(CONTACTS_DIR, args.primary_contact, "Contact")
    organization_path = (
        resolve_record_path(ORGANIZATIONS_DIR, args.organization, "Organization")
        if args.organization
        else infer_organization_path(account_path)
    )
    deal_path = resolve_optional_record_path(DEALS_DIR, args.deal, "Deal")
    source_lead_path = resolve_optional_record_path(LEADS_DIR, args.source_lead, "Lead")

    account_fm, _ = load_frontmatter_file(account_path)
    contact_fm, _ = load_frontmatter_file(contact_path)
    influencer_links, influencer_paths = resolve_contact_links(args.influencers)

    if args.name:
        opportunity_name = args.name
    else:
        product = args.product_service or "Advisory"
        year = args.year or date.today().year
        opportunity_name = f"{display_name(account_fm, account_path)} - {product} - {year}"

    file_path = os.path.join(OPPORTUNITIES_DIR, f"{slugify(opportunity_name)}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Opportunity already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        OPPORTUNITY_TEMPLATE_PATH,
        {
            "opportunity-id": slugify(opportunity_name),
            "Account": link_target_for_path(account_path),
            "Product/Service": args.product_service or "Advisory",
            "YYYY": args.year or date.today().year,
            "Owner": args.owner or account_fm.get("owner", "john"),
            "YYYY-MM-DD": today,
            "Deal Name": link_target_for_path(deal_path) if deal_path else "",
            "Contact Name": link_target_for_path(contact_path),
            "Source Lead": link_target_for_path(source_lead_path) if source_lead_path else "",
            "Organization Link": link_target_for_path(organization_path),
            "advisory | consulting | financing | hiring | partnership | other": args.opportunity_type,
            "manual | lead-conversion | referral | workspace-discovery": args.source,
            "Source Reference": args.source_ref or "",
            "opportunity-name": opportunity_name,
            "Primary Contact": display_name(contact_fm, contact_path),
            "High-level overview of the deal, its strategic importance, and the current state of the relationship.": args.summary or "",
            "Next immediate action": args.next_steps[0] if args.next_steps else "{{Next immediate action}}",
            "Follow-up task": args.next_steps[1] if len(args.next_steps) > 1 else "{{Follow-up task}}",
        },
    )
    frontmatter, body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = slugify(opportunity_name)
    frontmatter["opportunity-name"] = opportunity_name
    frontmatter["owner"] = args.owner or account_fm.get("owner", "john")
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today
    frontmatter["account"] = link_for_path(account_path)
    frontmatter["organization"] = link_for_path(organization_path)
    frontmatter["primary-contact"] = link_for_path(contact_path)
    frontmatter["deal"] = link_for_path(deal_path) if deal_path else ""
    frontmatter["source-lead"] = link_for_path(source_lead_path) if source_lead_path else ""
    frontmatter["opportunity-type"] = args.opportunity_type
    frontmatter["is-active"] = True
    frontmatter["stage"] = args.stage
    frontmatter["commercial-value"] = args.commercial_value
    frontmatter["close-date"] = args.close_date or today
    frontmatter["probability"] = args.probability
    frontmatter["product-service"] = args.product_service or "Advisory"
    frontmatter["influencers"] = influencer_links
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["lost-at-stage"] = ""
    frontmatter["lost-reason"] = ""
    frontmatter["lost-date"] = ""

    influencer_names = [display_name(load_frontmatter_file(path)[0], path) for path in influencer_paths]
    body = build_opportunity_body(
        opportunity_name=opportunity_name,
        primary_contact_name=display_name(contact_fm, contact_path),
        summary=args.summary or "",
        next_steps=args.next_steps,
        influencers=influencer_names,
    )
    write_opportunity(
        file_path,
        frontmatter,
        body,
        action="create",
        details=f"stage={args.stage}; probability={args.probability}; opportunity-type={args.opportunity_type}",
    )
    print(file_path)


def cmd_update(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    updates = []

    if args.name:
        frontmatter["opportunity-name"] = args.name
        updates.append(f"name={args.name}")
    if args.opportunity_type:
        frontmatter["opportunity-type"] = ensure_opportunity_type(args.opportunity_type)
        updates.append(f"opportunity-type={args.opportunity_type}")
    if args.product_service:
        frontmatter["product-service"] = args.product_service
        updates.append(f"product-service={args.product_service}")
    if args.commercial_value is not None:
        frontmatter["commercial-value"] = args.commercial_value
        updates.append(f"commercial-value={args.commercial_value}")
    if args.close_date:
        frontmatter["close-date"] = args.close_date
        updates.append(f"close-date={args.close_date}")
    if args.source:
        frontmatter["source"] = args.source
        updates.append(f"source={args.source}")
    if args.source_ref is not None:
        frontmatter["source-ref"] = args.source_ref
        updates.append("source-ref updated")
    if args.account:
        account_path = resolve_record_path(ACCOUNTS_DIR, args.account, "Account")
        frontmatter["account"] = link_for_path(account_path)
        updates.append(f"account={display_name(load_frontmatter_file(account_path)[0], account_path)}")
        if not args.organization:
            frontmatter["organization"] = link_for_path(infer_organization_path(account_path))
    if args.organization:
        organization_path = resolve_record_path(ORGANIZATIONS_DIR, args.organization, "Organization")
        frontmatter["organization"] = link_for_path(organization_path)
        updates.append(f"organization={display_name(load_frontmatter_file(organization_path)[0], organization_path)}")
    if args.primary_contact:
        contact_path = resolve_record_path(CONTACTS_DIR, args.primary_contact, "Contact")
        frontmatter["primary-contact"] = link_for_path(contact_path)
        updates.append(f"primary-contact={display_name(load_frontmatter_file(contact_path)[0], contact_path)}")
    if args.deal is not None:
        deal_path = resolve_optional_record_path(DEALS_DIR, args.deal, "Deal")
        frontmatter["deal"] = link_for_path(deal_path) if deal_path else ""
        updates.append("deal updated")
    if args.summary is not None:
        body = replace_section(body, "Executive Summary", args.summary)
        updates.append("summary updated")
    if args.next_steps is not None:
        body = replace_section(body, "Next Steps", render_next_steps(args.next_steps))
        updates.append(f"next-steps={len(args.next_steps)}")

    if not updates:
        raise ValueError("No updates provided.")

    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_opportunity(file_path, frontmatter, body, action="update", details="; ".join(updates))
    print(file_path)


def cmd_assign_stakeholders(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    updates = []
    if args.primary_contact:
        contact_path = resolve_record_path(CONTACTS_DIR, args.primary_contact, "Contact")
        contact_fm, _ = load_frontmatter_file(contact_path)
        frontmatter["primary-contact"] = link_for_path(contact_path)
        body = re.sub(
            r"(\*   \*\*Economic Buyer:\*\* ).*",
            rf"\1{display_name(contact_fm, contact_path)}",
            body,
            count=1,
        )
        updates.append(f"primary-contact={display_name(contact_fm, contact_path)}")
    if args.influencers:
        influencer_links, influencer_paths = resolve_contact_links(args.influencers)
        influencer_names = [display_name(load_frontmatter_file(path)[0], path) for path in influencer_paths]
        frontmatter["influencers"] = influencer_links
        body = re.sub(r"(\*   \*\*Influencers:\*\* ).*", rf"\1{', '.join(influencer_names)}", body, count=1)
        updates.append(f"influencers={len(influencer_links)}")
    if not updates:
        raise ValueError("No stakeholder updates provided.")
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_opportunity(file_path, frontmatter, body, action="update", details="; ".join(updates))
    print(file_path)


def cmd_set_stage(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    ensure_stage(args.stage)
    frontmatter["stage"] = args.stage
    if args.probability is not None:
        frontmatter["probability"] = ensure_probability(args.probability)
    frontmatter["is-active"] = args.stage not in {"closed-won", "closed-lost"}
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    details = f"stage={args.stage}"
    if args.probability is not None:
        details += f"; probability={args.probability}"
    write_opportunity(file_path, frontmatter, body, action="update", details=details)
    print(file_path)


def cmd_set_probability(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    frontmatter["probability"] = ensure_probability(args.probability)
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_opportunity(file_path, frontmatter, body, action="update", details=f"probability={args.probability}")
    print(file_path)


def cmd_mark_won(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    close_date = args.close_date or date.today().strftime("%Y-%m-%d")
    frontmatter["stage"] = "closed-won"
    frontmatter["is-active"] = False
    frontmatter["probability"] = 100
    frontmatter["close-date"] = close_date
    frontmatter["lost-at-stage"] = ""
    frontmatter["lost-reason"] = ""
    frontmatter["lost-date"] = ""
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_opportunity(file_path, frontmatter, body, action="update", details=f"marked won; close-date={close_date}")
    print(file_path)


def cmd_mark_lost(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    prior_stage = frontmatter.get("stage", "")
    lost_date = args.lost_date or date.today().strftime("%Y-%m-%d")
    frontmatter["stage"] = "closed-lost"
    frontmatter["is-active"] = False
    frontmatter["probability"] = 0
    frontmatter["lost-at-stage"] = args.lost_at_stage or (prior_stage if prior_stage != "closed-lost" else frontmatter.get("lost-at-stage", ""))
    frontmatter["lost-reason"] = args.reason
    frontmatter["lost-date"] = lost_date
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_opportunity(
        file_path,
        frontmatter,
        body,
        action="update",
        details=f"marked lost; reason={args.reason}; lost-at-stage={frontmatter['lost-at-stage']}; lost-date={lost_date}",
    )
    print(file_path)


def cmd_archive_stale(args):
    file_path, frontmatter, body = load_opportunity(args.opportunity)
    frontmatter["is-active"] = False
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)

    related = opportunity_related_links(frontmatter)
    details = f"archived stale opportunity; reason={args.reason or 'not specified'}"
    reminder_path = ""
    if args.recheck_date:
        reminder_name = args.recheck_task or f"Revisit {frontmatter.get('opportunity-name', 'opportunity')}"
        reminder_path = create_task_record(
            opportunity_path=file_path,
            opportunity_fm=frontmatter,
            task_name=reminder_name,
            due_date=args.recheck_date,
            priority=args.recheck_priority,
            description=args.reason or "Stale opportunity recheck.",
            source_ref=normalize_reference(args.opportunity),
        )
        related.append(link_for_path(reminder_path))
        details += f"; recheck-task={os.path.relpath(reminder_path, CRM_DATA_PATH)}"

    append_log_entry(
        action="update",
        entity_type="Opportunity Workflow",
        title=frontmatter.get("opportunity-name", os.path.splitext(os.path.basename(file_path))[0]),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=related,
        details=details,
        crm_data_path=CRM_DATA_PATH,
    )
    rebuild_index(CRM_DATA_PATH)
    print(file_path)


def cmd_spawn_task(args):
    opportunity_path, frontmatter, _body = load_opportunity(args.opportunity)
    file_path = create_task_record(
        opportunity_path=opportunity_path,
        opportunity_fm=frontmatter,
        task_name=args.name,
        due_date=args.due_date,
        priority=args.priority,
        description=args.description or "",
        source_ref=normalize_reference(args.opportunity),
    )
    record_mutation(
        action="create",
        entity_type="Task",
        title=args.name,
        path=file_path,
        source="manual",
        related=[link_for_path(opportunity_path), frontmatter.get("account", ""), frontmatter.get("primary-contact", "")],
        details=f"spawned from opportunity; due-date={args.due_date}; priority={args.priority}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_spawn_activity(args):
    opportunity_path, frontmatter, _body = load_opportunity(args.opportunity)
    activity_date = args.date or date.today().strftime("%Y-%m-%d")
    file_path = create_activity_record(
        opportunity_path=opportunity_path,
        opportunity_fm=frontmatter,
        title=args.title,
        activity_type=args.activity_type,
        activity_date=activity_date,
        status=args.status,
        summary=args.summary or "",
        outcomes=args.outcomes or "",
        source_ref=normalize_reference(args.opportunity),
    )
    record_mutation(
        action="create",
        entity_type="Activity",
        title=args.title,
        path=file_path,
        source="manual",
        related=[link_for_path(opportunity_path), frontmatter.get("account", ""), frontmatter.get("primary-contact", "")],
        details=f"spawned from opportunity; activity-type={args.activity_type}; status={args.status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_spawn_note(args):
    opportunity_path, frontmatter, _body = load_opportunity(args.opportunity)
    file_path = create_note_record(
        opportunity_path=opportunity_path,
        opportunity_fm=frontmatter,
        title=args.title,
        context=args.context or "",
        implication_1=args.implication_1 or "",
        implication_2=args.implication_2 or "",
        source_ref=normalize_reference(args.opportunity),
    )
    record_mutation(
        action="create",
        entity_type="Note",
        title=args.title,
        path=file_path,
        source="manual",
        related=[link_for_path(opportunity_path), frontmatter.get("account", ""), frontmatter.get("primary-contact", "")],
        details="spawned from opportunity",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def linked_to_opportunity(frontmatter, opportunity_link):
    for key in ["primary-parent", "opportunity"]:
        if normalize_reference(frontmatter.get(key, "")) == normalize_reference(opportunity_link):
            return True
    secondary_links = frontmatter.get("secondary-links", []) or []
    return any(normalize_reference(value) == normalize_reference(opportunity_link) for value in secondary_links)


def gather_related_records(base_dir, opportunity_link):
    matches = []
    for file_path in iter_markdown_files(base_dir):
        frontmatter, _body = load_frontmatter_file(file_path)
        if linked_to_opportunity(frontmatter, opportunity_link):
            matches.append((file_path, frontmatter))
    return sorted(matches, key=lambda item: os.path.basename(item[0]).lower())


def cmd_review(args):
    opportunity_path, frontmatter, body = load_opportunity(args.opportunity)
    opportunity_link = link_for_path(opportunity_path)
    tasks = gather_related_records(TASKS_DIR, opportunity_link)
    activities = gather_related_records(ACTIVITIES_DIR, opportunity_link)
    notes = gather_related_records(NOTES_DIR, opportunity_link)

    open_tasks = [item for item in tasks if item[1].get("status") not in {"done", "canceled"}]
    recent_activity_dates = sorted(
        [
            frontmatter_date_value(activity_frontmatter, "date", "date-modified", "date-created")
            for _path, activity_frontmatter in activities
            if frontmatter_date_value(activity_frontmatter, "date", "date-modified", "date-created")
        ],
        reverse=True,
    )
    missing = []
    for key in ["organization", "account", "primary-contact", "product-service", "close-date"]:
        if not frontmatter.get(key):
            missing.append(key)
    if not summary_text(body):
        missing.append("executive-summary")
    if frontmatter.get("stage") not in RECOMMENDED_STAGES:
        missing.append(f"non-standard-stage={frontmatter.get('stage', '')}")
    if frontmatter.get("is-active") and not open_tasks:
        missing.append("no-open-tasks")
    if frontmatter.get("is-active") and not recent_activity_dates:
        missing.append("no-linked-activities")

    print(f"Opportunity: {frontmatter.get('opportunity-name', os.path.basename(opportunity_path))}")
    print(f"Path: {opportunity_path}")
    print(f"Stage: {frontmatter.get('stage', '')}")
    print(f"Probability: {frontmatter.get('probability', '')}")
    print(f"Active: {frontmatter.get('is-active', '')}")
    print(f"Commercial Value: {frontmatter.get('commercial-value', '')}")
    print(f"Close Date: {frontmatter.get('close-date', '')}")
    print(f"Primary Contact: {frontmatter.get('primary-contact', '')}")
    print(f"Influencers: {len(frontmatter.get('influencers', []) or [])}")
    print(f"Open Tasks: {len(open_tasks)}")
    print(f"Activities: {len(activities)}")
    print(f"Notes: {len(notes)}")
    print(f"Recent Activity: {recent_activity_dates[0] if recent_activity_dates else 'none'}")
    print("Missing/Attention:")
    if missing:
        for item in missing:
            print(f"- {item}")
    else:
        print("- none")
    print("Recommended Next Action:")
    if "no-open-tasks" in missing and frontmatter.get("is-active"):
        print("- create a concrete follow-up task")
    elif "no-linked-activities" in missing and frontmatter.get("is-active"):
        print("- record the latest meeting, email, or call as an activity")
    elif frontmatter.get("stage") == "discovery":
        print("- clarify qualification signals and stakeholder map")
    elif frontmatter.get("stage") == "proposal":
        print("- confirm proposal follow-up owner and decision timeline")
    elif frontmatter.get("stage") == "negotiation":
        print("- capture blockers, owners, and close path explicitly")
    else:
        print("- review summary, next steps, and supporting records")


def build_parser():
    parser = argparse.ArgumentParser(description="Manage opportunity lifecycle workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a canonical opportunity.")
    create_parser.add_argument("--account", required=True)
    create_parser.add_argument("--organization")
    create_parser.add_argument("--primary-contact", required=True)
    create_parser.add_argument("--deal")
    create_parser.add_argument("--source-lead")
    create_parser.add_argument("--name")
    create_parser.add_argument("--opportunity-type", default="advisory")
    create_parser.add_argument("--stage", default="discovery")
    create_parser.add_argument("--probability", type=int, default=10)
    create_parser.add_argument("--commercial-value", type=int, default=0)
    create_parser.add_argument("--close-date")
    create_parser.add_argument("--product-service")
    create_parser.add_argument("--owner")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--summary")
    create_parser.add_argument("--influencers", nargs="*", default=[])
    create_parser.add_argument("--next-steps", nargs="*", default=[])
    create_parser.add_argument("--year", type=int)
    create_parser.set_defaults(func=cmd_create)

    update_parser = subparsers.add_parser("update", help="Update opportunity structure or metadata.")
    update_parser.add_argument("opportunity")
    update_parser.add_argument("--name")
    update_parser.add_argument("--account")
    update_parser.add_argument("--organization")
    update_parser.add_argument("--primary-contact")
    update_parser.add_argument("--deal")
    update_parser.add_argument("--opportunity-type")
    update_parser.add_argument("--product-service")
    update_parser.add_argument("--commercial-value", type=int)
    update_parser.add_argument("--close-date")
    update_parser.add_argument("--source")
    update_parser.add_argument("--source-ref")
    update_parser.add_argument("--summary")
    update_parser.add_argument("--next-steps", nargs="*")
    update_parser.set_defaults(func=cmd_update)

    stakeholder_parser = subparsers.add_parser("assign-stakeholders", help="Assign primary contact or influencers.")
    stakeholder_parser.add_argument("opportunity")
    stakeholder_parser.add_argument("--primary-contact")
    stakeholder_parser.add_argument("--influencers", nargs="*")
    stakeholder_parser.set_defaults(func=cmd_assign_stakeholders)

    stage_parser = subparsers.add_parser("set-stage", help="Update opportunity stage.")
    stage_parser.add_argument("opportunity")
    stage_parser.add_argument("--stage", required=True)
    stage_parser.add_argument("--probability", type=int)
    stage_parser.set_defaults(func=cmd_set_stage)

    probability_parser = subparsers.add_parser("set-probability", help="Update opportunity probability only.")
    probability_parser.add_argument("opportunity")
    probability_parser.add_argument("--probability", required=True, type=int)
    probability_parser.set_defaults(func=cmd_set_probability)

    won_parser = subparsers.add_parser("mark-won", help="Mark opportunity closed won.")
    won_parser.add_argument("opportunity")
    won_parser.add_argument("--close-date")
    won_parser.set_defaults(func=cmd_mark_won)

    lost_parser = subparsers.add_parser("mark-lost", help="Mark opportunity closed lost.")
    lost_parser.add_argument("opportunity")
    lost_parser.add_argument("--reason", required=True)
    lost_parser.add_argument("--lost-date")
    lost_parser.add_argument("--lost-at-stage")
    lost_parser.set_defaults(func=cmd_mark_lost)

    archive_parser = subparsers.add_parser("archive-stale", help="Archive a stale opportunity.")
    archive_parser.add_argument("opportunity")
    archive_parser.add_argument("--reason")
    archive_parser.add_argument("--recheck-date")
    archive_parser.add_argument("--recheck-task")
    archive_parser.add_argument("--recheck-priority", default="medium")
    archive_parser.set_defaults(func=cmd_archive_stale)

    task_parser = subparsers.add_parser("spawn-task", help="Create a task linked to the opportunity.")
    task_parser.add_argument("opportunity")
    task_parser.add_argument("--name", required=True)
    task_parser.add_argument("--due-date", required=True)
    task_parser.add_argument("--priority", default="medium")
    task_parser.add_argument("--description")
    task_parser.set_defaults(func=cmd_spawn_task)

    activity_parser = subparsers.add_parser("spawn-activity", help="Create an activity linked to the opportunity.")
    activity_parser.add_argument("opportunity")
    activity_parser.add_argument("--title", required=True)
    activity_parser.add_argument("--activity-type", required=True)
    activity_parser.add_argument("--date")
    activity_parser.add_argument("--status", default="completed")
    activity_parser.add_argument("--summary")
    activity_parser.add_argument("--outcomes")
    activity_parser.set_defaults(func=cmd_spawn_activity)

    note_parser = subparsers.add_parser("spawn-note", help="Create a note linked to the opportunity.")
    note_parser.add_argument("opportunity")
    note_parser.add_argument("--title", required=True)
    note_parser.add_argument("--context")
    note_parser.add_argument("--implication-1")
    note_parser.add_argument("--implication-2")
    note_parser.set_defaults(func=cmd_spawn_note)

    review_parser = subparsers.add_parser("review", help="Review current opportunity state and gaps.")
    review_parser.add_argument("opportunity")
    review_parser.set_defaults(func=cmd_review)

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
