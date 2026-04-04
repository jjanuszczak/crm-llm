# CLI Patterns

## Current Backing Script
- [lead_manager.py](../scripts/lead_manager.py)

## Supported Commands

### Create a lead
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py create \
  --name "Jane Doe - Example Capital" \
  --person-name "Jane Doe" \
  --company-name "Example Capital" \
  --email "jane@examplecapital.com" \
  --lead-source referral \
  --priority high
```

### Move to engaged
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py set-status "Jane-Doe-Example-Capital" --status engaged
```

### Validate qualification readiness
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py validate-qualified "Jane-Doe-Example-Capital"
```

### Move to qualified
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py set-status "Jane-Doe-Example-Capital" --status qualified
```

### Revive a disqualified lead
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py revive "Jane-Doe-Example-Capital" --meaningful-two-way
```

### Convert using the current implemented path
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py convert \
  "Jane-Doe-Example-Capital" \
  --opportunity-name "Example Capital - Strategic Advisory - 2026"
```

### Convert using the relationship-only path
```bash
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py convert \
  "Jane-Doe-Example-Capital" \
  --conversion-mode relationship-only
```

## Compatibility Note
The old entrypoint at `scripts/lead_manager.py` remains as a wrapper so older repo commands and imports still work.
