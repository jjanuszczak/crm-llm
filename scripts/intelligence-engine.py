import json
import os
import re
import subprocess
from datetime import date, datetime, timedelta

from frontmatter_utils import iter_markdown_files, load_frontmatter_file, write_frontmatter_file


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
                    if not os.path.isabs(path):
                        path = os.path.abspath(os.path.join(logic_root, path))
                    return path
    return os.getenv("CRM_DATA_PATH", os.getcwd())


CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
TASKS_DIR = os.path.join(CRM_DATA_PATH, "Tasks")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
STAGING_DIR = os.path.join(CRM_DATA_PATH, "staging")
IGNORE_LIST_PATH = os.path.join(STAGING_DIR, "ignore_list.json")
DISCOVERY_PATH = os.path.join(STAGING_DIR, "discovery.json")
WARM_PATHS_PATH = os.path.join(STAGING_DIR, "warm_paths.json")
MATCHES_PATH = os.path.join(STAGING_DIR, "matches.json")
INTERACTIONS_PATH = os.path.join(STAGING_DIR, "interactions.json")
INTELLIGENCE_DASHBOARD = os.path.join(CRM_DATA_PATH, "INTELLIGENCE.md")
RELATIONSHIP_MEMORY_SCRIPT = os.path.join(os.path.dirname(__file__), "relationship_memory.py")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deals")
LEGACY_DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")

PRIORITY_THRESHOLDS = {"high": 14, "medium": 30, "low": 90, "default": 30}
ACTIONABLE_TASK_STATUSES = {"todo", "in-progress"}
WAITING_TASK_STATUSES = {"waiting"}


def normalize_link(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text.strip()


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


def wikilink_for_path(file_path):
    rel_path = os.path.relpath(file_path, CRM_DATA_PATH)
    return f"[[{os.path.splitext(rel_path)[0]}]]"


def entity_basename(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]


def display_name(file_path, frontmatter):
    return (
        frontmatter.get("organization-name")
        or frontmatter.get("company-name")
        or frontmatter.get("full-name")
        or frontmatter.get("full--name")
        or frontmatter.get("opportunity-name")
        or frontmatter.get("lead-name")
        or frontmatter.get("activity-name")
        or frontmatter.get("task-name")
        or frontmatter.get("title")
        or entity_basename(file_path)
    )


def load_json(file_path, default=None):
    if default is None:
        default = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return default
    return default


def update_frontmatter(file_path, new_data):
    try:
        frontmatter, body = load_frontmatter_file(file_path)
    except Exception:
        return
    frontmatter.update(new_data)
    write_frontmatter_file(file_path, frontmatter, body)


def parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def bounded_date(value):
    parsed = parse_date(value)
    if not parsed:
        return None
    return min(parsed, date.today())


def activity_date(frontmatter):
    return bounded_date(frontmatter.get("activity-date") or frontmatter.get("date"))


def task_due_date(frontmatter):
    return bounded_date(frontmatter.get("due-date"))


def collect_records(directory):
    records = []
    if not os.path.exists(directory):
        return records
    for file_path in iter_markdown_files(directory):
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
                "link": wikilink_for_path(file_path),
                "basename": entity_basename(file_path),
                "display_name": display_name(file_path, frontmatter),
            }
        )
    return records


def telemetry_snapshot(email, interactions_cache):
    if not email:
        return None
    payload = interactions_cache.get(str(email).lower())
    if not isinstance(payload, dict):
        return None
    last_date = bounded_date(payload.get("last_date"))
    return {
        "last_date": last_date,
        "hits_last_7_days": max(0, int(payload.get("hits_last_7_days", 0) or 0)),
    }


def record_keys(record):
    keys = set()
    keys.update(link_variants(record["link"]))
    keys.update(link_variants(record["basename"]))
    keys.update(link_variants(record["display_name"]))
    return keys


def links_in_frontmatter(frontmatter):
    keys = set()
    for key in [
        "primary-parent",
        "organization",
        "account",
        "contact",
        "opportunity",
        "lead",
        "deal",
        "primary-contact",
    ]:
        keys.update(link_variants(frontmatter.get(key)))
    for key in ["secondary-links", "contacts"]:
        value = frontmatter.get(key) or []
        if not isinstance(value, list):
            value = [value]
        for item in value:
            keys.update(link_variants(item))
    return keys


