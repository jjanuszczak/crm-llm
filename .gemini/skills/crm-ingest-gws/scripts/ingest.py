import argparse
import base64
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.abspath(os.path.join(SKILL_ROOT, "../../../"))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from frontmatter_utils import (
        bucketed_record_path,
        dated_record_id,
        iter_markdown_files,
        load_frontmatter_file,
        slugify,
        write_frontmatter_file,
    )
except ImportError:
    def dated_record_id(record_date, title):
        safe = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return f"{record_date}-{safe}"

    def slugify(value):
        return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

    def iter_markdown_files(directory):
        for root, _, files in os.walk(directory):
            for name in sorted(files):
                if name.endswith(".md"):
                    yield os.path.join(root, name)

    def load_frontmatter_file(path):
        return {}, ""

    def write_frontmatter_file(path, frontmatter, body):
        raise RuntimeError("frontmatter_utils not available")

    def bucketed_record_path(base_dir, record_date, file_name):
        return os.path.join(base_dir, file_name)


OWN_EMAILS = {
    "operator@example.com",
}
ACTIVITY_WRITE_STATUSES = {"todo", "in-progress"}
PROFESSIONAL_KEYWORDS = (
    "proposal",
    "pricing",
    "agreement",
    "contract",
    "investment",
    "capital",
    "series",
    "deck",
    "teaser",
    "mandate",
    "partnership",
    "advisory",
    "introduc",
    "follow up",
    "next step",
)


def get_crm_data_path():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    path = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.abspath(os.path.join(PROJECT_ROOT, path)) if not os.path.isabs(path) else path
    return os.getenv("CRM_DATA_PATH", os.path.join(PROJECT_ROOT, "crm-data"))


CRM_DATA_PATH = get_crm_data_path()
STAGING_DIR = os.path.join(CRM_DATA_PATH, "staging")
SYNC_STATE_PATH = os.path.join(STAGING_DIR, "workspace_sync_state.json")
NOISE_DOMAINS_PATH = os.path.join(SCRIPTS_DIR, "noise_domains.json")
INTERACTIONS_PATH = os.path.join(STAGING_DIR, "interactions.json")
ACTIVITY_UPDATES_PATH = os.path.join(STAGING_DIR, "activity_updates.json")
CONTACT_DISCOVERIES_PATH = os.path.join(STAGING_DIR, "contact_discoveries.json")
LEAD_DECISIONS_PATH = os.path.join(STAGING_DIR, "lead_decisions.json")
OPPORTUNITY_SUGGESTIONS_PATH = os.path.join(STAGING_DIR, "opportunity_suggestions.json")
TASK_SUGGESTIONS_PATH = os.path.join(STAGING_DIR, "task_suggestions.json")
NOISE_REVIEW_PATH = os.path.join(STAGING_DIR, "noise_review.json")
INGESTION_AUDIT_PATH = os.path.join(STAGING_DIR, "ingestion_audit.json")
LEGACY_WORKSPACE_UPDATES_PATH = os.path.join(STAGING_DIR, "workspace_updates.json")
LEGACY_DISCOVERY_PATH = os.path.join(STAGING_DIR, "discovery.json")


def ensure_dirs():
    os.makedirs(STAGING_DIR, exist_ok=True)
    for name in ["Leads", "Activities", "Contacts", "Accounts", "Organizations", "Opportunities", "Tasks", "Notes", "Deal-Flow"]:
        os.makedirs(os.path.join(CRM_DATA_PATH, name), exist_ok=True)


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
        handle.write("\n")


def run_gws(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr.strip() or result.stdout.strip()}
        return json.loads(result.stdout or "{}")
    except Exception as exc:
        return {"error": str(exc)}


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


def wikilink_for_path(file_path):
    rel_path = os.path.relpath(file_path, CRM_DATA_PATH)
    return f"[[{os.path.splitext(rel_path)[0]}]]"


def as_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def as_date(value):
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def iso_today():
    return date.today().isoformat()


def parse_email_addresses(value):
    matches = re.findall(r"[\w.\-+%]+@[\w.\-]+\.\w+", value or "")
    return [match.lower() for match in matches]


def extract_message_text(payload):
    def get_part(part, mime_type):
        if part.get("mimeType") == mime_type and part.get("body", {}).get("data"):
            raw = part["body"]["data"]
            padded = raw + "=" * (-len(raw) % 4)
            return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
        for child in part.get("parts", []):
            found = get_part(child, mime_type)
            if found:
                return found
        return ""

    plain = get_part(payload, "text/plain")
    if plain:
        return plain
    html_text = get_part(payload, "text/html")
    if html_text:
        without_tags = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
        without_tags = re.sub(r"<[^>]+>", "", without_tags)
        return html.unescape(without_tags)
    return ""


def extract_urls(text):
    return re.findall(r"https?://[^\s>)]+", text or "")


def domain_from_email(email):
    email = str(email or "").strip().lower()
    if "@" not in email:
        return ""
    return email.split("@", 1)[1]


def domain_from_url(url):
    try:
        parsed = urlparse(str(url or "").strip())
        host = (parsed.netloc or parsed.path).lower()
        host = host.replace("www.", "")
        return host.split("/")[0]
    except Exception:
        return ""


def professional_signal_count(text):
    lowered = (text or "").lower()
    return sum(1 for keyword in PROFESSIONAL_KEYWORDS if keyword in lowered)


def summarize_text(text, limit=400):
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return cleaned[:limit].strip()


def sort_timestamp(value):
    text = str(value or "")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


