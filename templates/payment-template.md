---
id: "{{payment-id}}"
payment-name: "{{Payment Name}}"
owner: "{{Owner}}"
invoice: "[[Invoices/{{Invoice Link}}]]"
engagement: "[[Engagements/{{Engagement Link}}]]"
currency: "{{USD | PHP | SGD | EUR | GBP | other}}"
amount: 0
received-date: "{{YYYY-MM-DD}}"
payment-method: "{{bank-transfer | wire | cash | check | other}}"
status: "{{expected | received | reconciled | failed}}"
source: "{{manual | accounting-sync | gmail | bank-confirmation}}"
source-ref: "{{Source Reference}}"
date-created: "{{YYYY-MM-DD}}"
date-modified: "{{YYYY-MM-DD}}"
---

# **Payment: {{Payment Name}}**

## **Receipt Context**
{{What payment was received or expected, and what it settles.}}

## **Verification Notes**
{{Confirmation source, reconciliation status, and any mismatch or exception.}}
