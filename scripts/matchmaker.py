import json
import os
import re

from frontmatter_utils import iter_markdown_files, load_frontmatter_file


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
    return os.getenv("CRM_DATA_PATH", os.getcwd())


CRM_DATA_PATH = get_crm_data_path()
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deals")
LEGACY_DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
MATCHES_PATH = os.path.join(CRM_DATA_PATH, "staging", "matches.json")
WARM_PATHS_PATH = os.path.join(CRM_DATA_PATH, "staging", "warm_paths.json")

SECTOR_SYNONYMS = {
    "fintech": {"fintech", "financial services", "digital banking", "payments", "banking", "financial"},
    "energy": {"energy", "renewable", "power", "solar", "battery", "grid", "decarbonization", "climate"},
    "mobility": {"mobility", "transport", "transportation", "ev", "electric mobility", "fleet"},
    "agritech": {"agritech", "agriculture", "food security", "controlled environment agriculture", "cea"},
    "saas": {"saas", "software", "enterprise software", "b2b software"},
    "healthtech": {"healthtech", "healthcare", "health"},
    "infrastructure": {"infrastructure", "industrial", "utilities"},
}

STAGE_ORDER = {
    "pre-seed": 0,
    "seed": 1,
    "pre-series-a": 2,
    "series-a": 3,
    "series-b": 4,
    "growth": 5,
}


def deal_directories():
    directories = []
    for directory in [DEALS_DIR, LEGACY_DEALS_DIR]:
        if os.path.exists(directory):
            directories.append(directory)
    return directories