class SourceHarvester:
    def __init__(self, since_dt):
        self.since_dt = since_dt

    def get_gmail_messages(self):
        query = f"after:{int(self.since_dt.timestamp())}"
        listing = run_gws(
            ["gws", "gmail", "users", "messages", "list", "--params", json.dumps({"userId": "me", "q": query, "maxResults": 50})]
        )
        messages = []
        for item in listing.get("messages", []):
            detail = run_gws(
                ["gws", "gmail", "users", "messages", "get", "--params", json.dumps({"userId": "me", "id": item["id"], "format": "full"})]
            )
            if "error" not in detail:
                messages.append(detail)
        return messages

    def get_calendar_events(self):
        time_min = self.since_dt.isoformat().replace("+00:00", "Z")
        listing = run_gws(
            [
                "gws",
                "calendar",
                "events",
                "list",
                "--params",
                json.dumps({"calendarId": "primary", "timeMin": time_min, "showDeleted": False, "singleEvents": True, "orderBy": "startTime"}),
            ]
        )
        events = []
        for item in listing.get("items", []):
            updated = item.get("updated")
            if not updated:
                events.append(item)
                continue
            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if updated_dt > self.since_dt:
                events.append(item)
        return events


class EventNormalizer:
    @staticmethod
    def normalize_gmail(msg):
        headers = {header["name"]: header["value"] for header in msg.get("payload", {}).get("headers", [])}
        participants = []
        seen = set()

        def add_participants(header_value, role):
            for email in parse_email_addresses(header_value):
                if email in seen:
                    continue
                seen.add(email)
                participants.append({"email": email, "name": header_value, "role": role})

        add_participants(headers.get("From", ""), "sender")
        add_participants(headers.get("To", ""), "to")
        add_participants(headers.get("Cc", ""), "cc")

        sender = participants[0]["email"] if participants else ""
        return {
            "source_type": "gmail",
            "source_id": msg["id"],
            "source_link": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
            "thread_id": msg.get("threadId"),
            "event_time": datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000, UTC).isoformat(),
            "direction": "outbound" if sender in OWN_EMAILS else "inbound",
            "participants": participants,
            "subject_or_title": headers.get("Subject", "(no subject)"),
            "body_text": extract_message_text(msg.get("payload", {})),
            "snippet": msg.get("snippet", ""),
            "raw_payload_ref": msg["id"],
        }

    @staticmethod
    def normalize_calendar(event):
        participants = []
        for attendee in event.get("attendees", []):
            participants.append(
                {
                    "email": (attendee.get("email") or "").lower(),
                    "name": attendee.get("displayName") or attendee.get("email") or "",
                    "role": "attendee",
                }
            )

        start = event.get("start", {})
        event_time = start.get("dateTime") or start.get("date")
        return {
            "source_type": "calendar",
            "source_id": event["id"],
            "source_link": event.get("htmlLink", ""),
            "thread_id": None,
            "event_time": event_time,
            "direction": "meeting",
            "participants": participants,
            "subject_or_title": event.get("summary", "(untitled event)"),
            "body_text": event.get("description", ""),
            "snippet": summarize_text(event.get("description", ""), 160),
            "raw_payload_ref": event["id"],
        }


class CRMIndex:
    def __init__(self):
        self.contacts_by_email = {}
        self.leads_by_email = {}
        self.company_contexts_by_domain = {}
        self.company_contexts = []
        self.opportunities = []
        self.opportunities_by_contact = {}
        self.linked_records = {}
        self.open_tasks = []
        self.open_tasks_by_link = {}
        self.activities = []
        self.activity_dedupe = {}
        self.activity_history_by_email = {}

    def add_linked_record(self, record):
        for variant in link_variants(record["link"]):
            self.linked_records[variant] = record


def choose_display_name(frontmatter, rel_path):
    for key in ["full-name", "lead-name", "opportunity-name", "organization-name", "company-name", "task-name", "activity-name"]:
        if frontmatter.get(key):
            return str(frontmatter.get(key))
    return os.path.splitext(os.path.basename(rel_path))[0]


def build_company_context(record_type, record, frontmatter):
    domains = set()
    for candidate in [frontmatter.get("domain"), frontmatter.get("url")]:
        domain = domain_from_url(candidate) if candidate and "://" in str(candidate) else str(candidate or "").replace("www.", "").lower()
        if domain and "." in domain:
            domains.add(domain)
    for email in parse_email_addresses(frontmatter.get("email", "")):
        domains.add(domain_from_email(email))
    return {
        "type": record_type,
        "link": record["link"],
        "name": choose_display_name(frontmatter, record["rel_path"]),
        "domains": sorted(domain for domain in domains if domain),
        "record": record,
    }


