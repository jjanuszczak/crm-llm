import json
import os
import re
from datetime import date

from frontmatter_utils import iter_markdown_files, load_frontmatter_file
from lead_manager import get_crm_data_path


CRM_DATA_PATH = get_crm_data_path()
ALLOWED_ROOTS = {
    "Organizations",
    "Accounts",
    "Contacts",
    "Activities",
    "Opportunities",
    "Tasks",
    "Notes",
    "Deal-Flow",
}
ROOT_PRIORITY = {
    "Activities": 0,
    "Opportunities": 1,
    "Tasks": 2,
    "Contacts": 3,
    "Accounts": 4,
    "Organizations": 5,
    "Deal-Flow": 6,
    "Notes": 7,
}


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def split_sentences(value, limit=2):
    text = normalize_text(value)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()][:limit]


def combine_notes(*values):
    parts = []
    for value in values:
        text = normalize_text(value)
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def unique_preserve(values):
    seen = set()
    output = []
    for value in values:
        key = normalize_text(value).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(normalize_text(value))
    return output


def normalize_terms(terms):
    output = []
    for term in terms:
        text = normalize_text(term)
        if len(text) >= 3:
            output.append(text.lower())
        for token in re.split(r"[^a-zA-Z0-9.+-]+", text):
            token = token.strip().lower()
            if len(token) >= 4:
                output.append(token)
    return unique_preserve(output)


def display_name(frontmatter, path):
    for key in (
        "organization-name",
        "opportunity-name",
        "full-name",
        "task-name",
        "activity-name",
        "note-name",
        "startup-name",
        "lead-name",
    ):
        if frontmatter.get(key):
            return str(frontmatter[key])
    return os.path.splitext(os.path.basename(path))[0]


def first_meaningful_line(body, terms):
    for raw_line in (body or "").splitlines():
        line = normalize_text(raw_line.strip("*-# "))
        if not line:
            continue
        if any(term in line.lower() for term in terms):
            return line[:280]
    for raw_line in (body or "").splitlines():
        line = normalize_text(raw_line.strip("*-# "))
        if line and not line.startswith("**"):
            return line[:280]
    return ""


def extract_record_date(frontmatter):
    for key in ("date", "activity-date", "due-date", "last-contacted", "date-modified", "date-created", "date-sourced"):
        value = normalize_text(frontmatter.get(key, ""))
        if len(value) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", value[:10]):
            return value[:10]
    return ""


def collect_local_context(search_terms, crm_data_path=CRM_DATA_PATH, limit=16):
    terms = normalize_terms(search_terms)
    if not terms:
        return []

    matches = []
    for path in iter_markdown_files(crm_data_path):
        rel = os.path.relpath(path, crm_data_path)
        root = rel.split(os.sep, 1)[0]
        if root not in ALLOWED_ROOTS:
            continue

        frontmatter, body = load_frontmatter_file(path)
        haystack = " ".join(
            [
                json.dumps(frontmatter, ensure_ascii=False),
                body or "",
                rel,
            ]
        ).lower()
        if not any(term in haystack for term in terms):
            continue

        matches.append(
            {
                "path": path,
                "rel": rel,
                "root": root,
                "title": display_name(frontmatter, path),
                "date": extract_record_date(frontmatter),
                "snippet": first_meaningful_line(body, terms),
            }
        )

    matches.sort(
        key=lambda item: (
            ROOT_PRIORITY.get(item["root"], 99),
            item["date"] or date.min.isoformat(),
            item["title"].lower(),
        ),
        reverse=False,
    )
    return matches[:limit]


def titles_for(matches, root, limit=3):
    return [item["title"] for item in matches if item["root"] == root][:limit]


def summarize_roots(matches):
    counts = {}
    for item in matches:
        counts[item["root"]] = counts.get(item["root"], 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: ROOT_PRIORITY.get(pair[0], 99))
    return ", ".join(f"{root} ({count})" for root, count in ordered)


def infer_last_contacted(matches):
    dated = [item["date"] for item in matches if item.get("date")]
    return max(dated) if dated else ""


def join_paragraph(parts):
    cleaned = [normalize_text(part) for part in parts if normalize_text(part)]
    return "\n\n".join(cleaned)
