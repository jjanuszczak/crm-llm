import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
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
        find_markdown_file,
        iter_markdown_files,
        load_frontmatter_file,
        slugify,
        write_frontmatter_file,
    )
    from navigation_manager import record_mutation
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

    def find_markdown_file(directory, stem):
        target_name = f"{stem}.md"
        for file_path in iter_markdown_files(directory):
            if os.path.basename(file_path) == target_name:
                return file_path
        return None

    def load_frontmatter_file(path):
        return {}, ""

    def write_frontmatter_file(path, frontmatter, body):
        raise RuntimeError("frontmatter_utils not available")

    def record_mutation(*args, **kwargs):
        return None

    def bucketed_record_path(base_dir, record_date, file_name):
        return os.path.join(base_dir, file_name)


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

NOISE_TEXT_PATTERNS = (
    r"\bunsubscribe\b",
    r"\bview in browser\b",
    r"\bmanage preferences\b",
    r"\bemail statement\b",
    r"\bpassword protected\b",
    r"\bsecurity threats?\b",
    r"\bdear valued customer\b",
    r"\bterms and conditions apply\b",
    r"\bprivacy concerns\b",
    r"\brelationship manager\b",
    r"\bnewsletter\b",
    r"\bmarket outlook\b",
    r"\binternational benefits\b",
    r"\bwealth market outlook\b",
    r"\bnotification\b",
    r"\baccount statement\b",
    r"\bpodcasts?\b",
)

TASK_NOISE_PATTERNS = (
    r"delete it immediately and notify",
    r"unintended recipients are not authorized",
    r"consider the environment when printing",
    r"consider the environment before printing",
    r"consider the environment .* printing",
    r"terms and conditions apply",
    r"do not reply",
)

NOTE_SEARCH_STOPWORDS = {
    "about", "after", "before", "between", "call", "catch", "check", "discussion", "follow",
    "from", "have", "intro", "introduction", "john", "meeting", "notes", "regards", "re",
    "review", "sent", "share", "sync", "team", "teams", "thanks", "that", "the", "this",
    "update", "with", "would", "your",
}


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
SETTINGS_PATH = os.path.join(CRM_DATA_PATH, "settings.json")
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
DRIVE_DOCUMENT_UPDATES_PATH = os.path.join(STAGING_DIR, "drive_document_updates.json")
GRANOLA_UPDATES_PATH = os.path.join(STAGING_DIR, "granola_updates.json")
CALENDAR_EVENTS_CACHE_PATH = os.path.join(STAGING_DIR, "calendar_events_cache.json")
DEFAULT_CRM_DRIVE_LABEL_IDS = ["3qkuqYdjtgsnmboRjKmMiGOHl1MFONMnSuaSNNEbbFcb"]
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DEFAULT_GRANOLA_LOOKBACK_DAYS = 7
DEFAULT_WHATSAPP_LOOKBACK_DAYS = 7
GRANOLA_POST_INGEST_TIMEOUT_SECONDS = 180
WHATSAPP_UPDATES_PATH = os.path.join(STAGING_DIR, "whatsapp_updates.json")


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


def load_settings():
    settings = load_json(SETTINGS_PATH, {})
    return settings if isinstance(settings, dict) else {}


def resolve_crm_drive_label_ids():
    settings = load_settings()
    configured = settings.get("crm_drive_label_ids")
    if isinstance(configured, list):
        ids = [str(item).strip() for item in configured if str(item).strip()]
        if ids:
            return ids
    return list(DEFAULT_CRM_DRIVE_LABEL_IDS)


def granola_post_ingest_enabled():
    settings = load_settings()
    value = settings.get("granola_post_ingest_enabled")
    if value is None:
        return True
    return bool(value)


def granola_initial_lookback_days():
    settings = load_settings()
    value = settings.get("granola_post_ingest_lookback_days")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_GRANOLA_LOOKBACK_DAYS
    return max(1, min(parsed, 30))


def whatsapp_post_ingest_enabled():
    settings = load_settings()
    value = settings.get("whatsapp_post_ingest_enabled")
    if value is None:
        return False
    return bool(value)


def whatsapp_initial_lookback_days():
    settings = load_settings()
    value = settings.get("whatsapp_post_ingest_lookback_days")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_WHATSAPP_LOOKBACK_DAYS
    return max(1, min(parsed, 30))


def whatsapp_account_name():
    settings = load_settings()
    return str(settings.get("whatsapp_account") or "").strip()


def whatsapp_store_dir():
    settings = load_settings()
    value = str(settings.get("whatsapp_store_dir") or "").strip()
    if not value:
        return ""
    if os.path.isabs(value):
        return value
    return os.path.abspath(os.path.join(PROJECT_ROOT, value))


def resolve_own_emails():
    settings = load_settings()
    own_emails = set()

    preferred_email = str(settings.get("preferred_email") or "").strip().lower()
    if preferred_email:
        own_emails.add(preferred_email)

    for email in settings.get("self_emails", []) or []:
        normalized = str(email or "").strip().lower()
        if normalized:
            own_emails.add(normalized)

    return own_emails