def get_crm_index():
    index = CRMIndex()
    directories = ["Organizations", "Accounts", "Contacts", "Leads", "Opportunities", "Tasks", "Activities"]
    for directory in directories:
        base_dir = os.path.join(CRM_DATA_PATH, directory)
        for file_path in iter_markdown_files(base_dir):
            frontmatter, body = load_frontmatter_file(file_path)
            rel_path = os.path.relpath(file_path, CRM_DATA_PATH)
            record = {
                "type": directory[:-1] if directory.endswith("s") else directory,
                "file_path": file_path,
                "rel_path": rel_path,
                "link": wikilink_for_path(file_path),
                "frontmatter": frontmatter,
                "body": body,
                "name": choose_display_name(frontmatter, rel_path),
            }
            index.add_linked_record(record)

            if directory == "Contacts":
                for email in parse_email_addresses(frontmatter.get("email", "")):
                    index.contacts_by_email[email] = record
            elif directory == "Leads":
                for email in parse_email_addresses(frontmatter.get("email", "")):
                    index.leads_by_email[email] = record
            elif directory in {"Organizations", "Accounts"}:
                context = build_company_context(directory[:-1].lower(), record, frontmatter)
                index.company_contexts.append(context)
                for domain in context["domains"]:
                    index.company_contexts_by_domain.setdefault(domain, []).append(context)
            elif directory == "Opportunities":
                if frontmatter.get("is-active", False):
                    index.opportunities.append(record)
                    contact_links = set(link_variants(frontmatter.get("primary-contact")))
                    for influencer in as_list(frontmatter.get("influencers")):
                        contact_links.update(link_variants(influencer))
                    for variant in contact_links:
                        if variant:
                            index.opportunities_by_contact.setdefault(variant, []).append(record)
            elif directory == "Tasks":
                if str(frontmatter.get("status", "")).lower() in ACTIVITY_WRITE_STATUSES:
                    index.open_tasks.append(record)
                    for link_field in ["opportunity", "account", "contact", "lead", "primary-parent"]:
                        for variant in link_variants(frontmatter.get(link_field)):
                            index.open_tasks_by_link.setdefault(variant, []).append(record)
            elif directory == "Activities":
                index.activities.append(record)
                source_type = str(frontmatter.get("source", "")).lower()
                source_ref = str(frontmatter.get("source-ref", "")).strip()
                primary_parent = normalize_link(frontmatter.get("primary-parent"))
                if source_type and source_ref and primary_parent:
                    key = f"{source_type}|{source_ref}|{canonical_key(primary_parent)}"
                    index.activity_dedupe[key] = record
                text = " ".join([body, str(frontmatter.get("activity-name", ""))]).lower()
                for email, contact in index.contacts_by_email.items():
                    if contact["name"].lower() in text:
                        index.activity_history_by_email.setdefault(email, []).append(record)
    return index


class EntityResolver:
    def __init__(self, crm_index, noise_domains, service_domains, noise_prefixes):
        self.index = crm_index
        self.noise_domains = set(noise_domains)
        self.service_domains = set(service_domains)
        self.noise_prefixes = tuple(noise_prefixes)

    def classify_email(self, email):
        domain = domain_from_email(email)
        local = email.split("@", 1)[0].lower() if "@" in email else ""
        if not email or "@" not in email:
            return "invalid"
        if email in OWN_EMAILS:
            return "self"
        if domain in self.service_domains:
            return "service"
        if domain in self.noise_domains or any(local.startswith(prefix) for prefix in self.noise_prefixes):
            return "generic"
        return "professional"

    def resolve_participant(self, participant):
        email = participant["email"].lower()
        email_class = self.classify_email(email)
        if email_class in {"invalid", "self"}:
            return {"status": "ignore", "reason": email_class, "participant": participant}
        if email_class in {"service", "generic"}:
            return {"status": "noise", "reason": email_class, "participant": participant}

        if email in self.index.contacts_by_email:
            record = self.index.contacts_by_email[email]
            opps = []
            for variant in link_variants(record["link"]):
                opps.extend(self.index.opportunities_by_contact.get(variant, []))
            return {
                "status": "matched",
                "match_type": "contact",
                "confidence": 1.0,
                "participant": participant,
                "record": record,
                "opportunities": dedupe_records(opps),
            }

        if email in self.index.leads_by_email:
            record = self.index.leads_by_email[email]
            return {
                "status": "matched",
                "match_type": "lead",
                "confidence": 1.0,
                "participant": participant,
                "record": record,
                "opportunities": [],
            }

        domain = domain_from_email(email)
        contexts = self.index.company_contexts_by_domain.get(domain, [])
        if contexts:
            return {
                "status": "matched",
                "match_type": "company_context",
                "confidence": 0.75,
                "participant": participant,
                "company_contexts": contexts,
                "opportunities": [],
            }

        return {
            "status": "unknown",
            "match_type": "unknown",
            "confidence": 0.0,
            "participant": participant,
            "opportunities": [],
        }


def dedupe_records(records):
    seen = set()
    ordered = []
    for record in records:
        key = record["link"]
        if key in seen:
            continue
        seen.add(key)
        ordered.append(record)
    return ordered


class InteractionInferrer:
    @staticmethod
    def infer_signals(text, subject="", event_type="gmail"):
        combined = f"{subject}\n{text}".strip()
        signals = []
        if re.search(r"follow up|next steps|please send|will send|get back to you|action item|task", combined, re.I):
            signals.append("commitment_detected")
        if re.search(r"meet|intro|introducing|connecting|connect with", combined, re.I):
            signals.append("introduction_detected")
        if re.search(r"proposal|pricing|agreement|contract|investment|capital|series|deck|teaser|mandate|retainer", combined, re.I):
            signals.append("commercial_intent")
        if re.search(r"schedule|calendar|availability|zoom|meet\.google|teams|call", combined, re.I):
            signals.append("logistics_detected")
        if event_type == "calendar":
            signals.append("meeting_detected")
        if re.search(r"\b(done|completed|confirmed|scheduled|sent|reviewed|attached)\b", combined, re.I):
            signals.append("completion_evidence")
        return signals


class NotesAnalyzer:
    @staticmethod
    def detect_note_links(event):
        text = " ".join([event.get("body_text", ""), event.get("snippet", ""), event.get("subject_or_title", "")])
        urls = extract_urls(text)
        note_links = []
        for url in urls:
            if "docs.google.com/document" in url or "notes.granola.ai" in url:
                note_links.append(url)
        return note_links

    @staticmethod
    def build_notes_summary(note_links):
        if not note_links:
            return ""
        return "Detected meeting-note links: " + ", ".join(note_links[:3])


