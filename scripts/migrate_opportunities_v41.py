import os
from datetime import date

from frontmatter_utils import load_frontmatter_file, slugify, write_frontmatter_file


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
OPPORTUNITIES_DIR = os.path.join(CRM_DATA_PATH, "Opportunities")
ACCOUNTS_DIR = os.path.join(CRM_DATA_PATH, "Accounts")
CONTACTS_DIR = os.path.join(CRM_DATA_PATH, "Contacts")
ORGANIZATIONS_DIR = os.path.join(CRM_DATA_PATH, "Organizations")
DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deals")
LEGACY_DEALS_DIR = os.path.join(CRM_DATA_PATH, "Deal-Flow")


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


def wikilink(path_prefix, slug):
    return f"[[{path_prefix}/{slug}]]"


def build_index(directory):
    index = {}
    if not os.path.exists(directory):
        return index
    for file_name in os.listdir(directory):
        if not file_name.endswith(".md"):
            continue
        slug = os.path.splitext(file_name)[0]
        index[canonical(slug)] = slug
    return index


ACCOUNT_INDEX = build_index(ACCOUNTS_DIR)
CONTACT_INDEX = build_index(CONTACTS_DIR)
ORGANIZATION_INDEX = build_index(ORGANIZATIONS_DIR)
DEAL_INDEX = build_index(DEALS_DIR)
LEGACY_DEAL_INDEX = build_index(LEGACY_DEALS_DIR)


def normalize_entity_link(value, index, prefix, fallback_slug=None):
    key = canonical(value or fallback_slug)
    if not key:
        return ""
    slug = index.get(key)
    if not slug:
        return ""
    return wikilink(prefix, slug)


def normalize_deal_link(value):
    key = canonical(value)
    if not key:
        return ""
    if key in DEAL_INDEX:
        return wikilink("Deals", DEAL_INDEX[key])
    if key in LEGACY_DEAL_INDEX:
        return wikilink("Deal-Flow", LEGACY_DEAL_INDEX[key])
    return ""


def infer_opportunity_type(product_service, name, existing):
    existing_value = str(existing or "").strip().lower()
    if existing_value in {"advisory", "consulting", "financing", "hiring", "partnership"}:
        return existing_value

    text = f"{product_service} {name}".lower()
    if any(token in text for token in ["hiring", "role", "leadership", "ceo", "adjunct", "course"]):
        return "hiring"
    if any(token in text for token in ["financing", "fundraising", "debt", "equity", "series", "capital raise"]):
        return "financing"
    if any(token in text for token in ["partnership", "referral", "deal flow", "introduction", "bd", "ecosystem"]):
        return "partnership"
    if any(token in text for token in ["advisory", "advisor", "advice", "strategic"]):
        return "advisory"
    if any(token in text for token in ["implementation", "execution", "build", "gtm"]):
        return "consulting"
    return "other"


def normalize_stage(value, status):
    stage = str(value or "").strip().lower()
    status_value = str(status or "").strip().lower()
    if not stage and status_value:
        if status_value in {"engaged", "active"}:
            return "discovery"
        if status_value in {"won", "closed-won"}:
            return "closed-won"
        if status_value in {"lost", "closed-lost"}:
            return "closed-lost"
    return stage or "discovery"


def as_int(value, default=0):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value or "").strip()
    digits = []
    for ch in text:
        if ch.isdigit():
            digits.append(ch)
    return int("".join(digits)) if digits else default


def infer_probability(stage, existing):
    if existing not in (None, "", []):
        return as_int(existing)
    defaults = {
        "discovery": 10,
        "qualification": 25,
        "proposal": 50,
        "negotiation": 75,
        "closed-won": 100,
        "closed-lost": 0,
    }
    return defaults.get(stage, 10)


def infer_is_active(stage, existing):
    if stage in {"closed-won", "closed-lost"}:
        return False
    if existing in (True, False):
        return existing
    return True


