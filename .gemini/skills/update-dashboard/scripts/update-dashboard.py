import argparse
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta


def get_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return os.path.abspath(env_override)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logic_root = os.path.abspath(os.path.join(script_dir, "../../../../"))
    env_path = os.path.join(logic_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    path = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.abspath(os.path.join(logic_root, path)) if not os.path.isabs(path) else path
    return os.getenv("CRM_DATA_PATH", os.getcwd())


PROJECT_ROOT = get_crm_data_path()
DASHBOARD_PATH = os.path.join(PROJECT_ROOT, "DASHBOARD.md")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGIC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
sys.path.insert(0, os.path.join(LOGIC_ROOT, "scripts"))

from frontmatter_utils import load_frontmatter_file


DIRECTORIES = {
    "Accounts": os.path.join(PROJECT_ROOT, "Accounts"),
    "Contacts": os.path.join(PROJECT_ROOT, "Contacts"),
    "Opportunities": os.path.join(PROJECT_ROOT, "Opportunities"),
    "Leads": os.path.join(PROJECT_ROOT, "Leads"),
    "Tasks": os.path.join(PROJECT_ROOT, "Tasks"),
    "Activities": os.path.join(PROJECT_ROOT, "Activities"),
    "Notes": os.path.join(PROJECT_ROOT, "Notes"),
}

PRIORITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}
COMMIT_SCOPE_PREFIXES = [
    "Accounts/",
    "Contacts/",
    "Deal-Flow/",
]
COMMIT_SCOPE_FILES = {
    "DASHBOARD.md",
    "INTELLIGENCE.md",
    "RELATIONSHIP_MEMORY.md",
    "staging/matches.json",
    "staging/warm_paths.json",
}


def normalize_link(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text.strip()


def normalize_key(value):
    return normalize_link(value).lower()


def canonical_key(value):
    return re.sub(r"[^a-z0-9]+", "", normalize_link(value).lower())


def link_variants(value):
    normalized = normalize_link(value)
    if not normalized:
        return set()
    variants = {normalized.lower()}
    if "/" in normalized:
        variants.add(normalized.split("/")[-1].lower())
    canonical = canonical_key(normalized)
    if canonical:
        variants.add(canonical)
    return variants


def wikilink_for_record(record):
    rel_path = os.path.relpath(record["file_path"], PROJECT_ROOT)
    return f"[[{os.path.splitext(rel_path)[0]}]]"


def as_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def as_int(value, default=0):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return int(float(match.group(0)))
    return default


def as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, "", []):
        return []
    return [value]


def entity_name(entity_type, frontmatter, basename):
    if entity_type == "Accounts":
        return frontmatter.get("company-name", basename)
    if entity_type == "Contacts":
        return frontmatter.get("full-name") or frontmatter.get("full--name") or basename
    if entity_type == "Opportunities":
        return frontmatter.get("opportunity-name", basename)
    if entity_type == "Leads":
        return frontmatter.get("lead-name", basename)
    if entity_type == "Tasks":
        return frontmatter.get("task-name", basename)
    if entity_type == "Activities":
        return frontmatter.get("activity-name", basename)
    if entity_type == "Notes":
        return frontmatter.get("title", basename)
    return basename


def priority_label(*values):
    best = "low"
    for value in values:
        normalized = str(value or "").lower()
        if PRIORITY_WEIGHTS.get(normalized, 0) > PRIORITY_WEIGHTS.get(best, 0):
            best = normalized
    return best


def collect_records(entity_type):
    directory = DIRECTORIES[entity_type]
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
            basename = os.path.splitext(file_name)[0]
            record = {
                "entity_type": entity_type,
                "file_path": file_path,
                "basename": basename,
                "frontmatter": frontmatter,
                "body": body,
            }
            record["link"] = wikilink_for_record(record)
            record["display_name"] = entity_name(entity_type, frontmatter, basename)
            records.append(record)
    return records


def build_index(records):
    index = {}
    for record in records:
        for key in link_variants(record["link"]) | link_variants(record["basename"]) | link_variants(record["display_name"]):
            index[key] = record
    return index


def latest_record_date(records, keys, include_future=True):
    dates = []
    today = date.today()
    for record in records:
        for key in keys:
            parsed = as_date(record["frontmatter"].get(key))
            if parsed and (include_future or parsed <= today):
                dates.append(parsed)
    return max(dates) if dates else None


def related_task_links(task):
    fm = task["frontmatter"]
    links = set()
    for key in ["primary-parent", "account", "contact", "opportunity", "lead"]:
        links.update(link_variants(fm.get(key)))
    return links


