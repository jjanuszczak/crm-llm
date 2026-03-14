import os
import re
import sys
from datetime import datetime, timedelta, date

# --- Path Loading ---
def get_crm_data_path():
    # Attempt to load the path from .env in the logic root
    # Adjust logic_root calculation as needed if the script location changes
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logic_root = os.path.abspath(os.path.join(script_dir, "../../../../")) # Goes up to crm-logic root
    env_path = os.path.join(logic_root, ".env")
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('CRM_DATA_PATH='):
                    path = line.split('=', 1)[1].strip().strip('"').strip("'")
                    # If it's a relative path, resolve it against the logic_root
                    if not os.path.isabs(path):
                        path = os.path.abspath(os.path.join(logic_root, path))
                    return path
    
    # Fallback to current directory or an environment variable if not in .env
    return os.getenv("CRM_DATA_PATH", os.getcwd())

PROJECT_ROOT = get_crm_data_path()
DASHBOARD_PATH = os.path.join(PROJECT_ROOT, "DASHBOARD.md")
OPPORTUNITIES_DIR = os.path.join(PROJECT_ROOT, "Opportunities")
TASKS_DIR = os.path.join(PROJECT_ROOT, "Tasks")
ACTIVITIES_DIR = os.path.join(PROJECT_ROOT, "Activities")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGIC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
sys.path.insert(0, os.path.join(LOGIC_ROOT, "scripts"))

from frontmatter_utils import parse_markdown_frontmatter

# --- Helper Functions ---

def parse_frontmatter(content):
    """
    Extracts YAML frontmatter from a Markdown string.
    Assumes frontmatter is at the beginning, enclosed by '---'.
    Returns a dictionary of frontmatter key-value pairs.
    """
    match = re.match(r'---\s*\n(.*?)\n---\s*', content, re.DOTALL)
    if not match:
        return {}
    
    parsed, _ = parse_markdown_frontmatter(content)
    return parsed


def _coerce_int(value, default=0):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r'-?\d+', value)
        if match:
            return int(match.group(0))
    return default

def get_files_with_frontmatter(directory):
    """
    Walks through a directory, reads Markdown files, and parses their frontmatter.
    Returns a list of dictionaries, each containing 'file_path' and 'frontmatter'.
    """
    files_data = []
    if not os.path.exists(directory):
        return files_data

    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_name.endswith(".md"):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        fm = parse_frontmatter(content)
                        if fm:
                            files_data.append({'file_path': file_path, 'frontmatter': fm})
                except Exception as e:
                    print(f"Error reading or parsing {file_path}: {e}")
    return files_data

# --- Data Aggregation Functions ---

def create_opportunities_table(opportunities):
    """Creates a Markdown table for a list of opportunities."""
    if not opportunities:
        return "None found."

    table_rows = []
    for opp in opportunities:
        fm = opp['frontmatter']
        name = fm.get('opportunity-name', 'N/A')
        
        # Ensure account is a string before replacement
        account = str(fm.get('account', 'N/A')).replace('[[', '').replace(']]', '')
        
        stage = fm.get('stage', 'N/A')
        probability = f"{str(fm.get('probability', 0))}%"
        close_date = fm.get('close-date', 'N/A')
        
        # Create a wikilink for the opportunity name (without alias)
        rel_path = os.path.relpath(opp['file_path'], PROJECT_ROOT)
        link_target = os.path.splitext(rel_path)[0]
        name_link = f"[[{link_target}]]"
        
        table_rows.append(f"| {name_link} | {account} | {stage} | {probability} | {close_date} |")

    header = "| Opportunity | Account | Stage | Probability | Close Date |\n"
    separator = "| :--- | :--- | :--- | :--- | :--- |\n"
    return header + separator + "\n".join(table_rows)

def aggregate_opportunities(opportunities_data):
    """Splits active opportunities into Engaged (closed-won) and Pipeline (others)."""
    # Define a far-future date for sorting purposes
    FAR_FUTURE_DATE = datetime(9999, 12, 31).date()

    # Filter for active opportunities
    active_opportunities = [o for o in opportunities_data if o['frontmatter'].get('is-active', False)]
    
    # Sort by probability (desc) and close-date (asc)
    sorted_opps = sorted(
        active_opportunities,
        key=lambda x: (
            -_coerce_int(x['frontmatter'].get('probability', 0)),
            x['frontmatter'].get('close-date') if x['frontmatter'].get('close-date') is not None else FAR_FUTURE_DATE
        ),
    )
    
    # Separate into Engaged and Pipeline
    engaged = [o for o in sorted_opps if o['frontmatter'].get('stage') == 'closed-won']
    pipeline = [o for o in sorted_opps if o['frontmatter'].get('stage') != 'closed-won']

    return create_opportunities_table(engaged), create_opportunities_table(pipeline)