def normalize_influencers(value):
    if isinstance(value, list):
        values = value
    elif value in (None, "", []):
        values = []
    else:
        values = [value]
    normalized = []
    for item in values:
        link = normalize_entity_link(item, CONTACT_INDEX, "Contacts")
        if not link and str(item).strip():
            raw = normalize_link(item)
            if raw:
                if raw.startswith("Contacts/"):
                    link = f"[[{raw}]]"
                elif raw.startswith("[["):
                    link = raw
                else:
                    link = f"[[{raw}]]"
        if link and link not in normalized:
            normalized.append(link)
    return normalized


def infer_organization_link(account_link, existing_org):
    direct = normalize_entity_link(existing_org, ORGANIZATION_INDEX, "Organizations")
    if direct:
        return direct
    account_key = canonical(account_link)
    slug = ORGANIZATION_INDEX.get(account_key)
    if not slug:
        return ""
    return wikilink("Organizations", slug)


def build_frontmatter(file_name, frontmatter):
    basename = os.path.splitext(file_name)[0]
    today = date.today().strftime("%Y-%m-%d")
    name = frontmatter.get("opportunity-name") or frontmatter.get("name") or basename
    account_link = normalize_entity_link(frontmatter.get("account"), ACCOUNT_INDEX, "Accounts")
    primary_contact = normalize_entity_link(frontmatter.get("primary-contact"), CONTACT_INDEX, "Contacts")
    stage = normalize_stage(frontmatter.get("stage"), frontmatter.get("status"))
    commercial_value = max(as_int(frontmatter.get("commercial-value")), as_int(frontmatter.get("deal-value")), as_int(frontmatter.get("value")))
    organization_link = infer_organization_link(account_link, frontmatter.get("organization"))
    deal_link = normalize_deal_link(frontmatter.get("deal"))

    normalized = {
        "id": frontmatter.get("id") or slugify(name),
        "opportunity-name": name,
        "owner": frontmatter.get("owner") or "john",
        "date-created": frontmatter.get("date-created") or today,
        "date-modified": today,
        "account": account_link,
        "deal": deal_link,
        "primary-contact": primary_contact,
        "source-lead": frontmatter.get("source-lead") or "",
        "organization": organization_link,
        "opportunity-type": infer_opportunity_type(
            frontmatter.get("product-service") or frontmatter.get("value"),
            name,
            frontmatter.get("opportunity-type"),
        ),
        "is-active": infer_is_active(stage, frontmatter.get("is-active")),
        "stage": stage,
        "commercial-value": commercial_value,
        "deal-value": commercial_value,
        "close-date": frontmatter.get("close-date") or frontmatter.get("date-created") or today,
        "probability": infer_probability(stage, frontmatter.get("probability")),
        "product-service": frontmatter.get("product-service") or frontmatter.get("value") or "",
        "influencers": normalize_influencers(frontmatter.get("influencers")),
        "source": frontmatter.get("source") or "manual",
        "source-ref": frontmatter.get("source-ref") or "",
        "lost-at-stage": frontmatter.get("lost-at-stage") if stage == "closed-lost" else "",
        "lost-reason": frontmatter.get("lost-reason") if stage == "closed-lost" else "",
        "lost-date": frontmatter.get("lost-date") if stage == "closed-lost" else "",
    }

    if stage == "closed-lost" and not normalized["lost-at-stage"]:
        normalized["lost-at-stage"] = "proposal"
    if stage == "closed-lost" and not normalized["lost-date"]:
        normalized["lost-date"] = normalized["close-date"]

    return normalized


def migrate():
    updated = []
    for file_name in sorted(os.listdir(OPPORTUNITIES_DIR)):
        if not file_name.endswith(".md"):
            continue
        path = os.path.join(OPPORTUNITIES_DIR, file_name)
        frontmatter, body = load_frontmatter_file(path)
        if not frontmatter:
            continue
        normalized = build_frontmatter(file_name, frontmatter)
        write_frontmatter_file(path, normalized, body)
        updated.append(path)

    print("updated-opportunities:", len(updated))
    for path in updated:
        print(path)


if __name__ == "__main__":
    migrate()