def related_activities(entity_keys, activities):
    linked = []
    for activity in activities:
        if links_in_frontmatter(activity["frontmatter"]) & entity_keys:
            linked.append(activity)
            continue
        # Fallback for older records where only wikilinks exist in stringified frontmatter.
        text = str(activity["frontmatter"])
        if any(key in canonical_key(text) for key in entity_keys if key):
            linked.append(activity)
    return linked


def related_tasks(entity_keys, tasks):
    return [task for task in tasks if links_in_frontmatter(task["frontmatter"]) & entity_keys]


def latest_interaction_date(record, activities, telemetry):
    latest = telemetry["last_date"] if telemetry else None
    entity_keys = record_keys(record)
    for activity in related_activities(entity_keys, activities):
        current = activity_date(activity["frontmatter"])
        if current and (latest is None or current > latest):
            latest = current
    return latest


def recent_activity_count(record, activities, days):
    entity_keys = record_keys(record)
    cutoff = date.today() - timedelta(days=days)
    count = 0
    for activity in related_activities(entity_keys, activities):
        current = activity_date(activity["frontmatter"])
        if current and current >= cutoff:
            count += 1
    return count


def task_signal(record, tasks):
    entity_keys = record_keys(record)
    related = related_tasks(entity_keys, tasks)
    overdue = 0
    waiting = 0
    actionable_due_soon = 0
    today = date.today()
    for task in related:
        status = str(task["frontmatter"].get("status", "")).lower()
        due = task_due_date(task["frontmatter"])
        if status in ACTIONABLE_TASK_STATUSES and due:
            if due < today:
                overdue += 1
            elif due <= today + timedelta(days=7):
                actionable_due_soon += 1
        if status in WAITING_TASK_STATUSES:
            waiting += 1
    return {
        "overdue": overdue,
        "waiting": waiting,
        "actionable_due_soon": actionable_due_soon,
    }


def recency_score(last_contacted_date, priority):
    if not last_contacted_date:
        return 0, 999
    days_since = max(0, (date.today() - last_contacted_date).days)
    limit = PRIORITY_THRESHOLDS.get(str(priority or "medium").lower(), PRIORITY_THRESHOLDS["default"])
    base = max(0, int(100 * (1 - (days_since / limit))))
    if days_since <= 3:
        return max(base, 100), days_since
    if days_since <= 7:
        return max(base, 80), days_since
    if days_since <= 14:
        return max(base, 60), days_since
    if days_since <= 30:
        return max(base, 35), days_since
    if days_since <= 60:
        return max(base, 15), days_since
    return base, days_since


def activity_score(count_30d):
    return min(count_30d * 3, 18)


def momentum_score(telemetry_hits):
    return min(max(0, telemetry_hits) * 2, 12)


def execution_score(task_stats, days_since):
    score = 0
    if task_stats["actionable_due_soon"]:
        score += 10
    if task_stats["overdue"] and days_since > 14:
        score -= min(20, task_stats["overdue"] * 7)
    if task_stats["waiting"] and days_since > 21:
        score -= 10
    return max(-20, min(score, 10))


def classify_warmth(score):
    if score >= 80:
        return "hot"
    if score >= 60:
        return "warm"
    if score >= 35:
        return "monitor"
    return "cold"


def score_record(record, activities, tasks, interactions_cache):
    frontmatter = record["frontmatter"]
    telemetry = telemetry_snapshot(frontmatter.get("email"), interactions_cache)
    latest = latest_interaction_date(record, activities, telemetry)
    count_30d = recent_activity_count(record, activities, 30)
    hits_7d = telemetry["hits_last_7_days"] if telemetry else 0
    task_stats = task_signal(record, tasks)
    priority = frontmatter.get("strategic-importance") or frontmatter.get("priority", "medium")

    recency, days_since = recency_score(latest, priority)
    activity = activity_score(count_30d)
    momentum = momentum_score(hits_7d)
    execution = execution_score(task_stats, days_since)
    score = int(round((0.55 * recency) + activity + momentum + execution))
    score = max(0, min(score, 100))

    return {
        "score": score,
        "status": classify_warmth(score),
        "days_since": days_since,
        "last_contacted": latest,
        "recent_activity_30d": count_30d,
        "hits_last_7_days": hits_7d,
        "task_stats": task_stats,
        "priority": str(priority or "medium").lower(),
    }


