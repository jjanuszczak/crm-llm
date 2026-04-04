import argparse
import base64
import html
import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGIC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(LOGIC_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from frontmatter_utils import bucketed_record_path, dated_record_id, iter_markdown_files, load_frontmatter_file


def get_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return os.path.abspath(env_override)

    env_path = os.path.join(LOGIC_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    path = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.abspath(os.path.join(LOGIC_ROOT, path)) if not os.path.isabs(path) else path
    return os.getcwd()


CRM_DATA_PATH = get_crm_data_path()
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
STAGING_DIR = os.path.join(CRM_DATA_PATH, "staging")
DISCOVERY_PATH = os.path.join(STAGING_DIR, "discovery.json")
WORKSPACE_UPDATES_PATH = os.path.join(STAGING_DIR, "workspace_updates.json")
INTERACTIONS_PATH = os.path.join(STAGING_DIR, "interactions.json")
SYNC_STATE_PATH = os.path.join(STAGING_DIR, "workspace_sync_state.json")
NOISE_DOMAINS_PATH = os.path.join(SCRIPTS_DIR, "noise_domains.json")
FIXTURE_DIR = os.getenv("GWS_FIXTURE_DIR")


def ensure_dirs():
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(ACTIVITIES_DIR, exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return default
    return default


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_sync_state():
    return load_json(
        SYNC_STATE_PATH,
        {
            "gmail_last_sync_at": "",
            "calendar_last_sync_at": "",
        },
    )


def save_sync_state(gmail_until_iso, calendar_until_iso):
    save_json(
        SYNC_STATE_PATH,
        {
            "gmail_last_sync_at": gmail_until_iso,
            "calendar_last_sync_at": calendar_until_iso,
        },
    )


def run_gws(args):
    if FIXTURE_DIR:
        command_key = "_".join(arg.replace(".", "_") for arg in args[1:] if not arg.startswith("--"))
        fixture_path = os.path.join(FIXTURE_DIR, command_key + ".json")
        if os.path.exists(fixture_path):
            return load_json(fixture_path, {})

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gws command failed")
    return json.loads(result.stdout)


def slugify(value):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip())
    return re.sub(r"-{2,}", "-", cleaned).strip("-") or "record"


def normalize_link(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text


def extract_headers(message):
    headers = {}
    payload = message.get("payload", {})
    for header in payload.get("headers", []):
        headers[header.get("name", "")] = header.get("value", "")
    return headers


def extract_message_text(payload):
    plain_text = _extract_payload_part(payload, "text/plain")
    if plain_text:
        return plain_text
    html_text = _extract_payload_part(payload, "text/html")
    if html_text:
        return _strip_html(html_text)
    return ""


def _extract_payload_part(payload, mime_type):
    if not isinstance(payload, dict):
        return ""
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return _decode_gmail_body(payload["body"]["data"])
    for part in payload.get("parts", []):
        extracted = _extract_payload_part(part, mime_type)
        if extracted:
            return extracted
    return ""


def _decode_gmail_body(data):
    try:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_html(value):
    without_tags = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    without_tags = re.sub(r"</p\s*>", "\n\n", without_tags, flags=re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", "", without_tags)
    return html.unescape(without_tags)


def summarize_gmail_message(headers, detail):
    subject = headers.get("Subject", "(no subject)")
    sender = parse_display_name(headers.get("From", ""))
    body_text = extract_message_text(detail.get("payload", {}))
    cleaned = normalize_message_text(body_text or detail.get("snippet", ""))
    summary_line = first_meaningful_line(cleaned)
    if summary_line:
        return f"{sender or 'Sender'} emailed about {subject}: {summary_line}"
    return f"{sender or 'Sender'} emailed about {subject}."


def summarize_calendar_event(event):
    summary = event.get("summary", "(untitled event)")
    location = (event.get("location") or "").strip()
    description = normalize_message_text(event.get("description", ""))
    first_line = first_meaningful_line(description)
    attendee_names = [
        attendee.get("displayName") or parse_display_name(attendee.get("email", ""))
        for attendee in event.get("attendees", [])
        if attendee.get("email")
    ]
    attendee_names = [name for name in attendee_names if name]
    parts = [f"Calendar meeting: {summary}."]
    if attendee_names:
        parts.append(f"Attendees included {', '.join(attendee_names[:4])}.")
    if location:
        parts.append(f"Location: {location}.")
    if first_line:
        parts.append(f"Context: {first_line}")
    return " ".join(parts)


def normalize_message_text(text):
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">") or line.startswith("From:") or line.startswith("Sent:") or line.startswith("Subject:"):
            continue
        if re.match(r"^On .+wrote:$", line):
            break
        lines.append(line)
    return "\n".join(lines)


def first_meaningful_line(text):
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) >= 20:
            return cleaned
    return ""


def parse_email_addresses(value):
    matches = re.findall(r"[\w.\-+%]+@[\w.\-]+\.\w+", value or "")
    return [match.lower() for match in matches]


def parse_display_name(value):
    if not value:
        return ""
    if "<" in value:
        return value.split("<", 1)[0].strip().strip('"')
    if "@" in value:
        return value.split("@", 1)[0]
    return value.strip()


def contact_map():
    mapping = {}
    if not os.path.exists(CONTACTS_DIR):
        return mapping
    for file_name in os.listdir(CONTACTS_DIR):
        if not file_name.endswith(".md"):
            continue
        path = os.path.join(CONTACTS_DIR, file_name)
        frontmatter, _ = load_frontmatter_file(path)
        email = (frontmatter.get("email") or "").lower()
        if not email:
            continue
        mapping[email] = {
            "path": path,
            "link": f"[[Contacts/{os.path.splitext(file_name)[0]}]]",
            "name": frontmatter.get("full-name", os.path.splitext(file_name)[0]),
            "account": frontmatter.get("account", ""),
        }
    return mapping


def active_contact_emails(contact_index):
    emails = {}
    if not os.path.exists(OPPORTUNITIES_DIR):
        return emails
    for file_name in os.listdir(OPPORTUNITIES_DIR):
        if not file_name.endswith(".md"):
            continue
        path = os.path.join(OPPORTUNITIES_DIR, file_name)
        frontmatter, _ = load_frontmatter_file(path)
        if not frontmatter.get("is-active", False):
            continue
        primary_contact = normalize_link(frontmatter.get("primary-contact"))
        if not primary_contact:
            continue
        contact_name = os.path.basename(primary_contact)
        contact_email = next(
            (
                email
                for email, details in contact_index.items()
                if normalize_link(details["link"]).endswith(contact_name)
            ),
            None,
        )
        if contact_email:
            emails[contact_email] = {
                "opportunity": f"[[Opportunities/{os.path.splitext(file_name)[0]}]]",
                "contact": contact_index[contact_email]["link"],
                "account": contact_index[contact_email].get("account", ""),
            }
    return emails


def existing_activity_refs():
    refs = set()
    if not os.path.exists(ACTIVITIES_DIR):
        return refs
    for path in iter_markdown_files(ACTIVITIES_DIR):
        frontmatter, _ = load_frontmatter_file(path)
        source_ref = frontmatter.get("source-ref")
        if source_ref:
            refs.add(source_ref)
    return refs


def load_noise_domains():
    noise = load_json(NOISE_DOMAINS_PATH, {})
    domains = set(noise.get("generic", [])) | set(noise.get("service", []))
    prefixes = set(noise.get("noise", []))
    return domains, prefixes


def build_gmail_query(since_epoch, emails):
    after_term = f"after:{since_epoch}"
    if emails:
        email_terms = " OR ".join(f"(from:{email} OR to:{email})" for email in emails)
        return f"{after_term} ({email_terms})"
    return f"{after_term} is:unread"


def gmail_messages(query):
    response = run_gws(
        [
            "gws",
            "gmail",
            "users",
            "messages",
            "list",
            "--params",
            json.dumps({"userId": "me", "q": query, "maxResults": 25}),
        ]
    )
    return response.get("messages", [])


def gmail_message_detail(message_id):
    return run_gws(
        [
            "gws",
            "gmail",
            "users",
            "messages",
            "get",
            "--params",
            json.dumps({"userId": "me", "id": message_id, "format": "full"}),
        ]
    )


def list_calendar_events(since_iso, until_iso):
    response = run_gws(
        [
            "gws",
            "calendar",
            "events",
            "list",
            "--params",
            json.dumps(
                {
                    "calendarId": "primary",
                    "timeMin": since_iso,
                    "timeMax": until_iso,
                    "singleEvents": True,
                    "orderBy": "startTime",
                    "maxResults": 25,
                }
            ),
        ]
    )
    return response.get("items", [])


def upsert_interaction(cache, email, event_date):
    if not email:
        return
    record = cache.setdefault(email, {"last_date": event_date, "hits_last_7_days": 0})
    record["last_date"] = max(record.get("last_date", event_date), event_date)
    if event_date >= (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"):
        record["hits_last_7_days"] = int(record.get("hits_last_7_days", 0)) + 1


def stage_discovery(discoveries, existing, email, name, rationale, source_ref):
    if not email or any(item.get("email") == email for item in existing + discoveries):
        return
    discoveries.append(
        {
            "name": name or email,
            "email": email,
            "type": "lead",
            "rationale": rationale,
            "source_ref": source_ref,
        }
    )


def create_activity_file(
    title,
    activity_type,
    event_date,
    primary_parent_type,
    primary_parent,
    secondary_links,
    source,
    source_ref,
    summary,
):
    ref_slug = slugify(str(source_ref))[:16]
    unique_title = f"{title} {ref_slug}" if ref_slug else title
    record_id = dated_record_id(event_date, unique_title)
    file_path = bucketed_record_path(ACTIVITIES_DIR, event_date, f"{record_id}.md")
    if os.path.exists(file_path):
        return file_path

    content = (
        "---\n"
        f'id: "{record_id}"\n'
        f'activity-name: "{title}"\n'
        f'activity-type: "{activity_type}"\n'
        'status: "completed"\n'
        'owner: "john"\n'
        f"date: {event_date}\n"
        f'primary-parent-type: "{primary_parent_type}"\n'
        f'primary-parent: "[[{primary_parent}]]"\n'
        "secondary-links:\n"
    )
    for link in secondary_links:
        content += f'  - "{link}"\n'
    content += (
        f'source: "{source}"\n'
        f'source-ref: "{source_ref}"\n'
        f"date-created: {event_date}\n"
        f"date-modified: {event_date}\n"
        "---\n\n"
        f"# **Activity: {title}**\n\n"
        "## **Executive Summary / Objective**\n"
        f"{summary}\n"
    )
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return file_path


def process_gmail(active_emails, contacts, since_date, since_epoch, autonomous, interactions, proposals, discoveries, existing_refs):
    domains, noise_prefixes = load_noise_domains()
    query = build_gmail_query(since_epoch, list(active_emails.keys()))
    messages = gmail_messages(query)

    for item in messages:
        detail = gmail_message_detail(item["id"])
        headers = extract_headers(detail)
        source_ref = detail.get("id")
        if source_ref in existing_refs:
            continue

        date_value = datetime.fromtimestamp(int(detail.get("internalDate", "0")) / 1000, UTC).strftime("%Y-%m-%d")
        from_value = headers.get("From", "")
        emails = parse_email_addresses(from_value)
        email = emails[0] if emails else ""
        upsert_interaction(interactions, email, date_value)
        subject = headers.get("Subject", "(no subject)")
        name = parse_display_name(from_value)

        if email in active_emails:
            parent = active_emails[email]
            summary = summarize_gmail_message(headers, detail)
            if autonomous:
                path = create_activity_file(
                    title=f"Gmail - {subject}",
                    activity_type="email",
                    event_date=date_value,
                    primary_parent_type="opportunity",
                    primary_parent=normalize_link(parent["opportunity"]),
                    secondary_links=[parent["contact"], parent["account"]] if parent.get("account") else [parent["contact"]],
                    source="gmail",
                    source_ref=source_ref,
                    summary=summary,
                )
                proposals.append({"type": "activity_created", "path": path, "source_ref": source_ref})
            else:
                proposals.append(
                    {
                        "type": "activity_proposal",
                        "channel": "gmail",
                        "source_ref": source_ref,
                        "subject": subject,
                        "contact": parent["contact"],
                        "opportunity": parent["opportunity"],
                    }
                )
            continue

        if not email:
            continue
        domain = email.split("@", 1)[-1]
        local_part = email.split("@", 1)[0]
        if domain in domains or any(token in local_part for token in noise_prefixes):
            continue
        rationale = f"Professional-looking inbound email after {since_date}: {subject}"
        stage_discovery(discoveries, load_json(DISCOVERY_PATH, []), email, name, rationale, source_ref)


def process_calendar(active_emails, contacts, since_iso, until_iso, autonomous, interactions, proposals, discoveries, existing_refs):
    domains, noise_prefixes = load_noise_domains()
    for event in list_calendar_events(since_iso, until_iso):
        source_ref = event.get("id")
        if source_ref in existing_refs:
            continue

        start = event.get("start", {})
        event_date = (start.get("dateTime") or start.get("date", ""))[:10]
        summary = event.get("summary", "(untitled event)")
        attendees = event.get("attendees", [])

        matched_parent = None
        matched_links = []
        for attendee in attendees:
            email = (attendee.get("email") or "").lower()
            if not email:
                continue
            upsert_interaction(interactions, email, event_date)
            if email in active_emails:
                parent = active_emails[email]
                matched_parent = parent
                matched_links = [parent["contact"]]
                if parent.get("account"):
                    matched_links.append(parent["account"])
            elif "@" in email:
                domain = email.split("@", 1)[-1]
                local_part = email.split("@", 1)[0]
                if domain not in domains and not any(token in local_part for token in noise_prefixes):
                    stage_discovery(
                        discoveries,
                        load_json(DISCOVERY_PATH, []),
                        email,
                        attendee.get("displayName") or email,
                        f"New calendar attendee after {event_date}: {summary}",
                        source_ref,
                    )

        if matched_parent:
            if autonomous:
                path = create_activity_file(
                    title=f"Calendar - {summary}",
                    activity_type="meeting",
                    event_date=event_date,
                    primary_parent_type="opportunity",
                    primary_parent=normalize_link(matched_parent["opportunity"]),
                    secondary_links=matched_links,
                    source="calendar",
                    source_ref=source_ref,
                    summary=summarize_calendar_event(event),
                )
                proposals.append({"type": "activity_created", "path": path, "source_ref": source_ref})
            else:
                proposals.append(
                    {
                        "type": "activity_proposal",
                        "channel": "calendar",
                        "source_ref": source_ref,
                        "summary": summary,
                        "opportunity": matched_parent["opportunity"],
                    }
                    )


def resolve_sync_window(since_override, sync_state):
    if since_override:
        base_dt = datetime.fromisoformat(f"{since_override}T00:00:00+00:00")
    else:
        latest = sync_state.get("gmail_last_sync_at") or sync_state.get("calendar_last_sync_at")
        if latest:
            try:
                base_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            except ValueError:
                base_dt = datetime.now(UTC) - timedelta(days=7)
        else:
            base_dt = datetime.now(UTC) - timedelta(days=7)
    base_dt = base_dt.astimezone(UTC).replace(microsecond=0)
    return {
        "gmail_since_epoch": int(base_dt.timestamp()),
        "gmail_since_date": base_dt.strftime("%Y-%m-%d"),
        "calendar_since_iso": base_dt.isoformat().replace("+00:00", "Z"),
    }


def main():
    parser = argparse.ArgumentParser(description="Sync Gmail and Calendar into CRM memory.")
    parser.add_argument("--since")
    parser.add_argument("--autonomous", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    contacts = contact_map()
    active_emails = active_contact_emails(contacts)
    interactions = load_json(INTERACTIONS_PATH, {})
    sync_state = load_sync_state()
    sync_window = resolve_sync_window(args.since, sync_state)
    discoveries = []
    proposals = []
    existing_refs = existing_activity_refs()

    until_iso = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    process_gmail(
        active_emails,
        contacts,
        sync_window["gmail_since_date"],
        sync_window["gmail_since_epoch"],
        args.autonomous,
        interactions,
        proposals,
        discoveries,
        existing_refs,
    )
    process_calendar(
        active_emails,
        contacts,
        sync_window["calendar_since_iso"],
        until_iso,
        args.autonomous,
        interactions,
        proposals,
        discoveries,
        existing_refs,
    )

    if discoveries:
        existing = load_json(DISCOVERY_PATH, [])
        merged = existing + [item for item in discoveries if all(existing_item.get("email") != item.get("email") for existing_item in existing)]
        save_json(DISCOVERY_PATH, merged)

    save_json(WORKSPACE_UPDATES_PATH, proposals)
    save_json(INTERACTIONS_PATH, interactions)
    save_sync_state(until_iso, until_iso)
    print(
        json.dumps(
            {
                "mode": "autonomous" if args.autonomous else "interactive",
                "known_contacts": len(active_emails),
                "gmail_since_date": sync_window["gmail_since_date"],
                "calendar_since_iso": sync_window["calendar_since_iso"],
                "discoveries_added": len(discoveries),
                "workspace_updates": len(proposals),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