class TaskAnalyzer:
    def __init__(self, crm_index):
        self.crm_index = crm_index

    def find_matching_tasks(self, anchor_links):
        matches = []
        seen = set()
        for variant in anchor_links:
            for task in self.crm_index.open_tasks_by_link.get(variant, []):
                if task["link"] in seen:
                    continue
                seen.add(task["link"])
                matches.append(task)
        return matches

    @staticmethod
    def extract_action_items(text):
        items = []
        patterns = [
            r"(?:I will|I'll|Please|Action item|Next steps?|Task):?\s*(.*)",
            r"(?:\n|^)\s*[-*]\s+(.*(?:follow up|send|check|call|meeting|review|share|draft|intro).*)",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text or "", re.I):
                line = match.split("\n")[0].strip()
                if 12 <= len(line) <= 220:
                    items.append(line)
        unique = []
        for item in items:
            if item not in unique:
                unique.append(item)
        return unique

    @staticmethod
    def looks_owner_assigned(text):
        return bool(re.search(r"\b(i will|i'll|john to|please send to me|please review|please draft|please follow up)\b", text or "", re.I))

    @staticmethod
    def completion_confidence(text, event_type):
        score = 0.0
        lowered = (text or "").lower()
        if any(word in lowered for word in ["done", "completed", "scheduled", "sent", "attached", "reviewed", "confirmed"]):
            score += 0.55
        if event_type == "calendar":
            score += 0.2
        return min(score, 0.95)


def proposal_group_id(event, suffix=""):
    raw = f"{event['source_type']}|{event['source_id']}|{suffix}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def build_company_context_link(contexts):
    if not contexts:
        return ""
    return contexts[0]["link"]


def choose_primary_anchor(event, resolutions, crm_index):
    candidate_opps = []
    candidate_contacts = []
    candidate_leads = []
    candidate_companies = []

    for resolution in resolutions:
        if resolution["status"] != "matched":
            continue
        if resolution["match_type"] == "contact":
            record = resolution["record"]
            candidate_contacts.append(record)
            candidate_opps.extend(resolution.get("opportunities", []))
            account_link = record["frontmatter"].get("account")
            linked_company = crm_index.linked_records.get(next(iter(link_variants(account_link)), ""), None)
            if linked_company:
                candidate_companies.append(linked_company)
        elif resolution["match_type"] == "lead":
            candidate_leads.append(resolution["record"])
        elif resolution["match_type"] == "company_context":
            for context in resolution.get("company_contexts", []):
                candidate_companies.append(context["record"])

    candidate_opps = dedupe_records(candidate_opps)
    candidate_contacts = dedupe_records(candidate_contacts)
    candidate_leads = dedupe_records(candidate_leads)
    candidate_companies = dedupe_records(candidate_companies)

    subject = event.get("subject_or_title", "")
    body = event.get("body_text", "")
    combined = f"{subject}\n{body}".lower()
    if candidate_opps:
        scored = []
        for opp in candidate_opps:
            score = 0
            for keyword in [opp["name"], opp["frontmatter"].get("opportunity-type", ""), opp["frontmatter"].get("product-service", "")]:
                if keyword and str(keyword).lower() in combined:
                    score += 3
            if score == 0:
                score = 1
            scored.append((score, opp))
        scored.sort(key=lambda item: item[0], reverse=True)
        return {"type": "opportunity", "record": scored[0][1]}
    if candidate_contacts:
        return {"type": "contact", "record": candidate_contacts[0]}
    if candidate_leads:
        return {"type": "lead", "record": candidate_leads[0]}
    if candidate_companies:
        company_type = "account" if "Accounts/" in candidate_companies[0]["link"] else "organization"
        return {"type": company_type, "record": candidate_companies[0]}
    return None


def build_secondary_links(primary_anchor, resolutions):
    links = []
    primary_link = primary_anchor["record"]["link"] if primary_anchor else ""
    for resolution in resolutions:
        if resolution["status"] != "matched":
            continue
        if resolution["match_type"] == "contact":
            if resolution["record"]["link"] != primary_link:
                links.append(resolution["record"]["link"])
            for opp in resolution.get("opportunities", []):
                if opp["link"] != primary_link:
                    links.append(opp["link"])
            account_link = resolution["record"]["frontmatter"].get("account")
            if account_link and normalize_link(account_link) != normalize_link(primary_link):
                links.append(account_link)
        elif resolution["match_type"] == "lead":
            if resolution["record"]["link"] != primary_link:
                links.append(resolution["record"]["link"])
        elif resolution["match_type"] == "company_context":
            company_link = build_company_context_link(resolution.get("company_contexts", []))
            if company_link and normalize_link(company_link) != normalize_link(primary_link):
                links.append(company_link)
    unique = []
    seen = set()
    for link in links:
        normalized = normalize_link(link)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(f"[[{normalized}]]" if not str(link).startswith("[[") else str(link))
    return unique[:8]


def build_activity_frontmatter(event, primary_anchor, secondary_links, note_links):
    event_date = event["event_time"][:10]
    title = event["subject_or_title"]
    source_type = event["source_type"]
    activity_name = title
    if source_type == "calendar":
        activity_type = "meeting"
    else:
        activity_type = "email"
    activity_id = dated_record_id(event_date, title)
    return {
        "id": activity_id,
        "activity-name": title,
        "activity-type": activity_type,
        "status": "completed",
        "owner": "john",
        "date": event_date,
        "primary-parent-type": primary_anchor["type"],
        "primary-parent": primary_anchor["record"]["link"],
        "secondary-links": secondary_links,
        "source": source_type,
        "source-ref": event["source_id"],
        "email-link": event["source_link"] if source_type == "gmail" else "",
        "meeting-notes": note_links[0] if note_links else "",
        "date-created": iso_today(),
        "date-modified": iso_today(),
    }