def entity_type_for_directory(directory):
    if directory == ORGANIZATIONS_DIR:
        return "Organization"
    if directory == ACCOUNTS_DIR:
        return "Account"
    if directory == CONTACTS_DIR:
        return "Contact"
    return "Deal"


def deal_directories():
    directories = []
    for directory in [DEALS_DIR, LEGACY_DEALS_DIR]:
        if os.path.exists(directory):
            directories.append(directory)
    return directories


def render_table(headers, rows, empty_text):
    if not rows:
        return empty_text
    header = "| " + " | ".join(headers) + " |\n"
    separator = "| " + " | ".join([":---"] * len(headers)) + " |\n"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return header + separator + body


def render_intelligence(sections):
    lines = [
        "# Intelligence Dashboard",
        "",
        f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Warmest Relationships",
        "",
        sections["warmest"],
        "",
        "## Cooling Relationships That Matter",
        "",
        sections["cooling"],
        "",
        "## New Discoveries",
        "",
        sections["discoveries"],
        "",
        "## Warm Paths",
        "",
        sections["warm_paths"],
        "",
        "## Suggested Brokerage Matches",
        "",
        sections["matches"],
        "",
    ]
    return "\n".join(lines)


def main():
    print("Running Intelligence Engine...")
    activities = collect_records(ACTIVITIES_DIR)
    tasks = collect_records(TASKS_DIR)
    interactions_cache = load_json(INTERACTIONS_PATH, default={})

    scored_records = []
    linked_scores = {}

    for directory in [CONTACTS_DIR, ORGANIZATIONS_DIR, ACCOUNTS_DIR] + deal_directories():
        for record in collect_records(directory):
            score_data = score_record(record, activities, tasks, interactions_cache)
            entry = {
                "record": record,
                "entity_type": entity_type_for_directory(directory),
                **score_data,
            }
            scored_records.append(entry)

            parent = normalize_link(
                record["frontmatter"].get("account")
                or record["frontmatter"].get("organization")
                or record["frontmatter"].get("deal")
            )
            if parent:
                linked_scores.setdefault(parent, []).append(score_data["score"])

    for entry in scored_records:
        record = entry["record"]
        frontmatter = record["frontmatter"]
        parent_name = normalize_link(
            frontmatter.get("account") or frontmatter.get("organization") or frontmatter.get("deal")
        )
        linked = linked_scores.get(record["basename"], [])
        if not linked and parent_name == record["basename"]:
            linked = linked_scores.get(parent_name, [])
        account_index = max(linked) if linked else entry["score"]

        payload = {
            "warmth-score": entry["score"],
            "warmth-status": entry["status"],
            "velocity-score": entry["hits_last_7_days"],
            "account-warmth-index": account_index,
            "date-modified": date.today().strftime("%Y-%m-%d"),
        }
        if entry["last_contacted"]:
            payload["last-contacted"] = entry["last_contacted"].strftime("%Y-%m-%d")
        update_frontmatter(record["file_path"], payload)

    warmest_rows = []
    warmest_candidates = [
        entry
        for entry in scored_records
        if entry["score"] >= 55 or entry["recent_activity_30d"] > 0 or entry["hits_last_7_days"] > 0
    ]
    for entry in sorted(
        warmest_candidates,
        key=lambda item: (item["score"], item["recent_activity_30d"], item["hits_last_7_days"]),
        reverse=True,
    )[:12]:
        warmest_rows.append(
            [
                record["link"] if (record := entry["record"]) else "",
                entry["entity_type"],
                str(entry["score"]),
                entry["status"].upper(),
                str(entry["recent_activity_30d"]),
                str(entry["hits_last_7_days"]),
                str(entry["days_since"]),
            ]
        )

    cooling_rows = []
    cooling_candidates = [
        entry
        for entry in scored_records
        if entry["priority"] in {"high", "medium"}
        and (entry["score"] < 45 or entry["task_stats"]["overdue"] > 0)
    ]
    for entry in sorted(
        cooling_candidates,
        key=lambda item: (item["task_stats"]["overdue"], item["days_since"], -item["score"]),
        reverse=True,
    )[:12]:
        reasons = []
        if entry["task_stats"]["overdue"]:
            reasons.append(f"{entry['task_stats']['overdue']} overdue task(s)")
        if entry["days_since"] < 999:
            reasons.append(f"{entry['days_since']}d since last interaction")
        if entry["task_stats"]["waiting"]:
            reasons.append(f"{entry['task_stats']['waiting']} waiting")
        cooling_rows.append(
            [
                entry["record"]["link"],
                entry["entity_type"],
                str(entry["score"]),
                entry["status"].upper(),
                ", ".join(reasons) or "stale relationship",
            ]
        )

    ignore = set(load_json(IGNORE_LIST_PATH, default=[]))
    raw_discoveries = load_json(DISCOVERY_PATH, default=[])
    active_discoveries = []
    for discovery in raw_discoveries:
        if not isinstance(discovery, dict):
            continue
        email = discovery.get("email")
        if email and email in ignore:
            continue
        if not discovery.get("name") and not discovery.get("rationale"):
            continue
        active_discoveries.append(discovery)

    discovery_rows = [
        [
            str(item.get("name") or "Unknown"),
            str(item.get("type") or "Unknown"),
            str(item.get("rationale") or ""),
        ]
        for item in active_discoveries[:10]
    ]

    warm_path_rows = []
    for item in load_json(WARM_PATHS_PATH, default=[]):
        if not isinstance(item, dict):
            continue
        warm_path_rows.append(
            [
                str(item.get("deal") or ""),
                str(item.get("person") or ""),
                f"[[{item.get('connection')}]]" if item.get("connection") else "",
                str(item.get("rationale") or ""),
            ]
        )

    match_rows = []
    for item in load_json(MATCHES_PATH, default=[])[:10]:
        if not isinstance(item, dict):
            continue
        match_rows.append(
            [
                f"[[{item.get('deal')}]]" if item.get("deal") else "",
                f"[[{item.get('investor')}]]" if item.get("investor") else "",
                f"{item.get('score', 0)}%",
                str(item.get("rationale") or item.get("rationate") or ""),
            ]
        )

    sections = {
        "warmest": render_table(
            ["Entity", "Type", "Warmth", "Status", "30d Activity", "7d Velocity", "Days Since"],
            warmest_rows,
            "No warm relationships identified yet.",
        ),
        "cooling": render_table(
            ["Entity", "Type", "Warmth", "Status", "Why It Matters"],
            cooling_rows,
            "No high-priority relationships are currently cooling.",
        ),
        "discoveries": render_table(
            ["Name", "Type", "Rationale"],
            discovery_rows,
            "No new discoveries pending.",
        ),
        "warm_paths": render_table(
            ["Deal", "Key Person", "Warm Connection", "Rationale"],
            warm_path_rows,
            "No warm paths identified.",
        ),
        "matches": render_table(
            ["Deal", "Potential Investor", "Confidence", "Rationale"],
            match_rows,
            "No automated matches found.",
        ),
    }

    print(f"Generating {INTELLIGENCE_DASHBOARD}...")
    with open(INTELLIGENCE_DASHBOARD, "w", encoding="utf-8") as handle:
        handle.write(render_intelligence(sections))

    if os.path.exists(RELATIONSHIP_MEMORY_SCRIPT):
        try:
            print("Generating relationship memory...")
            subprocess.run(
                ["python3", RELATIONSHIP_MEMORY_SCRIPT],
                check=True,
                env={**os.environ, "CRM_DATA_PATH": CRM_DATA_PATH},
            )
        except Exception as exc:
            print(f"Warning: relationship memory generation failed: {exc}")

    print("Intelligence Engine run complete.")


if __name__ == "__main__":
    main()