OWN_EMAILS = resolve_own_emails()


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def run_gws(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            error_text = result.stderr.strip() or result.stdout.strip() or "unknown gws error"
            raise RuntimeError(error_text)
        payload = json.loads(result.stdout or "{}")
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(json.dumps(payload["error"], ensure_ascii=True))
        return payload
    except Exception as exc:
        raise RuntimeError(f"gws command failed for {' '.join(args)}: {exc}") from exc


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


def normalize_person_name(value):
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", text)


def normalize_phone_number(value):
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        return ""
    return digits.lstrip("0") or digits


def extract_phone_numbers(value):
    text = str(value or "")
    candidates = re.findall(r"\+?\d[\d\s().-]{6,}\d", text)
    numbers = []
    seen = set()
    for candidate in candidates:
        normalized = normalize_phone_number(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            numbers.append(normalized)
    return numbers


def phone_from_jid(jid):
    match = re.match(r"(\d+)@s\.whatsapp\.net$", str(jid or "").strip().lower())
    if not match:
        return ""
    return normalize_phone_number(match.group(1))


def is_whatsapp_group_jid(jid):
    return str(jid or "").strip().lower().endswith("@g.us")


def is_whatsapp_channel_jid(jid):
    return str(jid or "").strip().lower().endswith("@newsletter")


def default_wacli_store_dir():
    home = os.path.expanduser("~")
    if sys.platform == "linux":
        xdg = os.getenv("XDG_STATE_HOME")
        if xdg:
            return os.path.join(xdg, "wacli")
        return os.path.join(home, ".local", "state", "wacli")
    return os.path.join(home, ".wacli")


def extract_wacli_store_dir(payload):
    candidates = []

    def collect(node):
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                if lowered in {"path", "store", "store_dir", "dir"} and isinstance(value, str):
                    candidates.append(value)
                collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    collect(payload)
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text and os.path.isdir(text):
            return text
    return ""


class WacliAdapter:
    def __init__(self, account="", store_dir=""):
        self.account = str(account or "").strip()
        self.store_dir = str(store_dir or "").strip()

    def _base_command(self):
        cmd = ["wacli"]
        if self.account:
            cmd.extend(["--account", self.account])
        elif self.store_dir:
            cmd.extend(["--store", self.store_dir])
        return cmd

    def _env(self):
        env = os.environ.copy()
        env["WACLI_READONLY"] = "1"
        if self.store_dir:
            env["WACLI_STORE_DIR"] = self.store_dir
        return env

    def doctor(self):
        if not shutil.which("wacli"):
            raise RuntimeError("wacli binary not found on PATH")
        result = subprocess.run(
            self._base_command() + ["doctor", "--json"],
            capture_output=True,
            text=True,
            env=self._env(),
        )
        if result.returncode != 0:
            error_text = result.stderr.strip() or result.stdout.strip() or "wacli doctor failed"
            raise RuntimeError(error_text)
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSON from wacli doctor: {exc}") from exc
        if not self.store_dir:
            self.store_dir = extract_wacli_store_dir(payload) or self.store_dir or default_wacli_store_dir()
        return payload

    def database_path(self):
        store_dir = self.store_dir or default_wacli_store_dir()
        return os.path.join(store_dir, "wacli.db")

    def fetch_messages(self, min_rowid, since_timestamp, limit=500):
        db_path = self.database_path()
        if not os.path.exists(db_path):
            raise RuntimeError(f"wacli store not found at {db_path}")
        query = """
            SELECT
                m.rowid,
                m.chat_jid,
                COALESCE(m.chat_name, c.name, '') AS chat_name,
                m.msg_id,
                m.sender_jid,
                COALESCE(m.sender_name, '') AS sender_name,
                m.ts,
                COALESCE(m.display_text, m.text, '') AS text,
                COALESCE(m.media_caption, '') AS media_caption,
                COALESCE(m.media_type, '') AS media_type,
                COALESCE(m.from_me, 0) AS from_me
            FROM messages m
            LEFT JOIN chats c ON c.jid = m.chat_jid
            WHERE m.revoked = 0
              AND m.deleted_for_me = 0
              AND m.rowid > ?
              AND m.ts >= ?
            ORDER BY m.rowid ASC
            LIMIT ?
        """
        conn = None
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (int(min_rowid), int(since_timestamp), int(limit))).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(f"failed to read wacli.db: {exc}") from exc
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return [dict(row) for row in rows]


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


def extract_attachment_names(payload):
    names = []

    def walk_parts(part):
        filename = str(part.get("filename") or "").strip()
        body = part.get("body", {}) or {}
        attachment_id = body.get("attachmentId")
        if filename and attachment_id:
            names.append(filename)
        for child in part.get("parts", []) or []:
            walk_parts(child)

    walk_parts(payload or {})
    unique = []
    seen = set()
    for name in names:
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(name)
    return unique


def extract_urls(text):
    return re.findall(r"https?://[^\s>)]+", text or "")


def domain_from_email(email):
    email = str(email or "").strip().lower()
    if "@" not in email:
        return ""
    return email.split("@", 1)[1]


def domain_matches(domain, candidates):
    domain = str(domain or "").strip().lower()
    if not domain:
        return False
    for candidate in candidates:
        candidate = str(candidate or "").strip().lower()
        if not candidate:
            continue
        if domain == candidate or domain.endswith(f".{candidate}"):
            return True
    return False


def domain_from_url(url):
    try:
        parsed = urlparse(str(url or "").strip())
        host = (parsed.netloc or parsed.path).lower()
        host = host.replace("www.", "")
        return host.split("/")[0]
    except Exception:
        return ""


def extract_google_doc_id(value):
    match = re.search(r"/document/d/([A-Za-z0-9_-]+)", str(value or ""))
    if match:
        return match.group(1)
    text = str(value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", text):
        return text
    match = re.search(r"drive-doc:([A-Za-z0-9_-]{20,})", text)
    return match.group(1) if match else ""


def professional_signal_count(text):
    lowered = (text or "").lower()
    return sum(1 for keyword in PROFESSIONAL_KEYWORDS if keyword in lowered)


def summarize_text(text, limit=400):
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return cleaned[:limit].strip()


def clean_source_text_for_activity(text):
    lines = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            continue
        if re.match(r"^(from|sent|to|cc|subject|date):\s", line, re.I):
            continue
        if re.match(r"^on .+ wrote:?\s*$", line, re.I):
            continue
        if re.search(r"get outlook for ios|confidentiality notice|unsubscribe|manage preferences|external email", line, re.I):
            continue
        if re.fullmatch(r"[-_=]{3,}", line):
            continue
        lines.append(line)
    cleaned = re.sub(r"https?://\S+", "", " ".join(lines))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def sentence_candidates(text, max_sentences=5):
    sentences = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        cleaned = sentence.strip(" -*\t")
        if not 20 <= len(cleaned) <= 260:
            continue
        if re.search(r"\b(from|sent|subject|unsubscribe|confidentiality notice)\b", cleaned, re.I):
            continue
        sentences.append(cleaned)
        if len(sentences) >= max_sentences:
            break
    return sentences


def human_join(items):
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def summarize_activity_event(event, matched_names):
    source_type = event.get("source_type", "workspace")
    title = str(event.get("subject_or_title") or "Workspace interaction").strip()
    clean_text = clean_source_text_for_activity(event.get("body_text") or event.get("snippet", ""))
    sentences = sentence_candidates(clean_text, 3)
    context = human_join(matched_names[:3])
    direction = event.get("direction", "")

    if source_type == "calendar":
        summary = f"Calendar event logged: {title}."
    elif source_type == "drive":
        summary = f"CRM-labeled Drive document reviewed: {title}."
    elif source_type == "whatsapp":
        summary = f"WhatsApp conversation update captured about {title}."
    elif direction == "outbound":
        summary = f"John sent a Gmail update about {title}."
    elif direction == "inbound":
        summary = f"Inbound Gmail update received about {title}."
    else:
        summary = f"Gmail thread updated: {title}."

    if context:
        summary += f" Matched CRM context: {context}."
    if sentences:
        summary += " " + " ".join(sentences[:2])
    return summarize_text(summary, 520)


def activity_outcome_lines(event):
    clean_text = clean_source_text_for_activity(event.get("body_text") or event.get("snippet", ""))
    lowered = clean_text.lower()
    outcomes = [f"Logged {event.get('source_type', 'workspace')} interaction dated {event['event_time'][:10]}."]

    if re.search(r"\b(attached|attachment|shared|sent over|sending over)\b", lowered):
        outcomes.append("Captured that material was shared or attached.")
    if re.search(r"\b(reviewed|looks standard|approved|confirmed|works for me|getting started)\b", lowered):
        outcomes.append("Captured review / confirmation signal.")
    if re.search(r"\b(revert|circle back|get back|follow up|next step|next steps)\b", lowered):
        outcomes.append("Captured follow-up dependency.")
    if re.search(r"\b(schedule|scheduled|calendar|invite|meet|call)\b", lowered):
        outcomes.append("Captured scheduling or meeting-logistics signal.")
    return outcomes[:4]


def search_tokens(text, limit=4):
    tokens = []
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9&.-]{2,}", text or ""):
        normalized = token.strip(" .,-_").lower()
        if len(normalized) < 3 or normalized in NOTE_SEARCH_STOPWORDS:
            continue
        if normalized not in tokens:
            tokens.append(normalized)
        if len(tokens) >= limit:
            break
    return tokens


def looks_like_noise_message(event):
    combined = " ".join(
        [
            str(event.get("subject_or_title", "")),
            str(event.get("snippet", "")),
            str(event.get("body_text", "")),
        ]
    ).lower()
    return any(re.search(pattern, combined, re.I) for pattern in NOISE_TEXT_PATTERNS)


def sort_timestamp(value):
    text = str(value or "")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def build_thread_context(history):
    prior_subjects = []
    prior_outbound = []
    prior_inbound = []
    prior_attachments = []
    for item in history[-6:]:
        subject = str(item.get("subject_or_title", "")).strip()
        body = str(item.get("body_text") or item.get("snippet") or "").strip()
        attachment_text = " ".join(item.get("attachment_names", []) or [])
        combined = "\n".join(part for part in [subject, body, attachment_text] if part).strip()
        if subject and subject not in prior_subjects:
            prior_subjects.append(subject)
        if item.get("direction") == "outbound" and combined:
            prior_outbound.append(combined)
        elif item.get("direction") == "inbound" and combined:
            prior_inbound.append(combined)
        prior_attachments.extend(item.get("attachment_names", []) or [])

    return {
        "message_count": len(history),
        "prior_subjects": "\n".join(prior_subjects[-3:]),
        "prior_outbound_text": "\n\n".join(prior_outbound[-3:]),
        "prior_inbound_text": "\n\n".join(prior_inbound[-3:]),
        "prior_attachment_names": prior_attachments[-6:],
    }


def whatsapp_thread_context_text(event):
    if event.get("source_type") != "whatsapp":
        return ""
    context = event.get("_thread_context") or {}
    parts = [
        str(context.get("prior_subjects", "")).strip(),
        str(context.get("prior_outbound_text", "")).strip(),
        str(context.get("prior_inbound_text", "")).strip(),
        " ".join(context.get("prior_attachment_names", []) or []).strip(),
    ]
    return "\n\n".join(part for part in parts if part).strip()


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
        now = datetime.now(UTC)
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
            start = item.get("start", {})
            start_value = start.get("dateTime") or start.get("date")
            if start_value:
                try:
                    if "T" in start_value:
                        start_dt = datetime.fromisoformat(start_value.replace("Z", "+00:00"))
                    else:
                        start_dt = datetime.fromisoformat(f"{start_value}T00:00:00+00:00")
                    if start_dt > now:
                        continue
                except Exception:
                    pass
            updated = item.get("updated")
            if not updated:
                events.append(item)
                continue
            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if updated_dt > self.since_dt:
                events.append(item)
        return events

    def get_calendar_events_window(self, start_dt, end_dt):
        listing = run_gws(
            [
                "gws",
                "calendar",
                "events",
                "list",
                "--params",
                json.dumps(
                    {
                        "calendarId": "primary",
                        "timeMin": start_dt.isoformat().replace("+00:00", "Z"),
                        "timeMax": end_dt.isoformat().replace("+00:00", "Z"),
                        "showDeleted": False,
                        "singleEvents": True,
                        "orderBy": "startTime",
                    }
                ),
            ]
        )
        return listing.get("items", []) if isinstance(listing, dict) else []

    def get_labeled_drive_documents(self, label_ids):
        if not label_ids:
            return []

        label_clauses = [f"'labels/{label_id}' in labels" for label_id in label_ids if str(label_id).strip()]
        if not label_clauses:
            return []
        modified_after = self.since_dt.isoformat().replace("+00:00", "Z")
        query = (
            "(" + " or ".join(label_clauses) + ")"
            + f" and trashed=false and mimeType='{GOOGLE_DOC_MIME}' and modifiedTime > '{modified_after}'"
        )
        payload = run_gws(
            [
                "gws",
                "drive",
                "files",
                "list",
                "--params",
                json.dumps(
                    {
                        "q": query,
                        "pageSize": 50,
                        "supportsAllDrives": True,
                        "includeItemsFromAllDrives": True,
                        "orderBy": "modifiedTime asc",
                        "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",
                    }
                ),
            ]
        )
        return payload.get("files", []) if isinstance(payload, dict) else []


class EventNormalizer:
    @staticmethod
    def normalize_gmail(msg):
        headers = {header["name"]: header["value"] for header in msg.get("payload", {}).get("headers", [])}
        payload = msg.get("payload", {})
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
            "body_text": extract_message_text(payload),
            "snippet": msg.get("snippet", ""),
            "attachment_names": extract_attachment_names(payload),
            "references": headers.get("References", ""),
            "in_reply_to": headers.get("In-Reply-To", ""),
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
        end = event.get("end", {})
        event_time = start.get("dateTime") or start.get("date")
        return {
            "source_type": "calendar",
            "source_id": event["id"],
            "source_link": event.get("htmlLink", ""),
            "thread_id": None,
            "event_time": event_time,
            "end_time": end.get("dateTime") or end.get("date"),
            "location": event.get("location", ""),
            "status": event.get("status", ""),
            "direction": "meeting",
            "participants": participants,
            "subject_or_title": event.get("summary", "(untitled event)"),
            "body_text": event.get("description", ""),
            "snippet": summarize_text(event.get("description", ""), 160),
            "attachment_names": [str(item.get("title") or item.get("fileUrl") or "").strip() for item in event.get("attachments", []) if str(item.get("title") or item.get("fileUrl") or "").strip()],
            "organizer_email": (event.get("organizer", {}) or {}).get("email", "").lower(),
            "raw_payload_ref": event["id"],
        }

    @staticmethod
    def normalize_drive_file(file_item, body_text):
        modified_time = str(file_item.get("modifiedTime") or "")
        return {
            "source_type": "drive",
            "source_id": str(file_item.get("id") or ""),
            "source_link": str(file_item.get("webViewLink") or ""),
            "thread_id": None,
            "event_time": modified_time,
            "direction": "document",
            "participants": [],
            "subject_or_title": str(file_item.get("name") or "(untitled document)"),
            "body_text": body_text,
            "snippet": summarize_text(body_text, 160),
            "attachment_names": [],
            "raw_payload_ref": str(file_item.get("id") or ""),
        }

    @staticmethod
    def normalize_whatsapp_message(message, account_name=""):
        ts = int(message.get("ts") or 0)
        event_time = datetime.fromtimestamp(ts, UTC).isoformat() if ts else datetime.now(UTC).isoformat()
        chat_jid = str(message.get("chat_jid") or "").strip().lower()
        sender_jid = str(message.get("sender_jid") or chat_jid).strip().lower()
        from_me = bool(message.get("from_me"))
        chat_name = str(message.get("chat_name") or "").strip()
        sender_name = str(message.get("sender_name") or "").strip()
        text = summarize_text("\n".join(part for part in [message.get("text"), message.get("media_caption")] if str(part or "").strip()), 4000)
        phone = phone_from_jid(sender_jid if not from_me else chat_jid)
        participant_name = sender_name or chat_name or phone or sender_jid
        chat_kind = "group" if is_whatsapp_group_jid(chat_jid) else "channel" if is_whatsapp_channel_jid(chat_jid) else "direct"
        participants = [
            {
                "email": "",
                "name": participant_name,
                "role": "sender" if not from_me else "chat",
                "phone": phone,
                "jid": sender_jid if not from_me else chat_jid,
                "is_self": from_me and not is_whatsapp_group_jid(chat_jid),
                "source_type": "whatsapp",
                "chat_kind": chat_kind,
            }
        ]
        thread_id = f"whatsapp:{account_name}:{chat_jid}" if account_name else f"whatsapp:{chat_jid}"
        title_parts = [part for part in [chat_name, sender_name] if part]
        if not title_parts:
            title_parts.append(phone or chat_jid or "WhatsApp chat")
        subject = " / ".join(title_parts[:2])
        return {
            "source_type": "whatsapp",
            "source_id": f"{chat_jid}:{message.get('msg_id')}",
            "source_link": "",
            "thread_id": thread_id,
            "event_time": event_time,
            "direction": "outbound" if from_me else "inbound",
            "participants": participants,
            "subject_or_title": f"WhatsApp: {subject}",
            "body_text": text,
            "snippet": summarize_text(text, 160),
            "attachment_names": [str(message.get("media_type") or "").strip()] if str(message.get("media_type") or "").strip() else [],
            "references": "",
            "in_reply_to": "",
            "raw_payload_ref": str(message.get("msg_id") or ""),
            "chat_jid": chat_jid,
            "sender_jid": sender_jid,
            "whatsapp_rowid": int(message.get("rowid") or 0),
            "whatsapp_account": account_name,
            "chat_kind": chat_kind,
        }


class CRMIndex:
    def __init__(self):
        self.contacts_by_email = {}
        self.contacts_by_phone = {}
        self.contacts_by_name = {}
        self.leads_by_email = {}
        self.leads_by_phone = {}
        self.leads_by_name = {}
        self.company_contexts_by_domain = {}
        self.company_contexts = []
        self.opportunities = []
        self.opportunities_by_contact = {}
        self.linked_records = {}
        self.open_tasks = []
        self.open_tasks_by_link = {}
        self.task_records = []
        self.task_source_refs = {}
        self.activities = []
        self.activity_dedupe = {}
        self.activity_source_refs = {}
        self.activity_history_by_email = {}
        self.notes = []
        self.drive_ingestion_markers = {}
        self.all_records = []

    def add_linked_record(self, record):
        for variant in link_variants(record["link"]):
            self.linked_records[variant] = record

    def mark_drive_ingestion(self, key, timestamp):
        if not key:
            return
        existing = self.drive_ingestion_markers.get(key, 0.0)
        self.drive_ingestion_markers[key] = max(existing, timestamp)


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


def record_drive_ingestion_markers(index, frontmatter):
    marker_ts = sort_timestamp(frontmatter.get("date-modified") or frontmatter.get("date-created") or frontmatter.get("date") or "")
    source_ref = str(frontmatter.get("source-ref", "")).strip()
    if source_ref:
        index.mark_drive_ingestion(source_ref, marker_ts)
        doc_id = extract_google_doc_id(source_ref)
        if doc_id:
            index.mark_drive_ingestion(doc_id, marker_ts)

    meeting_notes = str(frontmatter.get("meeting-notes", "")).strip()
    if meeting_notes:
        index.mark_drive_ingestion(meeting_notes, marker_ts)
        doc_id = extract_google_doc_id(meeting_notes)
        if doc_id:
            index.mark_drive_ingestion(doc_id, marker_ts)


def get_crm_index():
    index = CRMIndex()
    directories = ["Organizations", "Accounts", "Contacts", "Leads", "Opportunities", "Tasks", "Activities", "Notes"]
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
            index.all_records.append(record)

            if directory == "Contacts":
                for email in parse_email_addresses(frontmatter.get("email", "")):
                    index.contacts_by_email[email] = record
                for phone in extract_phone_numbers(frontmatter.get("mobile", "")) + extract_phone_numbers(frontmatter.get("phone", "")):
                    index.contacts_by_phone[phone] = record
                for candidate_name in [frontmatter.get("full-name", ""), frontmatter.get("nickname", ""), record["name"]]:
                    normalized_name = normalize_person_name(candidate_name)
                    if normalized_name:
                        index.contacts_by_name.setdefault(normalized_name, []).append(record)
            elif directory == "Leads":
                for email in parse_email_addresses(frontmatter.get("email", "")):
                    index.leads_by_email[email] = record
                for phone in extract_phone_numbers(frontmatter.get("mobile", "")) + extract_phone_numbers(frontmatter.get("phone", "")):
                    index.leads_by_phone[phone] = record
                for candidate_name in [frontmatter.get("person-name", ""), frontmatter.get("lead-name", ""), record["name"]]:
                    normalized_name = normalize_person_name(candidate_name)
                    if normalized_name:
                        index.leads_by_name.setdefault(normalized_name, []).append(record)
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
                index.task_records.append(record)
                task_source_ref = str(frontmatter.get("source-ref", "")).strip()
                if task_source_ref:
                    index.task_source_refs.setdefault(task_source_ref, []).append(record)
                if str(frontmatter.get("status", "")).lower() in ACTIVITY_WRITE_STATUSES:
                    index.open_tasks.append(record)
                    for link_field in ["opportunity", "account", "contact", "lead", "primary-parent"]:
                        for variant in link_variants(frontmatter.get(link_field)):
                            index.open_tasks_by_link.setdefault(variant, []).append(record)
                record_drive_ingestion_markers(index, frontmatter)
            elif directory == "Activities":
                index.activities.append(record)
                source_type = str(frontmatter.get("source", "")).lower()
                source_ref = str(frontmatter.get("source-ref", "")).strip()
                primary_parent = normalize_link(frontmatter.get("primary-parent"))
                if source_ref:
                    index.activity_source_refs.setdefault(source_ref, []).append(record)
                if source_type and source_ref and primary_parent:
                    key = f"{source_type}|{source_ref}|{canonical_key(primary_parent)}"
                    index.activity_dedupe[key] = record
                text = " ".join([body, str(frontmatter.get("activity-name", ""))]).lower()
                for email, contact in index.contacts_by_email.items():
                    if contact["name"].lower() in text:
                        index.activity_history_by_email.setdefault(email, []).append(record)
                record_drive_ingestion_markers(index, frontmatter)
            elif directory == "Notes":
                index.notes.append(record)
                record_drive_ingestion_markers(index, frontmatter)
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
        if domain_matches(domain, self.service_domains):
            return "service"
        if domain_matches(domain, self.noise_domains) or any(local.startswith(prefix) for prefix in self.noise_prefixes):
            return "generic"
        return "professional"

    def classify_participant(self, participant):
        email = str(participant.get("email") or "").lower().strip()
        if email:
            return self.classify_email(email)
        if participant.get("is_self"):
            return "self"
        if participant.get("phone") or participant.get("jid"):
            return "professional"
        return "invalid"

    def resolve_participant(self, participant):
        email = str(participant.get("email") or "").lower()
        phone = normalize_phone_number(participant.get("phone") or phone_from_jid(participant.get("jid", "")))
        email_class = self.classify_participant(participant)
        if email_class in {"invalid", "self"}:
            return {"status": "ignore", "reason": email_class, "participant": participant}
        if email_class in {"service", "generic"}:
            return {"status": "noise", "reason": email_class, "participant": participant}

        if email and email in self.index.contacts_by_email:
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

        if phone and phone in self.index.contacts_by_phone:
            record = self.index.contacts_by_phone[phone]
            opps = []
            for variant in link_variants(record["link"]):
                opps.extend(self.index.opportunities_by_contact.get(variant, []))
            return {
                "status": "matched",
                "match_type": "contact",
                "confidence": 0.95,
                "participant": participant,
                "record": record,
                "opportunities": dedupe_records(opps),
            }

        if email and email in self.index.leads_by_email:
            record = self.index.leads_by_email[email]
            return {
                "status": "matched",
                "match_type": "lead",
                "confidence": 1.0,
                "participant": participant,
                "record": record,
                "opportunities": [],
            }

        if phone and phone in self.index.leads_by_phone:
            record = self.index.leads_by_phone[phone]
            return {
                "status": "matched",
                "match_type": "lead",
                "confidence": 0.95,
                "participant": participant,
                "record": record,
                "opportunities": [],
            }

        if participant.get("source_type") == "whatsapp" and participant.get("chat_kind") == "direct":
            name = normalize_person_name(participant.get("name", ""))
            if len(name.split()) >= 2:
                contact_matches = dedupe_records(self.index.contacts_by_name.get(name, []))
                if len(contact_matches) == 1:
                    record = contact_matches[0]
                    opps = []
                    for variant in link_variants(record["link"]):
                        opps.extend(self.index.opportunities_by_contact.get(variant, []))
                    return {
                        "status": "matched",
                        "match_type": "contact",
                        "confidence": 0.7,
                        "participant": participant,
                        "record": record,
                        "opportunities": dedupe_records(opps),
                    }

                lead_matches = dedupe_records(self.index.leads_by_name.get(name, []))
                if len(lead_matches) == 1:
                    return {
                        "status": "matched",
                        "match_type": "lead",
                        "confidence": 0.65,
                        "participant": participant,
                        "record": lead_matches[0],
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
    def get_note_context(event):
        context = event.get("_notes_context")
        if isinstance(context, dict):
            return context
        return {"links": [], "summary": "", "text": "", "looked_up": False}

    @classmethod
    def get_note_links(cls, event):
        links = list(cls.detect_note_links(event))
        context = cls.get_note_context(event)
        for link in context.get("links", []):
            if link and link not in links:
                links.append(link)
        return links

    @classmethod
    def build_notes_summary(cls, note_links, notes_text=""):
        if not note_links and not notes_text:
            return ""
        details = []
        if note_links:
            details.append("Detected meeting-note links: " + ", ".join(note_links[:3]))
        excerpt = summarize_text(notes_text, 360)
        if excerpt:
            details.append(f"Notes summary: {excerpt}")
        return " ".join(details).strip()

    @classmethod
    def get_note_summary(cls, event):
        context = cls.get_note_context(event)
        if context.get("summary"):
            return context["summary"]
        return cls.build_notes_summary(cls.get_note_links(event), context.get("text", ""))

    @classmethod
    def combined_event_text(cls, event):
        context = cls.get_note_context(event)
        note_text = str(context.get("text", "")).strip()
        base_text = "\n".join(
            [
                str(event.get("subject_or_title", "")).strip(),
                str(event.get("body_text", "")).strip(),
                str(event.get("snippet", "")).strip(),
            ]
        ).strip()
        if note_text:
            return f"{base_text}\n\nMeeting notes:\n{note_text}".strip()
        return base_text


class DriveMeetingNotesResolver:
    GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

    def __init__(self, crm_index):
        self.crm_index = crm_index
        self.search_cache = {}
        self.doc_cache = {}
        self.metadata_cache = {}

    @staticmethod
    def _escape_drive_query(value):
        return str(value or "").replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _extract_google_doc_id(url):
        match = re.search(r"/document/d/([A-Za-z0-9_-]+)", str(url or ""))
        return match.group(1) if match else ""

    @staticmethod
    def _google_doc_url(document_id):
        if not document_id:
            return ""
        return f"https://docs.google.com/document/d/{document_id}/edit"

    def _drive_list(self, query):
        cache_key = query
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        payload = run_gws(
            [
                "gws",
                "drive",
                "files",
                "list",
                "--params",
                json.dumps(
                    {
                        "q": query,
                        "pageSize": 5,
                        "orderBy": "modifiedTime desc",
                        "supportsAllDrives": True,
                        "includeItemsFromAllDrives": True,
                    }
                ),
            ]
        )
        files = payload.get("files", []) if isinstance(payload, dict) else []
        self.search_cache[cache_key] = files
        return files

    def _drive_get_metadata(self, file_id):
        if not file_id:
            return {}
        if file_id in self.metadata_cache:
            return self.metadata_cache[file_id]
        payload = run_gws(
            [
                "gws",
                "drive",
                "files",
                "get",
                "--params",
                json.dumps({"fileId": file_id, "supportsAllDrives": True}),
            ]
        )
        self.metadata_cache[file_id] = payload if isinstance(payload, dict) else {}
        return self.metadata_cache[file_id]

    def _docs_get_text(self, document_id):
        if not document_id:
            return ""
        if document_id in self.doc_cache:
            return self.doc_cache[document_id]
        payload = run_gws(
            [
                "gws",
                "docs",
                "documents",
                "get",
                "--params",
                json.dumps({"documentId": document_id}),
            ]
        )
        text = self._extract_doc_text(payload if isinstance(payload, dict) else {})
        self.doc_cache[document_id] = text
        return text

    def _extract_doc_text(self, payload):
        chunks = []

        def walk_content(content):
            for item in content or []:
                paragraph = item.get("paragraph")
                if paragraph:
                    for element in paragraph.get("elements", []):
                        text_run = element.get("textRun")
                        if text_run and text_run.get("content"):
                            chunks.append(text_run["content"])
                table = item.get("table")
                if table:
                    for row in table.get("tableRows", []):
                        for cell in row.get("tableCells", []):
                            walk_content(cell.get("content", []))
                toc = item.get("tableOfContents")
                if toc:
                    walk_content(toc.get("content", []))

        if payload.get("tabs"):
            for tab in payload.get("tabs", []):
                document_tab = tab.get("documentTab", {})
                walk_content(document_tab.get("body", {}).get("content", []))
                for child in tab.get("childTabs", []) or []:
                    document_tab = child.get("documentTab", {})
                    walk_content(document_tab.get("body", {}).get("content", []))
        else:
            walk_content(payload.get("body", {}).get("content", []))

        return summarize_text("".join(chunks), 4000)

    def _linked_record_note_links(self, primary_anchor, secondary_links):
        links = []
        candidate_links = []
        if primary_anchor:
            candidate_links.append(primary_anchor["record"]["link"])
        candidate_links.extend(secondary_links or [])
        for link in candidate_links:
            for variant in link_variants(link):
                record = self.crm_index.linked_records.get(variant)
                if not record:
                    continue
                note_link = str(record["frontmatter"].get("meeting-notes", "")).strip()
                if note_link and note_link not in links:
                    links.append(note_link)
                for url in extract_urls(record.get("body", "")):
                    if ("docs.google.com/document" in url or "notes.granola.ai" in url) and url not in links:
                        links.append(url)
        return links

    def _search_terms(self, event, primary_anchor, secondary_links):
        terms = []

        def add_terms(text, limit):
            for token in search_tokens(text, limit=limit):
                if token not in terms:
                    terms.append(token)

        add_terms(event.get("subject_or_title", ""), 4)
        if primary_anchor:
            add_terms(primary_anchor["record"].get("name", ""), 3)
        for link in secondary_links or []:
            for variant in link_variants(link):
                record = self.crm_index.linked_records.get(variant)
                if record:
                    add_terms(record.get("name", ""), 2)
                    break
        for participant in event.get("participants", []):
            email = participant.get("email", "")
            if email in OWN_EMAILS:
                continue
            add_terms(participant.get("name", "") or email.split("@", 1)[0], 2)
        return terms[:5]

    def _search_drive_candidates(self, event, primary_anchor, secondary_links):
        terms = self._search_terms(event, primary_anchor, secondary_links)
        if not terms:
            return []

        queries = []
        term_pairs = [terms[:2], [terms[0]], terms[1:3]]
        for pair in term_pairs:
            pair = [term for term in pair if term]
            if not pair:
                continue
            clauses = [
                f"(name contains '{self._escape_drive_query(term)}' or fullText contains '{self._escape_drive_query(term)}')"
                for term in pair
            ]
            queries.append(
                "mimeType='application/vnd.google-apps.document' and trashed=false and " + " and ".join(clauses)
            )

        candidates = []
        seen_ids = set()
        for query in queries:
            try:
                for item in self._drive_list(query):
                    file_id = str(item.get("id", "")).strip()
                    if not file_id or file_id in seen_ids:
                        continue
                    seen_ids.add(file_id)
                    candidates.append(item)
            except RuntimeError:
                continue
        return candidates[:5]

    @staticmethod
    def _needs_drive_search(event):
        if event.get("source_type") == "calendar":
            return True
        combined = " ".join(
            [
                str(event.get("subject_or_title", "")).strip(),
                str(event.get("body_text", "")).strip(),
                str(event.get("snippet", "")).strip(),
            ]
        )
        return bool(
            re.search(
                r"\b(meet|meeting|call|sync|agenda|minutes|notes|debrief|follow[- ]up call|teams|zoom|google meet)\b",
                combined,
                re.I,
            )
        )

    def resolve_for_event(self, event, primary_anchor, secondary_links):
        links = []
        for link in NotesAnalyzer.detect_note_links(event):
            if link not in links:
                links.append(link)
        for link in self._linked_record_note_links(primary_anchor, secondary_links):
            if link not in links:
                links.append(link)

        looked_up = False
        if self._needs_drive_search(event):
            drive_candidates = self._search_drive_candidates(event, primary_anchor, secondary_links)
            if drive_candidates:
                looked_up = True
            for item in drive_candidates[:1]:
                file_id = str(item.get("id", "")).strip()
                if not file_id:
                    continue
                doc_url = self._google_doc_url(file_id)
                if doc_url and doc_url not in links:
                    links.append(doc_url)

        notes_text_parts = []
        for link in links[:2]:
            document_id = self._extract_google_doc_id(link)
            if not document_id:
                continue
            looked_up = True
            try:
                metadata = self._drive_get_metadata(document_id)
            except RuntimeError:
                metadata = {}
            title = str(metadata.get("name", "")).strip()
            try:
                doc_text = self._docs_get_text(document_id)
            except RuntimeError:
                doc_text = ""
            excerpt = summarize_text(doc_text, 900)
            if title and excerpt:
                notes_text_parts.append(f"{title}: {excerpt}")
            elif excerpt:
                notes_text_parts.append(excerpt)

        notes_text = "\n".join(part for part in notes_text_parts if part).strip()
        summary = NotesAnalyzer.build_notes_summary(links, notes_text)
        return {"links": links[:5], "summary": summary, "text": notes_text, "looked_up": looked_up}


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
    def _relevance_tokens(text):
        stopwords = {
            "about", "after", "before", "between", "could", "email", "follow", "from", "have", "john", "meeting",
            "need", "next", "note", "notes", "outline", "please", "regards", "review", "sent", "share", "task",
            "that", "their", "them", "this", "today", "will", "with", "would", "your",
        }
        tokens = re.findall(r"[a-z0-9]{4,}", (text or "").lower())
        return {token for token in tokens if token not in stopwords}

    @staticmethod
    def event_text(event, include_thread=True):
        parts = [
            event.get("subject_or_title", ""),
            event.get("body_text", ""),
            event.get("snippet", ""),
            " ".join(event.get("attachment_names", []) or []),
        ]
        if include_thread:
            thread_context = event.get("_thread_context", {}) or {}
            parts.extend(
                [
                    thread_context.get("prior_subjects", ""),
                    thread_context.get("prior_outbound_text", ""),
                    thread_context.get("prior_inbound_text", ""),
                    " ".join(thread_context.get("prior_attachment_names", []) or []),
                ]
            )
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def sentence_candidates(text):
        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text or "")
        return [sentence.strip(" -\t") for sentence in raw_sentences if 8 <= len(sentence.strip()) <= 240]

    def task_relevance_score(self, event, task):
        event_text = self.event_text(event)
        task_text = " ".join(
            [
                task.get("name", ""),
                task.get("body", ""),
                task.get("frontmatter", {}).get("contact", ""),
                task.get("frontmatter", {}).get("primary-parent", ""),
                task.get("frontmatter", {}).get("account", ""),
            ]
        )
        overlap = self._relevance_tokens(event_text) & self._relevance_tokens(task_text)
        if len(overlap) >= 2:
            return 0.25
        if len(overlap) == 1:
            return 0.15
        if any(token in event_text.lower() for token in self._relevance_tokens(task_text)):
            return 0.1
        return 0.0

    @staticmethod
    def extract_action_items(text):
        items = []
        patterns = [
            r"(?:I will|I'll|Please|Action item|Next steps?|Task):?\s*(.*)",
            r"(?:\n|^)\s*[-*]\s+(.*(?:follow up|send|check|call|meeting|review|share|draft|intro).*)",
            r"(?:\bwe should\b|\byou should\b|\bneed to\b|\bcan you\b|\blet's\b)\s+(.*)",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text or "", re.I):
                line = match.split("\n")[0].strip()
                if 12 <= len(line) <= 220 and not any(re.search(pattern, line, re.I) for pattern in TASK_NOISE_PATTERNS):
                    items.append(line)
        for sentence in TaskAnalyzer.sentence_candidates(text):
            if not re.search(r"\b(follow up|send|share|draft|review|introduce|intro|schedule|set up|book|confirm|check in|circle back|prepare|connect)\b", sentence, re.I):
                continue
            if any(re.search(pattern, sentence, re.I) for pattern in TASK_NOISE_PATTERNS):
                continue
            items.append(sentence)
        unique = []
        for item in items:
            if item not in unique:
                unique.append(item)
        return unique

    @staticmethod
    def looks_owner_assigned(text):
        return bool(
            re.search(
                r"\b(i will|i'll|john to|please send to me|please review|please draft|please follow up|i can|i should|let me)\b",
                text or "",
                re.I,
            )
        )

    @staticmethod
    def completion_confidence(text, event_type, metadata_text=""):
        score = 0.0
        lowered = " ".join([text or "", metadata_text or ""]).lower()
        if any(re.search(pattern, lowered, re.I) for pattern in TASK_NOISE_PATTERNS):
            return 0.0
        if any(word in lowered for word in ["done", "completed", "scheduled", "sent", "attached", "reviewed", "confirmed"]):
            score += 0.55
        if re.search(r"\b(attached|attachment|see attached|shared here|sending over)\b", lowered):
            score += 0.15
        if re.search(r"\b(calendar invite|invite sent|booked for|scheduled for|see you on)\b", lowered):
            score += 0.2
        if event_type == "calendar":
            score += 0.2
        return min(score, 0.95)

    @staticmethod
    def prior_commitment_score(event, task):
        thread_context = event.get("_thread_context", {}) or {}
        prior_outbound = thread_context.get("prior_outbound_text", "")
        if not prior_outbound:
            return 0.0

        task_name = (task.get("name") or "").lower()
        task_tokens = TaskAnalyzer._relevance_tokens(task_name)
        prior_tokens = TaskAnalyzer._relevance_tokens(prior_outbound)
        overlap = task_tokens & prior_tokens
        score = 0.0
        if overlap:
            score += 0.2
        if re.search(r"\b(i will|i'll|let me|i can|i should|john to)\b", prior_outbound, re.I):
            score += 0.15
        if any(word in task_name for word in ["send", "share", "draft", "introduce", "intro", "schedule", "confirm", "follow"]):
            score += 0.1
        return min(score, 0.35)

    def completion_confidence_for_task(self, event, task):
        metadata_text = " ".join(event.get("attachment_names", []) or [])
        base = self.completion_confidence(self.event_text(event, include_thread=False), event["source_type"], metadata_text)
        relevance = self.task_relevance_score(event, task)
        if relevance == 0.0:
            return 0.0

        score = base + relevance
        score += self.prior_commitment_score(event, task)
        if event.get("direction") == "outbound":
            score += 0.2
            task_name = (task.get("name") or "").lower()
            if any(word in task_name for word in ["send", "introduce", "intro", "nudge", "request", "outline", "follow"]):
                score += 0.1
        elif event.get("direction") == "inbound" and re.search(r"\b(thanks|received|looks good|works for me|confirmed)\b", self.event_text(event, include_thread=False), re.I):
            score += 0.1
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
    elif source_type == "drive":
        activity_type = "meeting" if re.search(r"\b(meeting|call|sync|catch up|checkpoint|debrief|board)\b", title, re.I) else "analysis"
    elif source_type == "whatsapp":
        activity_type = "note-derived"
    else:
        activity_type = "email"
    if source_type == "drive":
        activity_id = dated_record_id(event_date, f"{title} {event['source_id'][:8]} {event_date}")
    else:
        activity_id = dated_record_id(event_date, title)
    source_ref = drive_source_ref(event["source_id"], event["event_time"]) if source_type == "drive" else event["source_id"]
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
        "source-ref": source_ref,
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
    summary = summarize_activity_event(event, matched_names)
    source_excerpt = summarize_text(clean_source_text_for_activity(event.get("body_text") or event.get("snippet", "")), 260)
    note_summary = NotesAnalyzer.get_note_summary(event)
    lines = [
        f"# **Activity: {event['subject_or_title']}**",
        "",
        "## **Executive Summary / Objective**",
        summary or "Interaction logged from workspace ingestion.",
        "",
        "## **Outcomes**",
    ]
    for outcome in activity_outcome_lines(event):
        lines.append(f"- [x] {outcome}")
    if matched_names:
        lines.append(f"- [x] Matched CRM context: {', '.join(matched_names)}.")
    if participants:
        lines.extend(["", "## **Detailed Notes**", f"* **Participants:** {participants}."])
    else:
        lines.extend(["", "## **Detailed Notes**", "* **Participants:** Not available."])
    if source_excerpt:
        lines.append(f"* **Source Excerpt:** {source_excerpt}")
    if note_summary:
        lines.extend(["", "## **Strategic Insights**", note_summary])
    return "\n".join(lines).rstrip() + "\n"


def activity_dedupe_key(source_type, source_id, primary_parent):
    return f"{source_type}|{source_id}|{canonical_key(primary_parent)}"


def maybe_write_activity(event, primary_anchor, secondary_links, crm_index, resolutions):
    note_links = NotesAnalyzer.get_note_links(event)
    frontmatter = build_activity_frontmatter(event, primary_anchor, secondary_links, note_links)
    key = activity_dedupe_key(event["source_type"], frontmatter["source-ref"], frontmatter["primary-parent"])
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
    if event["source_type"] == "drive":
        marker_ts = sort_timestamp(event["event_time"])
        crm_index.mark_drive_ingestion(frontmatter["source-ref"], marker_ts)
        crm_index.mark_drive_ingestion(event["source_id"], marker_ts)
        if event.get("source_link"):
            crm_index.mark_drive_ingestion(event["source_link"], marker_ts)
    return {"written": True, "duplicate": False, "record": record, "note_links": note_links}


def drive_source_ref(file_id, modified_time):
    return f"drive-doc:{file_id}:{modified_time}"


def infer_anchor_from_text(title, text, crm_index):
    combined = f"{title}\n{text}".lower()
    combined_tokens = set(search_tokens(combined, limit=40))
    candidates = []
    seen = set()
    type_priority = {"opportunity": 0, "contact": 1, "lead": 2, "account": 3, "organization": 4}

    for record in crm_index.all_records:
        record_type = str(record.get("type", "")).lower()
        if record_type not in type_priority:
            continue
        if record["link"] in seen:
            continue
        seen.add(record["link"])
        name = str(record.get("name", "")).strip()
        if not name:
            continue
        score = 0
        lowered_name = name.lower()
        if lowered_name in combined:
            score += 5
        name_tokens = set(search_tokens(name, limit=8))
        overlap = combined_tokens & name_tokens
        score += len(overlap)
        if record_type == "opportunity":
            for keyword in [record["frontmatter"].get("product-service", ""), record["frontmatter"].get("opportunity-type", "")]:
                if keyword and str(keyword).lower() in combined:
                    score += 1
        if score > 0:
            candidates.append((score, type_priority[record_type], record))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]["name"]))
    record = candidates[0][2]
    return {"type": str(record.get("type", "")).lower(), "record": record}


