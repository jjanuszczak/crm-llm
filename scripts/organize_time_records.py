import argparse
import os
import re
import shutil
from datetime import date, datetime

from frontmatter_utils import bucketed_record_path, frontmatter_date_value, iter_markdown_files, load_frontmatter_file
from lead_manager import get_crm_data_path


CRM_DATA_PATH = get_crm_data_path()
TARGETS = {
    "Activities": ("date", "activity-date", "date-created", "date-modified"),
    "Tasks": ("due-date", "date-created", "date-modified"),
    "Notes": ("date-created", "date-modified", "date"),
}
LINKED_FILE_SUFFIXES = {".md", ".json"}


def extract_date_from_text(text):
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text or "")
    return match.group(1) if match else ""


def infer_record_date(file_path, frontmatter, body, keys):
    frontmatter_date = frontmatter_date_value(frontmatter, *keys)
    if frontmatter_date:
        return frontmatter_date

    basename = os.path.splitext(os.path.basename(file_path))[0]
    filename_date = extract_date_from_text(basename)
    if filename_date:
        return filename_date

    body_date = extract_date_from_text(body)
    if body_date:
        return body_date

    return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d")


def desired_path(root_dir, file_path, frontmatter, body, keys):
    record_date = infer_record_date(file_path, frontmatter, body, keys)
    return bucketed_record_path(root_dir, record_date, os.path.basename(file_path))


def build_move_plan():
    plan = []
    link_mapping = {}

    for directory_name, keys in TARGETS.items():
        root_dir = os.path.join(CRM_DATA_PATH, directory_name)
        if not os.path.exists(root_dir):
            continue

        for file_path in iter_markdown_files(root_dir):
            frontmatter, body = load_frontmatter_file(file_path)
            destination = desired_path(root_dir, file_path, frontmatter, body, keys)
            if destination == file_path:
                continue

            current_rel = os.path.splitext(os.path.relpath(file_path, CRM_DATA_PATH))[0]
            destination_rel = os.path.splitext(os.path.relpath(destination, CRM_DATA_PATH))[0]
            plan.append((file_path, destination))
            link_mapping[current_rel] = destination_rel

    return plan, link_mapping


def replace_wikilinks(content, mapping):
    updated = content
    for old_rel, new_rel in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"\[\[\s*{re.escape(old_rel)}(\|[^\]]+)?\]\]")
        updated = pattern.sub(lambda match: f"[[{new_rel}{match.group(1) or ''}]]", updated)
    return updated


def rewrite_links(mapping):
    rewritten = []
    if not mapping:
        return rewritten

    for root, _, files in os.walk(CRM_DATA_PATH):
        for file_name in files:
            if os.path.splitext(file_name)[1] not in LINKED_FILE_SUFFIXES:
                continue
            file_path = os.path.join(root, file_name)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                original = handle.read()
            updated = replace_wikilinks(original, mapping)
            if updated == original:
                continue
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(updated)
            rewritten.append(file_path)
    return rewritten


def apply_moves(plan):
    moved = []
    for source, destination in plan:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.move(source, destination)
        moved.append((source, destination))
    return moved


def main():
    parser = argparse.ArgumentParser(description="Organize timestamped CRM records into YYYY/MM subfolders.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned moves without modifying files.")
    args = parser.parse_args()

    plan, link_mapping = build_move_plan()
    for source, destination in plan:
        print(f"move: {source} -> {destination}")

    if args.dry_run:
        print(f"planned-moves: {len(plan)}")
        print(f"planned-link-rewrites: {len(link_mapping)}")
        return

    moved = apply_moves(plan)
    rewritten = rewrite_links(link_mapping)
    print(f"moved-files: {len(moved)}")
    print(f"rewritten-files: {len(rewritten)}")


if __name__ == "__main__":
    main()