def related_activity_links(activity):
    fm = activity["frontmatter"]
    links = set(link_variants(fm.get("primary-parent")))
    for link in as_list(fm.get("secondary-links")):
        links.update(link_variants(link))
    for link in as_list(fm.get("contacts")):
        links.update(link_variants(link))
    for key in ["account", "contact", "opportunity", "lead", "deal"]:
        links.update(link_variants(fm.get(key)))
    return links


def related_note_links(note):
    fm = note["frontmatter"]
    links = set(link_variants(fm.get("primary-parent")))
    for link in as_list(fm.get("secondary-links")):
        links.update(link_variants(link))
    return links


def relationship_candidates(accounts, contacts, opportunities, tasks, activities, notes):
    account_index = build_index(accounts)
    contact_index = build_index(contacts)
    active_opportunities = [record for record in opportunities if record["frontmatter"].get("is-active", False)]

    candidates = []
    for opportunity in active_opportunities:
        fm = opportunity["frontmatter"]
        opportunity_key = link_variants(opportunity["link"])
        account = account_index.get(normalize_key(fm.get("account")))
        contact = contact_index.get(normalize_key(fm.get("primary-contact")))
        linked_keys = set(opportunity_key)

        if account:
            linked_keys.update(link_variants(account["link"]))
        if contact:
            linked_keys.update(link_variants(contact["link"]))

        linked_tasks = [task for task in tasks if related_task_links(task) & linked_keys]
        linked_activities = [activity for activity in activities if related_activity_links(activity) & linked_keys]
        linked_notes = [note for note in notes if related_note_links(note) & linked_keys]

        open_tasks = [task for task in linked_tasks if task["frontmatter"].get("status") in {"todo", "in-progress"}]
        today = date.today()
        overdue_tasks = [
            task for task in open_tasks if (as_date(task["frontmatter"].get("due-date")) and as_date(task["frontmatter"].get("due-date")) < today)
        ]
        due_soon_tasks = [
            task
            for task in open_tasks
            if (as_date(task["frontmatter"].get("due-date")) and today <= as_date(task["frontmatter"].get("due-date")) <= today + timedelta(days=7))
        ]
        latest_activity = latest_record_date(linked_activities, ["date", "activity-date", "date-modified"], include_future=False)
        latest_note = latest_record_date(linked_notes, ["date-modified", "date-created"])
        recent_window = today - timedelta(days=7)
        recent_activity_count = sum(
            1
            for activity in linked_activities
            if (as_date(activity["frontmatter"].get("date")) or as_date(activity["frontmatter"].get("activity-date")))
            and recent_window <= (as_date(activity["frontmatter"].get("date")) or as_date(activity["frontmatter"].get("activity-date"))) <= today
        )

        account_fm = account["frontmatter"] if account else {}
        contact_fm = contact["frontmatter"] if contact else {}
        warmth = max(
            as_int(contact_fm.get("warmth-score")),
            as_int(account_fm.get("account-warmth-index")),
            as_int(account_fm.get("warmth-score")),
        )
        velocity = max(as_int(contact_fm.get("velocity-score")), as_int(account_fm.get("velocity-score")), recent_activity_count)
        priority = priority_label(fm.get("priority"), account_fm.get("priority"), contact_fm.get("priority"))
        probability = as_int(fm.get("probability"))
        commercial_value = max(as_int(fm.get("deal-value")), as_int(account_fm.get("size")))
        days_since = (today - latest_activity).days if latest_activity else 999
        attention_score = (
            (100 - min(warmth, 100))
            + PRIORITY_WEIGHTS.get(priority, 1) * 12
            + len(overdue_tasks) * 15
            + len(due_soon_tasks) * 8
            + min(probability, 100) // 5
            + min(commercial_value, 50)
            - min(velocity, 5) * 6
        )
        heat_score = (
            min(velocity, 5) * 18
            + max(0, 14 - min(days_since, 14)) * 4
            + min(probability, 100) // 4
            + min(recent_activity_count, 4) * 6
        )

        candidates.append(
            {
                "opportunity": opportunity,
                "account": account,
                "contact": contact,
                "priority": priority,
                "warmth": warmth,
                "velocity": velocity,
                "probability": probability,
                "commercial_value": commercial_value,
                "latest_activity": latest_activity,
                "latest_note": latest_note,
                "recent_activity_count": recent_activity_count,
                "open_tasks": open_tasks,
                "overdue_tasks": overdue_tasks,
                "due_soon_tasks": due_soon_tasks,
                "attention_score": attention_score,
                "heat_score": heat_score,
                "days_since": days_since,
            }
        )
    return candidates