def already_ingested_drive_doc(crm_index, file_id, source_link, modified_time):
    modified_ts = sort_timestamp(modified_time)
    keys = [file_id, source_link, drive_source_ref(file_id, modified_time)]
    for key in keys:
        if not key:
            continue
        if crm_index.drive_ingestion_markers.get(key, 0.0) >= modified_ts:
            return True
    return False


def classify_drive_document(event, signals, action_items):
    title = str(event.get("subject_or_title", ""))
    combined = f"{title}\n{event.get('body_text', '')}"
    if re.search(r"\b(meeting|call|sync|catch up|debrief|board|minutes|notes)\b", combined, re.I):
        return "activity"
    if action_items and re.search(r"\b(next steps|action items?|todo|to do|follow up)\b", combined, re.I):
        return "note"
    if "commercial_intent" in signals or "meeting_detected" in signals or "logistics_detected" in signals:
        return "activity"
    return "note"


def build_note_frontmatter(event, primary_anchor, secondary_links):
    event_date = event["event_time"][:10]
    note_id = slugify(f"{event_date}-{event['subject_or_title']}-{event['source_id'][:8]}")
    return {
        "id": note_id,
        "title": event["subject_or_title"],
        "owner": "john",
        "primary-parent-type": primary_anchor["type"],
        "primary-parent": primary_anchor["record"]["link"],
        "secondary-links": secondary_links,
        "source": event["source_type"],
        "source-ref": drive_source_ref(event["source_id"], event["event_time"]),
        "date-created": iso_today(),
        "date-modified": iso_today(),
    }