def build_activity_body(event, note_links, resolutions):
    participants = ", ".join(sorted({p["email"] for p in event["participants"] if p.get("email") and p["email"] not in OWN_EMAILS}))
    matched_names = []
    for resolution in resolutions:
        if resolution["status"] == "matched":
            if resolution["match_type"] in {"contact", "lead"}:
                matched_names.append(resolution["record"]["name"])
            elif resolution["match_type"] == "company_context":
                matched_names.extend([context["name"] for context in resolution.get("company_contexts", [])[:2]])
    matched_names = sorted({name for name in matched_names if name})
    body_text = summarize_text(event.get("body_text") or event.get("snippet", ""), 900)
    note_summary = NotesAnalyzer.build_notes_summary(note_links)
    lines = [
        f"# **Activity: {event['subject_or_title']}**",
        "",
        "## **Executive Summary / Objective**",
        body_text or "Interaction logged from workspace ingestion.",
        "",
        "## **Outcomes**",
        f"- [x] Logged {event['source_type']} interaction dated {event['event_time'][:10]}.",
    ]
    if matched_names:
        lines.append(f"- [x] Matched CRM context: {', '.join(matched_names)}.")
    if participants:
        lines.extend(["", "## **Detailed Notes**", f"* **Participants:** {participants}."])
    else:
        lines.extend(["", "## **Detailed Notes**", "* **Participants:** Not available."])
    if body_text:
        lines.append(f"* **Source Summary:** {body_text}")
    if note_summary:
        lines.extend(["", "## **Strategic Insights**", note_summary])
    return "\n".join(lines).rstrip() + "\n"


def activity_dedupe_key(source_type, source_id, primary_parent):
    return f"{source_type}|{source_id}|{canonical_key(primary_parent)}"


def maybe_write_activity(event, primary_anchor, secondary_links, crm_index, resolutions):
    note_links = NotesAnalyzer.detect_note_links(event)
    frontmatter = build_activity_frontmatter(event, primary_anchor, secondary_links, note_links)
    key = activity_dedupe_key(event["source_type"], event["source_id"], frontmatter["primary-parent"])
    if key in crm_index.activity_dedupe:
        return {"written": False, "duplicate": True, "existing": crm_index.activity_dedupe[key]}

    file_name = f"{frontmatter['id']}.md"
    activity_dir = os.path.join(CRM_DATA_PATH, "Activities")
    file_path = bucketed_record_path(activity_dir, frontmatter["date"], file_name)
    body = build_activity_body(event, note_links, resolutions)
    write_frontmatter_file(file_path, frontmatter, body)
    record = {
        "type": "Activity",
        "file_path": file_path,
        "rel_path": os.path.relpath(file_path, CRM_DATA_PATH),
        "link": wikilink_for_path(file_path),
        "frontmatter": frontmatter,
        "body": body,
        "name": frontmatter["activity-name"],
    }
    crm_index.activity_dedupe[key] = record
    return {"written": True, "duplicate": False, "record": record, "note_links": note_links}


def anchor_context_type(primary_anchor):
    if not primary_anchor:
        return ""
    return primary_anchor["type"]


def is_relationship_relevant(event, resolutions):
    text = f"{event.get('subject_or_title', '')}\n{event.get('body_text', '')}"
    if professional_signal_count(text) >= 2:
        return True
    return any(resolution["status"] == "matched" for resolution in resolutions)


def classify_unknown_participant(event, participant, anchor, anchor_resolutions, crm_index):
    domain = domain_from_email(participant["email"])
    anchor_type = anchor_context_type(anchor)
    anchor_links = []
    if anchor:
        anchor_links.append(anchor["record"]["link"])
    anchor_domains = set()
    for resolution in anchor_resolutions:
        if resolution["status"] == "matched" and resolution["match_type"] == "company_context":
            for context in resolution.get("company_contexts", []):
                anchor_domains.update(context["domains"])
        elif resolution["status"] == "matched" and resolution["match_type"] == "contact":
            account_link = resolution["record"]["frontmatter"].get("account")
            for variant in link_variants(account_link):
                linked = crm_index.linked_records.get(variant)
                if linked:
                    anchor_domains.add(domain_from_url(linked["frontmatter"].get("url")))
    if anchor_type == "lead":
        return "new_contact_for_existing_lead_context"
    if anchor_type in {"opportunity", "account", "organization", "contact"}:
        if domain and domain not in anchor_domains:
            return "create_contact_and_flag_secondary_lead"
        return "attach_contact_to_existing_relationship"
    return "create_lead"


def build_contact_discovery(event, participant, action_type, anchor):
    payload = {
        "proposal_group_id": proposal_group_id(event, participant["email"]),
        "source_event_id": event["source_id"],
        "source_type": event["source_type"],
        "source_link": event["source_link"],
        "event_time": event["event_time"],
        "action_type": action_type,
        "proposed_contact_name": participant.get("name") or participant["email"],
        "email": participant["email"],
        "inferred_company_context": domain_from_email(participant["email"]),
        "linked_anchor": anchor["record"]["link"] if anchor else "",
        "rationale": "",
        "ambiguity_flags": [],
    }
    if action_type == "attach_contact_to_existing_relationship":
        payload["rationale"] = "New participant appears clearly anchored to an existing active relationship."
    elif action_type == "new_contact_for_existing_lead_context":
        payload["rationale"] = "New participant appeared in a thread centered on an existing lead."
    elif action_type == "create_contact_and_flag_secondary_lead":
        payload["rationale"] = "Participant appears related to the current thread but represents a distinct company context."
        payload["ambiguity_flags"].append("dual_role_possible")
    else:
        payload["rationale"] = "Participant appears relationship-relevant and should be reviewed."
    return payload