def aggregate_tasks(tasks_data):
    """Aggregates todo/in-progress tasks into a Markdown table format."""
    table_rows = []
    
    # Define a far-future date for sorting purposes
    FAR_FUTURE_DATE = datetime(9999, 12, 31).date()

    # Filter for 'todo' or 'in-progress' tasks and sort by due-date
    relevant_tasks = sorted(
        [t for t in tasks_data if t['frontmatter'].get('status') in ['todo', 'in-progress']],
        key=lambda x: x['frontmatter'].get('due-date') if x['frontmatter'].get('due-date') is not None else FAR_FUTURE_DATE
    )

    for task in relevant_tasks:
        fm = task['frontmatter']
        name = fm.get('task-name', 'N/A')
        status = fm.get('status', 'N/A')
        priority = fm.get('priority', 'N/A')
        due_date = fm.get('due-date', 'N/A')
        
        # Determine related entities and format as wikilinks
        related_to_links = []
        for key in ['account', 'contact', 'opportunity']:
            value = fm.get(key)
            if value:
                # Ensure value is a string before replacement
                related_to_links.append(f"[[{str(value).replace('[[', '').replace(']]', '')}]]")
        
        related_to = ", ".join(related_to_links) if related_to_links else "N/A"

        # Create a wikilink for the task name (without alias)
        rel_path = os.path.relpath(task['file_path'], PROJECT_ROOT)
        link_target = os.path.splitext(rel_path)[0]
        name_link = f"[[{link_target}]]" # Simplified link

        table_rows.append(f"| {name_link} | {status} | {priority} | {due_date} | {related_to} |")

    if not table_rows:
        return "No upcoming tasks found."

    header = "| Task | Status | Priority | Due Date | Related To |\n"
    separator = "| :--- | :--- | :--- | :--- | :--- |\n"
    return header + separator + "\n".join(table_rows)

def synthesize_insights(activities_data, opportunities_data, tasks_data):
    """Synthesizes dashboard insights from current CRM data."""
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_out = today + timedelta(days=14)

    recent_activities = [
        a for a in activities_data
        if isinstance(a['frontmatter'].get('date'), date) and a['frontmatter']['date'] >= seven_days_ago
    ]
    overdue_tasks = [
        t for t in tasks_data
        if t['frontmatter'].get('status') in ['todo', 'in-progress']
        and isinstance(t['frontmatter'].get('due-date'), date)
        and t['frontmatter']['due-date'] < today
    ]
    due_soon_tasks = [
        t for t in tasks_data
        if t['frontmatter'].get('status') in ['todo', 'in-progress']
        and isinstance(t['frontmatter'].get('due-date'), date)
        and today <= t['frontmatter']['due-date'] <= today + timedelta(days=7)
    ]
    high_confidence_opps = [
        o for o in opportunities_data
        if o['frontmatter'].get('is-active', False)
        and _coerce_int(o['frontmatter'].get('probability', 0)) >= 70
    ]
    closing_soon_opps = [
        o for o in opportunities_data
        if o['frontmatter'].get('is-active', False)
        and isinstance(o['frontmatter'].get('close-date'), date)
        and o['frontmatter']['close-date'] <= fourteen_days_out
    ]

    insights = []

    if recent_activities:
        latest = sorted(
            recent_activities,
            key=lambda a: a['frontmatter'].get('date'),
            reverse=True,
        )[:3]
        latest_names = ", ".join(os.path.splitext(os.path.basename(item['file_path']))[0] for item in latest)
        insights.append(
            f"Recent activity volume is {len(recent_activities)} item(s) in the last 7 days; latest updates: {latest_names}."
        )

    if high_confidence_opps:
        ranked = sorted(
            high_confidence_opps,
            key=lambda o: (
                -_coerce_int(o['frontmatter'].get('probability', 0)),
                o['frontmatter'].get('close-date') or date.max,
            ),
        )[:3]
        summary = ", ".join(
            f"{item['frontmatter'].get('opportunity-name', os.path.splitext(os.path.basename(item['file_path']))[0])} "
            f"({item['frontmatter'].get('probability', 0)}%)"
            for item in ranked
        )
        insights.append(f"Highest-conviction opportunities: {summary}.")

    if closing_soon_opps:
        ranked = sorted(
            closing_soon_opps,
            key=lambda o: o['frontmatter'].get('close-date') or date.max,
        )[:3]
        summary = ", ".join(
            f"{item['frontmatter'].get('opportunity-name', os.path.splitext(os.path.basename(item['file_path']))[0])} "
            f"(target close {item['frontmatter'].get('close-date')})"
            for item in ranked
        )
        insights.append(f"Near-term closing window: {summary}.")

    if overdue_tasks:
        ranked = sorted(overdue_tasks, key=lambda t: t['frontmatter'].get('due-date'))[:3]
        summary = ", ".join(
            f"{item['frontmatter'].get('task-name', os.path.splitext(os.path.basename(item['file_path']))[0])} "
            f"(due {item['frontmatter'].get('due-date')})"
            for item in ranked
        )
        insights.append(f"Execution risk from overdue tasks: {summary}.")
    elif due_soon_tasks:
        ranked = sorted(due_soon_tasks, key=lambda t: t['frontmatter'].get('due-date'))[:3]
        summary = ", ".join(
            f"{item['frontmatter'].get('task-name', os.path.splitext(os.path.basename(item['file_path']))[0])} "
            f"(due {item['frontmatter'].get('due-date')})"
            for item in ranked
        )
        insights.append(f"Next 7-day task focus: {summary}.")

    if not insights:
        return "No new strategic insights identified from recent activities, opportunities, or tasks."

    return "\n".join(f"* {insight}" for insight in insights)