def build_note_body(event):
    source_summary = summarize_text(event.get("body_text") or event.get("snippet", ""), 1400)
    lines = [
        f"# **Note: {event['subject_or_title']}**",
        "",
        "## **Context**",
        source_summary or "Imported from labeled Google Drive document.",
        "",
        "## **Implications**",
        f"- Source document: {event.get('source_link', '')}".rstrip(),
        f"- Updated: {event.get('event_time', '')[:10]}".rstrip(),
        "",
    ]
    return "\n".join(lines)


def maybe_write_note(event, primary_anchor, secondary_links, crm_index):
    if already_ingested_drive_doc(crm_index, event["source_id"], event.get("source_link", ""), event["event_time"]):
        return {"written": False, "duplicate": True}
    frontmatter = build_note_frontmatter(event, primary_anchor, secondary_links)
    file_name = f"{frontmatter['id']}.md"
    note_dir = os.path.join(CRM_DATA_PATH, "Notes")
    file_path = bucketed_record_path(note_dir, event["event_time"][:10], file_name)
    body = build_note_body(event)
    write_frontmatter_file(file_path, frontmatter, body)
    record = {
        "type": "Note",
        "file_path": file_path,
        "rel_path": os.path.relpath(file_path, CRM_DATA_PATH),
        "link": wikilink_for_path(file_path),
        "frontmatter": frontmatter,
        "body": body,
        "name": frontmatter["title"],
    }
    crm_index.notes.append(record)
    crm_index.mark_drive_ingestion(frontmatter["source-ref"], sort_timestamp(event["event_time"]))
    crm_index.mark_drive_ingestion(event["source_id"], sort_timestamp(event["event_time"]))
    if event.get("source_link"):
        crm_index.mark_drive_ingestion(event["source_link"], sort_timestamp(event["event_time"]))
    return {"written": True, "duplicate": False, "record": record}


