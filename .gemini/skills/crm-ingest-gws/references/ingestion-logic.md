# CRM Ingestion Logic Reference

## Center of Gravity Rules
When an interaction is ingested, the primary parent of the resulting Activity record should follow this precedence:

1. **Opportunity**: If a contact is linked to an active Opportunity (via `primary-contact` or `influencers`), that Opportunity is the primary parent.
2. **Contact**: If the contact is known but not linked to any active Opportunity.
3. **Lead**: If the contact is matched to an existing Lead.
4. **Account**: If the contact is known but only linked to an Account (fallback).

## Matching Logic
- **Email Match**: Exact case-insensitive match on the `email` field of Contacts and Leads.
- **Discovery**: If no email match is found, evaluate the domain and local part against `noise_domains.json`.
  - Professional outbound/inbound -> New Lead.
  - Personal/Service -> Ignore.

## Deduplication
- **Source Reference**: Every Activity created from Gmail or Calendar MUST have a `source-ref` field (e.g., Gmail `messageId` or Calendar `eventId`).
- **Check before creation**: Always search existing Activities for the same `source-ref` before creating a new one.

## Content Enrichment
- **Gmail**: Read the `payload` for `text/plain` or `text/html`. Strip tags and summarize.
- **Calendar**: Read the `description` and `location`. Include attendee list in the summary.
- **Tasks**: Look for action-oriented language (e.g., "I'll follow up," "Please send me," "Meeting next week") to suggest Task records.

## Checkpointing
- **Persistent State**: `crm-data/staging/workspace_sync_state.json`
- **Fields**: `gmail_last_sync_at`, `calendar_last_sync_at`.
- **Format**: ISO 8601 string in UTC.
- **Manual Override**: The `--since` flag overrides the checkpoint.
