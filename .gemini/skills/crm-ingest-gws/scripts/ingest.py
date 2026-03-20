import argparse
import base64
import html
import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta

# --- Path resolution ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.abspath(os.path.join(SKILL_ROOT, "../../../"))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from frontmatter_utils import dated_record_id, load_frontmatter_file, slugify
except ImportError:
    def dated_record_id(event_date, title):
        return f"{event_date}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}"
    def load_frontmatter_file(path):
        return {}, ""
    def slugify(value):
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

# --- Configuration & Paths ---
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
WORKSPACE_UPDATES_PATH = os.path.join(STAGING_DIR, "workspace_updates.json")
DISCOVERY_PATH = os.path.join(STAGING_DIR, "discovery.json")
INGESTION_AUDIT_PATH = os.path.join(STAGING_DIR, "ingestion_audit.json")

# --- Utilities ---
def ensure_dirs():
    os.makedirs(STAGING_DIR, exist_ok=True)
    for d in ["Leads", "Activities", "Contacts", "Accounts", "Opportunities", "Tasks", "Notes", "Deal-Flow"]:
        os.makedirs(os.path.join(CRM_DATA_PATH, d), exist_ok=True)

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

def run_gws(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}

def parse_email_addresses(value):
    matches = re.findall(r"[\w.\-+%]+@[\w.\-]+\.\w+", value or "")
    return [match.lower() for match in matches]

def extract_message_text(payload):
    def _get_part(p, mt):
        if p.get("mimeType") == mt and p.get("body", {}).get("data"):
            data = p["body"]["data"]
            padded = data + "=" * (-len(data) % 4)
            return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
        for part in p.get("parts", []):
            extracted = _get_part(part, mt)
            if extracted: return extracted
        return ""
    plain = _get_part(payload, "text/plain")
    if plain: return plain
    html_text = _get_part(payload, "text/html")
    if html_text:
        without_tags = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
        without_tags = re.sub(r"<[^>]+>", "", without_tags)
        return html.unescape(without_tags)
    return ""

# --- Pipeline Components ---

class SourceHarvester:
    """Fetches Gmail and Calendar deltas."""
    def __init__(self, since_dt):
        self.since_dt = since_dt

    def get_gmail_messages(self):
        query = f"after:{int(self.since_dt.timestamp())}"
        resp = run_gws(["gws", "gmail", "users", "messages", "list", "--params", json.dumps({"userId": "me", "q": query, "maxResults": 50})])
        messages = []
        for m in resp.get("messages", []):
            detail = run_gws(["gws", "gmail", "users", "messages", "get", "--params", json.dumps({"userId": "me", "id": m["id"], "format": "full"})])
            if "error" not in detail:
                messages.append(detail)
        return messages

    def get_calendar_events(self):
        cal_since = self.since_dt.isoformat().replace("+00:00", "Z")
        resp = run_gws(["gws", "calendar", "events", "list", "--params", json.dumps({
            "calendarId": "primary", "timeMin": cal_since, "showDeleted": False, "singleEvents": True, "orderBy": "startTime"
        })])
        events = []
        for event in resp.get("items", []):
            updated = event.get("updated")
            if not updated or datetime.fromisoformat(updated.replace("Z", "+00:00")) > self.since_dt:
                events.append(event)
        return events

class EventNormalizer:
    """Maps source-specific JSON to a canonical WorkspaceEvent schema."""
    @staticmethod
    def normalize_gmail(msg):
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        from_raw = headers.get("From", "")
        emails = parse_email_addresses(from_raw)
        from_email = emails[0] if emails else ""
        
        return {
            "source_type": "gmail",
            "source_id": msg["id"],
            "source_link": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
            "thread_id": msg["threadId"],
            "event_time": datetime.fromtimestamp(int(msg.get("internalDate", 0))/1000, UTC).isoformat(),
            "direction": "inbound" if from_email != "operator@example.com" else "outbound",
            "participants": [{"email": from_email, "name": from_raw, "role": "sender"}],
            "subject_or_title": headers.get("Subject", "(no subject)"),
            "body_text": extract_message_text(msg.get("payload", {})),
            "snippet": msg.get("snippet", ""),
            "raw_payload_ref": msg["id"]
        }

    @staticmethod
    def normalize_calendar(event):
        participants = []
        for a in event.get("attendees", []):
            participants.append({
                "email": (a.get("email") or "").lower(),
                "name": a.get("displayName") or a.get("email"),
                "role": "attendee"
            })
        
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
            "snippet": event.get("description", "")[:100],
            "raw_payload_ref": event["id"]
        }