def extract_json_payload(text):
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty JSON payload")
    fence_match = re.search(r"```(?:json)?\s*(.+?)```", raw, re.DOTALL | re.I)
    if fence_match:
        raw = fence_match.group(1).strip()
    for candidate in (raw,):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    bounds = []
    if "{" in raw and "}" in raw:
        bounds.append((raw.find("{"), raw.rfind("}") + 1))
    if "[" in raw and "]" in raw:
        bounds.append((raw.find("["), raw.rfind("]") + 1))
    for start, end in bounds:
        snippet = raw[start:end].strip()
        if not snippet:
            continue
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            continue
    raise ValueError("unable to parse JSON payload from Codex output")


def run_codex(prompt, timeout_seconds=GRANOLA_POST_INGEST_TIMEOUT_SECONDS):
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as handle:
            output_path = handle.name
        result = subprocess.run(
            [
                "codex",
                "-a",
                "never",
                "exec",
                "-C",
                PROJECT_ROOT,
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--output-last-message",
                output_path,
                prompt,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            error_text = result.stderr.strip() or result.stdout.strip() or "codex exec failed"
            raise RuntimeError(error_text)
        with open(output_path, "r", encoding="utf-8") as handle:
            return handle.read()
    finally:
        if output_path and os.path.exists(output_path):
            os.unlink(output_path)


def granola_activity_source_ref(meeting_date, title):
    return f"granola:{meeting_date}:{slugify(title)}"


def granola_task_source_ref(meeting_date, title, action_item):
    return f"{granola_activity_source_ref(meeting_date, title)}:task:{slugify(action_item)[:48]}"


def normalize_iso_datetime(value, fallback_date):
    text = str(value or "").strip()
    if not text:
        text = str(fallback_date)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{text}T12:00:00+00:00"
    if text.endswith("Z"):
        return text.replace("Z", "+00:00")
    return text


def normalize_granola_meetings(payload):
    if isinstance(payload, dict):
        meetings = payload.get("meetings") or payload.get("items") or []
    elif isinstance(payload, list):
        meetings = payload
    else:
        meetings = []

    normalized = []
    for item in meetings:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        meeting_date = str(item.get("date") or item.get("meeting_date") or "").strip()[:10]
        if not title or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meeting_date):
            continue
        attendees = []
        for attendee in item.get("attendees") or []:
            name = str(attendee or "").strip()
            if name and name not in attendees:
                attendees.append(name)
        action_items = []
        for action_item in item.get("action_items") or []:
            text = str(action_item or "").strip().strip("-").strip()
            if text and text not in action_items:
                action_items.append(text.rstrip(".") + ("." if not text.endswith(".") else ""))
        summary = str(item.get("summary") or "").strip()
        notes_url = str(item.get("notes_url") or item.get("source_link") or item.get("url") or "").strip()
        normalized.append(
            {
                "title": title,
                "date": meeting_date,
                "attendees": attendees,
                "summary": summary,
                "action_items": action_items,
                "notes_url": notes_url,
                "event_time": normalize_iso_datetime(item.get("event_time"), meeting_date),
            }
        )
    return normalized


def fetch_granola_meetings(since_date, until_date):
    prompt = (
        "Use the connected Granola MCP.\n"
        f"Find CRM-relevant meetings from {since_date} through {until_date} inclusive.\n"
        "Return JSON only with this shape: "
        '{"meetings":[{"title":"", "date":"YYYY-MM-DD", "attendees":[""], "summary":"", "action_items":[""], "notes_url":""}]}. '
        "Only include meetings likely relevant to business, relationship, fundraising, advisory, or deal work. "
        "For action_items, include only clear follow-up items John Januszczak should own or actively track. "
        'Use [] when there are no such action items. Use "" when the notes URL is unavailable. Do not include markdown or commentary.'
    )
    return normalize_granola_meetings(extract_json_payload(run_codex(prompt)))


def granola_event_from_meeting(meeting):
    attendees = [{"email": "", "name": name, "role": "attendee"} for name in meeting.get("attendees", [])]
    summary = str(meeting.get("summary") or "").strip()
    action_items = [str(item).strip() for item in meeting.get("action_items", []) if str(item).strip()]
    body_parts = []
    if summary:
        body_parts.append(summary)
    if attendees:
        body_parts.append("Attendees: " + ", ".join(name["name"] for name in attendees))
    if action_items:
        body_parts.append("Action items:\n" + "\n".join(f"- {item}" for item in action_items))
    source_ref = granola_activity_source_ref(meeting["date"], meeting["title"])
    return {
        "source_type": "granola",
        "source_id": source_ref,
        "source_link": meeting.get("notes_url", ""),
        "thread_id": None,
        "event_time": meeting.get("event_time", normalize_iso_datetime("", meeting["date"])),
        "direction": "meeting",
        "participants": attendees,
        "subject_or_title": meeting["title"],
        "body_text": "\n\n".join(part for part in body_parts if part),
        "snippet": summarize_text(summary, 160),
        "attachment_names": [],
        "raw_payload_ref": meeting.get("notes_url") or source_ref,
        "_granola_summary": summary,
        "_granola_action_items": action_items,
    }


GRANOLA_GENERIC_ANCHOR_TOKENS = {
    "account",
    "advisory",
    "bank",
    "buyer",
    "capital",
    "company",
    "contact",
    "corporation",
    "development",
    "energy",
    "finance",
    "financial",
    "funding",
    "global",
    "group",
    "international",
    "investment",
    "limited",
    "management",
    "meeting",
    "opportunity",
    "partners",
    "real",
    "sale",
    "security",
    "services",
    "systems",
    "transaction",
    "ventures",
}


def granola_anchor_for_event(event, crm_index):
    attendee_text = " ".join(participant.get("name", "") for participant in event.get("participants", []))
    title = event.get("subject_or_title", "")
    body_text = event.get("body_text", "")
    combined = f"{title}\n{body_text}\n{attendee_text}".lower()
    combined_tokens = set(search_tokens(combined, limit=80)) - GRANOLA_GENERIC_ANCHOR_TOKENS
    candidates = []
    seen = set()
    type_priority = {"opportunity": 0, "contact": 1, "lead": 2, "account": 3, "organization": 4, "deal": 5}

    for record in crm_index.all_records:
        record_type = str(record.get("type", "")).lower()
        if record_type not in type_priority or record["link"] in seen:
            continue
        seen.add(record["link"])
        name = str(record.get("name", "")).strip()
        if not name:
            continue
        lowered_name = name.lower()
        exact_name_match = bool(lowered_name and lowered_name in combined)
        name_tokens = set(search_tokens(name, limit=10)) - GRANOLA_GENERIC_ANCHOR_TOKENS
        overlap = combined_tokens & name_tokens
        if not exact_name_match and len(overlap) < 2:
            continue
        score = (6 if exact_name_match else 0) + len(overlap)
        candidates.append((score, type_priority[record_type], record))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]["name"]))
    record = candidates[0][2]
    return {"type": str(record.get("type", "")).lower(), "record": record}


