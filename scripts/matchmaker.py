import os
import json

from frontmatter_utils import load_frontmatter_file

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
                    return os.path.abspath(os.path.join(logic_root, path)) if not os.path.isabs(path) else path
    return os.getenv("CRM_DATA_PATH", os.getcwd())

CRM_DATA_PATH = get_crm_data_path()
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deals")
LEGACY_DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
MATCHES_PATH = os.path.join(CRM_DATA_PATH, "staging/matches.json")


def deal_directories():
    directories = []
    for directory in [DEALS_DIR, LEGACY_DEALS_DIR]:
        if os.path.exists(directory):
            directories.append(directory)
    return directories

def calculate_match(deal, account):
    score = 0
    # 1. Sector Match
    d_sector = deal.get('sector', '').lower()
    mandate = account.get('investment-mandate', [])
    if isinstance(mandate, list):
        a_mandate = " ".join(str(item).lower() for item in mandate)
    else:
        a_mandate = str(mandate).lower()
    if d_sector and d_sector in a_mandate:
        score += 50
    
    # 2. Check Size / Raise Match (Approximate)
    # This is a simple heuristic since check-size is often a string
    d_raise = str(deal.get('target-raise', '0'))
    a_check = str(account.get('check-size', ''))
    if d_raise != '0' and d_raise in a_check:
        score += 30
        
    # 3. Stage Match
    d_stage = str(deal.get('fundraising-stage') or deal.get('stage', '')).lower()
    a_type = account.get('type', '').lower()
    if a_type == 'investor':
        score += 10 # Default bonus for investors
        
    return score

def main():
    print("Running Brokerage Matchmaker...")
    deals = []
    seen_paths = set()
    for directory in deal_directories():
        for f in os.listdir(directory):
            if not f.endswith(".md"):
                continue
            path = os.path.join(directory, f)
            if path in seen_paths:
                continue
            seen_paths.add(path)
            fm, _ = load_frontmatter_file(path)
            if fm:
                deals.append({'name': f[:-3], 'fm': fm})

    accounts = []
    if os.path.exists(ACCOUNTS_DIR):
        for f in os.listdir(ACCOUNTS_DIR):
            if f.endswith(".md"):
                fm, _ = load_frontmatter_file(os.path.join(ACCOUNTS_DIR, f))
                if fm and fm.get('type') == 'investor':
                    accounts.append({'name': f[:-3], 'fm': fm})

    all_matches = []
    for d in deals:
        for a in accounts:
            score = calculate_match(d['fm'], a['fm'])
            if score >= 50: # Only report high-confidence matches
                all_matches.append({
                    'deal': d['name'],
                    'investor': a['name'],
                    'score': score,
                    'rationate': f"Sector match ({d['fm'].get('sector')}) with mandate."
                })

    # Sort by score
    all_matches.sort(key=lambda x: x['score'], reverse=True)

    os.makedirs(os.path.dirname(MATCHES_PATH), exist_ok=True)
    with open(MATCHES_PATH, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"Matchmaker complete. Found {len(all_matches)} high-probability matches.")

if __name__ == "__main__":
    main()
