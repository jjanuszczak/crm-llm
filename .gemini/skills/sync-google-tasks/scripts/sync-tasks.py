import os
import re
import json
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGIC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(LOGIC_ROOT, "scripts")

if SCRIPTS_DIR not in os.sys.path:
    os.sys.path.insert(0, SCRIPTS_DIR)

from frontmatter_utils import iter_markdown_files

def get_crm_data_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logic_root = os.path.abspath(os.path.join(script_dir, "../../../../"))
    env_path = os.path.join(logic_root, ".env")
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('CRM_DATA_PATH='):
                    path = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if not os.path.isabs(path):
                        path = os.path.abspath(os.path.join(logic_root, path))
                    return path
    return os.getenv("CRM_DATA_PATH", os.getcwd())

def parse_frontmatter(content):
    match = re.match(r'---\s*\n(.*?)\n---\s*', content, re.DOTALL)
    if not match: return {}
    data = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key, value = parts
                data[key.strip()] = value.strip().strip('"').strip("'")
    return data

def get_local_tasks(tasks_dir):
    tasks = []
    if not os.path.exists(tasks_dir):
        return tasks
    for file_path in iter_markdown_files(tasks_dir):
        with open(file_path, 'r') as f:
            content = f.read()
            fm = parse_frontmatter(content)
            tasks.append({
                'title': fm.get('task-name'),
                'due': fm.get('due-date'),
                'status': fm.get('status'),
                'file': os.path.basename(file_path),
                'full_path': file_path
            })
    return tasks

def update_local_task_status(file_path, new_status):
    with open(file_path, 'r') as f:
        content = f.read()
    
    updated_content = re.sub(r'status: (todo|in-progress)', f'status: {new_status}', content)
    updated_content = re.sub(r'date-modified: \d{4}-\d{2}-\d{2}', f'date-modified: {datetime.now().strftime("%Y-%m-%d")}', updated_content)
    
    with open(file_path, 'w') as f:
        f.write(updated_content)

def run_gws(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"GWS Error: {result.stderr}")
            return None
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error running gws: {e}")
        return None

def main():
    print("Starting Bidirectional Google Tasks Sync...")
    crm_path = get_crm_data_path()
    tasks_dir = os.path.join(crm_path, "Tasks")
    local_tasks = get_local_tasks(tasks_dir)
    
    # 1. Get primary task list ID
    tasklists = run_gws("gws tasks tasklists list")
    if not tasklists or 'items' not in tasklists:
        print("Could not retrieve task lists.")
        return
    
    list_id = tasklists['items'][0]['id']
    print(f"Using Task List: {tasklists['items'][0]['title']}")
    
    # 2. Get remote tasks (including completed ones)
    remote_tasks_data = run_gws(f"gws tasks tasks list --params '{{\"tasklist\": \"{list_id}\", \"showCompleted\": true, \"showHidden\": true}}'")
    remote_items = remote_tasks_data.get('items', []) if remote_tasks_data else []
    
    # Map by title -> list of {status, id} to handle potential duplicates
    remote_map = {}
    for t in remote_items:
        title = t.get('title', 'Untitled')
        if title not in remote_map:
            remote_map[title] = []
        remote_map[title].append({'status': t.get('status'), 'id': t.get('id')})
    
    # 3. Synchronize
    pushed_count = 0
    updated_local_count = 0
    updated_remote_count = 0
    
    for task in local_tasks:
        task_title = task['title']
        remote_occurrences = remote_map.get(task_title, [])
        
        # PUSH NEW: If local is active and doesn't exist remotely at all
        if task['status'] in ['todo', 'in-progress'] and not remote_occurrences:
            print(f"Pushing to Google: {task_title}...")
            due_str = f"{task['due']}T00:00:00Z" if task['due'] else None
            task_json = {"title": task_title}
            if due_str: task_json["due"] = due_str
            
            cmd = f"gws tasks tasks insert --params '{{\"tasklist\": \"{list_id}\"}}' --json '{json.dumps(task_json)}'"
            if run_gws(cmd):
                pushed_count += 1
        
        # SYNC STATUS
        elif remote_occurrences:
            # Check if any remote version is completed
            remote_is_completed = any(o['status'] == 'completed' for o in remote_occurrences)
            # Check if any remote version is still open (needsAction)
            open_remote_ids = [o['id'] for o in remote_occurrences if o['status'] == 'needsAction']
            
            # PULL COMPLETION: If local is active but remote is completed
            if task['status'] in ['todo', 'in-progress'] and remote_is_completed:
                print(f"Marking local task as COMPLETED: {task_title}...")
                update_local_task_status(task['full_path'], 'completed')
                updated_local_count += 1
            
            # PUSH COMPLETION: If local is completed but remote is still open
            elif task['status'] == 'completed' and open_remote_ids:
                for rid in open_remote_ids:
                    print(f"Marking Google task as COMPLETED: {task_title}...")
                    patch_cmd = f"gws tasks tasks patch --params '{{\"tasklist\": \"{list_id}\", \"task\": \"{rid}\"}}' --json '{{\"status\": \"completed\"}}'"
                    if run_gws(patch_cmd):
                        updated_remote_count += 1
            
    print(f"Sync complete. Pushed: {pushed_count} | Updated Local: {updated_local_count} | Updated Remote: {updated_remote_count}")

if __name__ == "__main__":
    main()
