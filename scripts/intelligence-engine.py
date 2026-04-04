import os
import re
import subprocess
from datetime import datetime, date, timedelta

from frontmatter_utils import load_frontmatter_file, write_frontmatter_file

def get_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return os.path.abspath(env_override)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logic_root = os.path.abspath(os.path.join(script_dir, "../"))
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

CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
ACTIVITIES_DIR = os.path.join(CRM_DATA_PATH, "Activities")
STAGING_DIR = os.path.join(CRM_DATA_PATH, "staging")
IGNORE_LIST_PATH = os.path.join(STAGING_DIR, "ignore_list.json")
DISCOVERY_PATH = os.path.join(STAGING_DIR, "discovery.json")
WARM_PATHS_PATH = os.path.join(STAGING_DIR, "warm_paths.json")
MATCHES_PATH = os.path.join(STAGING_DIR, "matches.json")
INTERACTIONS_PATH = os.path.join(STAGING_DIR, "interactions.json")
INTELLIGENCE_DASHBOARD = os.path.join(CRM_DATA_PATH, "INTELLIGENCE.md")
RELATIONSHIP_MEMORY_SCRIPT = os.path.join(os.path.dirname(__file__), "relationship_memory.py")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deals")
LEGACY_DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")

PRIORITY_THRESHOLDS = {'high': 14, 'medium': 30, 'low': 90, 'default': 30}


def as_link_name(value):
    if isinstance(value, list):
        return ""
    return str(value or "").replace("[[", "").replace("]]", "")

def load_json(file_path, default=None):
    if default is None: default = []
    if os.path.exists(file_path):
        try:
            import json
            with open(file_path, 'r') as f: return json.load(f)
        except: return default
    return default

def update_frontmatter(file_path, new_data):
    try:
        fm, body = load_frontmatter_file(file_path)
    except:
        return
    fm.update(new_data)
    write_frontmatter_file(file_path, fm, body)

def get_latest_interaction_date(entity_name, entity_email, activities_data, interactions_cache):
    latest_date = date(2000, 1, 1)
    if entity_email and interactions_cache and entity_email in interactions_cache:
        try:
            telemetry_date_str = interactions_cache[entity_email].get('last_date')
            if telemetry_date_str:
                telemetry_date = datetime.strptime(telemetry_date_str, '%Y-%m-%d').date()
                if telemetry_date > latest_date: latest_date = telemetry_date
        except: pass
    variants = [entity_name, entity_name.replace('-', ' '), entity_name.replace(' ', '-')]
    for act in activities_data:
        fm_str = str(act['frontmatter'])
        act_date_str = act['frontmatter'].get('activity-date') or act['frontmatter'].get('date')
        if not act_date_str: continue
        try: act_date = datetime.strptime(act_date_str, '%Y-%m-%d').date()
        except: continue
        links = re.findall(r'\[\[(.*?)\]\]', fm_str)
        found = any(any(v.lower() in link.lower() for v in variants) for link in links)
        if found and act_date > latest_date: latest_date = act_date
    return latest_date if latest_date != date(2000, 1, 1) else None

def get_velocity(entity_email, interactions_cache):
    if not entity_email or not interactions_cache or entity_email not in interactions_cache: return 0
    return interactions_cache[entity_email].get('hits_last_7_days', 0)


def deal_directories():
    directories = []
    for directory in [DEALS_DIR, LEGACY_DEALS_DIR]:
        if os.path.exists(directory):
            directories.append(directory)
    return directories

def calculate_warmth(last_contacted_date, priority, velocity=0):
    if not last_contacted_date: return 0, "cold", 999
    today = date.today()
    days_since = (today - last_contacted_date).days
    limit = PRIORITY_THRESHOLDS.get(str(priority or "medium").lower(), PRIORITY_THRESHOLDS['default'])
    score = max(0, int(100 * (1 - (days_since / limit))))
    score = min(100, score + (velocity * 10))
    if score > 70: status = "warm"
    elif score > 30: status = "neutral"
    else: status = "cold"
    return score, status, days_since

