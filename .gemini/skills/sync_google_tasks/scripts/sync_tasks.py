import os
import re
import json
import subprocess
from datetime import datetime

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
            key, value = line.split(':', 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data

def get_local_tasks(tasks_dir):
    tasks = []
    if not os.path.exists(tasks_dir): return tasks
    for file_name in os.listdir(tasks_dir):
        if file_name.endswith(".md"):
            with open(os.path.join(tasks_dir, file_name), 'r') as f:
                fm = parse_frontmatter(f.read())
                if fm.get('status') in ['todo', 'in-progress']:
                    tasks.append({
                        'title': fm.get('task-name'),
                        'due': fm.get('due-date'),
                        'file': file_name
                    })
    return tasks

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
    print("Starting Google Tasks Sync...")
    crm_path = get_crm_data_path()
    tasks_dir = os.path.join(crm_path, "Tasks")
    local_tasks = get_local_tasks(tasks_dir)
    
    # Get primary task list ID
    tasklists = run_gws("gws tasks tasklists list")
    if not tasklists or 'items' not in tasklists:
        print("Could not retrieve task lists.")
        return
    
    list_id = tasklists['items'][0]['id'] # Assuming first is primary
    print(f"Using Task List: {tasklists['items'][0]['title']} ({list_id})")
    
    # Get remote tasks for deduplication
    remote_tasks_data = run_gws(f"gws tasks tasks list --params '{{\"tasklist\": \"{list_id}\", \"showCompleted\": false}}'")
    remote_titles = [t['title'] for t in remote_tasks_data.get('items', [])] if remote_tasks_data else []
    
    pushed_count = 0
    for task in local_tasks:
        if task['title'] not in remote_titles:
            print(f"Pushing: {task['title']}...")
            due_str = f"{task['due']}T00:00:00Z" if task['due'] else None
            task_json = {"title": task['title']}
            if due_str: task_json["due"] = due_str
            
            cmd = f"gws tasks tasks insert --params '{{\"tasklist\": \"{list_id}\"}}' --json '{json.dumps(task_json)}'"
            if run_gws(cmd):
                pushed_count += 1
        else:
            print(f"Skipping (Duplicate): {task['title']}")
            
    print(f"Sync complete. Pushed {pushed_count} new tasks.")

if __name__ == "__main__":
    main()
