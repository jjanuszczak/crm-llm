---
id: "{{invoice-id}}"
invoice-name: "{{Invoice Name}}"
owner: "{{Owner}}"
engagement: "[[Engagements/{{Engagement Link}}]]"
workstream: "[[Workstreams/{{Workstream Link}}]]"
retainer: "[[Retainers/{{Retainer Link}}]]"
invoice-number: "{{Invoice Number}}"
currency: "{{USD | PHP | SGD | EUR | GBP | other}}"
amount: 0
issue-date: "{{YYYY-MM-DD}}"
due-date: "{{YYYY-MM-DD}}"
status: "{{draft | issued | partially-paid | paid | void | overdue}}"
source: "{{manual | engagement-admin | accounting-sync | gmail}}"
source-ref: "{{Source Reference}}"
date-created: "{{YYYY-MM-DD}}"
date-modified: "{{YYYY-MM-DD}}"
---

# **Invoice: {{Invoice Name}}**

## **Billing Context**
{{What this invoice covers and why it was issued.}}

## **Commercial Details**
- **Engagement:** [[Engagements/{{Engagement Link}}]]
- **Workstream:** [[Workstreams/{{Workstream Link}}]]
- **Amount:** {{Amount}} {{Currency}}
- **Due:** {{YYYY-MM-DD}}

## **Notes**
{{Outstanding dependencies, payment follow-up context, or exceptions.}}