def main():
    print("Running Intelligence Engine...")
    activities_data = []
    if os.path.exists(ACTIVITIES_DIR):
        for f in os.listdir(ACTIVITIES_DIR):
            if f.endswith(".md"):
                try:
                    fm, _ = load_frontmatter_file(os.path.join(ACTIVITIES_DIR, f))
                    if fm:
                        activities_data.append({'frontmatter': fm})
                except: pass

    interactions_cache = load_json(INTERACTIONS_PATH, default={})
    at_risk = []
    account_stats = {} # {account_name: [scores]}

    # 1. Process Contacts first to aggregate account health
    contacts = []
    if os.path.exists(CONTACTS_DIR):
        for f in os.listdir(CONTACTS_DIR):
            if f.endswith(".md"):
                path = os.path.join(CONTACTS_DIR, f)
                name = f[:-3]
                try:
                    fm, _ = load_frontmatter_file(path)
                    if not fm:
                        continue
                    if directory == ACCOUNTS_DIR and fm.get('migration-target') == 'organization':
                        continue
                except: continue
                
                last_date = get_latest_interaction_date(name, fm.get('email'), activities_data, interactions_cache)
                vel = get_velocity(fm.get('email'), interactions_cache)
                score, stat, days = calculate_warmth(last_date, fm.get('priority', 'medium'), vel)
                
                update_frontmatter(path, {
                    'warmth-score': score, 'warmth-status': stat, 'velocity-score': vel,
                    'last-contacted': last_date.strftime('%Y-%m-%d') if last_date else "2000-01-01",
                    'date-modified': date.today().strftime('%Y-%m-%d')
                })
                
                if (stat == "cold" and fm.get('priority') in ['high', 'medium']) or vel >= 3:
                    at_risk.append({'name': name, 'type': 'Contact', 'status': stat, 'velocity': vel, 'days': days})
                
                # Aggregate for account or deal
                acc_link = as_link_name(fm.get('account', ''))
                deal_link = as_link_name(fm.get('deal', ''))
                parent = acc_link if acc_link else deal_link
                
                if parent:
                    if parent not in account_stats: account_stats[parent] = []
                    account_stats[parent].append(score)

    # 2. Process Organizations, Accounts, and Deals
    for directory in [ORGANIZATIONS_DIR, ACCOUNTS_DIR] + deal_directories():
        if not os.path.exists(directory): continue
        for f in os.listdir(directory):
            if f.endswith(".md"):
                path = os.path.join(directory, f)
                name = f[:-3]
                try:
                    fm, _ = load_frontmatter_file(path)
                    if not fm:
                        continue
                except: continue
                
                last_date = get_latest_interaction_date(name, fm.get('email'), activities_data, interactions_cache)
                vel = get_velocity(fm.get('email'), interactions_cache)
                importance = fm.get('strategic-importance') or fm.get('priority', 'medium')
                score, stat, days = calculate_warmth(last_date, importance, vel)
                
                # Relational Graphing: Calculate Account/Deal Warmth Index
                linked_scores = account_stats.get(name, [])
                if linked_scores:
                    avg_score = sum(linked_scores) / len(linked_scores)
                    acc_index = min(100, int(avg_score + (len(linked_scores) * 5)))
                else:
                    acc_index = score

                update_frontmatter(path, {
                    'warmth-score': score, 'warmth-status': stat, 'velocity-score': vel,
                    'account-warmth-index': acc_index,
                    'last-contacted': last_date.strftime('%Y-%m-%d') if last_date else "2000-01-01",
                    'date-modified': date.today().strftime('%Y-%m-%d')
                })
                
                important = importance in ['high', 'medium']
                if (stat == "cold" and important) or vel >= 3:
                    if directory == ORGANIZATIONS_DIR:
                        type_label = 'Organization'
                    elif directory == ACCOUNTS_DIR:
                        type_label = 'Account'
                    else:
                        type_label = 'Deal'
                    at_risk.append({'name': name, 'type': type_label, 'status': stat, 'velocity': vel, 'days': days, 'index': acc_index})

    # 3. Generate INTELLIGENCE.md
    print(f"Generating {INTELLIGENCE_DASHBOARD}...")
    content = f"# Intelligence Dashboard\n\n**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    content += "## ⚠️ High-Priority & Momentum Relationships\n"
    if at_risk:
        content += "| Entity | Type | Status | Velocity (7d) | Account Health | Days Since |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for i in sorted(at_risk, key=lambda x: (x['velocity'], x['days']), reverse=True):
            v_str = f"🔥 {i['velocity']}" if i['velocity'] >= 3 else str(i['velocity'])
            idx_str = str(i.get('index', 'N/A'))
            content += f"| [[{i['name']}]] | {i['type']} | {('HOT' if i['velocity'] >= 3 else i['status'].upper())} | {v_str} | {idx_str} | {i['days']} |\n"
    else: content += "All relationships are warm or neutral. Great job!\n"
    
    content += "\n## ✨ New Discoveries\n"
    disc = load_json(DISCOVERY_PATH); ignore = load_json(IGNORE_LIST_PATH)
    active_disc = [d for d in disc if d.get('email') not in ignore]
    if active_disc:
        content += "| Name | Type | Rationale | Action |\n| :--- | :--- | :--- | :--- |\n"
        for d in active_disc: content += f"| {d.get('name')} | {d.get('type')} | {d.get('rationale')} | `approve-discovery` |\n"
    else: content += "No new discoveries pending.\n"
    
    content += "\n## 🔗 Warm Paths\n"
    paths = load_json(WARM_PATHS_PATH)
    if paths:
        content += "| Deal | Key Person | Warm Connection | Rationale |\n| :--- | :--- | :--- | :--- |\n"
        for p in paths: content += f"| {p.get('deal')} | {p.get('person')} | [[{p.get('connection')}]] | {p.get('rationale')} |\n"
    else: content += "No new warm paths identified.\n"

    content += "\n## 🤝 Suggested Brokerage Matches\n"
    matches = load_json(MATCHES_PATH)
    if matches:
        content += "| Deal | Potential Investor | Confidence | Rationale |\n| :--- | :--- | :--- | :--- |\n"
        for m in matches[:5]: # Top 5
            content += f"| [[{m.get('deal')}]] | [[{m.get('investor')}]] | {m.get('score')}% | {m.get('rationate')} |\n"
    else: content += "No automated matches found.\n"
    
    with open(INTELLIGENCE_DASHBOARD, 'w', encoding='utf-8') as f: f.write(content)

    if os.path.exists(RELATIONSHIP_MEMORY_SCRIPT):
        try:
            print("Generating relationship memory...")
            subprocess.run(["python3", RELATIONSHIP_MEMORY_SCRIPT], check=True, env={**os.environ, "CRM_DATA_PATH": CRM_DATA_PATH})
        except Exception as exc:
            print(f"Warning: relationship memory generation failed: {exc}")
    print("Intelligence Engine run complete.")

if __name__ == "__main__": main()
