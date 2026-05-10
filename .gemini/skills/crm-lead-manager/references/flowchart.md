# CRM Lead Manager Flowchart

```mermaid
flowchart TD
    A["Start: identified person, organization, or both"] --> B{"Enough to create a lead?"}
    B -->|Yes| C["Create Lead<br/>status = new"]
    B -->|No| Z["Keep in discovery / inbox"]

    C --> D{"Meaningful engagement exists?<br/>email, call, meeting, activity"}
    D -->|No| E["Stay in new"]
    D -->|Yes| F["Move to engaged"]

    E --> R{"Still viable,<br/>but review later?"}
    R -->|Yes| S["Move to deferred<br/>create waiting task with review date"]
    R -->|No| D

    F --> G{"Known contact AND known organization<br/>AND intent to pursue relationship?"}
    G -->|No| H["Keep enriching lead<br/>add activity, notes, tasks"]
    G -->|Yes| I["Move to qualified"]

    I --> J{"What is the conversion path?"}

    J -->|Commercial opportunity identified| K["Convert to:<br/>Organization + Contact + Account + Opportunity"]
    J -->|Deal / Partner / Supplier<br/>without active opportunity| L["Convert to:<br/>Organization + Contact"]
    J -->|Not ready| M["Stay qualified<br/>until path is clear"]

    K --> N["Move linked notes, activities, and tasks<br/>onto new operating records"]
    L --> O["Link lead history to new<br/>relationship records"]

    N --> P["Archive lead as converted"]
    O --> P

    P --> Q["End"]

    H --> D
    M --> J
    S --> D
```

## Notes

- `new` means identified but not yet meaningfully engaged.
- `deferred` means still viable but parked for later review; use a `waiting` task with a future `due-date`.
- `engaged` requires a real interaction with a known contact.
- `qualified` requires a known contact, known organization, and intent to pursue a structured relationship.
- `converted` can follow either the commercial path or the relationship-only path.