class EntityResolver:
    """Matches participants to CRM objects with confidence scoring."""
    def __init__(self, crm_index, noise_domains, noise_prefixes):
        self.index = crm_index
        self.noise_domains = noise_domains
        self.noise_prefixes = noise_prefixes

    def resolve_participant(self, email):
        email = email.lower()
        if not email or "@" not in email:
            return None, 0.0, "Invalid email"
            
        domain = email.split("@")[-1]
        local = email.split("@")[0]
        
        if domain in self.noise_domains or any(p in local for p in self.noise_prefixes):
            return None, 0.0, "Noise domain/prefix"

        # Tier A: Exact Match
        if email in self.index["opportunities"]:
            return {"type": "opportunity", "data": self.index["opportunities"][email]}, 1.0, "Exact email match to active opportunity"
        if email in self.index["contacts"]:
            return {"type": "contact", "data": self.index["contacts"][email]}, 1.0, "Exact email match to contact"
        if email in self.index["leads"]:
            return {"type": "lead", "data": self.index["leads"][email]}, 1.0, "Exact email match to lead"
            
        # Tier B: Domain Match to Account
        if domain in self.index["accounts"]:
            return {"type": "account", "data": self.index["accounts"][domain]}, 0.7, f"Matched domain @{domain} to existing Account"
        
        return None, 0.0, "No match found"

class InteractionInferrer:
    """Extracts facts and intent."""
    @staticmethod
    def infer_signals(text):
        signals = []
        # Commitment / Follow-up
        if re.search(r"follow up|next steps|please send|will send|get back to you|action item|task", text, re.I):
            signals.append("commitment_detected")
        
        # Introduction
        if re.search(r"meet|intro|introducing|connecting|connect with", text, re.I):
            signals.append("introduction_detected")
            
        # Commercial / Deal Intent
        if re.search(r"proposal|pricing|agreement|contract|investment|capital|series|deck|teaser|mandate", text, re.I):
            signals.append("commercial_intent")
            
        # Logistics / Meeting
        if re.search(r"schedule|calendar|availability|zoom|meet\.google|teams", text, re.I):
            signals.append("logistics_detected")
            
        return signals

