import re
from datetime import date, datetime

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


DATE_KEYS = {
    "activity-date",
    "captured-at",
    "close-date",
    "date",
    "date-created",
    "date-modified",
    "due-date",
    "last-contacted",
    "lost-date",
    "report-date",
}


def parse_markdown_frontmatter(content):
    match = re.match(r"---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}, content

    frontmatter_str = match.group(1)
    body = content[match.end():]
    parsed = _parse_yaml(frontmatter_str)
    return _normalize_mapping(parsed), body


def load_frontmatter_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        return parse_markdown_frontmatter(handle.read())


def write_frontmatter_file(file_path, frontmatter, body):
    serialized = serialize_frontmatter(frontmatter)
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(serialized + body)


def dated_record_id(record_date, title):
    normalized_date = _coerce_date_string(record_date)
    return f"{normalized_date}-{slugify(title)}"


def slugify(value):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", str(value).strip())
    return re.sub(r"-{2,}", "-", cleaned).strip("-") or "record"


def serialize_frontmatter(frontmatter):
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.extend(_serialize_key_value(key, value))
    lines.append("---")
    return "\n".join(lines) + "\n"


def _parse_yaml(frontmatter_str):
    if yaml is not None:
        parsed = yaml.safe_load(frontmatter_str)
        return parsed if isinstance(parsed, dict) else {}
    return _parse_simple_frontmatter(frontmatter_str)


def _parse_simple_frontmatter(frontmatter_str):
    data = {}
    current_key = None

    for raw_line in frontmatter_str.splitlines():
        if not raw_line.strip():
            continue

        if raw_line.startswith((" ", "\t")) and current_key and raw_line.strip().startswith("- "):
            data.setdefault(current_key, []).append(raw_line.strip()[2:].strip().strip('"').strip("'"))
            continue

        if ":" not in raw_line:
            current_key = None
            continue

        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = None

        if not value:
            data[key] = []
            current_key = key
            continue

        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
            continue

        data[key] = value.strip('"').strip("'")

    return data


def _normalize_mapping(data):
    if not isinstance(data, dict):
        return {}

    normalized = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            normalized[key] = value.date()
        elif isinstance(value, list):
            normalized[key] = [_normalize_scalar(item, key) for item in value]
        else:
            normalized[key] = _normalize_scalar(value, key)
    if "full-name" not in normalized and "full--name" in normalized:
        normalized["full-name"] = normalized["full--name"]
    return normalized


def _normalize_scalar(value, key=None):
    if isinstance(value, str):
        stripped = value.strip().strip('"').strip("'")
        if key in DATE_KEYS:
            parsed_date = _parse_date(stripped)
            if parsed_date is not None:
                return parsed_date
        if stripped.lower() == "true":
            return True
        if stripped.lower() == "false":
            return False
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return value


def _parse_date(value):
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _coerce_date_string(value):
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    parsed = _parse_date(str(value))
    if parsed is not None:
        return parsed.strftime("%Y-%m-%d")
    return str(value)


def _serialize_key_value(key, value):
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        lines = [f"{key}:"]
        for item in value:
            lines.append(f"  - {_format_scalar(item)}")
        return lines
    return [f"{key}: {_format_scalar(value)}"]


def _format_scalar(value):
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    if _should_quote(text):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _should_quote(text):
    if text == "":
        return True
    return any(
        (
            text.startswith("[["),
            text.startswith("{"),
            text.startswith("["),
            ":" in text,
            "#" in text,
            text != text.strip(),
            " " in text,
            "-" in text,
            "@" in text,
            "/" in text,
        )
    )
