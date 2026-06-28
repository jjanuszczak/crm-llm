import argparse
import os
import sys
from datetime import date


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from crm_manager_utils import (  # noqa: E402
    display_name,
    link_for_path,
    load_display_name,
    replace_section,
    resolve_optional_record_path,
    resolve_record_path,
)
from frontmatter_utils import find_markdown_file, load_frontmatter_file, parse_markdown_frontmatter, slugify, write_frontmatter_file  # noqa: E402
from lead_manager import get_crm_data_path  # noqa: E402
from navigation_manager import record_mutation  # noqa: E402


VALID_ENGAGEMENT_TYPES = {"retainer", "pilot", "advisory", "consulting", "board", "workshop", "research", "financing-support", "other"}
VALID_ENGAGEMENT_STATUSES = {"active", "paused", "completed", "cancelled"}
VALID_COMMERCIAL_MODELS = {"retainer", "fixed-fee", "milestone", "pilot", "hourly", "hybrid", "other"}
VALID_WORKSTREAM_TYPES = {"advisory", "implementation", "research", "marketing", "board-support", "fundraising-support", "operations", "other"}
VALID_WORKSTREAM_STATUSES = {"planned", "active", "waiting", "paused", "completed", "cancelled"}
VALID_PRIORITIES = {"high", "medium", "low"}

CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")
ENGAGEMENTS_DIR = os.path.join(CRM_DATA_PATH, "Engagements")
WORKSTREAMS_DIR = os.path.join(CRM_DATA_PATH, "Workstreams")
TASKS_DIR = os.path.join(CRM_DATA_PATH, "Tasks")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
NOTES_DIR = os.path.join(CRM_DATA_PATH, "Notes")
SOURCE_ARTIFACTS_DIR = os.path.join(CRM_DATA_PATH, "Source-Artifacts")

ENGAGEMENT_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "engagement-template.md")
WORKSTREAM_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "workstream-template.md")


def ensure_dirs():
    os.makedirs(ENGAGEMENTS_DIR, exist_ok=True)
    os.makedirs(WORKSTREAMS_DIR, exist_ok=True)


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


def ensure_choice(value, valid, label):
    if value not in valid:
        raise ValueError(f"Invalid {label} '{value}'. Expected one of: {', '.join(sorted(valid))}")
    return value


def engagement_related_links(frontmatter):
    return [
        frontmatter.get("organization", ""),
        frontmatter.get("account", ""),
        frontmatter.get("source-opportunity", ""),
        frontmatter.get("primary-contact", ""),
    ]


def workstream_related_links(frontmatter):
    return [
        frontmatter.get("engagement", ""),
        frontmatter.get("organization", ""),
        frontmatter.get("account", ""),
    ]


def infer_organization_path(account_path):
    frontmatter, _body = load_frontmatter_file(account_path)
    organization_value = frontmatter.get("organization")
    if not organization_value:
        raise ValueError("Account is missing canonical organization link.")
    return resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, organization_value, "Organization")