def get_crm_index():
    index = {"contacts": {}, "leads": {}, "accounts": {}, "opportunities": {}}
    
    # Accounts
    accounts_dir = os.path.join(CRM_DATA_PATH, "Accounts")
    if os.path.exists(accounts_dir):
        for f in os.listdir(accounts_dir):
            if f.endswith(".md"):
                fm, _ = load_frontmatter_file(os.path.join(accounts_dir, f))
                url = fm.get("url", "")
                domain = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0] if url else ""
                if domain:
                    index["accounts"][domain.lower()] = {
                        "name": fm.get("company-name", f[:-3]),
                        "path": f"[[Accounts/{f[:-3]}]]"
                    }
    def _add_emails(dir_name, target_key, fm_name_key, path_prefix):
        dir_path = os.path.join(CRM_DATA_PATH, dir_name)
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.endswith(".md"):
                    fm, _ = load_frontmatter_file(os.path.join(dir_path, f))
                    emails = fm.get("email", [])
                    if isinstance(emails, str): emails = [emails]
                    for email in emails:
                        if email:
                            index[target_key][email.lower()] = {
                                "name": fm.get(fm_name_key, f[:-3]),
                                "path": f"[[{path_prefix}/{f[:-3]}]]",
                                "account": fm.get("account")
                            }

    _add_emails("Contacts", "contacts", "full-name", "Contacts")
    _add_emails("Leads", "leads", "lead-name", "Leads")

    opps_dir = os.path.join(CRM_DATA_PATH, "Opportunities")
    if os.path.exists(opps_dir):
        for f in os.listdir(opps_dir):
            if f.endswith(".md"):
                fm, _ = load_frontmatter_file(os.path.join(opps_dir, f))
                if fm.get("is-active", False):
                    contact = fm.get("primary-contact")
                    if contact:
                        for email, data in index["contacts"].items():
                            if data["path"] == contact:
                                index["opportunities"][email] = {"name": fm.get("opportunity-name", f[:-3]), "path": f"[[Opportunities/{f[:-3]}]]", "contact": contact}
    return index

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since")
    parser.add_argument("--autonomous", action="store_true")
    parser.add_argument("--auto-tier", type=int, default=0, help="Max automation tier (1: Safe-Auto, 2: Auto-with-Audit)")
    args = parser.parse_args()

    ensure_dirs()
    index = get_crm_index()
    noise_domains, noise_prefixes = load_json(NOISE_DOMAINS_PATH, {}).get("generic", []), load_json(NOISE_DOMAINS_PATH, {}).get("noise", [])
    state = load_json(SYNC_STATE_PATH, {"gmail_last_sync_at": "", "calendar_last_sync_at": ""})

    # Time window
    now = datetime.now(UTC).replace(microsecond=0)
    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=UTC)
    else:
        last = state.get("gmail_last_sync_at") or (now - timedelta(days=7)).isoformat()
        since_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))

    harvester = SourceHarvester(since_dt)
    resolver = EntityResolver(index, noise_domains, noise_prefixes)
    inferrer = InteractionInferrer()
    
    proposals = []
    discoveries = []
    audit_log = {"scanned": 0, "ignored": 0, "actions": []}
    interactions = load_json(os.path.join(STAGING_DIR, "interactions.json"), {})

    def upsert_interaction(email, event_date):
        if not email: return
        record = interactions.setdefault(email.lower(), {"last_date": event_date, "hits_last_7_days": 0})
        record["last_date"] = max(record.get("last_date", event_date), event_date)
        if event_date >= (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"):
            record["hits_last_7_days"] = int(record.get("hits_last_7_days", 0)) + 1

    # Process Gmail
    for msg in harvester.get_gmail_messages():
        audit_log["scanned"] += 1
        event = EventNormalizer.normalize_gmail(msg)
        from_email = event["participants"][0]["email"]
        event_date = event["event_time"][:10]
        
        upsert_interaction(from_email, event_date)
        
        match, confidence, reason = resolver.resolve_participant(from_email)
        
        # Determine Tier
        tier = 3 # Default: Approval Required
        if confidence == 1.0: tier = 1
        elif confidence >= 0.7: tier = 2

        if confidence > 0:
            signals = inferrer.infer_signals(event["body_text"])
            proposals.append({
                "action_type": "activity_proposal",
                "source_event": event,
                "confidence": confidence,
                "match": match,
                "rationale": reason,
                "signals": signals,
                "tier": tier,
                "auto_execute": args.autonomous or args.auto_tier >= tier
            })
        elif reason == "No match found":
            discoveries.append(event)
        else:
            audit_log["ignored"] += 1

    # Process Calendar
    for cal_event in harvester.get_calendar_events():
        audit_log["scanned"] += 1
        event = EventNormalizer.normalize_calendar(cal_event)
        event_date = event["event_time"][:10]
        
        matched_any = False
        for p in event["participants"]:
            email = p["email"]
            upsert_interaction(email, event_date)
            
            match, confidence, reason = resolver.resolve_participant(email)
            
            # Determine Tier
            tier = 3
            if confidence == 1.0: tier = 1
            elif confidence >= 0.7: tier = 2

            if confidence > 0:
                signals = inferrer.infer_signals(event["body_text"])
                proposals.append({
                    "action_type": "activity_proposal",
                    "source_event": event,
                    "confidence": confidence,
                    "match": match,
                    "rationale": reason,
                    "signals": signals,
                    "tier": tier,
                    "auto_execute": args.autonomous or args.auto_tier >= tier
                })
                matched_any = True
                break
        
        if not matched_any:
            discoveries.append(event)

    # Save results
    save_json(WORKSPACE_UPDATES_PATH, proposals)
    save_json(DISCOVERY_PATH, discoveries)
    save_json(INGESTION_AUDIT_PATH, audit_log)
    save_json(os.path.join(STAGING_DIR, "interactions.json"), interactions)
    
    # Update state
    state["gmail_last_sync_at"] = now.isoformat().replace("+00:00", "Z")
    state["calendar_last_sync_at"] = now.isoformat().replace("+00:00", "Z")
    save_json(SYNC_STATE_PATH, state)

    print(json.dumps({
        "scanned": audit_log["scanned"],
        "proposals": len(proposals),
        "discoveries": len(discoveries),
        "status": "staged"
    }, indent=2))

if __name__ == "__main__":
    main()
