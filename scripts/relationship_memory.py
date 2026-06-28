import json
import os
from datetime import date, datetime, timedelta

from frontmatter_utils import load_frontmatter_file


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
    return os.getcwd()


CRM_DATA_PATH = get_crm_data_path()
RELATIONSHIP_MEMORY_PATH = os.path.join(CRM_DATA_PATH, "RELATIONSHIP_MEMORY.md")
INTERACTIONS_PATH = os.path.join(CRM_DATA_PATH, "staging", "interactions.json")
ENTITY_DIRS = {
    "Organizations": os.path.join(CRM_DATA_PATH, "Organizations"),
    "Accounts": os.path.join(CRM_DATA_PATH, "Accounts"),
    "Contacts": os.path.join(CRM_DATA_PATH, "Contacts"),
    "Opportunities": os.path.join(CRM_DATA_PATH, "Opportunities"),
    "Engagements": os.path.join(CRM_DATA_PATH, "Engagements"),
    "Workstreams": os.path.join(CRM_DATA_PATH, "Workstreams"),
    "Source-Artifacts": os.path.join(CRM_DATA_PATH, "Source-Artifacts"),
    "Retainers": os.path.join(CRM_DATA_PATH, "Retainers"),
    "Invoices": os.path.join(CRM_DATA_PATH, "Invoices"),
    "Payments": os.path.join(CRM_DATA_PATH, "Payments"),
    "Leads": os.path.join(CRM_DATA_PATH, "Leads"),
}
LINKED_DIRS = {
    "Notes": os.path.join(CRM_DATA_PATH, "Notes"),
    "Activities": os.path.join(CRM_DATA_PATH, "Activities"),
    "Tasks": os.path.join(CRM_DATA_PATH, "Tasks"),
    "Source-Artifacts": os.path.join(CRM_DATA_PATH, "Source-Artifacts"),
    "Retainers": os.path.join(CRM_DATA_PATH, "Retainers"),
    "Invoices": os.path.join(CRM_DATA_PATH, "Invoices"),
    "Payments": os.path.join(CRM_DATA_PATH, "Payments"),
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def collect_records(directory):
    records = []
    if not os.path.exists(directory):
        return records

    for root, _, files in os.walk(directory):
        for file_name in files:
            if not file_name.endswith(".md"):
                continue
            file_path = os.path.join(root, file_name)
            try:
                frontmatter, body = load_frontmatter_file(file_path)
            except Exception:
                continue
            if not frontmatter:
                continue
            if root == ENTITY_DIRS.get("Accounts") and frontmatter.get("migration-target") == "organization":
                continue
            records.append(
                {
                    "file_path": file_path,
                    "frontmatter": frontmatter,
                    "body": body,
                    "link": to_wikilink(file_path),
                    "basename": os.path.splitext(os.path.basename(file_path))[0],
                }
            )
    return records


def to_wikilink(file_path):
    rel_path = os.path.relpath(file_path, CRM_DATA_PATH)
    return f"[[{os.path.splitext(rel_path)[0]}]]"


def normalize_link(value):
    if not value:
        return ""
    text = str(value).strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text


def link_matches(value, record_link):
    return normalize_link(value) == normalize_link(record_link)


def latest_date(records):
    dates = []
    for record in records:
        frontmatter = record["frontmatter"]
        record_date = frontmatter.get("date") or frontmatter.get("activity-date") or frontmatter.get("date-modified")
        if isinstance(record_date, date):
            dates.append(record_date)
        elif isinstance(record_date, str):
            try:
                dates.append(datetime.strptime(record_date, "%Y-%m-%d").date())
            except ValueError:
                continue
    return max(dates) if dates else None


def normalize_amount(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return 0.0
    return 0.0


def collect_related(entity, notes, activities, tasks, source_artifacts, retainers, invoices, payments):
    entity_link = entity["link"]
    related_notes = []
    related_activities = []
    related_tasks = []
    related_source_artifacts = []
    related_retainers = []
    related_invoices = []
    related_payments = []

    for note in notes:
        frontmatter = note["frontmatter"]
        if link_matches(frontmatter.get("primary-parent"), entity_link) or any(
            link_matches(link, entity_link) for link in frontmatter.get("secondary-links", [])
        ):
            related_notes.append(note)

    for activity in activities:
        frontmatter = activity["frontmatter"]
        if link_matches(frontmatter.get("primary-parent"), entity_link) or any(
            link_matches(link, entity_link) for link in frontmatter.get("secondary-links", [])
        ):
            related_activities.append(activity)

    for task in tasks:
        frontmatter = task["frontmatter"]
        candidates = [
            frontmatter.get("account"),
            frontmatter.get("contact"),
            frontmatter.get("opportunity"),
            frontmatter.get("engagement"),
            frontmatter.get("workstream"),
            frontmatter.get("lead"),
            frontmatter.get("primary-parent"),
        ]
        if any(link_matches(candidate, entity_link) for candidate in candidates):
            related_tasks.append(task)

    for record in source_artifacts:
        frontmatter = record["frontmatter"]
        if link_matches(frontmatter.get("primary-parent"), entity_link) or any(
            link_matches(link, entity_link) for link in frontmatter.get("secondary-links", [])
        ):
            related_source_artifacts.append(record)

    for record in retainers:
        if link_matches(record["frontmatter"].get("engagement"), entity_link):
            related_retainers.append(record)

    for record in invoices:
        frontmatter = record["frontmatter"]
        candidates = [
            frontmatter.get("engagement"),
            frontmatter.get("workstream"),
            frontmatter.get("retainer"),
        ]
        if any(link_matches(candidate, entity_link) for candidate in candidates):
            related_invoices.append(record)

    for record in payments:
        frontmatter = record["frontmatter"]
        candidates = [
            frontmatter.get("engagement"),
            frontmatter.get("invoice"),
        ]
        if any(link_matches(candidate, entity_link) for candidate in candidates):
            related_payments.append(record)

    return related_notes, related_activities, related_tasks, related_source_artifacts, related_retainers, related_invoices, related_payments


def build_observed_summary(entity, notes, activities, tasks, source_artifacts, retainers, invoices, payments, interactions_cache):
    bullets = []
    bullets.append(f"Linked notes: {len(notes)}")
    bullets.append(f"Linked activities: {len(activities)}")
    bullets.append(f"Open tasks: {sum(1 for task in tasks if task['frontmatter'].get('status') in {'todo', 'in-progress'})}")
    if source_artifacts:
        bullets.append(f"Linked source artifacts: {len(source_artifacts)}")
    if retainers:
        bullets.append(f"Linked retainers: {len(retainers)}")
    if invoices:
        bullets.append(f"Linked invoices: {len(invoices)}")
    if payments:
        bullets.append(f"Linked payments: {len(payments)}")

    latest_activity = latest_date(activities)
    if latest_activity:
        bullets.append(f"Latest recorded activity: {latest_activity}")

    email = entity["frontmatter"].get("email")
    if email and email in interactions_cache:
        hits = interactions_cache[email].get("hits_last_7_days", 0)
        last_date = interactions_cache[email].get("last_date")
        bullets.append(f"Workspace telemetry: {hits} hit(s) in last 7 days; last signal {last_date}")

    source_refs = []
    for record in notes + activities:
        source_ref = record["frontmatter"].get("source-ref")
        if source_ref and source_ref not in source_refs:
            source_refs.append(source_ref)
    for record in source_artifacts + invoices + payments:
        source_ref = record["frontmatter"].get("source-ref")
        if source_ref and source_ref not in source_refs:
            source_refs.append(source_ref)
    if source_refs:
        bullets.append("Source refs: " + ", ".join(source_refs[:3]))
    if invoices or payments:
        total_invoiced = sum(normalize_amount(record["frontmatter"].get("amount")) for record in invoices if record["frontmatter"].get("status") != "void")
        total_received = sum(normalize_amount(record["frontmatter"].get("amount")) for record in payments if record["frontmatter"].get("status") in {"received", "reconciled"})
        bullets.append(f"Finance rollup: invoiced {int(total_invoiced) if total_invoiced.is_integer() else round(total_invoiced, 2)}, received {int(total_received) if total_received.is_integer() else round(total_received, 2)}")
    return bullets


def build_inferred_summary(notes, activities, tasks, source_artifacts, retainers, invoices, payments):
    bullets = []
    today = date.today()
    latest_activity = latest_date(activities)
    open_tasks = [task for task in tasks if task["frontmatter"].get("status") in {"todo", "in-progress"}]
    overdue_tasks = [
        task
        for task in open_tasks
        if isinstance(task["frontmatter"].get("due-date"), date) and task["frontmatter"]["due-date"] < today
    ]

    if latest_activity and latest_activity >= today - timedelta(days=7):
        bullets.append("Momentum appears active based on recent linked activity.")
    elif activities:
        bullets.append("Relationship memory exists, but recent momentum appears muted.")
    else:
        bullets.append("Memory coverage is thin; there are no linked activities yet.")

    if overdue_tasks:
        bullets.append(f"Execution pressure is building with {len(overdue_tasks)} overdue linked task(s).")
    elif open_tasks:
        bullets.append(f"There are {len(open_tasks)} open linked task(s) to advance this relationship.")

    if notes and not activities:
        bullets.append("Context is captured primarily in notes rather than event history.")
    elif activities and not notes:
        bullets.append("Interaction history is present, but durable context notes are sparse.")
    if source_artifacts and not notes:
        bullets.append("Evidence exists, but durable interpretation notes are still thin.")
    overdue_invoices = [
        record
        for record in invoices
        if str(record["frontmatter"].get("status", "")).lower() == "overdue"
        or (
            str(record["frontmatter"].get("status", "")).lower() in {"issued", "partially-paid"}
            and isinstance(record["frontmatter"].get("due-date"), date)
            and record["frontmatter"]["due-date"] < today
        )
    ]
    total_invoiced = sum(normalize_amount(record["frontmatter"].get("amount")) for record in invoices if record["frontmatter"].get("status") != "void")
    total_received = sum(normalize_amount(record["frontmatter"].get("amount")) for record in payments if record["frontmatter"].get("status") in {"received", "reconciled"})
    if overdue_invoices:
        bullets.append(f"Commercial follow-through needs attention with {len(overdue_invoices)} overdue invoice(s).")
    elif total_invoiced > total_received:
        bullets.append("Commercial work is partially collected, so receivables still need tracking.")
    elif retainers and not invoices:
        bullets.append("A retainer exists without invoice coverage yet.")
    return bullets


def related_links(records, limit=5):
    return ", ".join(record["link"] for record in records[:limit]) if records else "None"


def entity_display_name(entity_type, frontmatter, basename):
    if entity_type == "Organizations":
        return frontmatter.get("organization-name", basename)
    if entity_type == "Accounts":
        return frontmatter.get("company-name", basename)
    if entity_type == "Contacts":
        return frontmatter.get("full-name", basename)
    if entity_type == "Opportunities":
        return frontmatter.get("opportunity-name", basename)
    if entity_type == "Engagements":
        return frontmatter.get("engagement-name", basename)
    if entity_type == "Workstreams":
        return frontmatter.get("workstream-name", basename)
    if entity_type == "Leads":
        return frontmatter.get("lead-name", basename)
    return basename


def build_memory_section(entity_type, records, notes, activities, tasks, source_artifacts, retainers, invoices, payments, interactions_cache):
    if not records:
        return f"## {entity_type}\n\nNo records found.\n"

    lines = [f"## {entity_type}", ""]
    for entity in records:
        related = collect_related(entity, notes, activities, tasks, source_artifacts, retainers, invoices, payments)
        related_notes, related_activities, related_tasks, related_source_artifacts, related_retainers, related_invoices, related_payments = related
        observed = build_observed_summary(
            entity,
            related_notes,
            related_activities,
            related_tasks,
            related_source_artifacts,
            related_retainers,
            related_invoices,
            related_payments,
            interactions_cache,
        )
        inferred = build_inferred_summary(
            related_notes,
            related_activities,
            related_tasks,
            related_source_artifacts,
            related_retainers,
            related_invoices,
            related_payments,
        )
        display_name = entity_display_name(entity_type, entity["frontmatter"], entity["basename"])
        lines.append(f"### {entity['link']} {display_name}")
        lines.append("")
        lines.append("Observed:")
        for bullet in observed:
            lines.append(f"- {bullet}")
        lines.append("Inferred:")
        for bullet in inferred:
            lines.append(f"- {bullet}")
        lines.append("Drill down:")
        lines.append(f"- Notes: {related_links(related_notes)}")
        lines.append(f"- Activities: {related_links(related_activities)}")
        lines.append(f"- Tasks: {related_links(related_tasks)}")
        lines.append(f"- Source Artifacts: {related_links(related_source_artifacts)}")
        lines.append(f"- Retainers: {related_links(related_retainers)}")
        lines.append(f"- Invoices: {related_links(related_invoices)}")
        lines.append(f"- Payments: {related_links(related_payments)}")
        lines.append("")
    return "\n".join(lines)


def main():
    interactions_cache = load_json(INTERACTIONS_PATH, {})
    notes = collect_records(LINKED_DIRS["Notes"])
    activities = collect_records(LINKED_DIRS["Activities"])
    tasks = collect_records(LINKED_DIRS["Tasks"])
    source_artifacts = collect_records(LINKED_DIRS["Source-Artifacts"])
    retainers = collect_records(LINKED_DIRS["Retainers"])
    invoices = collect_records(LINKED_DIRS["Invoices"])
    payments = collect_records(LINKED_DIRS["Payments"])

    sections = [
        "# Relationship Memory",
        "",
        f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "This derived view assembles relationship memory from linked Notes, Activities, Tasks, and source references.",
        "",
    ]

    for entity_type, directory in ENTITY_DIRS.items():
        records = collect_records(directory)
        sections.append(build_memory_section(entity_type, records, notes, activities, tasks, source_artifacts, retainers, invoices, payments, interactions_cache))
        sections.append("")

    with open(RELATIONSHIP_MEMORY_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sections).rstrip() + "\n")

    print(f"Relationship memory written to {RELATIONSHIP_MEMORY_PATH}")


if __name__ == "__main__":
    main()