def lead_candidates(leads, activities, notes, tasks):
    today = date.today()
    qualified = []
    for lead in leads:
        if str(lead["frontmatter"].get("status", "")).lower() != "qualified":
            continue
        lead_key = link_variants(lead["link"])
        linked_activities = [activity for activity in activities if lead_key & related_activity_links(activity)]
        linked_notes = [note for note in notes if lead_key & related_note_links(note)]
        linked_tasks = [task for task in tasks if lead_key & related_task_links(task)]
        latest_signal = max(
            [
                value
                for value in [
                    latest_record_date(linked_activities, ["date", "activity-date", "date-modified"], include_future=False),
                    latest_record_date(linked_notes, ["date-created", "date-modified"]),
                    as_date(lead["frontmatter"].get("date-modified")),
                ]
                if value
            ],
            default=None,
        )
        priority = priority_label(lead["frontmatter"].get("priority"))
        completeness = 0
        if lead["frontmatter"].get("person-name"):
            completeness += 1
        if lead["frontmatter"].get("company-name"):
            completeness += 1
        score = PRIORITY_WEIGHTS.get(priority, 1) * 20 + completeness * 15 + len(linked_tasks) * 8
        if latest_signal:
            score += max(0, 14 - (today - latest_signal).days) * 2
        qualified.append(
            {
                "lead": lead,
                "priority": priority,
                "latest_signal": latest_signal,
                "open_tasks": [task for task in linked_tasks if task["frontmatter"].get("status") in {"todo", "in-progress"}],
                "activity_count": len(linked_activities),
                "note_count": len(linked_notes),
                "score": score,
            }
        )
    return qualified


def format_priority(priority):
    return str(priority or "low").capitalize()


def render_table(headers, rows, empty_text):
    if not rows:
        return empty_text
    header = "| " + " | ".join(headers) + " |\n"
    separator = "| " + " | ".join([":---"] * len(headers)) + " |\n"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return header + separator + body


def format_date(value):
    parsed = as_date(value)
    return parsed.isoformat() if parsed else "N/A"


def relationship_label(candidate):
    parts = []
    if candidate["contact"]:
        parts.append(candidate["contact"]["link"])
    if candidate["account"]:
        parts.append(candidate["account"]["link"])
    if not parts:
        parts.append(candidate["opportunity"]["link"])
    return " / ".join(parts)


def build_attention_section(candidates):
    ranked = sorted(candidates, key=lambda item: (item["attention_score"], item["probability"]), reverse=True)[:8]
    rows = []
    for candidate in ranked:
        reason_parts = []
        if candidate["overdue_tasks"]:
            reason_parts.append(f"{len(candidate['overdue_tasks'])} overdue task(s)")
        elif candidate["due_soon_tasks"]:
            reason_parts.append(f"{len(candidate['due_soon_tasks'])} due soon")
        if candidate["days_since"] < 999:
            reason_parts.append(f"{candidate['days_since']}d since last activity")
        else:
            reason_parts.append("no recent linked activity")
        rows.append(
            [
                relationship_label(candidate),
                candidate["opportunity"]["link"],
                str(candidate["warmth"]),
                str(candidate["velocity"]),
                format_priority(candidate["priority"]),
                ", ".join(reason_parts),
            ]
        )
    return render_table(
        ["Relationship", "Opportunity", "Warmth", "Velocity", "Priority", "Why Now"],
        rows,
        "No active relationships currently need attention.",
    )


def build_heating_section(candidates):
    ranked = sorted(candidates, key=lambda item: (item["heat_score"], item["recent_activity_count"]), reverse=True)[:8]
    rows = []
    for candidate in ranked:
        if candidate["recent_activity_count"] == 0 and candidate["velocity"] == 0:
            continue
        rows.append(
            [
                relationship_label(candidate),
                candidate["opportunity"]["link"],
                format_date(candidate["latest_activity"]),
                str(candidate["recent_activity_count"]),
                str(candidate["velocity"]),
                f"{candidate['probability']}%",
            ]
        )
    return render_table(
        ["Relationship", "Opportunity", "Latest Activity", "7d Activity", "Velocity", "Probability"],
        rows,
        "No relationships are currently heating up.",
    )


def build_qualified_leads_section(candidates):
    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)[:8]
    rows = []
    for item in ranked:
        lead = item["lead"]
        fm = lead["frontmatter"]
        rows.append(
            [
                lead["link"],
                fm.get("person-name") or "N/A",
                fm.get("company-name") or "N/A",
                format_priority(item["priority"]),
                format_date(item["latest_signal"]),
                str(len(item["open_tasks"])),
            ]
        )
    return render_table(
        ["Lead", "Person", "Company", "Priority", "Latest Signal", "Open Tasks"],
        rows,
        "No qualified leads are currently awaiting conversion.",
    )


