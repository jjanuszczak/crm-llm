import os
from datetime import date

from frontmatter_utils import load_frontmatter_file, write_frontmatter_file


def get_crm_data_path():
    env_override = os.getenv("CRM_DATA_PATH")
    if env_override:
        return os.path.abspath(env_override)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logic_root = os.path.abspath(os.path.join(script_dir, "../"))
    env_path = os.path.join(logic_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CRM_DATA_PATH="):
                    path = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.abspath(os.path.join(logic_root, path)) if not os.path.isabs(path) else path
    return os.getcwd()


CRM_DATA_PATH = get_crm_data_path()
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")


def normalize_link(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text.strip()


def canonical(value):
    text = normalize_link(value)
    if "/" in text:
        text = text.split("/")[-1]
    return "".join(ch.lower() for ch in text if ch.isalnum())


def link_for(directory, slug):
    return f"[[{directory}/{slug}]]"


def map_account_type(account_type):
    value = str(account_type or "").strip().lower()
    if value == "investor":
        return "investor"
    if value == "startup":
        return "operating-company"
    if value == "corporate":
        return "operating-company"
    return "other"


def org_frontmatter_from_account(account_slug, frontmatter):
    today = date.today().strftime("%Y-%m-%d")
    return {
        "id": f"org-{account_slug}",
        "organization-name": frontmatter.get("company-name") or account_slug,
        "domain": frontmatter.get("domain", ""),
        "headquarters": frontmatter.get("headquarters", ""),
        "industry": frontmatter.get("industry", ""),
        "size": frontmatter.get("size", 0),
        "url": frontmatter.get("url", ""),
        "organization-class": map_account_type(frontmatter.get("type")),
        "organization-subtype": frontmatter.get("organization-subtype", ""),
        "investment-mandate": frontmatter.get("investment-mandate", []),
        "check-size": frontmatter.get("check-size", ""),
        "last-contacted": frontmatter.get("last-contacted", today),
        "source": frontmatter.get("source", "manual"),
        "source-ref": frontmatter.get("source-ref", ""),
        "date-created": frontmatter.get("date-created", today),
        "date-modified": today,
    }


def org_body_from_account(account_slug, frontmatter, body):
    title = frontmatter.get("company-name") or account_slug
    if body.strip():
        return body
    return f"# **Organization: {title}**\n\n## **Identity**\nMigrated from legacy account record.\n"


def ensure_organization(account_slug, frontmatter, body):
    os.makedirs(ORGANIZATIONS_DIR, exist_ok=True)
    path = os.path.join(ORGANIZATIONS_DIR, f"{account_slug}.md")
    if os.path.exists(path):
        return path, False
    write_frontmatter_file(path, org_frontmatter_from_account(account_slug, frontmatter), org_body_from_account(account_slug, frontmatter, body))
    return path, True


def account_variants(account_slug, frontmatter):
    values = {
        canonical(account_slug),
        canonical(frontmatter.get("company-name")),
        canonical(frontmatter.get("organization")),
    }
    return {value for value in values if value}


def matching_opportunities(accounts):
    matches = {slug: [] for slug in accounts}
    for file_name in sorted(os.listdir(OPPORTUNITIES_DIR)):
        if not file_name.endswith(".md"):
            continue
        path = os.path.join(OPPORTUNITIES_DIR, file_name)
        frontmatter, _ = load_frontmatter_file(path)
        if not frontmatter:
            continue
        account_key = canonical(frontmatter.get("account"))
        if not account_key:
            continue
        for slug, account_data in accounts.items():
            if account_key in account_data["variants"]:
                matches[slug].append(path)
    return matches


def migrate():
    today = date.today().strftime("%Y-%m-%d")
    accounts = {}
    for file_name in sorted(os.listdir(ACCOUNTS_DIR)):
        if not file_name.endswith(".md") or file_name.startswith(".!"):
            continue
        path = os.path.join(ACCOUNTS_DIR, file_name)
        frontmatter, body = load_frontmatter_file(path)
        if not frontmatter:
            continue
        slug = os.path.splitext(file_name)[0]
        accounts[slug] = {
            "path": path,
            "frontmatter": frontmatter,
            "body": body,
            "variants": account_variants(slug, frontmatter),
        }

    opportunity_matches = matching_opportunities(accounts)
    created_orgs = []
    updated_accounts = []
    updated_opps = []
    no_opp_accounts = []

    for slug, account in accounts.items():
        org_path, created = ensure_organization(slug, account["frontmatter"], account["body"])
        if created:
            created_orgs.append(org_path)

        organization_link = link_for("Organizations", slug)
        opps = opportunity_matches.get(slug, [])
        if opps:
            frontmatter = dict(account["frontmatter"])
            changed = False
            if frontmatter.get("organization") != organization_link:
                frontmatter["organization"] = organization_link
                changed = True
            if "strategic-importance" not in frontmatter and frontmatter.get("priority"):
                frontmatter["strategic-importance"] = frontmatter.get("priority")
                changed = True
            if changed:
                frontmatter["date-modified"] = today
                write_frontmatter_file(account["path"], frontmatter, account["body"])
                updated_accounts.append(account["path"])

            for opp_path in opps:
                opp_frontmatter, opp_body = load_frontmatter_file(opp_path)
                if not opp_frontmatter:
                    continue
                if opp_frontmatter.get("organization") == organization_link:
                    continue
                opp_frontmatter["organization"] = organization_link
                opp_frontmatter["date-modified"] = today
                write_frontmatter_file(opp_path, opp_frontmatter, opp_body)
                updated_opps.append(opp_path)
        else:
            frontmatter = dict(account["frontmatter"])
            changed = False
            if frontmatter.get("organization") != organization_link:
                frontmatter["organization"] = organization_link
                changed = True
            if frontmatter.get("migration-target") != "organization":
                frontmatter["migration-target"] = "organization"
                changed = True
            if frontmatter.get("migration-note") != "No linked opportunities; treat Organization as canonical.":
                frontmatter["migration-note"] = "No linked opportunities; treat Organization as canonical."
                changed = True
            if changed:
                frontmatter["date-modified"] = today
                write_frontmatter_file(account["path"], frontmatter, account["body"])
                updated_accounts.append(account["path"])
            no_opp_accounts.append(account["path"])

    print("created-organizations:", len(created_orgs))
    for path in created_orgs:
        print(path)
    print("updated-accounts:", len(updated_accounts))
    for path in updated_accounts:
        print(path)
    print("updated-opportunities:", len(updated_opps))
    for path in updated_opps:
        print(path)
    print("organization-canonical-no-opportunity:", len(no_opp_accounts))
    for path in no_opp_accounts:
        print(path)


if __name__ == "__main__":
    migrate()