def normalize_link(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    return text.split("/")[-1]


def canonical_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def normalize_account_key(value):
    text = normalize_link(value)
    if text.startswith("Accounts/") or text.startswith("Organizations/"):
        text = text.split("/", 1)[1]
    return text


def tokenize(value):
    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").lower()) if token}


def extract_categories(*values):
    text = " ".join(str(value or "") for value in values).lower()
    categories = set()
    for category, synonyms in SECTOR_SYNONYMS.items():
        if any(phrase in text for phrase in synonyms):
            categories.add(category)
    return categories


def parse_stage(value):
    text = str(value or "").lower()
    if "pre" in text and "series a" in text:
        return "pre-series-a"
    if "seed" in text:
        return "seed"
    if "series a" in text:
        return "series-a"
    if "series b" in text or "series c" in text or "growth round" in text or "growth" in text:
        return "growth"
    if "acquisition" in text or "buyout" in text:
        return "growth"
    if "working capital" in text:
        return "growth"
    return ""


def parse_money_range(value):
    text = str(value or "").upper().replace(",", "")
    matches = re.findall(r"\$?\s*(\d+(?:\.\d+)?)\s*([KMB])?", text)
    if not matches:
        return (None, None)

    values = []
    for amount_text, suffix in matches:
        amount = float(amount_text)
        if suffix == "K":
            amount *= 1_000
        elif suffix == "M":
            amount *= 1_000_000
        elif suffix == "B":
            amount *= 1_000_000_000
        values.append(amount)

    if "+" in text and values:
        return (values[0], None)
    if len(values) == 1:
        return (values[0], values[0])
    return (min(values), max(values))


def location_tokens(value):
    text = str(value or "").lower()
    tokens = set()
    for keyword in [
        "philippines",
        "manila",
        "singapore",
        "indonesia",
        "australia",
        "uk",
        "london",
        "usa",
        "southeast asia",
        "emerging market",
        "global",
    ]:
        if keyword in text:
            tokens.add(keyword)
    return tokens


def collect_deals():
    deals = []
    seen_paths = set()
    for directory in deal_directories():
        for path in iter_markdown_files(directory):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            frontmatter, body = load_frontmatter_file(path)
            if not frontmatter:
                continue
            name = os.path.splitext(os.path.basename(path))[0]
            sector_text = frontmatter.get("sector") or ""
            stage_text = frontmatter.get("fundraising-stage") or frontmatter.get("stage") or ""
            deals.append(
                {
                    "name": name,
                    "frontmatter": frontmatter,
                    "body": body,
                    "categories": extract_categories(sector_text),
                    "stage": parse_stage(stage_text),
                    "target_raise": float(frontmatter.get("target-raise") or 0),
                    "location_tokens": location_tokens(frontmatter.get("location")),
                    "canonical_name": canonical_key(name),
                }
            )
    return deals


def collect_investors():
    organizations = {}
    if os.path.exists(ORGANIZATIONS_DIR):
        for path in iter_markdown_files(ORGANIZATIONS_DIR):
            frontmatter, body = load_frontmatter_file(path)
            if not frontmatter:
                continue
            name = os.path.splitext(os.path.basename(path))[0]
            organizations[name] = {"frontmatter": frontmatter, "body": body, "name": name}

    investors = []
    if os.path.exists(ACCOUNTS_DIR):
        for path in iter_markdown_files(ACCOUNTS_DIR):
            frontmatter, body = load_frontmatter_file(path)
            if not frontmatter or frontmatter.get("migration-target") == "organization":
                continue
            org_name = normalize_link(frontmatter.get("organization"))
            organization = organizations.get(org_name)
            merged = {}
            if organization:
                merged.update(organization["frontmatter"])
            merged.update(frontmatter)
            investor_type = (organization["frontmatter"].get("organization-class") if organization else "") or frontmatter.get("type")
            if str(investor_type or "").lower() != "investor":
                continue

            mandate_values = merged.get("investment-mandate") or []
            if not isinstance(mandate_values, list):
                mandate_values = [mandate_values]
            mandate_text = " ".join(str(item) for item in mandate_values)
            check_size = merged.get("check-size") or ""
            investors.append(
                {
                    "name": os.path.splitext(os.path.basename(path))[0],
                    "organization_name": org_name or os.path.splitext(os.path.basename(path))[0],
                    "frontmatter": merged,
                    "body": (organization["body"] if organization else "") + "\n" + body,
                    "categories": extract_categories(mandate_text, merged.get("industry")),
                    "mandate_tokens": tokenize(mandate_text),
                    "location_tokens": location_tokens(mandate_text) | location_tokens(merged.get("headquarters")) | location_tokens(organization["body"] if organization else ""),
                    "stage": parse_stage(check_size + " " + mandate_text + " " + (organization["body"] if organization else "")),
                    "check_size_range": parse_money_range(check_size),
                    "relationship_score": max(
                        int(merged.get("warmth-score") or 0),
                        int(merged.get("account-warmth-index") or 0),
                    ),
                    "canonical_name": canonical_key(org_name or os.path.splitext(os.path.basename(path))[0]),
                }
            )
    return investors


def collect_contacts():
    contacts_dir = os.path.join(CRM_DATA_PATH, "Contacts")
    contacts = []
    if not os.path.exists(contacts_dir):
        return contacts
    for path in iter_markdown_files(contacts_dir):
        frontmatter, body = load_frontmatter_file(path)
        if not frontmatter:
            continue
        account_name = normalize_account_key(frontmatter.get("account"))
        contacts.append(
            {
                "name": frontmatter.get("full-name") or frontmatter.get("full--name") or os.path.splitext(os.path.basename(path))[0],
                "account_name": account_name,
                "warmth_score": int(frontmatter.get("warmth-score") or 0),
                "last_contacted": str(frontmatter.get("last-contacted") or ""),
                "role": body,
            }
        )
    return contacts


def stage_alignment(deal_stage, investor_stage):
    if not deal_stage:
        return 0
    if not investor_stage:
        return 5
    if deal_stage == investor_stage:
        return 15
    deal_rank = STAGE_ORDER.get(deal_stage)
    investor_rank = STAGE_ORDER.get(investor_stage)
    if deal_rank is None or investor_rank is None:
        return 5
    if abs(deal_rank - investor_rank) <= 1:
        return 8
    return 0


def raise_alignment(target_raise, check_size_range):
    if not target_raise:
        return 0
    minimum, maximum = check_size_range
    if minimum is None and maximum is None:
        return 5
    if maximum is None:
        return 12 if target_raise >= minimum else 0
    if minimum <= target_raise <= maximum:
        return 20
    if minimum * 0.5 <= target_raise <= maximum * 1.5:
        return 10
    return 0


def geography_alignment(deal_locations, investor_locations):
    if not deal_locations or not investor_locations:
        return 0
    if deal_locations & investor_locations:
        return 12
    if "southeast asia" in investor_locations and deal_locations & {"philippines", "manila", "indonesia", "singapore"}:
        return 10
    if "emerging market" in investor_locations and deal_locations:
        return 8
    if "global" in investor_locations:
        return 4
    return 0


def explicit_interest_bonus(deal, investor):
    body_text = (deal["body"] or "").lower()
    if investor["canonical_name"] and investor["canonical_name"] in canonical_key(body_text):
        return 25
    if deal["canonical_name"] and deal["canonical_name"] in canonical_key(investor["body"]):
        return 15
    return 0


def calculate_match(deal, investor):
    score = 0
    reasons = []

    direct_bonus = explicit_interest_bonus(deal, investor)
    if direct_bonus:
        score += direct_bonus
        reasons.append("already named in CRM strategy or target-client context")

    sector_overlap = deal["categories"] & investor["categories"]
    if sector_overlap:
        sector_score = 35 if len(sector_overlap) == 1 else 45
        score += sector_score
        reasons.append(f"sector alignment on {', '.join(sorted(sector_overlap))}")

    geo_score = geography_alignment(deal["location_tokens"], investor["location_tokens"])
    if geo_score:
        score += geo_score
        reasons.append("geography fit")

    stage_score = stage_alignment(deal["stage"], investor["stage"])
    if stage_score:
        score += stage_score
        reasons.append("stage fit")

    raise_score = raise_alignment(deal["target_raise"], investor["check_size_range"])
    if raise_score:
        score += raise_score
        reasons.append("raise-size fit")

    relationship_bonus = min(15, int(round(investor["relationship_score"] / 7)))
    if relationship_bonus:
        score += relationship_bonus
        reasons.append("existing relationship warmth")

    if score < 50:
        return None

    confidence = min(100, score)
    return {
        "deal": deal["name"],
        "investor": investor["organization_name"],
        "score": confidence,
        "fit_score": confidence - relationship_bonus,
        "relationship_score": relationship_bonus,
        "rationale": "; ".join(reasons[:4]),
    }


def best_contact_for_investor(investor, contacts):
    candidates = []
    target_names = {
        normalize_account_key(investor["organization_name"]),
        normalize_account_key(investor["name"]),
    }
    for contact in contacts:
        if contact["account_name"] in target_names and contact["warmth_score"] >= 40:
            candidates.append(contact)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item["warmth_score"], item["last_contacted"]), reverse=True)[0]