def load_engagement(reference):
    path = resolve_record_path(ENGAGEMENTS_DIR, CRM_DATA_PATH, reference, "Engagement")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def load_workstream(reference):
    path = resolve_record_path(WORKSTREAMS_DIR, CRM_DATA_PATH, reference, "Workstream")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def build_engagement_body(name, summary, success_definition, commercial_notes):
    rendered = render_template(
        ENGAGEMENT_TEMPLATE_PATH,
        {
            "engagement-id": slugify(name),
            "Engagement Name": name,
            "Owner": "john",
            "Organization Link": "",
            "Account Link": "",
            "Source Opportunity": "",
            "Primary Contact": "",
            "retainer | pilot | advisory | consulting | board | workshop | research | financing-support | other": "advisory",
            "active | paused | completed | cancelled": "active",
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
            "retainer | fixed-fee | milestone | pilot | hourly | hybrid | other": "other",
            "USD | PHP | SGD | EUR | GBP | other": "USD",
            "Success definition": success_definition or "",
            "Source Reference": "",
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = replace_section(body, "Commercial Summary", summary or "Created through crm-engagement-manager.")
    body = replace_section(body, "Success Definition", success_definition or "")
    body = replace_section(body, "Commercial Notes", commercial_notes or "")
    return body


def build_workstream_body(name, objective, scope, current_state, outputs):
    rendered = render_template(
        WORKSTREAM_TEMPLATE_PATH,
        {
            "workstream-id": slugify(name),
            "Workstream Name": name,
            "Owner": "john",
            "Engagement Link": "",
            "Organization Link": "",
            "Account Link": "",
            "advisory | implementation | research | marketing | board-support | fundraising-support | operations | other": "advisory",
            "planned | active | waiting | paused | completed | cancelled": "active",
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
            "high | medium | low": "medium",
            "Success definition": objective or "",
            "Source Reference": "",
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = replace_section(body, "Objective", objective or "")
    body = replace_section(body, "Scope", scope or "")
    body = replace_section(body, "Current State", current_state or "")
    if outputs:
        lines = "\n".join(f"- {item}" for item in outputs)
        body = replace_section(body, "Key Deliverables / Outputs", lines)
    return body


def linked_to_record(frontmatter, record_link):
    normalized = normalize_reference(record_link)
    values = [frontmatter.get("primary-parent"), frontmatter.get("account"), frontmatter.get("contact"), frontmatter.get("opportunity"), frontmatter.get("engagement"), frontmatter.get("workstream"), frontmatter.get("lead")]
    for value in values:
        if normalize_reference(value) == normalized:
            return True
    for field in ["secondary-links", "evidence-links"]:
        raw = frontmatter.get(field) or []
        values = raw if isinstance(raw, list) else [raw]
        if any(normalize_reference(item) == normalized for item in values):
            return True
    return False


def gather_related(base_dir, record_link):
    items = []
    if not os.path.exists(base_dir):
        return items
    for root, _dirs, files in os.walk(base_dir):
        for file_name in sorted(files):
            if not file_name.endswith(".md"):
                continue
            file_path = os.path.join(root, file_name)
            try:
                frontmatter, _body = load_frontmatter_file(file_path)
            except Exception:
                continue
            if linked_to_record(frontmatter, record_link):
                items.append((file_path, frontmatter))
    return items


def gather_related_many(base_dir, record_links):
    combined = []
    seen = set()
    for record_link in record_links:
        for file_path, frontmatter in gather_related(base_dir, record_link):
            key = os.path.abspath(file_path)
            if key in seen:
                continue
            seen.add(key)
            combined.append((file_path, frontmatter))
    return combined


def cmd_create(args):
    ensure_dirs()
    ensure_choice(args.engagement_type, VALID_ENGAGEMENT_TYPES, "engagement-type")
    ensure_choice(args.status, VALID_ENGAGEMENT_STATUSES, "status")
    ensure_choice(args.commercial_model, VALID_COMMERCIAL_MODELS, "commercial-model")

    account_path = resolve_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, args.account, "Account")
    account_fm, _account_body = load_frontmatter_file(account_path)
    organization_path = resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, args.organization, "Organization") if args.organization else infer_organization_path(account_path)
    source_opportunity_path = resolve_optional_record_path(OPPORTUNITIES_DIR, CRM_DATA_PATH, args.source_opportunity, "Opportunity")
    primary_contact_path = resolve_optional_record_path(CONTACTS_DIR, CRM_DATA_PATH, args.primary_contact, "Contact")

    if args.name:
        engagement_name = args.name
    elif source_opportunity_path:
        engagement_name = load_display_name(source_opportunity_path)
    else:
        engagement_name = f"{display_name(account_fm, account_path)} - {args.engagement_type.replace('-', ' ').title()} - {date.today().year}"

    file_path = os.path.join(ENGAGEMENTS_DIR, f"{slugify(engagement_name)}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Engagement already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        ENGAGEMENT_TEMPLATE_PATH,
        {
            "engagement-id": slugify(engagement_name),
            "Engagement Name": engagement_name,
            "Owner": args.owner or account_fm.get("owner", "john"),
            "Organization Link": os.path.splitext(os.path.relpath(organization_path, CRM_DATA_PATH))[0],
            "Account Link": os.path.splitext(os.path.relpath(account_path, CRM_DATA_PATH))[0],
            "Source Opportunity": os.path.splitext(os.path.relpath(source_opportunity_path, CRM_DATA_PATH))[0] if source_opportunity_path else "",
            "Primary Contact": os.path.splitext(os.path.relpath(primary_contact_path, CRM_DATA_PATH))[0] if primary_contact_path else "",
            "retainer | pilot | advisory | consulting | board | workshop | research | financing-support | other": args.engagement_type,
            "active | paused | completed | cancelled": args.status,
            "YYYY-MM-DD": today,
            "retainer | fixed-fee | milestone | pilot | hourly | hybrid | other": args.commercial_model,
            "USD | PHP | SGD | EUR | GBP | other": args.currency,
            "Success definition": args.success_definition or "",
            "Source Reference": args.source_ref or "",
        },
    )
    frontmatter, _body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = f"eng-{slugify(engagement_name)}"
    frontmatter["engagement-name"] = engagement_name
    frontmatter["owner"] = args.owner or account_fm.get("owner", "john")
    frontmatter["organization"] = link_for_path(organization_path, CRM_DATA_PATH)
    frontmatter["account"] = link_for_path(account_path, CRM_DATA_PATH)
    frontmatter["source-opportunity"] = link_for_path(source_opportunity_path, CRM_DATA_PATH) if source_opportunity_path else ""
    frontmatter["primary-contact"] = link_for_path(primary_contact_path, CRM_DATA_PATH) if primary_contact_path else ""
    frontmatter["engagement-type"] = args.engagement_type
    frontmatter["status"] = args.status
    frontmatter["start-date"] = args.start_date or today
    frontmatter["target-end-date"] = args.target_end_date or ""
    frontmatter["end-date"] = args.end_date or ""
    frontmatter["commercial-model"] = args.commercial_model
    frontmatter["currency"] = args.currency
    frontmatter["contracted-value"] = args.contracted_value
    frontmatter["success-definition"] = args.success_definition or ""
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = build_engagement_body(engagement_name, args.summary or "", args.success_definition or "", args.commercial_notes or "")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Engagement",
        title=engagement_name,
        path=file_path,
        source=args.source,
        related=engagement_related_links(frontmatter),
        details=f"engagement-type={args.engagement_type}; status={args.status}; commercial-model={args.commercial_model}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_update(args):
    file_path, frontmatter, body = load_engagement(args.engagement)
    updates = []

    if args.name:
        frontmatter["engagement-name"] = args.name
        updates.append(f"name={args.name}")
    if args.organization:
        organization_path = resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, args.organization, "Organization")
        frontmatter["organization"] = link_for_path(organization_path, CRM_DATA_PATH)
        updates.append(f"organization={load_display_name(organization_path)}")
    if args.account:
        account_path = resolve_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, args.account, "Account")
        frontmatter["account"] = link_for_path(account_path, CRM_DATA_PATH)
        updates.append(f"account={load_display_name(account_path)}")
    if args.primary_contact is not None:
        primary_contact_path = resolve_optional_record_path(CONTACTS_DIR, CRM_DATA_PATH, args.primary_contact, "Contact")
        frontmatter["primary-contact"] = link_for_path(primary_contact_path, CRM_DATA_PATH) if primary_contact_path else ""
        updates.append("primary-contact updated")
    if args.engagement_type:
        frontmatter["engagement-type"] = ensure_choice(args.engagement_type, VALID_ENGAGEMENT_TYPES, "engagement-type")
        updates.append(f"engagement-type={args.engagement_type}")
    if args.start_date:
        frontmatter["start-date"] = args.start_date
        updates.append(f"start-date={args.start_date}")
    if args.target_end_date is not None:
        frontmatter["target-end-date"] = args.target_end_date
        updates.append("target-end-date updated")
    if args.end_date is not None:
        frontmatter["end-date"] = args.end_date
        updates.append("end-date updated")
    if args.commercial_model:
        frontmatter["commercial-model"] = ensure_choice(args.commercial_model, VALID_COMMERCIAL_MODELS, "commercial-model")
        updates.append(f"commercial-model={args.commercial_model}")
    if args.currency:
        frontmatter["currency"] = args.currency
        updates.append(f"currency={args.currency}")
    if args.contracted_value is not None:
        frontmatter["contracted-value"] = args.contracted_value
        updates.append(f"contracted-value={args.contracted_value}")
    if args.success_definition is not None:
        frontmatter["success-definition"] = args.success_definition
        body = replace_section(body, "Success Definition", args.success_definition)
        updates.append("success-definition updated")
    if args.summary is not None:
        body = replace_section(body, "Commercial Summary", args.summary)
        updates.append("summary updated")
    if args.commercial_notes is not None:
        body = replace_section(body, "Commercial Notes", args.commercial_notes)
        updates.append("commercial-notes updated")
    if args.source is not None:
        frontmatter["source"] = args.source
        updates.append(f"source={args.source}")
    if args.source_ref is not None:
        frontmatter["source-ref"] = args.source_ref
        updates.append("source-ref updated")

    if not updates:
        raise ValueError("No updates provided.")

    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Engagement",
        title=frontmatter.get("engagement-name", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=engagement_related_links(frontmatter),
        details="; ".join(updates),
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_set_status(args):
    file_path, frontmatter, body = load_engagement(args.engagement)
    status = ensure_choice(args.status, VALID_ENGAGEMENT_STATUSES, "status")
    frontmatter["status"] = status
    if args.end_date is not None:
        frontmatter["end-date"] = args.end_date
    if status in {"completed", "cancelled"} and not frontmatter.get("end-date"):
        frontmatter["end-date"] = date.today().strftime("%Y-%m-%d")
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Engagement",
        title=frontmatter.get("engagement-name", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=engagement_related_links(frontmatter),
        details=f"status={status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_link_opportunity(args):
    file_path, frontmatter, body = load_engagement(args.engagement)
    source_opportunity_path = resolve_optional_record_path(OPPORTUNITIES_DIR, CRM_DATA_PATH, args.source_opportunity, "Opportunity")
    frontmatter["source-opportunity"] = link_for_path(source_opportunity_path, CRM_DATA_PATH) if source_opportunity_path else ""
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Engagement",
        title=frontmatter.get("engagement-name", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=engagement_related_links(frontmatter),
        details="source-opportunity updated",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_create_workstream(args):
    ensure_dirs()
    ensure_choice(args.workstream_type, VALID_WORKSTREAM_TYPES, "workstream-type")
    ensure_choice(args.status, VALID_WORKSTREAM_STATUSES, "status")
    ensure_choice(args.priority, VALID_PRIORITIES, "priority")

    engagement_path, engagement_fm, _engagement_body = load_engagement(args.engagement)
    account_path = resolve_record_path(ACCOUNTS_DIR, CRM_DATA_PATH, engagement_fm.get("account"), "Account")
    organization_path = resolve_record_path(ORGANIZATIONS_DIR, CRM_DATA_PATH, engagement_fm.get("organization"), "Organization")

    workstream_name = args.name or f"{engagement_fm.get('engagement-name', load_display_name(engagement_path))} - {args.workstream_type.replace('-', ' ').title()}"
    file_path = os.path.join(WORKSTREAMS_DIR, f"{slugify(workstream_name)}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Workstream already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        WORKSTREAM_TEMPLATE_PATH,
        {
            "workstream-id": slugify(workstream_name),
            "Workstream Name": workstream_name,
            "Owner": args.owner or engagement_fm.get("owner", "john"),
            "Engagement Link": os.path.splitext(os.path.relpath(engagement_path, CRM_DATA_PATH))[0],
            "Organization Link": os.path.splitext(os.path.relpath(organization_path, CRM_DATA_PATH))[0],
            "Account Link": os.path.splitext(os.path.relpath(account_path, CRM_DATA_PATH))[0],
            "advisory | implementation | research | marketing | board-support | fundraising-support | operations | other": args.workstream_type,
            "planned | active | waiting | paused | completed | cancelled": args.status,
            "YYYY-MM-DD": today,
            "high | medium | low": args.priority,
            "Success definition": args.success_definition or "",
            "Source Reference": args.source_ref or "",
        },
    )
    frontmatter, _body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = f"ws-{slugify(workstream_name)}"
    frontmatter["workstream-name"] = workstream_name
    frontmatter["owner"] = args.owner or engagement_fm.get("owner", "john")
    frontmatter["engagement"] = link_for_path(engagement_path, CRM_DATA_PATH)
    frontmatter["organization"] = link_for_path(organization_path, CRM_DATA_PATH)
    frontmatter["account"] = link_for_path(account_path, CRM_DATA_PATH)
    frontmatter["workstream-type"] = args.workstream_type
    frontmatter["status"] = args.status
    frontmatter["start-date"] = args.start_date or today
    frontmatter["target-end-date"] = args.target_end_date or ""
    frontmatter["end-date"] = args.end_date or ""
    frontmatter["priority"] = args.priority
    frontmatter["success-definition"] = args.success_definition or ""
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = build_workstream_body(workstream_name, args.objective or "", args.scope or "", args.current_state or "", args.outputs)
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Workstream",
        title=workstream_name,
        path=file_path,
        source=args.source,
        related=workstream_related_links(frontmatter),
        details=f"workstream-type={args.workstream_type}; status={args.status}; priority={args.priority}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_update_workstream(args):
    file_path, frontmatter, body = load_workstream(args.workstream)
    updates = []
    if args.name:
        frontmatter["workstream-name"] = args.name
        updates.append(f"name={args.name}")
    if args.workstream_type:
        frontmatter["workstream-type"] = ensure_choice(args.workstream_type, VALID_WORKSTREAM_TYPES, "workstream-type")
        updates.append(f"workstream-type={args.workstream_type}")
    if args.status:
        frontmatter["status"] = ensure_choice(args.status, VALID_WORKSTREAM_STATUSES, "status")
        updates.append(f"status={args.status}")
    if args.priority:
        frontmatter["priority"] = ensure_choice(args.priority, VALID_PRIORITIES, "priority")
        updates.append(f"priority={args.priority}")
    if args.start_date:
        frontmatter["start-date"] = args.start_date
        updates.append(f"start-date={args.start_date}")
    if args.target_end_date is not None:
        frontmatter["target-end-date"] = args.target_end_date
        updates.append("target-end-date updated")
    if args.end_date is not None:
        frontmatter["end-date"] = args.end_date
        updates.append("end-date updated")
    if args.success_definition is not None:
        frontmatter["success-definition"] = args.success_definition
        updates.append("success-definition updated")
    if args.objective is not None:
        body = replace_section(body, "Objective", args.objective)
        updates.append("objective updated")
    if args.scope is not None:
        body = replace_section(body, "Scope", args.scope)
        updates.append("scope updated")
    if args.current_state is not None:
        body = replace_section(body, "Current State", args.current_state)
        updates.append("current-state updated")
    if args.outputs is not None:
        body = replace_section(body, "Key Deliverables / Outputs", "\n".join(f"- {item}" for item in args.outputs))
        updates.append("outputs updated")
    if not updates:
        raise ValueError("No updates provided.")
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Workstream",
        title=frontmatter.get("workstream-name", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=workstream_related_links(frontmatter),
        details="; ".join(updates),
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_review(args):
    engagement_path, frontmatter, body = load_engagement(args.engagement)
    engagement_link = link_for_path(engagement_path, CRM_DATA_PATH)
    workstreams = gather_related(WORKSTREAMS_DIR, engagement_link)
    related_links = [engagement_link] + [link_for_path(path, CRM_DATA_PATH) for path, _fm in workstreams]
    tasks = gather_related_many(TASKS_DIR, related_links)
    activities = gather_related_many(ACTIVITIES_DIR, related_links)
    notes = gather_related_many(NOTES_DIR, related_links)
    source_artifacts = gather_related_many(SOURCE_ARTIFACTS_DIR, related_links)

    active_workstreams = [item for item in workstreams if item[1].get("status") not in {"completed", "cancelled"}]
    open_tasks = [item for item in tasks if str(item[1].get("status", "")).lower() not in {"done", "completed", "canceled"}]
    missing = []
    for key in ["organization", "account", "engagement-type", "status", "start-date", "commercial-model"]:
        if not frontmatter.get(key):
            missing.append(key)
    if frontmatter.get("status") == "active" and not active_workstreams:
        missing.append("no-active-workstreams")
    if frontmatter.get("status") == "active" and not open_tasks:
        missing.append("no-open-tasks")

    print(f"Engagement: {frontmatter.get('engagement-name', load_display_name(engagement_path))}")
    print(f"Path: {engagement_path}")
    print(f"Status: {frontmatter.get('status', '')}")
    print(f"Type: {frontmatter.get('engagement-type', '')}")
    print(f"Commercial Model: {frontmatter.get('commercial-model', '')}")
    print(f"Contracted Value: {frontmatter.get('contracted-value', '')} {frontmatter.get('currency', '')}".strip())
    print(f"Source Opportunity: {frontmatter.get('source-opportunity', '') or 'none'}")
    print(f"Active Workstreams: {len(active_workstreams)}")
    print(f"Tasks: {len(open_tasks)}")
    print(f"Activities: {len(activities)}")
    print(f"Notes: {len(notes)}")
    print(f"Source Artifacts: {len(source_artifacts)}")
    print("Missing/Attention:")
    if missing:
        for item in missing:
            print(f"- {item}")
    else:
        print("- none")
    print("Recommended Next Action:")
    if "no-active-workstreams" in missing:
        print("- create the first concrete workstream under this engagement")
    elif "no-open-tasks" in missing:
        print("- create a concrete execution task under the engagement or a workstream")
    elif not source_artifacts:
        print("- attach the key source artifacts or delivery documents")
    else:
        print("- review workstream scope, delivery momentum, and commercial follow-through")
    if args.verbose and body:
        print("Summary:")
        print(body.strip())


def build_parser():
    parser = argparse.ArgumentParser(description="Manage engagement lifecycle workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a canonical engagement.")
    create_parser.add_argument("--account", required=True)
    create_parser.add_argument("--organization")
    create_parser.add_argument("--source-opportunity")
    create_parser.add_argument("--primary-contact")
    create_parser.add_argument("--name")
    create_parser.add_argument("--engagement-type", default="advisory")
    create_parser.add_argument("--status", default="active")
    create_parser.add_argument("--start-date")
    create_parser.add_argument("--target-end-date")
    create_parser.add_argument("--end-date")
    create_parser.add_argument("--commercial-model", default="other")
    create_parser.add_argument("--currency", default="USD")
    create_parser.add_argument("--contracted-value", type=int, default=0)
    create_parser.add_argument("--success-definition")
    create_parser.add_argument("--summary")
    create_parser.add_argument("--commercial-notes")
    create_parser.add_argument("--owner")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.set_defaults(func=cmd_create)

    update_parser = subparsers.add_parser("update", help="Update engagement structure or metadata.")
    update_parser.add_argument("engagement")
    update_parser.add_argument("--name")
    update_parser.add_argument("--organization")
    update_parser.add_argument("--account")
    update_parser.add_argument("--primary-contact")
    update_parser.add_argument("--engagement-type")
    update_parser.add_argument("--start-date")
    update_parser.add_argument("--target-end-date")
    update_parser.add_argument("--end-date")
    update_parser.add_argument("--commercial-model")
    update_parser.add_argument("--currency")
    update_parser.add_argument("--contracted-value", type=int)
    update_parser.add_argument("--success-definition")
    update_parser.add_argument("--summary")
    update_parser.add_argument("--commercial-notes")
    update_parser.add_argument("--source")
    update_parser.add_argument("--source-ref")
    update_parser.set_defaults(func=cmd_update)

    status_parser = subparsers.add_parser("set-status", help="Update engagement status.")
    status_parser.add_argument("engagement")
    status_parser.add_argument("--status", required=True)
    status_parser.add_argument("--end-date")
    status_parser.set_defaults(func=cmd_set_status)

    link_parser = subparsers.add_parser("link-opportunity", help="Attach or clear the source opportunity on an engagement.")
    link_parser.add_argument("engagement")
    link_parser.add_argument("--source-opportunity")
    link_parser.set_defaults(func=cmd_link_opportunity)

    create_workstream_parser = subparsers.add_parser("create-workstream", help="Create a workstream under an engagement.")
    create_workstream_parser.add_argument("--engagement", required=True)
    create_workstream_parser.add_argument("--name")
    create_workstream_parser.add_argument("--workstream-type", default="advisory")
    create_workstream_parser.add_argument("--status", default="active")
    create_workstream_parser.add_argument("--start-date")
    create_workstream_parser.add_argument("--target-end-date")
    create_workstream_parser.add_argument("--end-date")
    create_workstream_parser.add_argument("--priority", default="medium")
    create_workstream_parser.add_argument("--success-definition")
    create_workstream_parser.add_argument("--objective")
    create_workstream_parser.add_argument("--scope")
    create_workstream_parser.add_argument("--current-state")
    create_workstream_parser.add_argument("--outputs", nargs="*", default=[])
    create_workstream_parser.add_argument("--owner")
    create_workstream_parser.add_argument("--source", default="manual")
    create_workstream_parser.add_argument("--source-ref")
    create_workstream_parser.set_defaults(func=cmd_create_workstream)

    update_workstream_parser = subparsers.add_parser("update-workstream", help="Update a workstream.")
    update_workstream_parser.add_argument("workstream")
    update_workstream_parser.add_argument("--name")
    update_workstream_parser.add_argument("--workstream-type")
    update_workstream_parser.add_argument("--status")
    update_workstream_parser.add_argument("--priority")
    update_workstream_parser.add_argument("--start-date")
    update_workstream_parser.add_argument("--target-end-date")
    update_workstream_parser.add_argument("--end-date")
    update_workstream_parser.add_argument("--success-definition")
    update_workstream_parser.add_argument("--objective")
    update_workstream_parser.add_argument("--scope")
    update_workstream_parser.add_argument("--current-state")
    update_workstream_parser.add_argument("--outputs", nargs="*")
    update_workstream_parser.set_defaults(func=cmd_update_workstream)

    review_parser = subparsers.add_parser("review", help="Review an engagement and its linked execution surface.")
    review_parser.add_argument("engagement")
    review_parser.add_argument("--verbose", action="store_true")
    review_parser.set_defaults(func=cmd_review)

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