def generate_dashboard_content(engaged_table, pipeline_table, tasks_table, insights_text):
    """Assembles the full Markdown content for DASHBOARD.md."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# CRM Dashboard\n\n"
    content += f"**Last Updated:** {current_date}\n\n"
    content += f"## Engaged Opportunities\n\n{engaged_table}\n\n"
    content += f"## Active Pipeline\n\n{pipeline_table}\n\n"
    content += f"## Upcoming Tasks\n\n{tasks_table}\n\n"
    content += f"## Strategic Insights\n\n{insights_text}\n"
    
    return content

# --- Main Execution ---

def main():
    print("Generating CRM Dashboard...")

    # 1. Aggregate Opportunities
    opportunities_data = get_files_with_frontmatter(OPPORTUNITIES_DIR)
    engaged_table, pipeline_table = aggregate_opportunities(opportunities_data)

    # 2. Aggregate Tasks
    tasks_data = get_files_with_frontmatter(TASKS_DIR)
    tasks_table = aggregate_tasks(tasks_data)

    # 3. Synthesize Insights
    activities_data = get_files_with_frontmatter(ACTIVITIES_DIR)
    insights_text = synthesize_insights(activities_data, opportunities_data, tasks_data)

    # 4. Generate and write Dashboard content
    dashboard_content = generate_dashboard_content(engaged_table, pipeline_table, tasks_table, insights_text)
    
    with open(DASHBOARD_PATH, 'w', encoding='utf-8') as f:
        f.write(dashboard_content)
    
    print(f"DASHBOARD.md updated successfully at {DASHBOARD_PATH}")

    # 5. Run Matchmaker & Intelligence Engine
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        match_script = os.path.abspath(os.path.join(script_dir, "../../../../scripts/matchmaker.py"))
        intel_script = os.path.abspath(os.path.join(script_dir, "../../../../scripts/intelligence-engine.py"))
        
        if os.path.exists(match_script):
            print("Running Brokerage Matchmaker...")
            subprocess.run(["python3", match_script], check=True)
            
        if os.path.exists(intel_script):
            print("Running Intelligence Engine integration...")
            subprocess.run(["python3", intel_script], check=True)
        else:
            print(f"Warning: Intelligence Engine script not found at {intel_script}")
    except Exception as e:
        print(f"Error running Intelligence Engine: {e}")

    # 6. Commit changes to CRM Data if it's a git repo
    try:
        print("Committing changes to CRM data...")
        subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=True)
        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "agent: update dashboard and intelligence metrics"], cwd=PROJECT_ROOT, check=True)
            print("Changes committed to CRM data.")
        else:
            print("No changes to commit in CRM data.")
    except Exception as e:
        print(f"Error committing changes to CRM data: {e}")

if __name__ == "__main__":
    main()
