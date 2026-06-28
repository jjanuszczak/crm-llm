import argparse
import json
import os
import subprocess
import sys
from datetime import date


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from crm_manager_utils import link_for_path, load_display_name, replace_section, resolve_record_path  # noqa: E402
from frontmatter_utils import find_markdown_file, load_frontmatter_file, parse_markdown_frontmatter, slugify, write_frontmatter_file  # noqa: E402
from lead_manager import get_crm_data_path  # noqa: E402
from navigation_manager import record_mutation  # noqa: E402


VALID_SOURCE_SYSTEMS = {"google-drive", "readwise", "granola", "gmail", "url", "local-file", "other"}
VALID_SOURCE_TYPES = {"doc", "sheet", "slides", "pdf", "folder", "article", "book", "podcast", "meeting-note", "email-thread", "video", "other"}
VALID_CONFIDENTIALITY = {"internal-only", "client-confidential", "reusable-anonymized", "public-safe"}
VALID_STATUSES = {"active", "archived", "superseded"}
VALID_PARENT_TYPES = {
    "organization": "Organizations",
    "account": "Accounts",
    "contact": "Contacts",
    "lead": "Leads",
    "opportunity": "Opportunities",
    "engagement": "Engagements",
    "workstream": "Workstreams",
    "deal": "Deal-Flow",
    "activity": "Activities",
    "note": "Notes",
    "invoice": "Invoices",
    "payment": "Payments",
    "retainer": "Retainers",
}

CRM_DATA_PATH = get_crm_data_path()
SOURCE_ARTIFACTS_DIR = os.path.join(CRM_DATA_PATH, "Source-Artifacts")
NOTES_DIR = os.path.join(CRM_DATA_PATH, "Notes")
ENTITY_DIRS = {key: os.path.join(CRM_DATA_PATH, directory) for key, directory in VALID_PARENT_TYPES.items()}

SOURCE_ARTIFACT_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "source-artifact-template.md")


def ensure_dirs():
    os.makedirs(SOURCE_ARTIFACTS_DIR, exist_ok=True)


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


def resolve_parent_path(parent_type, reference):
    if parent_type not in VALID_PARENT_TYPES:
        raise ValueError(f"Invalid primary-parent-type '{parent_type}'.")
    return resolve_record_path(ENTITY_DIRS[parent_type], CRM_DATA_PATH, reference, VALID_PARENT_TYPES[parent_type][:-1] if VALID_PARENT_TYPES[parent_type].endswith("s") else VALID_PARENT_TYPES[parent_type])


def resolve_optional_note_path(reference):
    if not reference:
        return ""
    return resolve_record_path(NOTES_DIR, CRM_DATA_PATH, reference, "Note")


def normalize_links(values):
    links = []
    seen = set()
    for value in values or []:
        text = normalize_reference(value)
        if not text:
            continue
        link = value if str(value).strip().startswith("[[") else f"[[{text}]]"
        if link in seen:
            continue
        seen.add(link)
        links.append(link)
    return links


def source_artifact_related_links(frontmatter):
    related = [frontmatter.get("primary-parent", ""), frontmatter.get("summary-note", "")]
    related.extend(frontmatter.get("secondary-links", []) or [])
    return related


def load_source_artifact(reference):
    path = resolve_record_path(SOURCE_ARTIFACTS_DIR, CRM_DATA_PATH, reference, "Source Artifact")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def find_source_artifact_by_external_id(external_id, source_system=None):
    target = str(external_id or "").strip()
    if not target or not os.path.exists(SOURCE_ARTIFACTS_DIR):
        return None
    source_system_value = str(source_system or "").strip()
    for root, _dirs, files in os.walk(SOURCE_ARTIFACTS_DIR):
        for file_name in sorted(files):
            if not file_name.endswith(".md"):
                continue
            file_path = os.path.join(root, file_name)
            try:
                frontmatter, _body = load_frontmatter_file(file_path)
            except Exception:
                continue
            if str(frontmatter.get("external-id") or "").strip() != target:
                continue
            if source_system_value and str(frontmatter.get("source-system") or "").strip() != source_system_value:
                continue
            return file_path
    return None


