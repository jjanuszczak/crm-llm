import json
import os
import re
import subprocess


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGIC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(LOGIC_ROOT, "scripts")

if SCRIPTS_DIR not in os.sys.path:
    os.sys.path.insert(0, SCRIPTS_DIR)

from frontmatter_utils import iter_markdown_files


COMPLETED_STATUSES = {"completed", "done", "complete"}
ACTIVE_STATUSES = {"todo", "waiting", "in-progress", "blocked", "open"}


def get_crm_data_path():
    env_path = os.path.join(LOGIC_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    path = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if not os.path.isabs(path):
                        path = os.path.abspath(os.path.join(LOGIC_ROOT, path))
                    return path
    return os.getenv("CRM_DATA_PATH", os.getcwd())


def parse_frontmatter(content):
    match = re.match(r"---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}
    data = {}
    for line in match.group(1).split("\n"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def normalize_status(value):
    status = (value or "").strip().lower()
    if status in COMPLETED_STATUSES:
        return "completed"
    if status in ACTIVE_STATUSES:
        return status
    return status or "todo"


def remote_status_for_local(local_status):
    return "completed" if normalize_status(local_status) == "completed" else "needsAction"


def local_due_to_remote(local_due):
    if not local_due:
        return None
    return f"{local_due}T00:00:00.000Z"


def remote_due_to_local(remote_due):
    if not remote_due:
        return ""
    return remote_due[:10]


def get_local_tasks(tasks_dir):
    tasks = []
    if not os.path.exists(tasks_dir):
        return tasks
    for file_path in iter_markdown_files(tasks_dir):
        with open(file_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        fm = parse_frontmatter(content)
        tasks.append(
            {
                "title": fm.get("task-name"),
                "due": fm.get("due-date", ""),
                "status": normalize_status(fm.get("status")),
                "google_task_id": fm.get("google-task-id", ""),
                "google_task_list_id": fm.get("google-task-list-id", ""),
                "full_path": file_path,
            }
        )
    return tasks


def run_command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(f"Command error: {' '.join(args)}")
        if stderr:
            print(stderr)
        return None
    return result


def run_gws(args):
    result = run_command(["gws", *args])
    if not result:
        return None
    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        print(f"GWS JSON parse error: {exc}")
        return None


def update_local_task(file_path, status=None, google_task_id=None, google_task_list_id=None):
    command = [
        "python3",
        os.path.join(SCRIPTS_DIR, "task_manager.py"),
        "update",
        file_path,
    ]
    if status is not None:
        command.extend(["--status", status])
    if google_task_id is not None:
        command.extend(["--google-task-id", google_task_id])
    if google_task_list_id is not None:
        command.extend(["--google-task-list-id", google_task_list_id])
    result = run_command(command)
    return result is not None


def fetch_primary_task_list():
    tasklists = run_gws(["tasks", "tasklists", "list"])
    if not tasklists or "items" not in tasklists or not tasklists["items"]:
        return None
    return tasklists["items"][0]


def fetch_remote_tasks(list_id):
    items = []
    page_token = None
    while True:
        params_payload = {
            "tasklist": list_id,
            "showCompleted": True,
            "showHidden": True,
            "maxResults": 100,
        }
        if page_token:
            params_payload["pageToken"] = page_token
        remote_data = run_gws(["tasks", "tasks", "list", "--params", json.dumps(params_payload)])
        if not remote_data:
            break
        items.extend(remote_data.get("items", []))
        page_token = remote_data.get("nextPageToken")
        if not page_token:
            break
    return items


def create_remote_task(list_id, task):
    params = json.dumps({"tasklist": list_id})
    payload = {"title": task["title"]}
    due = local_due_to_remote(task["due"])
    if due:
        payload["due"] = due
    created = run_gws(["tasks", "tasks", "insert", "--params", params, "--json", json.dumps(payload)])
    if not created or "id" not in created:
        return None
    if remote_status_for_local(task["status"]) == "completed":
        patch_remote_task(
            list_id,
            created["id"],
            {"status": "completed"},
        )
        created["status"] = "completed"
    return created


def patch_remote_task(list_id, task_id, payload):
    params = json.dumps({"tasklist": list_id, "task": task_id})
    return run_gws(["tasks", "tasks", "patch", "--params", params, "--json", json.dumps(payload)])


def unique_title_match(remote_by_title, title):
    matches = remote_by_title.get(title, [])
    if len(matches) == 1:
        return matches[0]
    return None


def needs_remote_patch(remote_task, local_task):
    desired_status = remote_status_for_local(local_task["status"])
    desired_due = local_task["due"] or ""
    remote_due = remote_due_to_local(remote_task.get("due"))
    if remote_task.get("title") != local_task["title"]:
        return True
    if remote_task.get("status") != desired_status:
        return True
    if remote_due != desired_due:
        return True
    return False


def build_remote_patch_payload(remote_task, local_task):
    payload = {}
    desired_status = remote_status_for_local(local_task["status"])
    desired_due = local_due_to_remote(local_task["due"])
    remote_due = remote_due_to_local(remote_task.get("due"))
    if remote_task.get("title") != local_task["title"]:
        payload["title"] = local_task["title"]
    if remote_task.get("status") != desired_status:
        payload["status"] = desired_status
    if remote_due != (local_task["due"] or ""):
        payload["due"] = desired_due
    return payload


def main():
    print("Starting Google Tasks sync...")
    crm_path = get_crm_data_path()
    tasks_dir = os.path.join(crm_path, "Tasks")
    local_tasks = get_local_tasks(tasks_dir)

    primary_list = fetch_primary_task_list()
    if not primary_list:
        print("Could not retrieve task lists.")
        return

    list_id = primary_list["id"]
    print(f"Using Task List: {primary_list['title']}")

    remote_items = fetch_remote_tasks(list_id)
    remote_by_id = {item["id"]: item for item in remote_items if item.get("id")}
    remote_by_title = {}
    for item in remote_items:
        title = item.get("title", "")
        remote_by_title.setdefault(title, []).append(item)

    linked_count = 0
    created_count = 0
    updated_local_count = 0
    updated_remote_count = 0
    ambiguous_titles = []

    for task in local_tasks:
        remote_task = None
        remote_id = task["google_task_id"]
        remote_list_id = task["google_task_list_id"] or list_id

        if remote_id:
            remote_task = remote_by_id.get(remote_id)

        if not remote_task and not remote_id:
            matched = unique_title_match(remote_by_title, task["title"])
            if matched:
                remote_task = matched
                remote_id = matched["id"]
                remote_list_id = list_id
                print(f"Linking existing Google task: {task['title']}...")
                if update_local_task(
                    task["full_path"],
                    google_task_id=remote_id,
                    google_task_list_id=remote_list_id,
                ):
                    task["google_task_id"] = remote_id
                    task["google_task_list_id"] = remote_list_id
                    linked_count += 1
            elif len(remote_by_title.get(task["title"], [])) > 1:
                ambiguous_titles.append(task["title"])
                continue

        if not remote_task:
            print(f"Creating Google task: {task['title']}...")
            created = create_remote_task(list_id, task)
            if not created:
                continue
            remote_task = created
            remote_id = created["id"]
            remote_list_id = list_id
            remote_by_id[remote_id] = remote_task
            remote_by_title.setdefault(task["title"], []).append(remote_task)
            if update_local_task(
                task["full_path"],
                google_task_id=remote_id,
                google_task_list_id=remote_list_id,
            ):
                task["google_task_id"] = remote_id
                task["google_task_list_id"] = remote_list_id
                linked_count += 1
            created_count += 1

        if remote_task.get("status") == "completed" and task["status"] != "completed":
            print(f"Marking local task as COMPLETED from Google: {task['title']}...")
            if update_local_task(
                task["full_path"],
                status="completed",
                google_task_id=remote_id,
                google_task_list_id=remote_list_id,
            ):
                task["status"] = "completed"
                updated_local_count += 1

        if needs_remote_patch(remote_task, task):
            payload = build_remote_patch_payload(remote_task, task)
            if payload:
                print(f"Updating Google task from CRM: {task['title']}...")
                patched = patch_remote_task(remote_list_id, remote_id, payload)
                if patched:
                    remote_task.update(patched)
                    updated_remote_count += 1

    print(
        "Sync complete. "
        f"Linked: {linked_count} | "
        f"Created Remote: {created_count} | "
        f"Updated Local: {updated_local_count} | "
        f"Updated Remote: {updated_remote_count}"
    )
    if ambiguous_titles:
        print("Ambiguous title matches left unresolved:")
        for title in sorted(set(ambiguous_titles)):
            print(f"- {title}")


if __name__ == "__main__":
    main()