def granola_secondary_links(primary_anchor, crm_index):
    if not primary_anchor:
        return []
    links = []
    record = primary_anchor["record"]
    frontmatter = record.get("frontmatter", {})
    if primary_anchor["type"] == "contact":
        if frontmatter.get("account"):
            links.append(frontmatter.get("account"))
        for variant in link_variants(record["link"]):
            for opportunity in crm_index.opportunities_by_contact.get(variant, []):
                links.append(opportunity["link"])
    elif primary_anchor["type"] == "opportunity":
        for field in ["primary-contact", "organization", "account"]:
            if frontmatter.get(field):
                links.append(frontmatter.get(field))
        for influencer in as_list(frontmatter.get("influencers")):
            links.append(influencer)
    elif primary_anchor["type"] == "account" and frontmatter.get("organization"):
        links.append(frontmatter.get("organization"))
    unique = []
    seen = set()
    for link in links:
        normalized = normalize_link(link)
        if not normalized or normalized == normalize_link(record["link"]) or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(f"[[{normalized}]]" if not str(link).startswith("[[") else str(link))
    return unique[:8]


def granola_activity_body(event, participants):
    summary = str(event.get("_granola_summary") or "").strip()
    action_items = list(event.get("_granola_action_items", []))
    participant_names = ", ".join(participants) if participants else "Not available"
    lines = [
        f"# **Activity: {event['subject_or_title']}**",
        "",
        "## **Executive Summary / Objective**",
        summary or "Granola meeting imported during post-ingest CRM enrichment.",
        "",
        "## **Outcomes**",
        f"- [x] Logged Granola meeting dated {event['event_time'][:10]}.",
    ]
    if action_items:
        lines.append(f"- [x] Captured {len(action_items)} Granola follow-up item(s).")
    lines.extend(
        [
            "",
            "## **Detailed Notes**",
            f"* **Participants:** {participant_names}.",
        ]
    )
    if summary:
        lines.append(f"* **Meeting Summary:** {summary}")
    if event.get("source_link"):
        lines.append(f"* **Granola Notes:** {event['source_link']}")
    if action_items:
        lines.extend(["", "## **Action Items**"])
        for item in action_items:
            lines.append(f"- [ ] {item}")
    lines.extend(["", "## **Strategic Insights**", "Imported from Granola after the normal Gmail / Calendar / Drive ingest pass."])
    return "\n".join(lines).rstrip() + "\n"


def unique_record_path(base_dir, record_date, record_id):
    candidate_id = record_id
    suffix = 2
    while True:
        file_path = bucketed_record_path(base_dir, record_date, f"{candidate_id}.md")
        if not os.path.exists(file_path):
            return candidate_id, file_path
        candidate_id = f"{record_id}-{suffix}"
        suffix += 1


def write_granola_activity(event, primary_anchor, secondary_links, crm_index):
    source_ref = granola_activity_source_ref(event["event_time"][:10], event["subject_or_title"])
    existing = crm_index.activity_source_refs.get(source_ref, [])
    if existing:
        return {"written": False, "duplicate": True, "record": existing[0]}

    frontmatter = {
        "id": "",
        "activity-name": event["subject_or_title"],
        "activity-type": "meeting",
        "status": "completed",
        "owner": "john",
        "date": event["event_time"][:10],
        "primary-parent-type": primary_anchor["type"],
        "primary-parent": primary_anchor["record"]["link"],
        "secondary-links": secondary_links,
        "source": "granola",
        "source-ref": source_ref,
        "email-link": "",
        "meeting-notes": event.get("source_link", ""),
        "date-created": iso_today(),
        "date-modified": iso_today(),
    }
    activity_dir = os.path.join(CRM_DATA_PATH, "Activities")
    record_id, file_path = unique_record_path(activity_dir, frontmatter["date"], dated_record_id(frontmatter["date"], event["subject_or_title"]))
    frontmatter["id"] = record_id
    body = granola_activity_body(event, [participant.get("name", "") for participant in event.get("participants", []) if participant.get("name")])
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Activity",
        title=frontmatter["activity-name"],
        path=file_path,
        source=frontmatter["source"],
        related=[frontmatter["primary-parent"]] + list(frontmatter.get("secondary-links", []) or []),
        details="activity-type=meeting; status=completed; granola-post-ingest=true",
        crm_data_path=CRM_DATA_PATH,
    )
    record = {
        "type": "Activity",
        "file_path": file_path,
        "rel_path": os.path.relpath(file_path, CRM_DATA_PATH),
        "link": wikilink_for_path(file_path),
        "frontmatter": frontmatter,
        "body": body,
        "name": frontmatter["activity-name"],
    }
    crm_index.activities.append(record)
    crm_index.activity_source_refs.setdefault(source_ref, []).append(record)
    activity_key = activity_dedupe_key("granola", source_ref, frontmatter["primary-parent"])
    crm_index.activity_dedupe[activity_key] = record
    return {"written": True, "duplicate": False, "record": record}


def granola_task_title(action_item):
    text = str(action_item or "").strip().lstrip("-").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    return text[0].upper() + text[1:]


def granola_task_status_and_due(meeting_date, action_item):
    text = str(action_item or "").lower()
    meeting_day = datetime.strptime(meeting_date, "%Y-%m-%d").date()
    today = date.today()
    if re.search(r"\b(track|monitor|check back|review|watch|wait)\b", text):
        days = 30 if re.search(r"\b30[- ]day|\b30 days?\b|\bnext 30 days?\b", text) else 7
        return "waiting", max(today, meeting_day + timedelta(days=days)).strftime("%Y-%m-%d")
    return "todo", max(today, meeting_day + timedelta(days=2)).strftime("%Y-%m-%d")


def granola_task_parent(anchor, secondary_links, crm_index):
    if anchor and anchor["type"] in {"opportunity", "contact", "account", "lead", "deal"}:
        return anchor
    preferred = {"opportunity": 0, "contact": 1, "account": 2, "lead": 3, "deal": 4}
    for link in secondary_links:
        normalized = normalize_link(link)
        record = crm_index.linked_records.get(next(iter(link_variants(normalized)), ""), None)
        if not record:
            continue
        record_type = str(record.get("type", "")).lower()
        if record_type in preferred:
            return {"type": record_type, "record": record}
    return None


def task_anchor_variants(task_record):
    variants = set()
    for field in ["primary-parent", "account", "contact", "opportunity", "lead"]:
        variants.update(link_variants(task_record.get("frontmatter", {}).get(field)))
    return {variant for variant in variants if variant}


def granola_task_duplicate(crm_index, task_name, task_source_ref, meeting_source_ref, anchor_links):
    if task_source_ref in crm_index.task_source_refs:
        return crm_index.task_source_refs[task_source_ref][0]
    target_tokens = TaskAnalyzer._relevance_tokens(task_name)
    meeting_related = crm_index.task_source_refs.get(meeting_source_ref, [])
    candidates = list(meeting_related) + list(crm_index.task_records)
    seen = set()
    for task in candidates:
        if task["file_path"] in seen:
            continue
        seen.add(task["file_path"])
        if anchor_links and not (task_anchor_variants(task) & anchor_links):
            continue
        existing_name = str(task.get("name", "")).strip()
        overlap = target_tokens & TaskAnalyzer._relevance_tokens(existing_name)
        if len(overlap) >= 2:
            return task
    return None


def granola_task_body(task_name, meeting, activity_link):
    summary = str(meeting.get("summary") or "").strip()
    context = [f"Granola notes from the {meeting['date']} meeting '{meeting['title']}'."]
    if summary:
        context.append(summary)
    notes = []
    if activity_link:
        notes.append(f"Related activity: {activity_link}.")
    if meeting.get("notes_url"):
        notes.append(f"Granola notes: {meeting['notes_url']}.")
    body = "\n".join(
        [
            f"# **Task: {task_name}**",
            "",
            "## **Description**",
            task_name,
            "",
            "## **Context & Background**",
            " ".join(context).strip(),
            "",
            "## **Notes / Updates**",
            ("*   " + " ".join(notes).strip()) if notes else "",
            "",
            "## **Outcome / Completion Notes**",
            "",
            "",
        ]
    )
    return body


def write_granola_task(meeting, action_item, parent_anchor, secondary_links, crm_index, activity_link=""):
    task_name = granola_task_title(action_item)
    if not task_name:
        return {"written": False, "duplicate": False, "reason": "blank_task"}
    source_ref = granola_task_source_ref(meeting["date"], meeting["title"], task_name)
    meeting_source_ref = granola_activity_source_ref(meeting["date"], meeting["title"])
    anchor_links = set(link_variants(parent_anchor["record"]["link"]))
    for link in secondary_links:
        anchor_links.update(link_variants(link))
    duplicate = granola_task_duplicate(crm_index, task_name, source_ref, meeting_source_ref, anchor_links)
    if duplicate:
        return {"written": False, "duplicate": True, "record": duplicate}

    status, due_date = granola_task_status_and_due(meeting["date"], task_name)
    frontmatter = {
        "id": "",
        "task-name": task_name,
        "status": status,
        "priority": "medium",
        "owner": "john",
        "due-date": due_date,
        "date-created": iso_today(),
        "date-modified": iso_today(),
        "primary-parent-type": parent_anchor["type"],
        "primary-parent": parent_anchor["record"]["link"],
        "account": "",
        "contact": "",
        "opportunity": "",
        "lead": "",
        "type": "follow-up",
        "source": "granola",
        "source-ref": source_ref,
        "google-task-id": "",
        "google-task-list-id": "",
        "email-link": "",
        "meeting-notes": meeting.get("notes_url", ""),
    }
    if parent_anchor["type"] == "account":
        frontmatter["account"] = parent_anchor["record"]["link"]
    elif parent_anchor["type"] == "contact":
        frontmatter["contact"] = parent_anchor["record"]["link"]
        account_link = parent_anchor["record"]["frontmatter"].get("account")
        if account_link:
            frontmatter["account"] = account_link
    elif parent_anchor["type"] == "opportunity":
        frontmatter["opportunity"] = parent_anchor["record"]["link"]
        contact_link = parent_anchor["record"]["frontmatter"].get("primary-contact")
        account_link = parent_anchor["record"]["frontmatter"].get("account")
        if contact_link:
            frontmatter["contact"] = contact_link
        if account_link:
            frontmatter["account"] = account_link
    elif parent_anchor["type"] == "lead":
        frontmatter["lead"] = parent_anchor["record"]["link"]
    task_dir = os.path.join(CRM_DATA_PATH, "Tasks")
    record_id, file_path = unique_record_path(task_dir, due_date, dated_record_id(due_date, task_name))
    frontmatter["id"] = record_id
    body = granola_task_body(task_name, meeting, activity_link)
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Task",
        title=frontmatter["task-name"],
        path=file_path,
        source=frontmatter["source"],
        related=[
            frontmatter.get("primary-parent", ""),
            frontmatter.get("account", ""),
            frontmatter.get("contact", ""),
            frontmatter.get("opportunity", ""),
            frontmatter.get("lead", ""),
        ],
        details=f"status={status}; priority=medium; due-date={due_date}; granola-post-ingest=true",
        crm_data_path=CRM_DATA_PATH,
    )
    record = {
        "type": "Task",
        "file_path": file_path,
        "rel_path": os.path.relpath(file_path, CRM_DATA_PATH),
        "link": wikilink_for_path(file_path),
        "frontmatter": frontmatter,
        "body": body,
        "name": frontmatter["task-name"],
    }
    crm_index.task_records.append(record)
    crm_index.task_source_refs.setdefault(source_ref, []).append(record)
    return {"written": True, "duplicate": False, "record": record}