def build_source_artifact_body(title, summary, usage_context, review_notes):
    rendered = render_template(
        SOURCE_ARTIFACT_TEMPLATE_PATH,
        {
            "source-artifact-id": "src-placeholder",
            "Source Artifact Title": title or "Source Artifact",
            "Owner": "john",
            "organization | account | contact | lead | opportunity | engagement | workstream | deal | activity | note | invoice | payment | retainer": "opportunity",
            "Primary Parent": "",
            "Secondary Link 1": "",
            "google-drive | readwise | granola | gmail | url | local-file | other": "url",
            "doc | sheet | slides | pdf | folder | article | book | podcast | meeting-note | email-thread | video | other": "article",
            "Primary URL": "",
            "External ID": "",
            "internal-only | client-confidential | reusable-anonymized | public-safe": "internal-only",
            "active | archived | superseded": "active",
            "Summary Note": "",
            "manual | drive-sync | readwise-sync | granola-sync | gmail | url": "manual",
            "Source Reference": "",
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = replace_section(body, "Artifact Summary", summary or "Created through crm-source-artifact-manager.")
    body = replace_section(body, "Usage Context", usage_context or "")
    body = replace_section(body, "Review Notes", review_notes or "")
    return body


def linked_to_record(frontmatter, record_link):
    normalized = normalize_reference(record_link)
    values = [frontmatter.get("primary-parent"), frontmatter.get("summary-note")]
    for value in values:
        if normalize_reference(value) == normalized:
            return True
    for field in ["secondary-links"]:
        raw = frontmatter.get(field) or []
        values = raw if isinstance(raw, list) else [raw]
        if any(normalize_reference(item) == normalized for item in values):
            return True
    return False


def gather_related_notes(source_artifact_link):
    matches = []
    if not os.path.exists(NOTES_DIR):
        return matches
    for root, _dirs, files in os.walk(NOTES_DIR):
        for file_name in sorted(files):
            if not file_name.endswith(".md"):
                continue
            file_path = os.path.join(root, file_name)
            try:
                frontmatter, _body = load_frontmatter_file(file_path)
            except Exception:
                continue
            values = [frontmatter.get("primary-parent"), frontmatter.get("derived-from")]
            if any(normalize_reference(value) == normalize_reference(source_artifact_link) for value in values):
                matches.append((file_path, frontmatter))
                continue
            evidence_links = frontmatter.get("evidence-links") or []
            if not isinstance(evidence_links, list):
                evidence_links = [evidence_links]
            if any(normalize_reference(value) == normalize_reference(source_artifact_link) for value in evidence_links):
                matches.append((file_path, frontmatter))
    return matches


def summarize_text(text, limit=400):
    collapsed = " ".join(str(text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 3)].rstrip() + "..."


def readwise_payload_title(payload):
    for key in ["title", "book_title", "article_title", "source_title", "document_title"]:
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    author = str(payload.get("author") or payload.get("source_author") or "").strip()
    source_url = str(payload.get("url") or payload.get("source_url") or "").strip()
    external_id = str(payload.get("id") or payload.get("external_id") or "").strip()
    if author:
        return f"Readwise - {author}"
    if source_url:
        return source_url
    if external_id:
        return f"Readwise Item {external_id}"
    return "Readwise Item"


def readwise_payload_source_type(payload):
    category = str(payload.get("category") or payload.get("type") or payload.get("source_type") or "").strip().lower()
    if category in {"article", "essay", "newsletter", "tweet", "thread"}:
        return "article"
    if category in {"book", "ebook", "kindle"}:
        return "book"
    if category in {"podcast", "episode"}:
        return "podcast"
    if category in {"video", "youtube"}:
        return "video"
    if category in {"pdf"}:
        return "pdf"
    return "article"


def readwise_payload_summary(payload):
    parts = []
    summary = str(payload.get("summary") or payload.get("notes") or payload.get("description") or "").strip()
    if summary:
        parts.append(summary)
    markdown = str(payload.get("content") or payload.get("markdown") or payload.get("text") or "").strip()
    if markdown and not parts:
        parts.append(summarize_text(markdown, 500))
    highlights = payload.get("highlights") or []
    if isinstance(highlights, list):
        snippets = []
        for item in highlights[:3]:
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("highlight") or "").strip()
            else:
                text = str(item).strip()
            if text:
                snippets.append(summarize_text(text, 180))
        if snippets:
            parts.append("Highlights: " + " | ".join(snippets))
    return "\n\n".join(parts).strip()


def run_readwise_cli(command_args, json_output=True):
    command = ["readwise"]
    if json_output:
        command.append("--json")
    command.extend(command_args)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Readwise CLI failed: {error_text or 'unknown error'}")
    output = (result.stdout or "").strip()
    if not json_output:
        return output
    if not output:
        raise RuntimeError("Readwise CLI returned no JSON output.")
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Readwise CLI returned invalid JSON output.") from exc


def normalize_readwise_cli_payload(payload, document_id=None):
    if isinstance(payload, dict):
        if "document" in payload and isinstance(payload["document"], dict):
            return payload["document"]
        if "results" in payload and isinstance(payload["results"], list) and len(payload["results"]) == 1 and isinstance(payload["results"][0], dict):
            return payload["results"][0]
        if payload.get("id") or payload.get("document_id") or payload.get("title") or payload.get("content") or payload.get("markdown"):
            normalized = dict(payload)
            if document_id and not normalized.get("id"):
                normalized["id"] = document_id
            return normalized
    raise ValueError("Readwise CLI payload shape is unsupported.")


def load_readwise_cli_payload(args):
    if not args.document_id:
        raise ValueError("Readwise CLI import requires --document-id.")
    payload = run_readwise_cli(["reader-get-document-details", "--document-id", args.document_id], json_output=True)
    return normalize_readwise_cli_payload(payload, document_id=args.document_id)


def load_readwise_payload(args):
    document_id = getattr(args, "document_id", None)
    if document_id:
        payload = load_readwise_cli_payload(args)
    elif args.json_path:
        with open(args.json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    elif args.json:
        payload = json.loads(args.json)
    else:
        raise ValueError("Either --json-path or --json is required.")
    if not isinstance(payload, dict):
        raise ValueError("Readwise payload must be a JSON object.")
    return payload


def cmd_create(args):
    ensure_dirs()
    ensure_choice(args.source_system, VALID_SOURCE_SYSTEMS, "source-system")
    ensure_choice(args.source_type, VALID_SOURCE_TYPES, "source-type")
    ensure_choice(args.confidentiality, VALID_CONFIDENTIALITY, "confidentiality")
    ensure_choice(args.status, VALID_STATUSES, "status")

    parent_path = resolve_parent_path(args.primary_parent_type, args.primary_parent)
    summary_note_path = resolve_optional_note_path(args.summary_note)

    title = args.title or args.url or args.external_id or f"{args.source_system} {args.source_type}"
    artifact_slug = slugify(title)
    file_path = os.path.join(SOURCE_ARTIFACTS_DIR, f"{artifact_slug}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Source Artifact already exists: {file_path}")

    if args.external_id:
        existing_external = find_source_artifact_by_external_id(args.external_id, args.source_system)
        if existing_external and os.path.abspath(existing_external) != os.path.abspath(file_path):
            raise FileExistsError(f"Source Artifact with matching external-id slug already exists: {existing_external}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        SOURCE_ARTIFACT_TEMPLATE_PATH,
        {
            "source-artifact-id": f"src-{artifact_slug}",
            "Source Artifact Title": title,
            "Owner": args.owner,
            "organization | account | contact | lead | opportunity | engagement | workstream | deal | activity | note | invoice | payment | retainer": args.primary_parent_type,
            "Primary Parent": os.path.splitext(os.path.relpath(parent_path, CRM_DATA_PATH))[0],
            "Secondary Link 1": normalize_reference(args.secondary_links[0]) if args.secondary_links else os.path.splitext(os.path.relpath(parent_path, CRM_DATA_PATH))[0],
            "google-drive | readwise | granola | gmail | url | local-file | other": args.source_system,
            "doc | sheet | slides | pdf | folder | article | book | podcast | meeting-note | email-thread | video | other": args.source_type,
            "Primary URL": args.url or "",
            "External ID": args.external_id or "",
            "internal-only | client-confidential | reusable-anonymized | public-safe": args.confidentiality,
            "active | archived | superseded": args.status,
            "Summary Note": os.path.splitext(os.path.relpath(summary_note_path, CRM_DATA_PATH))[0] if summary_note_path else "",
            "manual | drive-sync | readwise-sync | granola-sync | gmail | url": args.source,
            "Source Reference": args.source_ref or "",
            "YYYY-MM-DD": today,
        },
    )
    frontmatter, _body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = f"src-{artifact_slug}"
    frontmatter["title"] = title
    frontmatter["owner"] = args.owner
    frontmatter["primary-parent-type"] = args.primary_parent_type
    frontmatter["primary-parent"] = link_for_path(parent_path, CRM_DATA_PATH)
    frontmatter["secondary-links"] = normalize_links(args.secondary_links)
    frontmatter["source-system"] = args.source_system
    frontmatter["source-type"] = args.source_type
    frontmatter["url"] = args.url or ""
    frontmatter["external-id"] = args.external_id or ""
    frontmatter["confidentiality"] = args.confidentiality
    frontmatter["status"] = args.status
    frontmatter["summary-note"] = link_for_path(summary_note_path, CRM_DATA_PATH) if summary_note_path else ""
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["last-reviewed"] = args.last_reviewed or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = build_source_artifact_body(title, args.summary or "", args.usage_context or "", args.review_notes or "")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Source Artifact",
        title=title,
        path=file_path,
        source=args.source,
        related=source_artifact_related_links(frontmatter),
        details=f"source-system={args.source_system}; source-type={args.source_type}; status={args.status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_create_readwise(args):
    payload = load_readwise_payload(args)
    title = args.title or readwise_payload_title(payload)
    source_type = args.source_type or readwise_payload_source_type(payload)
    source_ref = args.source_ref or str(payload.get("id") or payload.get("external_id") or "").strip()
    url = args.url or str(payload.get("url") or payload.get("source_url") or "").strip()
    if not url and source_ref:
        url = f"https://read.readwise.io/read/{source_ref}"
    summary = args.summary or readwise_payload_summary(payload)
    usage_context = args.usage_context or str(payload.get("context") or payload.get("notes_context") or "").strip()
    review_notes = args.review_notes or ""
    source_args = argparse.Namespace(
        primary_parent_type=args.primary_parent_type,
        primary_parent=args.primary_parent,
        title=title,
        secondary_links=args.secondary_links,
        source_system="readwise",
        source_type=source_type,
        url=url,
        external_id=str(payload.get("id") or payload.get("external_id") or "").strip(),
        confidentiality=args.confidentiality,
        status=args.status,
        summary_note=args.summary_note,
        summary=summary,
        usage_context=usage_context,
        review_notes=review_notes,
        owner=args.owner,
        source="readwise-sync",
        source_ref=source_ref,
        last_reviewed=args.last_reviewed,
    )
    cmd_create(source_args)


def cmd_link(args):
    file_path, frontmatter, body = load_source_artifact(args.source_artifact)
    current_links = normalize_links(frontmatter.get("secondary-links", []))
    additions = normalize_links(args.secondary_links)
    combined = current_links[:]
    for link in additions:
        if link not in combined:
            combined.append(link)
    if not additions:
        raise ValueError("At least one secondary link is required.")
    frontmatter["secondary-links"] = combined
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Source Artifact",
        title=frontmatter.get("title", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=source_artifact_related_links(frontmatter),
        details=f"linked {len(additions)} additional record(s)",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_re_parent(args):
    file_path, frontmatter, body = load_source_artifact(args.source_artifact)
    parent_path = resolve_parent_path(args.primary_parent_type, args.primary_parent)
    frontmatter["primary-parent-type"] = args.primary_parent_type
    frontmatter["primary-parent"] = link_for_path(parent_path, CRM_DATA_PATH)
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Source Artifact",
        title=frontmatter.get("title", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=source_artifact_related_links(frontmatter),
        details=f"re-parented to {args.primary_parent_type}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_attach_summary_note(args):
    file_path, frontmatter, body = load_source_artifact(args.source_artifact)
    summary_note_path = resolve_record_path(NOTES_DIR, CRM_DATA_PATH, args.summary_note, "Note")
    frontmatter["summary-note"] = link_for_path(summary_note_path, CRM_DATA_PATH)
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Source Artifact",
        title=frontmatter.get("title", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=source_artifact_related_links(frontmatter),
        details="attached summary note",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_set_status(args):
    file_path, frontmatter, body = load_source_artifact(args.source_artifact)
    status = ensure_choice(args.status, VALID_STATUSES, "status")
    frontmatter["status"] = status
    if args.last_reviewed is not None:
        frontmatter["last-reviewed"] = args.last_reviewed
    frontmatter["date-modified"] = date.today().strftime("%Y-%m-%d")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="update",
        entity_type="Source Artifact",
        title=frontmatter.get("title", load_display_name(file_path)),
        path=file_path,
        source=frontmatter.get("source", ""),
        related=source_artifact_related_links(frontmatter),
        details=f"status={status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_review(args):
    file_path, frontmatter, body = load_source_artifact(args.source_artifact)
    source_artifact_link = link_for_path(file_path, CRM_DATA_PATH)
    related_notes = gather_related_notes(source_artifact_link)

    print(f"Source Artifact: {frontmatter.get('title', load_display_name(file_path))}")
    print(f"Path: {file_path}")
    print(f"Primary Parent: {frontmatter.get('primary-parent', '')}")
    print(f"Secondary Links: {len(frontmatter.get('secondary-links', []) or [])}")
    print(f"Source System: {frontmatter.get('source-system', '')}")
    print(f"Source Type: {frontmatter.get('source-type', '')}")
    print(f"Status: {frontmatter.get('status', '')}")
    print(f"Confidentiality: {frontmatter.get('confidentiality', '')}")
    print(f"URL: {frontmatter.get('url', '') or 'none'}")
    print(f"External ID: {frontmatter.get('external-id', '') or 'none'}")
    print(f"Summary Note: {frontmatter.get('summary-note', '') or 'none'}")
    print(f"Related Notes: {len(related_notes)}")
    print("Recommended Next Action:")
    if not frontmatter.get("summary-note"):
        print("- attach or create a durable summary note if this source matters operationally")
    elif not related_notes:
        print("- link the source artifact to the note evidence layer more explicitly")
    elif frontmatter.get("status") == "superseded":
        print("- confirm replacement source coverage and archive if no longer active")
    else:
        print("- verify placement, confidentiality, and whether more linked entities are needed")
    if args.verbose and body:
        print("Summary:")
        print(body.strip())


def build_parser():
    parser = argparse.ArgumentParser(description="Manage source artifact workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a canonical source artifact.")
    create_parser.add_argument("--primary-parent-type", required=True)
    create_parser.add_argument("--primary-parent", required=True)
    create_parser.add_argument("--title")
    create_parser.add_argument("--secondary-links", nargs="*", default=[])
    create_parser.add_argument("--source-system", required=True)
    create_parser.add_argument("--source-type", required=True)
    create_parser.add_argument("--url")
    create_parser.add_argument("--external-id")
    create_parser.add_argument("--confidentiality", default="internal-only")
    create_parser.add_argument("--status", default="active")
    create_parser.add_argument("--summary-note")
    create_parser.add_argument("--summary")
    create_parser.add_argument("--usage-context")
    create_parser.add_argument("--review-notes")
    create_parser.add_argument("--owner", default="john")
    create_parser.add_argument("--source", default="manual")
    create_parser.add_argument("--source-ref")
    create_parser.add_argument("--last-reviewed")
    create_parser.set_defaults(func=cmd_create)

    readwise_parser = subparsers.add_parser("create-readwise", help="Create a source artifact from a Readwise payload or Reader document.")
    readwise_parser.add_argument("--primary-parent-type", required=True)
    readwise_parser.add_argument("--primary-parent", required=True)
    readwise_parser.add_argument("--document-id")
    readwise_parser.add_argument("--json-path")
    readwise_parser.add_argument("--json")
    readwise_parser.add_argument("--title")
    readwise_parser.add_argument("--secondary-links", nargs="*", default=[])
    readwise_parser.add_argument("--source-type")
    readwise_parser.add_argument("--url")
    readwise_parser.add_argument("--source-ref")
    readwise_parser.add_argument("--confidentiality", default="internal-only")
    readwise_parser.add_argument("--status", default="active")
    readwise_parser.add_argument("--summary-note")
    readwise_parser.add_argument("--summary")
    readwise_parser.add_argument("--usage-context")
    readwise_parser.add_argument("--review-notes")
    readwise_parser.add_argument("--owner", default="john")
    readwise_parser.add_argument("--last-reviewed")
    readwise_parser.set_defaults(func=cmd_create_readwise)

    link_parser = subparsers.add_parser("link", help="Add secondary links to an existing source artifact.")
    link_parser.add_argument("source_artifact")
    link_parser.add_argument("--secondary-links", nargs="+", required=True)
    link_parser.set_defaults(func=cmd_link)

    reparent_parser = subparsers.add_parser("re-parent", help="Change the primary parent of an existing source artifact.")
    reparent_parser.add_argument("source_artifact")
    reparent_parser.add_argument("--primary-parent-type", required=True)
    reparent_parser.add_argument("--primary-parent", required=True)
    reparent_parser.set_defaults(func=cmd_re_parent)

    summary_note_parser = subparsers.add_parser("attach-summary-note", help="Attach a note as the canonical summary of a source artifact.")
    summary_note_parser.add_argument("source_artifact")
    summary_note_parser.add_argument("--summary-note", required=True)
    summary_note_parser.set_defaults(func=cmd_attach_summary_note)

    status_parser = subparsers.add_parser("set-status", help="Update source artifact status.")
    status_parser.add_argument("source_artifact")
    status_parser.add_argument("--status", required=True)
    status_parser.add_argument("--last-reviewed")
    status_parser.set_defaults(func=cmd_set_status)

    review_parser = subparsers.add_parser("review", help="Review a source artifact and its memory links.")
    review_parser.add_argument("source_artifact")
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
