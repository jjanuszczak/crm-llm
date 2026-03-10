import os
import re
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
    
    frontmatter_str = match.group(1)
    data = {}
    for line in frontmatter_str.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            original_value = value.strip().strip('"').strip("'") 

            # Handle known list fields first, if any
            # For this CRM, only 'investment-mandate' is a list. All others are single values.
            if key == 'investment-mandate':
                if original_value.startswith('[') and original_value.endswith(']'):
                    data[key] = [item.strip() for item in original_value[1:-1].split(',') if item.strip()]
                else:
                    data[key] = [original_value] if original_value else [] # Ensure it's always a list
            # Try to parse dates for known date keys
            elif key in ['date-created', 'date-modified', 'date', 'due-date', 'close-date']:
                if re.match(r'\d{4}-\d{2}-\d{2}', original_value):
                    try:
                        data[key] = datetime.strptime(original_value, '%Y-%m-%d').date()
                    except ValueError:
                        data[key] = None 
                else:
                    data[key] = None 
            # Handle booleans
            elif original_value.lower() == 'true':
                data[key] = True
            elif original_value.lower() == 'false':
                data[key] = False
            # Handle integers
            elif original_value.isdigit():
                data[key] = int(original_value)
            # Default to string for all other cases, including wikilinks
            else:
                data[key] = original_value
    return data

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

def aggregate_opportunities(opportunities_data):
    """Aggregates active opportunities into a Markdown table format."""
    table_rows = []
    
    # Define a far-future date for sorting purposes
    FAR_FUTURE_DATE = datetime(9999, 12, 31).date()

    # Filter for active opportunities and sort by probability (desc) and close-date (asc)
    active_opportunities = sorted(
        [o for o in opportunities_data if o['frontmatter'].get('is-active', False)],
        key=lambda x: (
            x['frontmatter'].get('probability', 0), 
            x['frontmatter'].get('close-date') if x['frontmatter'].get('close-date') is not None else FAR_FUTURE_DATE
        )
    )
    
    for opp in active_opportunities:
        fm = opp['frontmatter']
        name = fm.get('opportunity-name', 'N/A')
        
        # Ensure account is a string before replacement
        account = str(fm.get('account', 'N/A')).replace('[[', '').replace(']]', '')
        
        stage = fm.get('stage', 'N/A')
        probability = f"{str(fm.get('probability', 0))}%" # Ensure probability is string for f-string
        close_date = fm.get('close-date', 'N/A')
        
        # Create a wikilink for the opportunity name (without alias)
        rel_path = os.path.relpath(opp['file_path'], PROJECT_ROOT)
        link_target = os.path.splitext(rel_path)[0]
        name_link = f"[[{link_target}]]" # Simplified link
        
        table_rows.append(f"| {name_link} | {account} | {stage} | {probability} | {close_date} |")

    if not table_rows:
        return "No active opportunities found."

    header = "| Opportunity | Account | Stage | Probability | Close Date |\n"
    separator = "| :--- | :--- | :--- | :--- | :--- |\n"
    return header + separator + "\n".join(table_rows)

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

def synthesize_insights(activities_data):
    """
    Synthesizes strategic insights from recent activities.
    For now, this will return a hardcoded list of recent insights.
    Ideally, this would parse activity summaries for keywords/sentiment.
    """
    # Get activities from the last 7 days
    # (Note: Using datetime.now() for current date for consistent behavior with the dashboard timestamp)
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    recent_activities = [
        a for a in activities_data 
        if isinstance(a['frontmatter'].get('date'), date) and a['frontmatter']['date'] >= seven_days_ago
    ]

    # These are insights derived from the manual run, for now.
    insights = [
        "Example Bank Opportunity is Hot: Ghazal's team is actively looking at the Philippines corridor and is already speaking with other partners. The recent email exchange indicates high urgency and a need to move quickly.",
        "Example Fintech Pre-Series A in Play: The Example Fintech opportunity is moving forward with updated investment materials.",
        "ZingHR GTM Formalized: My role as Strategic Advisor Partner for ZingHR's entry into the Philippines banking vertical is confirmed, with clear next steps.",
        "Example Mobility Deal Flow: Initial review of Example Mobility materials is pending, with follow-up required with Bianca.",
        "iCLA Course Proposals: Follow-up needed with Sanjay if no feedback is received soon.",
        "Hello Clever Acquisition & Series A: Both opportunities are active, with follow-ups required for the Brick term sheet and Bob Seltzer for the Series A.",
        "Unpaid Fees: I need to collect outstanding advisory fees from 1882 Energy Ventures."
    ]

    if not recent_activities and not insights:
        return "No new strategic insights identified from recent activities."
    elif not recent_activities: # Use existing insights if no new activities to analyze
        return "Generated insights (from last analysis):\n" + "\n".join(f"*   {i}" for i in insights)
    else:
        # Placeholder for future dynamic insight generation based on recent_activities
        # For now, just return the hardcoded ones and mention recent activities
        activity_summaries = [f"Found activity '{os.path.basename(a['file_path'])}' on {a['frontmatter'].get('date').strftime('%Y-%m-%d')}." for a in recent_activities]
        return "Recent activities indicate potential developments. (Dynamic insight generation to be implemented).\n\n" + \
               "Details of recent activities:\n" + "\n".join(f"*   {s}" for s in activity_summaries) + "\n\n" + \
               "Current insights (from last analysis):\n" + \
               "\n".join(f"*   {i}" for i in insights)


def generate_dashboard_content(opportunities_table, tasks_table, insights_text):
    """Assembles the full Markdown content for DASHBOARD.md."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# CRM Dashboard\n\n"
    content += f"**Last Updated:** {current_date}\n\n"
    content += f"## Active Opportunities\n\n{opportunities_table}\n\n"
    content += f"## Upcoming Tasks\n\n{tasks_table}\n\n"
    content += f"## Strategic Insights\n\n{insights_text}\n"
    
    return content

# --- Main Execution ---

def main():
    print("Generating CRM Dashboard...")

    # 1. Aggregate Opportunities
    opportunities_data = get_files_with_frontmatter(OPPORTUNITIES_DIR)
    opportunities_table = aggregate_opportunities(opportunities_data)

    # 2. Aggregate Tasks
    tasks_data = get_files_with_frontmatter(TASKS_DIR)
    tasks_table = aggregate_tasks(tasks_data)

    # 3. Synthesize Insights
    activities_data = get_files_with_frontmatter(ACTIVITIES_DIR)
    insights_text = synthesize_insights(activities_data)

    # 4. Generate and write Dashboard content
    dashboard_content = generate_dashboard_content(opportunities_table, tasks_table, insights_text)
    
    with open(DASHBOARD_PATH, 'w', encoding='utf-8') as f:
        f.write(dashboard_content)
    
    print(f"DASHBOARD.md updated successfully at {DASHBOARD_PATH}")

if __name__ == "__main__":
    main()