def build_lead_decision(event, participant, decision_type, suggested_status="", conversion_mode="undetermined", anchor=""):
    payload = {
        "proposal_group_id": proposal_group_id(event, participant["email"]),
        "source_event_id": event["source_id"],
        "source_type": event["source_type"],
        "source_link": event["source_link"],
        "event_time": event["event_time"],
        "decision_type": decision_type,
        "participant_email": participant["email"],
        "participant_name": participant.get("name") or participant["email"],
        "anchor": anchor,
        "source_event_summary": summarize_text(event.get("body_text") or event.get("snippet", ""), 260),
        "meeting_notes_summary": NotesAnalyzer.build_notes_summary(NotesAnalyzer.detect_note_links(event)),
        "derived_recommendation": "",
    }
    if decision_type == "create_lead":
        payload["derived_recommendation"] = "Create a new lead candidate from this participant."
    elif decision_type == "suggest_status_change":
        payload["suggested_status"] = suggested_status
        payload["derived_recommendation"] = f"Suggest lead status change to {suggested_status} based on interaction evidence."
    elif decision_type == "suggest_conversion":
        payload["conversion_mode"] = conversion_mode
        payload["derived_recommendation"] = f"Suggest lead conversion with mode `{conversion_mode}`."
    return payload


def build_opportunity_suggestion(event, parent_record, parent_kind, rank=1, primary=True):
    subject = event.get("subject_or_title", "").strip() or "New Workstream"
    short_subject = re.sub(r"^re:\s*", "", subject, flags=re.I)
    if parent_kind == "lead":
        company = parent_record["frontmatter"].get("company-name") or parent_record["frontmatter"].get("lead-name") or parent_record["name"]
    else:
        company = parent_record["name"]
    proposed_name = f"{company} - {short_subject[:50]}".strip()
    return {
        "proposal_group_id": proposal_group_id(event, f"opp:{parent_record['link']}"),
        "source_event_id": event["source_id"],
        "source_type": event["source_type"],
        "source_link": event["source_link"],
        "event_time": event["event_time"],
        "proposal_rank": rank,
        "is_primary_suggestion": primary,
        "parent_context": parent_record["link"],
        "proposed_opportunity_name": proposed_name,
        "workstream_evidence": summarize_text(event.get("body_text") or event.get("snippet", ""), 260),
        "rationale": "Commercial intent or explicit workstream formation detected.",
        "source_event_summary": summarize_text(event.get("body_text") or event.get("snippet", ""), 260),
        "meeting_notes_summary": NotesAnalyzer.build_notes_summary(NotesAnalyzer.detect_note_links(event)),
        "derived_recommendation": f"Create or review a new opportunity suggestion for {proposed_name}.",
    }


def build_task_suggestion(event, parent_link, task_type, content, matched_task=None, confidence=0.0):
    payload = {
        "proposal_group_id": proposal_group_id(event, f"task:{task_type}:{matched_task['link'] if matched_task else content}"),
        "source_event_id": event["source_id"],
        "source_type": event["source_type"],
        "source_link": event["source_link"],
        "event_time": event["event_time"],
        "relationship_context": parent_link,
        "task_type": task_type,
        "source_event_summary": summarize_text(event.get("body_text") or event.get("snippet", ""), 240),
        "meeting_notes_summary": NotesAnalyzer.build_notes_summary(NotesAnalyzer.detect_note_links(event)),
        "derived_recommendation": "",
    }
    if task_type == "task_completion_suggestion":
        payload["matched_task"] = matched_task["link"]
        payload["completion_evidence"] = content
        payload["confidence"] = round(confidence, 2)
        payload["suggested_new_status"] = "completed"
        payload["derived_recommendation"] = f"Review whether {matched_task['name']} can now be closed."
    else:
        payload["content"] = content
        payload["derived_recommendation"] = f"Review whether this should become a {task_type}."
    return payload


def sort_activity_updates(items):
    status_order = {"pending_review": 0, "auto_written": 1}
    return sorted(items, key=lambda item: (status_order.get(item.get("status", ""), 9), -sort_timestamp(item.get("event_time", ""))))


def sort_contact_discoveries(items):
    anchor_order = {"opportunity": 0, "lead": 1, "account": 2, "organization": 2, "contact": 2, "": 3}
    return sorted(
        items,
        key=lambda item: (
            anchor_order.get(anchor_context_from_link(item.get("linked_anchor", "")), 3),
            item.get("linked_anchor", ""),
            -sort_timestamp(item.get("event_time", "")),
        ),
    )


def sort_lead_decisions(items):
    def key(item):
        if item.get("anchor", "").startswith("[[Leads/"):
            group = f"lead:{item['anchor']}"
            rank = 0
        else:
            group = f"group:{item.get('proposal_group_id', '')}"
            rank = 1
        return (rank, group, -sort_timestamp(item.get("event_time", "")))

    return sorted(items, key=key)


def sort_opportunity_suggestions(items):
    return sorted(
        items,
        key=lambda item: (
            item.get("parent_context", ""),
            0 if item.get("is_primary_suggestion") else 1,
            item.get("proposal_rank", 99),
            -sort_timestamp(item.get("event_time", "")),
        ),
    )


def task_type_rank(task_type):
    return {"task_completion_suggestion": 0, "committed_action": 1, "suggested_follow_up": 2}.get(task_type, 9)


def sort_task_suggestions(items):
    return sorted(
        items,
        key=lambda item: (
            item.get("relationship_context", ""),
            task_type_rank(item.get("task_type", "")),
            -sort_timestamp(item.get("event_time", "")),
        ),
    )


def anchor_context_from_link(link):
    normalized = normalize_link(link)
    if normalized.startswith("Opportunities/"):
        return "opportunity"
    if normalized.startswith("Leads/"):
        return "lead"
    if normalized.startswith("Accounts/"):
        return "account"
    if normalized.startswith("Organizations/"):
        return "organization"
    if normalized.startswith("Contacts/"):
        return "contact"
    return ""