def process_granola_post_ingest(args, crm_index, state):
    granola_updates = []
    if args.skip_granola or not granola_post_ingest_enabled():
        return granola_updates, False

    now = datetime.now(UTC).replace(microsecond=0)
    if args.since:
        since_date = args.since
    else:
        checkpoint = str(state.get("granola_last_sync_at") or "").strip()
        if checkpoint:
            since_date = checkpoint[:10]
        else:
            since_date = (now.date() - timedelta(days=granola_initial_lookback_days())).strftime("%Y-%m-%d")

    try:
        meetings = fetch_granola_meetings(since_date, now.date().strftime("%Y-%m-%d"))
    except Exception as exc:
        granola_updates.append({"status": "error", "reason": str(exc), "since_date": since_date})
        save_json(GRANOLA_UPDATES_PATH, granola_updates)
        return granola_updates, False

    for meeting in meetings:
        event = granola_event_from_meeting(meeting)
        source_ref = granola_activity_source_ref(meeting["date"], meeting["title"])
        primary_anchor = granola_anchor_for_event(event, crm_index)
        if not primary_anchor:
            granola_updates.append(
                {
                    "title": meeting["title"],
                    "date": meeting["date"],
                    "status": "skipped_unanchored",
                    "source_ref": source_ref,
                }
            )
            continue

        secondary_links = granola_secondary_links(primary_anchor, crm_index)
        activity_result = write_granola_activity(event, primary_anchor, secondary_links, crm_index)
        task_parent = granola_task_parent(primary_anchor, secondary_links, crm_index)
        task_results = []
        for action_item in meeting.get("action_items", []):
            if not task_parent:
                task_results.append({"task": action_item, "status": "skipped_no_task_parent"})
                continue
            task_result = write_granola_task(
                meeting,
                action_item,
                task_parent,
                secondary_links,
                crm_index,
                activity_link=activity_result.get("record", {}).get("link", ""),
            )
            if task_result.get("written"):
                task_results.append({"task": action_item, "status": "task_created", "path": task_result["record"]["rel_path"]})
            elif task_result.get("duplicate"):
                task_results.append({"task": action_item, "status": "duplicate_task", "path": task_result["record"]["rel_path"]})
            else:
                task_results.append({"task": action_item, "status": task_result.get("reason", "skipped")})

        granola_updates.append(
            {
                "title": meeting["title"],
                "date": meeting["date"],
                "status": "activity_created" if activity_result.get("written") else "duplicate_activity",
                "source_ref": source_ref,
                "primary_parent": primary_anchor["record"]["link"],
                "activity_path": activity_result.get("record", {}).get("rel_path", ""),
                "tasks": task_results,
            }
        )

    save_json(GRANOLA_UPDATES_PATH, granola_updates)
    state["granola_last_sync_at"] = now.isoformat().replace("+00:00", "Z")
    return granola_updates, True


def process_whatsapp_post_ingest(
    args,
    crm_index,
    state,
    resolver,
    inferrer,
    task_analyzer,
    meeting_notes_resolver,
    activity_updates,
    contact_discoveries,
    lead_decisions,
    opportunity_suggestions,
    task_suggestions,
    noise_review,
    audit_log,
    interactions,
):
    whatsapp_updates = []
    if args.skip_whatsapp or not whatsapp_post_ingest_enabled():
        return whatsapp_updates, False

    now = datetime.now(UTC).replace(microsecond=0)
    if args.since:
        since_date = args.since
        since_dt = datetime.fromisoformat(f"{args.since}T00:00:00+00:00")
        start_rowid = 0
        bootstrap_full_history = False
    else:
        checkpoint = str(state.get("whatsapp_last_sync_at") or "").strip()
        if checkpoint:
            since_date = checkpoint[:10]
            since_dt = datetime.fromisoformat(f"{since_date}T00:00:00+00:00")
            start_rowid = int(state.get("whatsapp_last_rowid") or 0)
            bootstrap_full_history = False
        else:
            since_date = "1970-01-01"
            since_dt = datetime.fromtimestamp(0, UTC)
            start_rowid = 0
            bootstrap_full_history = True

    adapter = WacliAdapter(account=whatsapp_account_name(), store_dir=whatsapp_store_dir())
    try:
        doctor = adapter.doctor()
    except Exception as exc:
        whatsapp_updates.append({"status": "unavailable", "reason": str(exc), "since_date": since_date})
        save_json(WHATSAPP_UPDATES_PATH, whatsapp_updates)
        return whatsapp_updates, False

    last_rowid = start_rowid
    rows = []
    try:
        while True:
            batch = adapter.fetch_messages(last_rowid, int(since_dt.timestamp()), limit=500)
            if not batch:
                break
            rows.extend(batch)
            last_rowid = max(last_rowid, int(batch[-1].get("rowid") or 0))
            if len(batch) < 500:
                break
    except Exception as exc:
        whatsapp_updates.append({"status": "error", "reason": str(exc), "since_date": since_date})
        save_json(WHATSAPP_UPDATES_PATH, whatsapp_updates)
        return whatsapp_updates, False

    thread_history = {}
    for row in rows:
        event = EventNormalizer.normalize_whatsapp_message(row, adapter.account)
        history = thread_history.setdefault(event["thread_id"], [])
        event["_thread_context"] = build_thread_context(history) if history else {}
        before_counts = (
            len(activity_updates),
            len(contact_discoveries),
            len(lead_decisions),
            len(opportunity_suggestions),
            len(task_suggestions),
        )
        process_ingest_event(
            event,
            args,
            crm_index,
            resolver,
            inferrer,
            task_analyzer,
            meeting_notes_resolver,
            activity_updates,
            contact_discoveries,
            lead_decisions,
            opportunity_suggestions,
            task_suggestions,
            noise_review,
            audit_log,
            interactions,
        )
        history.append(
            {
                "subject_or_title": event.get("subject_or_title", ""),
                "body_text": event.get("body_text", ""),
                "snippet": event.get("snippet", ""),
                "direction": event.get("direction", ""),
                "attachment_names": list(event.get("attachment_names", []) or []),
            }
        )
        after_counts = (
            len(activity_updates),
            len(contact_discoveries),
            len(lead_decisions),
            len(opportunity_suggestions),
            len(task_suggestions),
        )
        deltas = [after - before for before, after in zip(before_counts, after_counts)]
        status = "reviewed_no_change"
        if any(delta > 0 for delta in deltas):
            status = "staged_or_written"
        whatsapp_updates.append(
            {
                "rowid": int(row.get("rowid") or 0),
                "chat_jid": str(row.get("chat_jid") or ""),
                "msg_id": str(row.get("msg_id") or ""),
                "event_time": event["event_time"],
                "title": event["subject_or_title"],
                "status": status,
                "changes": {
                    "activity_updates": deltas[0],
                    "contact_discoveries": deltas[1],
                    "lead_decisions": deltas[2],
                    "opportunity_suggestions": deltas[3],
                    "task_suggestions": deltas[4],
                },
            }
        )

    state["whatsapp_last_sync_at"] = now.isoformat().replace("+00:00", "Z")
    state["whatsapp_last_rowid"] = last_rowid
    save_json(
        WHATSAPP_UPDATES_PATH,
        {
            "status": "ok",
            "since_date": since_date,
            "bootstrap_full_history": bootstrap_full_history,
            "account": adapter.account,
            "store_dir": adapter.store_dir,
            "doctor": doctor,
            "messages_scanned": len(rows),
            "last_rowid": last_rowid,
            "updates": whatsapp_updates,
        },
    )
    return whatsapp_updates, True


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
    domain = domain_from_email(participant.get("email", ""))
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
    if looks_like_noise_message(event):
        return "ignore"
    if anchor_type == "lead":
        return "new_contact_for_existing_lead_context"
    if anchor_type in {"opportunity", "account", "organization", "contact"}:
        if domain and domain not in anchor_domains:
            return "create_contact_and_flag_secondary_lead"
        return "attach_contact_to_existing_relationship"
    return "create_lead"


