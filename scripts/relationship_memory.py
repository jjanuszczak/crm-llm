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
    "Accounts": os.path.join(CRM_DATA_PATH, "Accounts"),
    "Contacts": os.path.join(CRM_DATA_PATH, "Contacts"),
    "Opportunities": os.path.join(CRM_DATA_PATH, "Opportunities"),
    "Leads": os.path.join(CRM_DATA_PATH, "Leads"),
}
LINKED_DIRS = {
    "Notes": os.path.join(CRM_DATA_PATH, "Notes"),
    "Activities": os.path.join(CRM_DATA_PATH, "Activities"),
    "Tasks": os.path.join(CRM_DATA_PATH, "Tasks"),
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


def collect_related(entity, notes, activities, tasks):
    entity_link = entity["link"]
    related_notes = []
    related_activities = []
    related_tasks = []

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
            frontmatter.get("lead"),
            frontmatter.get("primary-parent"),
        ]
        if any(link_matches(candidate, entity_link) for candidate in candidates):
            related_tasks.append(task)

    return related_notes, related_activities, related_tasks


def build_observed_summary(entity, notes, activities, tasks, interactions_cache):
    bullets = []
    bullets.append(f"Linked notes: {len(notes)}")
    bullets.append(f"Linked activities: {len(activities)}")
    bullets.append(f"Open tasks: {sum(1 for task in tasks if task['frontmatter'].get('status') in {'todo', 'in-progress'})}")

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
    if source_refs:
        bullets.append("Source refs: " + ", ".join(source_refs[:3]))
    return bullets


def build_inferred_summary(notes, activities, tasks):
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
    return bullets


def related_links(records, limit=5):
    return ", ".join(record["link"] for record in records[:limit]) if records else "None"


def entity_display_name(entity_type, frontmatter, basename):
    if entity_type == "Accounts":
        return frontmatter.get("company-name", basename)
    if entity_type == "Contacts":
        return frontmatter.get("full-name", basename)
    if entity_type == "Opportunities":
        return frontmatter.get("opportunity-name", basename)
    if entity_type == "Leads":
        return frontmatter.get("lead-name", basename)
    return basename


def build_memory_section(entity_type, records, notes, activities, tasks, interactions_cache):
    if not records:
        return f"## {entity_type}\n\nNo records found.\n"

    lines = [f"## {entity_type}", ""]
    for entity in records:
        observed = build_observed_summary(entity, *collect_related(entity, notes, activities, tasks), interactions_cache)
        related_notes, related_activities, related_tasks = collect_related(entity, notes, activities, tasks)
        inferred = build_inferred_summary(related_notes, related_activities, related_tasks)
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
        lines.append("")
    return "\n".join(lines)


def main():
    interactions_cache = load_json(INTERACTIONS_PATH, {})
    notes = collect_records(LINKED_DIRS["Notes"])
    activities = collect_records(LINKED_DIRS["Activities"])
    tasks = collect_records(LINKED_DIRS["Tasks"])

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
        sections.append(build_memory_section(entity_type, records, notes, activities, tasks, interactions_cache))
        sections.append("")

    with open(RELATIONSHIP_MEMORY_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sections).rstrip() + "\n")

    print(f"Relationship memory written to {RELATIONSHIP_MEMORY_PATH}")


if __name__ == "__main__":
    main()
