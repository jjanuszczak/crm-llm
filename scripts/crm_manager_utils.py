import os
import re

from frontmatter_utils import find_markdown_file, load_frontmatter_file, slugify


def normalize_reference(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2].strip()
    if text.endswith(".md"):
        text = text[:-3]
    return text.strip()


def resolve_record_path(base_dir, crm_data_path, reference, label):
    text = normalize_reference(reference)
    if not text:
        raise ValueError(f"{label} reference is required.")

    if os.path.isabs(text) and os.path.isfile(text):
        return text

    candidate = os.path.join(crm_data_path, text)
    if os.path.isfile(candidate):
        return candidate
    if os.path.isfile(candidate + ".md"):
        return candidate + ".md"

    stem = os.path.basename(text)
    direct = os.path.join(base_dir, stem)
    if os.path.isfile(direct):
        return direct
    if os.path.isfile(direct + ".md"):
        return direct + ".md"

    found = find_markdown_file(base_dir, stem)
    if found:
        return found

    found = find_markdown_file(base_dir, slugify(stem))
    if found:
        return found

    raise FileNotFoundError(f"{label} not found: {reference}")


def resolve_optional_record_path(base_dir, crm_data_path, reference, label):
    if not reference:
        return ""
    return resolve_record_path(base_dir, crm_data_path, reference, label)


def link_target_for_path(path, crm_data_path):
    relative = os.path.relpath(path, crm_data_path)
    return os.path.splitext(relative)[0].replace(os.sep, "/")


def link_for_path(path, crm_data_path):
    return f"[[{link_target_for_path(path, crm_data_path)}]]"


def display_name(frontmatter, default_path):
    for key in [
        "organization-name",
        "opportunity-name",
        "full-name",
        "lead-name",
        "task-name",
        "activity-name",
        "startup-name",
        "title",
        "name",
    ]:
        value = frontmatter.get(key)
        if value:
            return str(value)
    return os.path.splitext(os.path.basename(default_path))[0]


def replace_section(body, heading, content):
    pattern = re.compile(rf"(## \*\*{re.escape(heading)}\*\*\n)(.*?)(?=\n## \*\*|\Z)", re.DOTALL)
    if pattern.search(body):
        def _replace(match):
            section_body = (content or "").strip()
            if section_body:
                return match.group(1) + section_body + "\n\n"
            return match.group(1) + "\n"

        return pattern.sub(_replace, body, count=1)
    if body and not body.endswith("\n"):
        body += "\n"
    return body + f"\n## **{heading}**\n{(content or '').strip()}\n"


def load_display_name(path):
    frontmatter, _body = load_frontmatter_file(path)
    return display_name(frontmatter, path)