def build_contact_discovery(event, participant, action_type, anchor):
    participant_identity = interaction_identity(participant)
    payload = {
        "proposal_group_id": proposal_group_id(event, participant_identity),
        "source_event_id": event["source_id"],
        "source_type": event["source_type"],
        "source_link": event["source_link"],
        "event_time": event["event_time"],
        "action_type": action_type,
        "proposed_contact_name": participant.get("name") or participant_identity,
        "email": participant.get("email", ""),
        "phone": normalize_phone_number(participant.get("phone", "")),
        "participant_identity": participant_identity,
        "inferred_company_context": domain_from_email(participant.get("email", "")),
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
    participant_identity = interaction_identity(participant)
    payload = {
        "proposal_group_id": proposal_group_id(event, participant_identity),
        "source_event_id": event["source_id"],
        "source_type": event["source_type"],
        "source_link": event["source_link"],
        "event_time": event["event_time"],
        "decision_type": decision_type,
        "participant_email": participant.get("email", ""),
        "participant_phone": normalize_phone_number(participant.get("phone", "")),
        "participant_identity": participant_identity,
        "participant_name": participant.get("name") or participant_identity,
        "anchor": anchor,
        "source_event_summary": summarize_text(event.get("body_text") or event.get("snippet", ""), 260),
        "meeting_notes_summary": NotesAnalyzer.get_note_summary(event),
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
        "meeting_notes_summary": NotesAnalyzer.get_note_summary(event),
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
        "meeting_notes_summary": NotesAnalyzer.get_note_summary(event),
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
        identity = str(participant.get("email") or participant.get("phone") or participant.get("jid") or "").lower()
        if not identity or resolver.classify_participant(participant) == "self":
            continue
        result.append(participant)
    return result


def likely_calendar_relevant(event, resolutions):
    if is_relationship_relevant(event, resolutions):
        return True
    attendees = [p for p in event["participants"] if p.get("email") and domain_from_email(p["email"]) not in {"gmail.com", "icloud.com"}]
    return len(attendees) >= 2


def likely_whatsapp_relevant(event, resolutions):
    if event.get("chat_kind") == "channel":
        return False
    if any(resolution["status"] == "matched" for resolution in resolutions):
        return True
    if event.get("chat_kind") == "group":
        return False
    text = "\n".join(
        [
            str(event.get("subject_or_title", "")),
            str(event.get("body_text", "")),
            str(event.get("snippet", "")),
            whatsapp_thread_context_text(event),
        ]
    )
    if professional_signal_count(text) >= 2:
        return True
    if professional_signal_count(text) >= 1 and TaskAnalyzer.extract_action_items(text):
        return True
    return False


def should_stage_whatsapp_unknown_participant(event, primary_anchor, signals, participant):
    if event.get("source_type") != "whatsapp":
        return True
    if event.get("chat_kind") == "group":
        return bool(primary_anchor)
    if primary_anchor:
        return True
    if participant.get("is_self"):
        return False
    # For direct chats without an existing CRM anchor, require clear business evidence.
    if "commercial_intent" not in signals:
        return False
    if "commitment_detected" not in signals and "logistics_detected" not in signals:
        return False
    return professional_signal_count(event.get("body_text", "") or event.get("snippet", "")) >= 2


def interaction_identity(participant):
    return str(participant.get("email") or participant.get("phone") or participant.get("jid") or "").lower().strip()


def record_interaction(interactions, identity, event_date):
    if not identity:
        return
    item = interactions.setdefault(identity, {"last_date": event_date, "hits_last_7_days": 0})
    if event_date > item.get("last_date", ""):
        item["last_date"] = event_date
    if event_date >= (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"):
        item["hits_last_7_days"] = int(item.get("hits_last_7_days", 0)) + 1


def process_ingest_event(
    event,
    args,
    crm_index,
    resolver,
    inferrer,
    task_analyzer,
    meeting_notes_resolver,
    activity_updates,
    contact_discoveries,
    lead_decisions,
    opportunity_suggestions,
    task_suggestions,
    noise_review,
    audit_log,
    interactions,
):
    audit_log["scanned"] += 1
    for participant in event["participants"]:
        record_interaction(interactions, interaction_identity(participant), event["event_time"][:10])

    participants = external_participants(event, resolver)
    resolutions = [resolver.resolve_participant(participant) for participant in participants]

    if event["source_type"] == "calendar" and not likely_calendar_relevant(event, resolutions):
        audit_log["ignored"] += 1
        audit_log["actions"].append({"source_id": event["source_id"], "result": "ignored_calendar_noise"})
        return

    if event["source_type"] == "whatsapp" and not likely_whatsapp_relevant(event, resolutions):
        audit_log["ignored"] += 1
        audit_log["actions"].append({"source_id": event["source_id"], "result": "ignored_whatsapp_noise"})
        return

    primary_anchor = choose_primary_anchor(event, resolutions, crm_index)
    secondary_links = build_secondary_links(primary_anchor, resolutions)
    event["_notes_context"] = meeting_notes_resolver.resolve_for_event(event, primary_anchor, secondary_links)
    combined_text = NotesAnalyzer.combined_event_text(event)
    thread_context = whatsapp_thread_context_text(event)
    if thread_context:
        combined_text = f"{combined_text}\n\nThread context:\n{thread_context}".strip()
    signals = inferrer.infer_signals(combined_text, event.get("subject_or_title", ""), event.get("source_type", "gmail"))
    if NotesAnalyzer.get_note_links(event):
        signals.append("meeting_notes_detected")
    if event["_notes_context"].get("looked_up"):
        signals.append("drive_notes_lookup_attempted")

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
            "meeting_notes_summary": NotesAnalyzer.get_note_summary(event),
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
    for task in matched_tasks:
        completion_conf = task_analyzer.completion_confidence_for_task(event, task)
        if completion_conf < 0.65:
            continue
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

    if primary_anchor:
        for item in task_analyzer.extract_action_items(combined_text):
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
                        "email": participant.get("email", ""),
                        "reason": resolution["reason"],
                    }
                )
            else:
                audit_log["ignored"] += 1
            continue

        if resolution["status"] == "unknown":
            if not should_stage_whatsapp_unknown_participant(event, primary_anchor, signals, participant):
                audit_log["actions"].append(
                    {
                        "source_id": event["source_id"],
                        "participant": interaction_identity(participant),
                        "result": "ignored_whatsapp_unknown",
                    }
                )
                continue
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
            audit_log["actions"].append({"source_id": event["source_id"], "participant": interaction_identity(participant), "result": normalized_action})
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since")
    parser.add_argument("--autonomous", action="store_true")
    parser.add_argument("--auto-tier", type=int, default=0)
    parser.add_argument("--skip-granola", action="store_true")
    parser.add_argument("--skip-whatsapp", action="store_true")
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
    meeting_notes_resolver = DriveMeetingNotesResolver(crm_index)

    activity_updates = []
    contact_discoveries = []
    lead_decisions = []
    opportunity_suggestions = []
    task_suggestions = []
    noise_review = []
    drive_document_updates = []
    audit_log = {"scanned": 0, "ignored": 0, "actions": []}

    gmail_events = [EventNormalizer.normalize_gmail(message) for message in harvester.get_gmail_messages()]
    gmail_events.sort(key=lambda item: sort_timestamp(item.get("event_time", "")))
    thread_history = {}
    for event in gmail_events:
        thread_id = str(event.get("thread_id") or "")
        history = thread_history.setdefault(thread_id, []) if thread_id else []
        event["_thread_context"] = build_thread_context(history) if history else {}
        process_ingest_event(
            event,
            args,
            crm_index,
            resolver,
            inferrer,
            task_analyzer,
            meeting_notes_resolver,
            activity_updates,
            contact_discoveries,
            lead_decisions,
            opportunity_suggestions,
            task_suggestions,
            noise_review,
            audit_log,
            interactions,
        )
        if thread_id:
            history.append(
                {
                    "subject_or_title": event.get("subject_or_title", ""),
                    "body_text": event.get("body_text", ""),
                    "snippet": event.get("snippet", ""),
                    "direction": event.get("direction", ""),
                    "attachment_names": list(event.get("attachment_names", []) or []),
                }
            )

    for calendar_event in harvester.get_calendar_events():
        event = EventNormalizer.normalize_calendar(calendar_event)
        event["_thread_context"] = {}
        process_ingest_event(
            event,
            args,
            crm_index,
            resolver,
            inferrer,
            task_analyzer,
            meeting_notes_resolver,
            activity_updates,
            contact_discoveries,
            lead_decisions,
            opportunity_suggestions,
            task_suggestions,
            noise_review,
            audit_log,
            interactions,
        )

    try:
        calendar_cache_start = now - timedelta(days=1)
        calendar_cache_end = now + timedelta(days=14)
        calendar_cache_events = [
            EventNormalizer.normalize_calendar(calendar_event)
            for calendar_event in harvester.get_calendar_events_window(calendar_cache_start, calendar_cache_end)
        ]
        save_json(
            CALENDAR_EVENTS_CACHE_PATH,
            {
                "generated_at": now.isoformat().replace("+00:00", "Z"),
                "window_start": calendar_cache_start.isoformat().replace("+00:00", "Z"),
                "window_end": calendar_cache_end.isoformat().replace("+00:00", "Z"),
                "events": calendar_cache_events,
            },
        )
    except RuntimeError as exc:
        audit_log["actions"].append({"result": "calendar_cache_refresh_failed", "error": str(exc)})

    for file_item in harvester.get_labeled_drive_documents(resolve_crm_drive_label_ids()):
        file_id = str(file_item.get("id") or "").strip()
        modified_time = str(file_item.get("modifiedTime") or "").strip()
        if not file_id or not modified_time:
            continue

        if already_ingested_drive_doc(crm_index, file_id, str(file_item.get("webViewLink") or ""), modified_time):
            drive_document_updates.append(
                {
                    "file_id": file_id,
                    "title": str(file_item.get("name") or ""),
                    "modified_time": modified_time,
                    "status": "skipped_existing",
                }
            )
            continue

        try:
            doc_text = meeting_notes_resolver._docs_get_text(file_id)
        except RuntimeError:
            doc_text = ""

        event = EventNormalizer.normalize_drive_file(file_item, doc_text)
        event["_thread_context"] = {}
        primary_anchor = infer_anchor_from_text(event["subject_or_title"], event["body_text"], crm_index)
        if not primary_anchor:
            drive_document_updates.append(
                {
                    "file_id": file_id,
                    "title": event["subject_or_title"],
                    "modified_time": modified_time,
                    "status": "unresolved_anchor",
                }
            )
            continue

        resolutions = [
            {
                "status": "matched",
                "match_type": primary_anchor["type"],
                "participant": {"email": "", "name": ""},
                "record": primary_anchor["record"],
                "opportunities": [primary_anchor["record"]] if primary_anchor["type"] == "opportunity" else [],
            }
        ]
        secondary_links = build_secondary_links(primary_anchor, resolutions)
        event["_notes_context"] = {"links": [event["source_link"]] if event.get("source_link") else [], "summary": "", "text": event["body_text"], "looked_up": False}
        combined_text = NotesAnalyzer.combined_event_text(event)
        signals = inferrer.infer_signals(combined_text, event.get("subject_or_title", ""), "drive")
        action_items = task_analyzer.extract_action_items(combined_text)

        matched_tasks = task_analyzer.find_matching_tasks(set(link_variants(primary_anchor["record"]["link"])))
        for task in matched_tasks:
            completion_conf = task_analyzer.completion_confidence_for_task(event, task)
            if completion_conf < 0.65:
                continue
            task_suggestions.append(
                build_task_suggestion(
                    event,
                    primary_anchor["record"]["link"],
                    "task_completion_suggestion",
                    summarize_text(event.get("body_text") or event.get("snippet", ""), 200),
                    matched_task=task,
                    confidence=completion_conf,
                )
            )

        for item in action_items:
            task_type = "committed_action" if task_analyzer.looks_owner_assigned(item) else "suggested_follow_up"
            task_suggestions.append(build_task_suggestion(event, primary_anchor["record"]["link"], task_type, item))

        doc_kind = classify_drive_document(event, signals, action_items)
        if doc_kind == "activity":
            write_result = maybe_write_activity(event, primary_anchor, secondary_links, crm_index, resolutions)
            status = "duplicate_activity" if write_result.get("duplicate") else "activity_written"
        else:
            write_result = maybe_write_note(event, primary_anchor, secondary_links, crm_index)
            status = "duplicate_note" if write_result.get("duplicate") else "note_written"

        drive_document_updates.append(
            {
                "file_id": file_id,
                "title": event["subject_or_title"],
                "modified_time": modified_time,
                "status": status,
                "primary_parent": primary_anchor["record"]["link"],
                "task_suggestions_added": len(action_items),
            }
        )

    granola_updates, granola_ran = process_granola_post_ingest(args, crm_index, state)
    if not granola_ran and not os.path.exists(GRANOLA_UPDATES_PATH):
        save_json(GRANOLA_UPDATES_PATH, [])

    whatsapp_updates, whatsapp_ran = process_whatsapp_post_ingest(
        args,
        crm_index,
        state,
        resolver,
        inferrer,
        task_analyzer,
        meeting_notes_resolver,
        activity_updates,
        contact_discoveries,
        lead_decisions,
        opportunity_suggestions,
        task_suggestions,
        noise_review,
        audit_log,
        interactions,
    )
    if not whatsapp_ran and not os.path.exists(WHATSAPP_UPDATES_PATH):
        save_json(WHATSAPP_UPDATES_PATH, [])

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
    save_json(DRIVE_DOCUMENT_UPDATES_PATH, drive_document_updates)
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
                "granola_updates": len(granola_updates),
                "whatsapp_updates": len(whatsapp_updates),
                "status": "staged",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