def build_next_actions_section(tasks, opportunities, accounts, contacts):
    opportunity_index = build_index(opportunities)
    account_index = build_index(accounts)
    contact_index = build_index(contacts)
    open_tasks = [task for task in tasks if task["frontmatter"].get("status") in {"todo", "in-progress"}]

    def task_sort_key(task):
        fm = task["frontmatter"]
        due_date = as_date(fm.get("due-date")) or date.max
        opp = opportunity_index.get(normalize_key(fm.get("opportunity")))
        probability = as_int(opp["frontmatter"].get("probability")) if opp else 0
        priority = PRIORITY_WEIGHTS.get(str(fm.get("priority", "medium")).lower(), 2)
        return (due_date, -priority, -probability)

    ranked = sorted(open_tasks, key=task_sort_key)[:12]
    rows = []
    today = date.today()
    for task in ranked:
        fm = task["frontmatter"]
        due_date = as_date(fm.get("due-date"))
        related = opportunity_index.get(normalize_key(fm.get("opportunity")))
        if related:
            related_link = related["link"]
        else:
            related = contact_index.get(normalize_key(fm.get("contact"))) or account_index.get(normalize_key(fm.get("account")))
            related_link = related["link"] if related else "N/A"

        if due_date and due_date < today:
            why_now = "Overdue"
        elif due_date and due_date <= today + timedelta(days=3):
            why_now = "Due within 3d"
        else:
            why_now = "Upcoming"

        rows.append(
            [
                task["link"],
                format_date(due_date),
                format_priority(fm.get("priority")),
                related_link,
                why_now,
            ]
        )
    return render_table(["Task", "Due", "Priority", "Related", "Why Now"], rows, "No open tasks found.")


def build_pipeline_section(opportunities):
    active = [record for record in opportunities if record["frontmatter"].get("is-active", False)]
    ranked = sorted(
        active,
        key=lambda record: (-as_int(record["frontmatter"].get("probability")), as_date(record["frontmatter"].get("close-date")) or date.max),
    )[:10]
    rows = []
    for record in ranked:
        fm = record["frontmatter"]
        rows.append(
            [
                record["link"],
                str(fm.get("account", "N/A")).replace("[[", "").replace("]]", ""),
                str(fm.get("stage", "N/A")),
                f"{as_int(fm.get('probability'))}%",
                format_date(fm.get("close-date")),
            ]
        )
    return render_table(["Opportunity", "Account", "Stage", "Probability", "Close Date"], rows, "No active opportunities found.")


def build_recent_memory_section(activities, notes):
    recent_records = []
    for activity in activities:
        record_date = as_date(activity["frontmatter"].get("date")) or as_date(activity["frontmatter"].get("activity-date"))
        if record_date:
            recent_records.append((record_date, "Activity", activity["link"]))
    for note in notes:
        record_date = as_date(note["frontmatter"].get("date-modified")) or as_date(note["frontmatter"].get("date-created"))
        if record_date:
            recent_records.append((record_date, "Note", note["link"]))
    rows = [
        [record_type, link, record_date.isoformat()]
        for record_date, record_type, link in sorted(recent_records, key=lambda item: item[0], reverse=True)[:10]
    ]
    return render_table(["Type", "Record", "Date"], rows, "No recent memory records found.")


def build_summary_bullets(attention, heating, qualified, tasks):
    bullets = []
    if attention:
        top = max(attention, key=lambda item: item["attention_score"])
        bullets.append(
            f"Highest attention need: {relationship_label(top)} around {top['opportunity']['link']} "
            f"(warmth {top['warmth']}, velocity {top['velocity']}, {len(top['open_tasks'])} open task(s))."
        )
    active_heating = [item for item in heating if item["recent_activity_count"] > 0 or item["velocity"] > 0]
    if active_heating:
        top = max(active_heating, key=lambda item: item["heat_score"])
        bullets.append(
            f"Most active relationship: {relationship_label(top)} with {top['recent_activity_count']} recent activity item(s) "
            f"and {top['probability']}% opportunity probability."
        )
    if qualified:
        top = max(qualified, key=lambda item: item["score"])
        bullets.append(
            f"Top near-conversion lead: {top['lead']['link']} "
            f"(latest signal {format_date(top['latest_signal'])}, {len(top['open_tasks'])} open task(s))."
        )
    open_tasks = [task for task in tasks if task["frontmatter"].get("status") in {"todo", "in-progress"}]
    overdue = [task for task in open_tasks if (as_date(task["frontmatter"].get("due-date")) and as_date(task["frontmatter"].get("due-date")) < date.today())]
    if overdue:
        bullets.append(f"Execution pressure: {len(overdue)} overdue task(s) need cleanup.")
    return bullets or ["No high-signal relationship updates were generated from the current vault state."]