def build_warm_paths(matches, investors, contacts):
    investor_index = {
        normalize_account_key(item["organization_name"]): item
        for item in investors
    }
    warm_paths = []
    for match in matches:
        if match["score"] < 60:
            continue
        investor = investor_index.get(normalize_account_key(match["investor"]))
        if not investor:
            continue
        contact = best_contact_for_investor(investor, contacts)
        if not contact:
            continue
        rationale = (
            f"{contact['name']} is an active relationship at {investor['organization_name']} "
            f"(warmth {contact['warmth_score']}) and provides the clearest current path for {match['deal']}. "
            f"Match rationale: {match['rationale']}."
        )
        warm_paths.append(
            {
                "deal": match["deal"],
                "person": investor["organization_name"],
                "connection": contact["name"].replace(" ", "-"),
                "rationale": rationale,
                "match_score": match["score"],
            }
        )

    deduped = {}
    for item in warm_paths:
        key = (item["deal"], item["connection"])
        current = deduped.get(key)
        if not current or item["match_score"] > current["match_score"]:
            deduped[key] = item
    return sorted(deduped.values(), key=lambda item: item["match_score"], reverse=True)


def main():
    print("Running Brokerage Matchmaker...")
    deals = collect_deals()
    investors = collect_investors()
    contacts = collect_contacts()

    all_matches = []
    for deal in deals:
        for investor in investors:
            match = calculate_match(deal, investor)
            if match:
                all_matches.append(match)

    deduped = {}
    for match in all_matches:
        key = (match["deal"], match["investor"])
        current = deduped.get(key)
        if not current or match["score"] > current["score"]:
            deduped[key] = match

    matches = sorted(deduped.values(), key=lambda item: (item["score"], item["fit_score"]), reverse=True)
    warm_paths = build_warm_paths(matches, investors, contacts)

    os.makedirs(os.path.dirname(MATCHES_PATH), exist_ok=True)
    with open(MATCHES_PATH, "w", encoding="utf-8") as handle:
        json.dump(matches, handle, indent=2)
        handle.write("\n")
    with open(WARM_PATHS_PATH, "w", encoding="utf-8") as handle:
        json.dump(warm_paths, handle, indent=2)
        handle.write("\n")

    print(f"Matchmaker complete. Found {len(matches)} credible matches and {len(warm_paths)} warm paths.")


if __name__ == "__main__":
    main()