def legacy_workspace_updates(activity_updates, task_suggestions, lead_decisions, opportunity_suggestions):
    combined = []
    for item in activity_updates:
        if item.get("status") == "pending_review":
            combined.append({"action_type": "activity_proposal", **item})
    for item in lead_decisions:
        combined.append({"action_type": item["decision_type"], **item})
    for item in opportunity_suggestions:
        combined.append({"action_type": "suggest_new_opportunity", **item})
    for item in task_suggestions:
        combined.append({"action_type": item["task_type"], **item})
    return combined


def legacy_discovery(contact_discoveries, lead_decisions, noise_review):
    discoveries = []
    for item in contact_discoveries:
        discoveries.append({"source_id": item["source_event_id"], "source_link": item["source_link"], "email": item["email"], "action_type": item["action_type"]})
    for item in lead_decisions:
        if item["decision_type"] == "create_lead":
            discoveries.append({"source_id": item["source_event_id"], "source_link": item["source_link"], "email": item["participant_email"], "action_type": "create_lead"})
    discoveries.extend(noise_review)
    return discoveries


def external_participants(event, resolver):
    result = []
    for participant in event["participants"]:
        email = participant.get("email", "").lower()
        if not email or resolver.classify_email(email) == "self":
            continue
        result.append(participant)
    return result


