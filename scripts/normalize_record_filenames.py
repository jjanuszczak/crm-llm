import argparse
import os
import re

from frontmatter_utils import iter_markdown_files, slugify
from lead_manager import get_crm_data_path


CANONICAL_DIRS = {
    "Accounts",
    "Activities",
    "Contacts",
    "Deal-Flow",
    "Inbox",
    "Leads",
    "Notes",
    "Opportunities",
    "Organizations",
    "Tasks",
}
SKIP_FILES = {"index.md", "log.md"}
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]+)?(\|[^\]]+)?\]\]")


def canonical_record_files(crm_data_path):
    for root_name in sorted(CANONICAL_DIRS):
        root = os.path.join(crm_data_path, root_name)
        for path in iter_markdown_files(root):
            yield path


def all_markdown_files(crm_data_path):
    for path in iter_markdown_files(crm_data_path):
        if os.path.basename(path) in SKIP_FILES:
            continue
        if any(part.startswith(".") for part in os.path.relpath(path, crm_data_path).split(os.sep)):
            continue
        yield path


def build_rename_plan(crm_data_path):
    plan = []
    duplicate_deletes = []
    seen_targets = {}
    for old_path in canonical_record_files(crm_data_path):
        stem, ext = os.path.splitext(os.path.basename(old_path))
        new_name = f"{slugify(stem)}{ext}"
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        if new_path == old_path:
            continue
        existing_source = seen_targets.get(new_path)
        if existing_source and existing_source != old_path:
            if files_match(existing_source, old_path):
                duplicate_deletes.append((old_path, new_path))
                continue
            new_path = next_available_path(new_path, seen_targets)
        elif os.path.exists(new_path):
            try:
                same_file = os.path.samefile(new_path, old_path)
            except FileNotFoundError:
                same_file = False
            if not same_file:
                if files_match(old_path, new_path):
                    duplicate_deletes.append((old_path, new_path))
                    continue
                new_path = next_available_path(new_path, seen_targets)
        seen_targets[new_path] = old_path
        plan.append((old_path, new_path))
    return sorted(plan, key=lambda item: item[0]), sorted(duplicate_deletes, key=lambda item: item[0])


def build_link_mapping(crm_data_path, rename_plan, duplicate_deletes):
    full_map = {}
    stem_map = {}
    for old_path, new_path in list(rename_plan) + list(duplicate_deletes):
        old_rel = os.path.relpath(old_path, crm_data_path)
        new_rel = os.path.relpath(new_path, crm_data_path)
        old_target = os.path.splitext(old_rel)[0].replace(os.sep, "/")
        new_target = os.path.splitext(new_rel)[0].replace(os.sep, "/")
        old_stem = os.path.splitext(os.path.basename(old_path))[0]
        new_stem = os.path.splitext(os.path.basename(new_path))[0]
        full_map[old_target] = new_target
        stem_map.setdefault(old_stem, new_stem)
    return full_map, stem_map


def build_alias_mapping_from_current_files(crm_data_path):
    full_map = {}
    stem_map = {}
    for path in canonical_record_files(crm_data_path):
        rel = os.path.relpath(path, crm_data_path)
        target = os.path.splitext(rel)[0].replace(os.sep, "/")
        stem = os.path.splitext(os.path.basename(path))[0]
        full_map.setdefault(target, target)
        stem_map.setdefault(stem, stem)
        spaced_stem = stem.replace("-", " ")
        if spaced_stem != stem:
            stem_map.setdefault(spaced_stem, stem)
            directory = os.path.dirname(target)
            if directory:
                full_map.setdefault(f"{directory}/{spaced_stem}", target)
    return full_map, stem_map