def generate_dashboard_content(sections):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Relationship Dashboard",
        "",
        f"**Last Updated:** {now}",
        "",
        "## Summary",
        "",
    ]
    for bullet in sections["summary"]:
        lines.append(f"- {bullet}")
    lines.extend(
        [
            "",
            "## Relationships Needing Attention",
            "",
            sections["attention"],
            "",
            "## Recently Active / Heating Up",
            "",
            sections["heating"],
            "",
            "## Qualified Leads / Near Conversion",
            "",
            sections["qualified_leads"],
            "",
            "## Recommended Next Actions",
            "",
            sections["next_actions"],
            "",
            "## Active Opportunities Snapshot",
            "",
            sections["pipeline"],
            "",
            "## Recent Memory",
            "",
            sections["recent_memory"],
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_followup_scripts():
    match_script = os.path.join(LOGIC_ROOT, "scripts", "matchmaker.py")
    intel_script = os.path.join(LOGIC_ROOT, "scripts", "intelligence-engine.py")
    if os.path.exists(match_script):
        print("Running Brokerage Matchmaker...")
        subprocess.run(["python3", match_script], check=True, env={**os.environ, "CRM_DATA_PATH": PROJECT_ROOT})
    if os.path.exists(intel_script):
        print("Running Intelligence Engine integration...")
        subprocess.run(["python3", intel_script], check=True, env={**os.environ, "CRM_DATA_PATH": PROJECT_ROOT})


def maybe_commit_changes():
    try:
        print("Committing dashboard updates to CRM data...")
        status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True)
        candidate_paths = []
        skipped_paths = []
        for line in status.stdout.splitlines():
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if path in COMMIT_SCOPE_FILES or any(path.startswith(prefix) for prefix in COMMIT_SCOPE_PREFIXES):
                candidate_paths.append(path)
            else:
                skipped_paths.append(path)

        if skipped_paths:
            print("Skipping unrelated CRM changes:")
            for path in skipped_paths:
                print(f" - {path}")

        if not candidate_paths:
            print("No scoped dashboard/intelligence changes to commit in CRM data.")
            return

        subprocess.run(["git", "add", "--"] + candidate_paths, cwd=PROJECT_ROOT, check=True)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        if staged.stdout.strip():
            subprocess.run(
                ["git", "commit", "-m", "agent: update dashboard and intelligence metrics", "--"] + candidate_paths,
                cwd=PROJECT_ROOT,
                check=True,
            )
            print("Changes committed to CRM data.")
        else:
            print("No scoped changes to commit in CRM data.")
    except Exception as exc:
        print(f"Error committing changes to CRM data: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Generate the relationship-first CRM dashboard.")
    parser.add_argument("--skip-followups", action="store_true", help="Skip matchmaker and intelligence regeneration.")
    parser.add_argument("--skip-commit", action="store_true", help="Skip nested CRM data git commit.")
    args = parser.parse_args()

    accounts = collect_records("Accounts")
    contacts = collect_records("Contacts")
    opportunities = collect_records("Opportunities")
    leads = collect_records("Leads")
    tasks = collect_records("Tasks")
    activities = collect_records("Activities")
    notes = collect_records("Notes")

    relationships = relationship_candidates(accounts, contacts, opportunities, tasks, activities, notes)
    qualified_leads = lead_candidates(leads, activities, notes, tasks)

    sections = {
        "summary": build_summary_bullets(relationships, relationships, qualified_leads, tasks),
        "attention": build_attention_section(relationships),
        "heating": build_heating_section(relationships),
        "qualified_leads": build_qualified_leads_section(qualified_leads),
        "next_actions": build_next_actions_section(tasks, opportunities, accounts, contacts),
        "pipeline": build_pipeline_section(opportunities),
        "recent_memory": build_recent_memory_section(activities, notes),
    }

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as handle:
        handle.write(generate_dashboard_content(sections))
    print(f"DASHBOARD.md updated successfully at {DASHBOARD_PATH}")

    if not args.skip_followups:
        try:
            run_followup_scripts()
        except Exception as exc:
            print(f"Error running follow-up generators: {exc}")

    if not args.skip_commit:
        maybe_commit_changes()


if __name__ == "__main__":
    main()
