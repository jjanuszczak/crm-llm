# Skill: Manage Intelligence

## Description
Manage staged discoveries and intelligence outputs in the v4 memory system.

## Usage
- `approve-discovery [name]`: Converts a staged discovery into a formal Account/Contact file.
- `ignore-discovery [email]`: Adds an email to the permanent ignore list and removes it from discoveries.
- `map-deal [name]`: Triggers a LinkedIn scrape of the startup leadership and matches against contacts.
- `map-opportunity [name]`: Triggers a LinkedIn scrape of the account stakeholders and matches against contacts.
- `refresh-intelligence`: Force a run of the intelligence engine.

## Implementation Steps

1.  **Paths:**
    *   `STAGING_DIR`: `CRM_DATA_PATH/staging/`
    *   `DISCOVERY_PATH`: `STAGING_DIR/discovery.json`
    *   `IGNORE_LIST_PATH`: `STAGING_DIR/ignore_list.json`
    *   `WARM_PATHS_PATH`: `STAGING_DIR/warm_paths.json`

2.  **approve-discovery [name]:**
    *   Load `discovery.json`.
    *   Find the entry matching the name.
    *   Use the appropriate `create-account` or `create-contact` skill with the data from the discovery entry (name, email, rationale).
    *   Remove the entry from `discovery.json`.
    *   Run `update-dashboard`.

3.  **ignore-discovery [email]:**
    *   Load `ignore_list.json`.
    *   Add the email to the list if not present.
    *   Save `ignore_list.json`.
    *   Remove any entries with that email from `discovery.json`.
    *   Run `update-dashboard`.

4.  **map-deal / map-opportunity [name]:**
    *   Find the corresponding file in `Deals/` or `Opportunities/`.
    *   Extract the `url` (for deals) or search for the `account` LinkedIn page (for opportunities).
    *   Navigate to LinkedIn using browser tools.
    *   Extract People/Leadership data.
    *   Compare names against `Contacts/` directory.
    *   Stage any matches in `CRM_DATA_PATH/staging/warm_paths.json`.
    *   Run `update-dashboard`.

5.  **refresh-intelligence:**
    *   Run `python3 scripts/intelligence-engine.py`.
    *   Run `update-dashboard`.