def rewrite_wikilinks(content, full_map, stem_map):
    changed = False

    def repl(match):
        nonlocal changed
        target = match.group(1).strip()
        heading = match.group(2) or ""
        alias = match.group(3) or ""
        replacement = full_map.get(target, stem_map.get(target))
        if not replacement:
            normalized_target = normalize_target_shape(target)
            replacement = full_map.get(normalized_target, stem_map.get(normalized_target))
        if not replacement or replacement == target:
            return match.group(0)
        changed = True
        return f"[[{replacement}{heading}{alias}]]"

    updated = WIKILINK_RE.sub(repl, content)
    return updated, changed


def rewrite_links_in_vault(crm_data_path, full_map, stem_map):
    changed_files = []
    for path in all_markdown_files(crm_data_path):
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            original = handle.read()
        updated, changed = rewrite_wikilinks(original, full_map, stem_map)
        if not changed:
            continue
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(updated)
        changed_files.append(path)
    return changed_files


def apply_renames(rename_plan):
    renamed = []
    for old_path, new_path in rename_plan:
        old_norm = os.path.normcase(os.path.abspath(old_path))
        new_norm = os.path.normcase(os.path.abspath(new_path))
        if old_norm == new_norm:
            temp_path = old_path + ".tmp-normalize"
            os.rename(old_path, temp_path)
            os.rename(temp_path, new_path)
        else:
            os.rename(old_path, new_path)
        renamed.append((old_path, new_path))
    return renamed


def delete_duplicates(duplicate_deletes):
    deleted = []
    for old_path, _canonical_path in duplicate_deletes:
        if os.path.exists(old_path):
            os.remove(old_path)
            deleted.append(old_path)
    return deleted


def files_match(left_path, right_path):
    with open(left_path, "r", encoding="utf-8", errors="ignore") as left_handle:
        left = left_handle.read()
    with open(right_path, "r", encoding="utf-8", errors="ignore") as right_handle:
        right = right_handle.read()
    return left == right


def next_available_path(candidate_path, seen_targets):
    directory = os.path.dirname(candidate_path)
    stem, ext = os.path.splitext(os.path.basename(candidate_path))
    counter = 2
    while True:
        next_path = os.path.join(directory, f"{stem}-{counter}{ext}")
        if next_path not in seen_targets and not os.path.exists(next_path):
            return next_path
        counter += 1


def normalize_target_shape(target):
    text = str(target or "").strip()
    if "/" not in text:
        return slugify(text)
    head, tail = text.rsplit("/", 1)
    return f"{head}/{slugify(tail)}"


def main():
    parser = argparse.ArgumentParser(description="Normalize CRM record filenames to hyphenated slugs and rewrite wikilinks.")
    parser.add_argument("--apply", action="store_true", help="Apply the rename plan and rewrite vault links.")
    args = parser.parse_args()

    crm_data_path = get_crm_data_path()
    rename_plan, duplicate_deletes = build_rename_plan(crm_data_path)
    full_map, stem_map = build_link_mapping(crm_data_path, rename_plan, duplicate_deletes)

    print("crm-data-path:", crm_data_path)
    print("files-to-rename:", len(rename_plan))
    print("duplicate-files-to-delete:", len(duplicate_deletes))
    for old_path, new_path in rename_plan:
        print(f"rename: {os.path.relpath(old_path, crm_data_path)} -> {os.path.relpath(new_path, crm_data_path)}")
    for old_path, new_path in duplicate_deletes:
        print(f"delete-duplicate: {os.path.relpath(old_path, crm_data_path)} -> {os.path.relpath(new_path, crm_data_path)}")

    if not args.apply:
        return

    changed_files = rewrite_links_in_vault(crm_data_path, full_map, stem_map)
    renamed = apply_renames(rename_plan)
    alias_full_map, alias_stem_map = build_alias_mapping_from_current_files(crm_data_path)
    alias_rewrites = rewrite_links_in_vault(crm_data_path, alias_full_map, alias_stem_map)
    deleted = delete_duplicates(duplicate_deletes)

    print("rewritten-files:", len(changed_files))
    print("canonicalized-link-files:", len(alias_rewrites))
    print("renamed-files:", len(renamed))
    print("deleted-duplicates:", len(deleted))


if __name__ == "__main__":
    main()