def likely_calendar_relevant(event, resolutions):
    if is_relationship_relevant(event, resolutions):
        return True
    attendees = [p for p in event["participants"] if p.get("email") and domain_from_email(p["email"]) not in {"gmail.com", "icloud.com"}]
    return len(attendees) >= 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since")
    parser.add_argument("--autonomous", action="store_true")
    parser.add_argument("--auto-tier", type=int, default=0)
    args = parser.parse_args()

    ensure_dirs()
    crm_index = get_crm_index()
    noise_config = load_json(NOISE_DOMAINS_PATH, {})
    noise_domains = set(noise_config.get("generic", []))
    service_domains = set(noise_config.get("service", []))
    noise_prefixes = noise_config.get("noise", [])
    state = load_json(SYNC_STATE_PATH, {"gmail_last_sync_at": "", "calendar_last_sync_at": ""})
    interactions = load_json(INTERACTIONS_PATH, {})

    now = datetime.now(UTC).replace(microsecond=0)
    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=UTC)
    else:
        last_sync = state.get("gmail_last_sync_at") or (now - timedelta(days=7)).isoformat()
        since_dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))

    harvester = SourceHarvester(since_dt)
    resolver = EntityResolver(crm_index, noise_domains, service_domains, noise_prefixes)
    inferrer = InteractionInferrer()
    task_analyzer = TaskAnalyzer(crm_index)

    activity_updates = []
    contact_discoveries = []
    lead_decisions = []
    opportunity_suggestions = []
    task_suggestions = []
    noise_review = []
    audit_log = {"scanned": 0, "ignored": 0, "actions": []}

    def record_interaction(email, event_date):
        if not email:
            return
        item = interactions.setdefault(email.lower(), {"last_date": event_date, "hits_last_7_days": 0})
        if event_date > item.get("last_date", ""):
            item["last_date"] = event_date
        if event_date >= (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"):
            item["hits_last_7_days"] = int(item.get("hits_last_7_days", 0)) + 1

    def process_event(event):
        audit_log["scanned"] += 1
        for participant in event["participants"]:
            record_interaction(participant.get("email", "").lower(), event["event_time"][:10])

        participants = external_participants(event, resolver)
        resolutions = [resolver.resolve_participant(participant) for participant in participants]
        signals = inferrer.infer_signals(event.get("body_text", ""), event.get("subject_or_title", ""), event.get("source_type", "gmail"))
        note_links = NotesAnalyzer.detect_note_links(event)
        if note_links:
            signals.append("meeting_notes_detected")

        if event["source_type"] == "calendar" and not likely_calendar_relevant(event, resolutions):
            audit_log["ignored"] += 1
            audit_log["actions"].append({"source_id": event["source_id"], "result": "ignored_calendar_noise"})
            return

        primary_anchor = choose_primary_anchor(event, resolutions, crm_index)
        secondary_links = build_secondary_links(primary_anchor, resolutions)

        if primary_anchor:
            activity_update = {
                "proposal_group_id": proposal_group_id(event, "activity"),
                "source_event_id": event["source_id"],
                "source_type": event["source_type"],
                "source_link": event["source_link"],
                "event_time": event["event_time"],
                "write_policy_tier": 1,
                "dedupe_result": "not_checked",
                "reason": "Matched known relationship context.",
                "primary_parent": primary_anchor["record"]["link"],
                "primary_parent_type": primary_anchor["type"],
                "secondary_links": secondary_links,
                "signals": signals,
            }
            if args.autonomous or args.auto_tier >= 1:
                write_result = maybe_write_activity(event, primary_anchor, secondary_links, crm_index, resolutions)
                if write_result["duplicate"]:
                    audit_log["actions"].append({"source_id": event["source_id"], "result": "duplicate_activity_skipped"})
                else:
                    activity_update["status"] = "auto_written"
                    activity_update["dedupe_result"] = "written"
                    activity_update["target_record_path"] = write_result["record"]["rel_path"]
                    activity_updates.append(activity_update)
            else:
                activity_update["status"] = "pending_review"
                activity_update["dedupe_result"] = "not_written"
                activity_updates.append(activity_update)

        matched_tasks = task_analyzer.find_matching_tasks(set(link_variants(primary_anchor["record"]["link"])) if primary_anchor else set())
        completion_conf = task_analyzer.completion_confidence(event.get("body_text", ""), event["source_type"])
        if completion_conf >= 0.55:
            for task in matched_tasks:
                task_suggestions.append(
                    build_task_suggestion(
                        event,
                        primary_anchor["record"]["link"] if primary_anchor else "",
                        "task_completion_suggestion",
                        summarize_text(event.get("body_text") or event.get("snippet", ""), 200),
                        matched_task=task,
                        confidence=completion_conf,
                    )
                )

        for item in task_analyzer.extract_action_items(event.get("body_text", "")):
            task_type = "committed_action" if task_analyzer.looks_owner_assigned(item) else "suggested_follow_up"
            task_suggestions.append(build_task_suggestion(event, primary_anchor["record"]["link"] if primary_anchor else "", task_type, item))

        for resolution in resolutions:
            participant = resolution["participant"]
            if resolution["status"] == "noise":
                if professional_signal_count(event.get("subject_or_title", "")) > 0:
                    noise_review.append(
                        {
                            "source_id": event["source_id"],
                            "source_link": event["source_link"],
                            "email": participant["email"],
                            "reason": resolution["reason"],
                        }
                    )
                else:
                    audit_log["ignored"] += 1
                continue

            if resolution["status"] == "unknown":
                action_type = classify_unknown_participant(event, participant, primary_anchor, resolutions, crm_index)
                normalized_action = action_type
                if action_type == "create_lead":
                    normalized_action = "new_lead_candidate"
                    lead_decisions.append(build_lead_decision(event, participant, "create_lead", anchor=primary_anchor["record"]["link"] if primary_anchor else ""))
                elif action_type == "new_contact_for_existing_lead_context":
                    contact_discoveries.append(build_contact_discovery(event, participant, "attach_contact_to_existing_relationship", primary_anchor))
                elif action_type == "attach_contact_to_existing_relationship":
                    contact_discoveries.append(build_contact_discovery(event, participant, action_type, primary_anchor))
                elif action_type == "create_contact_and_flag_secondary_lead":
                    contact_discoveries.append(build_contact_discovery(event, participant, action_type, primary_anchor))
                    lead_decisions.append(build_lead_decision(event, participant, "create_lead", anchor=primary_anchor["record"]["link"] if primary_anchor else ""))
                audit_log["actions"].append({"source_id": event["source_id"], "participant": participant["email"], "result": normalized_action})
                continue

            if resolution["status"] != "matched":
                continue

            if resolution["match_type"] == "lead":
                lead_record = resolution["record"]
                current_status = str(lead_record["frontmatter"].get("status", "")).lower()
                if any(signal in signals for signal in ["meeting_detected", "logistics_detected", "introduction_detected", "commitment_detected"]) and current_status == "new":
                    decision = build_lead_decision(event, participant, "suggest_status_change", suggested_status="engaged", anchor=lead_record["link"])
                    decision["current_status"] = current_status
                    decision["reason"] = "Real interaction detected with existing lead."
                    lead_decisions.append(decision)
                if "commercial_intent" in signals and current_status in {"engaged", "prospect", "new"}:
                    target_status = "qualified"
                    decision = build_lead_decision(event, participant, "suggest_status_change", suggested_status=target_status, anchor=lead_record["link"])
                    decision["current_status"] = current_status
                    decision["reason"] = "Commercial intent detected around existing lead."
                    lead_decisions.append(decision)
                if "commercial_intent" in signals and current_status == "qualified":
                    decision = build_lead_decision(event, participant, "suggest_conversion", conversion_mode="commercial", anchor=lead_record["link"])
                    decision["reason"] = "Qualified lead now shows explicit commercial workstream formation."
                    lead_decisions.append(decision)
                    opportunity_suggestions.append(build_opportunity_suggestion(event, lead_record, "lead"))

    for message in harvester.get_gmail_messages():
        process_event(EventNormalizer.normalize_gmail(message))

    for calendar_event in harvester.get_calendar_events():
        process_event(EventNormalizer.normalize_calendar(calendar_event))

    activity_updates = sort_activity_updates(activity_updates)
    contact_discoveries = sort_contact_discoveries(contact_discoveries)
    lead_decisions = sort_lead_decisions(lead_decisions)
    opportunity_suggestions = sort_opportunity_suggestions(opportunity_suggestions)
    task_suggestions = sort_task_suggestions(task_suggestions)

    save_json(ACTIVITY_UPDATES_PATH, activity_updates)
    save_json(CONTACT_DISCOVERIES_PATH, contact_discoveries)
    save_json(LEAD_DECISIONS_PATH, lead_decisions)
    save_json(OPPORTUNITY_SUGGESTIONS_PATH, opportunity_suggestions)
    save_json(TASK_SUGGESTIONS_PATH, task_suggestions)
    save_json(NOISE_REVIEW_PATH, noise_review)
    save_json(INGESTION_AUDIT_PATH, audit_log)
    save_json(INTERACTIONS_PATH, interactions)

    save_json(LEGACY_WORKSPACE_UPDATES_PATH, legacy_workspace_updates(activity_updates, task_suggestions, lead_decisions, opportunity_suggestions))
    save_json(LEGACY_DISCOVERY_PATH, legacy_discovery(contact_discoveries, lead_decisions, noise_review))

    state["gmail_last_sync_at"] = now.isoformat().replace("+00:00", "Z")
    state["calendar_last_sync_at"] = now.isoformat().replace("+00:00", "Z")
    save_json(SYNC_STATE_PATH, state)

    print(
        json.dumps(
            {
                "scanned": audit_log["scanned"],
                "activity_updates": len(activity_updates),
                "contact_discoveries": len(contact_discoveries),
                "lead_decisions": len(lead_decisions),
                "opportunity_suggestions": len(opportunity_suggestions),
                "task_suggestions": len(task_suggestions),
                "noise_review": len(noise_review),
                "status": "staged",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
