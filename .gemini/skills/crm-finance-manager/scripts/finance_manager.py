import argparse
import os
import sys
from datetime import date, datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from crm_manager_utils import link_for_path, load_display_name, replace_section, resolve_optional_record_path, resolve_record_path  # noqa: E402
from frontmatter_utils import iter_markdown_files, load_frontmatter_file, parse_markdown_frontmatter, slugify, write_frontmatter_file  # noqa: E402
from lead_manager import get_crm_data_path  # noqa: E402
from navigation_manager import record_mutation  # noqa: E402


VALID_RETAINER_STATUSES = {"planned", "active", "completed", "cancelled"}
VALID_INVOICE_STATUSES = {"draft", "issued", "partially-paid", "paid", "void", "overdue"}
VALID_PAYMENT_STATUSES = {"expected", "received", "reconciled", "failed"}
VALID_RETAINER_CADENCE = {"weekly", "monthly", "quarterly", "custom"}
VALID_PAYMENT_METHODS = {"bank-transfer", "wire", "cash", "check", "other"}
VALID_ENTITY_TYPES = {"retainer", "invoice", "payment"}
PAID_PAYMENT_STATUSES = {"received", "reconciled"}

CRM_DATA_PATH = get_crm_data_path()
ENGAGEMENTS_DIR = os.path.join(CRM_DATA_PATH, "Engagements")
WORKSTREAMS_DIR = os.path.join(CRM_DATA_PATH, "Workstreams")
RETAINERS_DIR = os.path.join(CRM_DATA_PATH, "Retainers")
INVOICES_DIR = os.path.join(CRM_DATA_PATH, "Invoices")
PAYMENTS_DIR = os.path.join(CRM_DATA_PATH, "Payments")

RETAINER_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "retainer-template.md")
INVOICE_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "invoice-template.md")
PAYMENT_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "payment-template.md")


def ensure_dirs():
    os.makedirs(RETAINERS_DIR, exist_ok=True)
    os.makedirs(INVOICES_DIR, exist_ok=True)
    os.makedirs(PAYMENTS_DIR, exist_ok=True)


def read_template(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def render_template(path, replacements):
    rendered = read_template(path)
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def normalize_reference(value):
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2].strip()
    if text.endswith(".md"):
        text = text[:-3]
    return text.strip()


def ensure_choice(value, valid, label):
    if value not in valid:
        raise ValueError(f"Invalid {label} '{value}'. Expected one of: {', '.join(sorted(valid))}")
    return value


def normalize_amount(value):
    amount = float(value or 0)
    rounded = round(amount, 2)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def parse_date_value(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def load_engagement(reference):
    path = resolve_record_path(ENGAGEMENTS_DIR, CRM_DATA_PATH, reference, "Engagement")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def load_workstream(reference):
    path = resolve_record_path(WORKSTREAMS_DIR, CRM_DATA_PATH, reference, "Workstream")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def load_retainer(reference):
    path = resolve_record_path(RETAINERS_DIR, CRM_DATA_PATH, reference, "Retainer")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def load_invoice(reference):
    path = resolve_record_path(INVOICES_DIR, CRM_DATA_PATH, reference, "Invoice")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def load_payment(reference):
    path = resolve_record_path(PAYMENTS_DIR, CRM_DATA_PATH, reference, "Payment")
    frontmatter, body = load_frontmatter_file(path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {path}")
    return path, frontmatter, body


def retainer_related_links(frontmatter):
    return [frontmatter.get("engagement", "")]


def invoice_related_links(frontmatter):
    return [
        frontmatter.get("engagement", ""),
        frontmatter.get("workstream", ""),
        frontmatter.get("retainer", ""),
    ]


def payment_related_links(frontmatter):
    return [
        frontmatter.get("invoice", ""),
        frontmatter.get("engagement", ""),
    ]


def build_retainer_body(summary, coverage):
    rendered = render_template(
        RETAINER_TEMPLATE_PATH,
        {
            "retainer-id": "ret-placeholder",
            "Retainer Name": "Retainer",
            "Owner": "john",
            "Engagement Link": "",
            "USD | PHP | SGD | EUR | GBP | other": "USD",
            "weekly | monthly | quarterly | custom": "monthly",
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
            "planned | active | completed | cancelled": "planned",
            "manual | engagement-admin | accounting-sync": "manual",
            "Source Reference": "",
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = replace_section(body, "Commercial Summary", summary or "Created through crm-finance-manager.")
    body = replace_section(body, "Coverage", coverage or "")
    return body


def build_invoice_body(context, notes, amount, currency, due_date, engagement_link, workstream_link):
    rendered = render_template(
        INVOICE_TEMPLATE_PATH,
        {
            "invoice-id": "inv-placeholder",
            "Invoice Name": "Invoice",
            "Owner": "john",
            "Engagement Link": engagement_link,
            "Workstream Link": workstream_link,
            "Retainer Link": "",
            "Invoice Number": "",
            "USD | PHP | SGD | EUR | GBP | other": currency,
            "Amount": amount,
            "Currency": currency,
            "YYYY-MM-DD": due_date,
            "draft | issued | partially-paid | paid | void | overdue": "draft",
            "manual | engagement-admin | accounting-sync | gmail": "manual",
            "Source Reference": "",
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = replace_section(body, "Billing Context", context or "Created through crm-finance-manager.")
    body = replace_section(body, "Notes", notes or "")
    return body


def build_payment_body(context, verification_notes):
    rendered = render_template(
        PAYMENT_TEMPLATE_PATH,
        {
            "payment-id": "pay-placeholder",
            "Payment Name": "Payment",
            "Owner": "john",
            "Invoice Link": "",
            "Engagement Link": "",
            "USD | PHP | SGD | EUR | GBP | other": "USD",
            "YYYY-MM-DD": date.today().strftime("%Y-%m-%d"),
            "bank-transfer | wire | cash | check | other": "bank-transfer",
            "expected | received | reconciled | failed": "received",
            "manual | accounting-sync | gmail | bank-confirmation": "manual",
            "Source Reference": "",
        },
    )
    _frontmatter, body = parse_markdown_frontmatter(rendered)
    body = replace_section(body, "Receipt Context", context or "Created through crm-finance-manager.")
    body = replace_section(body, "Verification Notes", verification_notes or "")
    return body


def workstream_belongs_to_engagement(workstream_fm, engagement_path):
    return normalize_reference(workstream_fm.get("engagement")) == normalize_reference(link_for_path(engagement_path, CRM_DATA_PATH))


def find_payments_for_invoice(invoice_link):
    payments = []
    for file_path in iter_markdown_files(PAYMENTS_DIR):
        frontmatter, body = load_frontmatter_file(file_path)
        if normalize_reference(frontmatter.get("invoice")) == normalize_reference(invoice_link):
            payments.append((file_path, frontmatter, body))
    return payments


def payments_total(payments):
    total = 0.0
    for _file_path, frontmatter, _body in payments:
        if frontmatter.get("status") in PAID_PAYMENT_STATUSES:
            total += float(frontmatter.get("amount") or 0)
    return round(total, 2)


def determine_invoice_status(invoice_fm, paid_total):
    current = str(invoice_fm.get("status") or "draft")
    if current == "void":
        return "void"
    amount = float(invoice_fm.get("amount") or 0)
    if paid_total > 0 and amount > 0 and paid_total + 0.0001 >= amount:
        return "paid"
    if paid_total > 0:
        return "partially-paid"
    if current == "draft":
        return "draft"
    due_date = parse_date_value(invoice_fm.get("due-date"))
    if due_date and due_date < date.today():
        return "overdue"
    return "issued"


def reconcile_invoice_status(invoice_path, invoice_fm, invoice_body, source="finance-reconcile", persist=True):
    invoice_link = link_for_path(invoice_path, CRM_DATA_PATH)
    payments = find_payments_for_invoice(invoice_link)
    paid_total = payments_total(payments)
    new_status = determine_invoice_status(invoice_fm, paid_total)
    if persist and invoice_fm.get("status") != new_status:
        invoice_fm["status"] = new_status
        invoice_fm["date-modified"] = date.today().strftime("%Y-%m-%d")
        write_frontmatter_file(invoice_path, invoice_fm, invoice_body)
        record_mutation(
            action="update",
            entity_type="Invoice",
            title=invoice_fm.get("invoice-name", load_display_name(invoice_path)),
            path=invoice_path,
            source=source,
            related=invoice_related_links(invoice_fm),
            details=f"status={new_status}; paid-total={normalize_amount(paid_total)}",
            crm_data_path=CRM_DATA_PATH,
        )
    return paid_total, new_status, payments


def cmd_create_retainer(args):
    ensure_dirs()
    ensure_choice(args.status, VALID_RETAINER_STATUSES, "status")
    ensure_choice(args.cadence, VALID_RETAINER_CADENCE, "cadence")

    engagement_path, engagement_fm, _engagement_body = load_engagement(args.engagement)
    engagement_name = engagement_fm.get("engagement-name", load_display_name(engagement_path))
    retainer_name = args.name or f"{engagement_name} - {args.cadence.title()} Retainer"
    file_path = os.path.join(RETAINERS_DIR, f"{slugify(retainer_name)}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Retainer already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        RETAINER_TEMPLATE_PATH,
        {
            "retainer-id": slugify(retainer_name),
            "Retainer Name": retainer_name,
            "Owner": args.owner or engagement_fm.get("owner", "john"),
            "Engagement Link": os.path.splitext(os.path.relpath(engagement_path, CRM_DATA_PATH))[0],
            "USD | PHP | SGD | EUR | GBP | other": args.currency,
            "weekly | monthly | quarterly | custom": args.cadence,
            "YYYY-MM-DD": args.period_start or today,
            "planned | active | completed | cancelled": args.status,
            "manual | engagement-admin | accounting-sync": args.source,
            "Source Reference": args.source_ref or "",
        },
    )
    frontmatter, _body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = f"ret-{slugify(retainer_name)}"
    frontmatter["retainer-name"] = retainer_name
    frontmatter["owner"] = args.owner or engagement_fm.get("owner", "john")
    frontmatter["engagement"] = link_for_path(engagement_path, CRM_DATA_PATH)
    frontmatter["currency"] = args.currency
    frontmatter["amount"] = normalize_amount(args.amount)
    frontmatter["cadence"] = args.cadence
    frontmatter["period-start"] = args.period_start or today
    frontmatter["period-end"] = args.period_end or ""
    frontmatter["status"] = args.status
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = build_retainer_body(args.summary or "", args.coverage or "")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Retainer",
        title=retainer_name,
        path=file_path,
        source=args.source,
        related=retainer_related_links(frontmatter),
        details=f"amount={frontmatter['amount']} {args.currency}; cadence={args.cadence}; status={args.status}",
        crm_data_path=CRM_DATA_PATH,
    )
    print(file_path)


def cmd_create_invoice(args):
    ensure_dirs()
    ensure_choice(args.status, VALID_INVOICE_STATUSES, "status")

    engagement_path, engagement_fm, _engagement_body = load_engagement(args.engagement)
    workstream_path = resolve_optional_record_path(WORKSTREAMS_DIR, CRM_DATA_PATH, args.workstream, "Workstream")
    retainer_path = resolve_optional_record_path(RETAINERS_DIR, CRM_DATA_PATH, args.retainer, "Retainer")

    if workstream_path:
        workstream_fm, _body = load_frontmatter_file(workstream_path)
        if not workstream_belongs_to_engagement(workstream_fm, engagement_path):
            raise ValueError("Workstream does not belong to the specified engagement.")
    if retainer_path:
        retainer_fm, _body = load_frontmatter_file(retainer_path)
        if normalize_reference(retainer_fm.get("engagement")) != normalize_reference(link_for_path(engagement_path, CRM_DATA_PATH)):
            raise ValueError("Retainer does not belong to the specified engagement.")

    engagement_name = engagement_fm.get("engagement-name", load_display_name(engagement_path))
    issue_date = args.issue_date or date.today().strftime("%Y-%m-%d")
    invoice_number = args.invoice_number or f"INV-{issue_date.replace('-', '')}-{slugify(engagement_name)[:12].upper()}"
    invoice_name = args.name or f"{engagement_name} - {invoice_number}"
    file_path = os.path.join(INVOICES_DIR, f"{slugify(invoice_name)}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Invoice already exists: {file_path}")

    workstream_link_target = os.path.splitext(os.path.relpath(workstream_path, CRM_DATA_PATH))[0] if workstream_path else ""
    retainer_link_target = os.path.splitext(os.path.relpath(retainer_path, CRM_DATA_PATH))[0] if retainer_path else ""
    rendered = render_template(
        INVOICE_TEMPLATE_PATH,
        {
            "invoice-id": slugify(invoice_name),
            "Invoice Name": invoice_name,
            "Owner": args.owner or engagement_fm.get("owner", "john"),
            "Engagement Link": os.path.splitext(os.path.relpath(engagement_path, CRM_DATA_PATH))[0],
            "Workstream Link": workstream_link_target,
            "Retainer Link": retainer_link_target,
            "Invoice Number": invoice_number,
            "USD | PHP | SGD | EUR | GBP | other": args.currency,
            "Amount": normalize_amount(args.amount),
            "Currency": args.currency,
            "YYYY-MM-DD": args.due_date,
            "draft | issued | partially-paid | paid | void | overdue": args.status,
            "manual | engagement-admin | accounting-sync | gmail": args.source,
            "Source Reference": args.source_ref or "",
        },
    )
    frontmatter, _body = parse_markdown_frontmatter(rendered)
    today = date.today().strftime("%Y-%m-%d")
    frontmatter["id"] = f"inv-{slugify(invoice_name)}"
    frontmatter["invoice-name"] = invoice_name
    frontmatter["owner"] = args.owner or engagement_fm.get("owner", "john")
    frontmatter["engagement"] = link_for_path(engagement_path, CRM_DATA_PATH)
    frontmatter["workstream"] = link_for_path(workstream_path, CRM_DATA_PATH) if workstream_path else ""
    frontmatter["retainer"] = link_for_path(retainer_path, CRM_DATA_PATH) if retainer_path else ""
    frontmatter["invoice-number"] = invoice_number
    frontmatter["currency"] = args.currency
    frontmatter["amount"] = normalize_amount(args.amount)
    frontmatter["issue-date"] = issue_date
    frontmatter["due-date"] = args.due_date
    frontmatter["status"] = args.status
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = build_invoice_body(
        args.billing_context or "",
        args.notes or "",
        frontmatter["amount"],
        args.currency,
        args.due_date,
        os.path.splitext(os.path.relpath(engagement_path, CRM_DATA_PATH))[0],
        workstream_link_target,
    )
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Invoice",
        title=invoice_name,
        path=file_path,
        source=args.source,
        related=invoice_related_links(frontmatter),
        details=f"invoice-number={invoice_number}; amount={frontmatter['amount']} {args.currency}; status={args.status}",
        crm_data_path=CRM_DATA_PATH,
    )
    if args.status != "void":
        reconcile_invoice_status(file_path, frontmatter, body)
    print(file_path)


def cmd_record_payment(args):
    ensure_dirs()
    ensure_choice(args.status, VALID_PAYMENT_STATUSES, "status")
    ensure_choice(args.payment_method, VALID_PAYMENT_METHODS, "payment-method")

    invoice_path, invoice_fm, invoice_body = load_invoice(args.invoice)
    engagement_path = resolve_record_path(ENGAGEMENTS_DIR, CRM_DATA_PATH, invoice_fm.get("engagement"), "Engagement")
    currency = args.currency or invoice_fm.get("currency") or "USD"
    if currency != invoice_fm.get("currency"):
        raise ValueError("Payment currency must match the linked invoice currency.")

    received_date = args.received_date or date.today().strftime("%Y-%m-%d")
    payment_name = args.name or f"{invoice_fm.get('invoice-number', load_display_name(invoice_path))} Payment {received_date}"
    file_path = os.path.join(PAYMENTS_DIR, f"{slugify(payment_name)}.md")
    if os.path.exists(file_path):
        raise FileExistsError(f"Payment already exists: {file_path}")

    today = date.today().strftime("%Y-%m-%d")
    rendered = render_template(
        PAYMENT_TEMPLATE_PATH,
        {
            "payment-id": slugify(payment_name),
            "Payment Name": payment_name,
            "Owner": args.owner or invoice_fm.get("owner", "john"),
            "Invoice Link": os.path.splitext(os.path.relpath(invoice_path, CRM_DATA_PATH))[0],
            "Engagement Link": os.path.splitext(os.path.relpath(engagement_path, CRM_DATA_PATH))[0],
            "USD | PHP | SGD | EUR | GBP | other": currency,
            "YYYY-MM-DD": received_date,
            "bank-transfer | wire | cash | check | other": args.payment_method,
            "expected | received | reconciled | failed": args.status,
            "manual | accounting-sync | gmail | bank-confirmation": args.source,
            "Source Reference": args.source_ref or "",
        },
    )
    frontmatter, _body = parse_markdown_frontmatter(rendered)
    frontmatter["id"] = f"pay-{slugify(payment_name)}"
    frontmatter["payment-name"] = payment_name
    frontmatter["owner"] = args.owner or invoice_fm.get("owner", "john")
    frontmatter["invoice"] = link_for_path(invoice_path, CRM_DATA_PATH)
    frontmatter["engagement"] = link_for_path(engagement_path, CRM_DATA_PATH)
    frontmatter["currency"] = currency
    frontmatter["amount"] = normalize_amount(args.amount)
    frontmatter["received-date"] = received_date
    frontmatter["payment-method"] = args.payment_method
    frontmatter["status"] = args.status
    frontmatter["source"] = args.source
    frontmatter["source-ref"] = args.source_ref or ""
    frontmatter["date-created"] = today
    frontmatter["date-modified"] = today

    body = build_payment_body(args.receipt_context or "", args.verification_notes or "")
    write_frontmatter_file(file_path, frontmatter, body)
    record_mutation(
        action="create",
        entity_type="Payment",
        title=payment_name,
        path=file_path,
        source=args.source,
        related=payment_related_links(frontmatter),
        details=f"amount={frontmatter['amount']} {currency}; status={args.status}",
        crm_data_path=CRM_DATA_PATH,
    )
    reconcile_invoice_status(invoice_path, invoice_fm, invoice_body)
    print(file_path)


def cmd_set_status(args):
    today = date.today().strftime("%Y-%m-%d")

    if args.entity_type == "retainer":
        file_path, frontmatter, body = load_retainer(args.record)
        status = ensure_choice(args.status, VALID_RETAINER_STATUSES, "status")
        frontmatter["status"] = status
        frontmatter["date-modified"] = today
        if args.period_end is not None:
            frontmatter["period-end"] = args.period_end
        write_frontmatter_file(file_path, frontmatter, body)
        record_mutation(
            action="update",
            entity_type="Retainer",
            title=frontmatter.get("retainer-name", load_display_name(file_path)),
            path=file_path,
            source=frontmatter.get("source", ""),
            related=retainer_related_links(frontmatter),
            details=f"status={status}",
            crm_data_path=CRM_DATA_PATH,
        )
    elif args.entity_type == "invoice":
        file_path, frontmatter, body = load_invoice(args.record)
        status = ensure_choice(args.status, VALID_INVOICE_STATUSES, "status")
        frontmatter["status"] = status
        frontmatter["date-modified"] = today
        if args.due_date is not None:
            frontmatter["due-date"] = args.due_date
        write_frontmatter_file(file_path, frontmatter, body)
        record_mutation(
            action="update",
            entity_type="Invoice",
            title=frontmatter.get("invoice-name", load_display_name(file_path)),
            path=file_path,
            source=frontmatter.get("source", ""),
            related=invoice_related_links(frontmatter),
            details=f"status={status}",
            crm_data_path=CRM_DATA_PATH,
        )
    else:
        file_path, frontmatter, body = load_payment(args.record)
        status = ensure_choice(args.status, VALID_PAYMENT_STATUSES, "status")
        frontmatter["status"] = status
        frontmatter["date-modified"] = today
        if args.received_date is not None:
            frontmatter["received-date"] = args.received_date
        write_frontmatter_file(file_path, frontmatter, body)
        record_mutation(
            action="update",
            entity_type="Payment",
            title=frontmatter.get("payment-name", load_display_name(file_path)),
            path=file_path,
            source=frontmatter.get("source", ""),
            related=payment_related_links(frontmatter),
            details=f"status={status}",
            crm_data_path=CRM_DATA_PATH,
        )
        invoice_path, invoice_fm, invoice_body = load_invoice(frontmatter.get("invoice"))
        reconcile_invoice_status(invoice_path, invoice_fm, invoice_body)
    print(file_path)


def review_engagement(reference, verbose=False):
    engagement_path, engagement_fm, _engagement_body = load_engagement(reference)
    engagement_link = link_for_path(engagement_path, CRM_DATA_PATH)
    retainers = []
    invoices = []
    payments = []

    for file_path in iter_markdown_files(RETAINERS_DIR):
        frontmatter, body = load_frontmatter_file(file_path)
        if normalize_reference(frontmatter.get("engagement")) == normalize_reference(engagement_link):
            retainers.append((file_path, frontmatter, body))
    for file_path in iter_markdown_files(INVOICES_DIR):
        frontmatter, body = load_frontmatter_file(file_path)
        if normalize_reference(frontmatter.get("engagement")) == normalize_reference(engagement_link):
            invoices.append((file_path, frontmatter, body))
    for file_path in iter_markdown_files(PAYMENTS_DIR):
        frontmatter, body = load_frontmatter_file(file_path)
        if normalize_reference(frontmatter.get("engagement")) == normalize_reference(engagement_link):
            payments.append((file_path, frontmatter, body))

    total_retainers = round(sum(float(item[1].get("amount") or 0) for item in retainers if item[1].get("status") != "cancelled"), 2)
    total_invoiced = round(sum(float(item[1].get("amount") or 0) for item in invoices if item[1].get("status") != "void"), 2)
    total_received = payments_total(payments)
    outstanding = round(max(total_invoiced - total_received, 0), 2)
    overdue = [item for item in invoices if determine_invoice_status(item[1], payments_total(find_payments_for_invoice(link_for_path(item[0], CRM_DATA_PATH)))) == "overdue"]

    print(f"Engagement: {engagement_fm.get('engagement-name', load_display_name(engagement_path))}")
    print(f"Path: {engagement_path}")
    print(f"Commercial Model: {engagement_fm.get('commercial-model', '')}")
    print(f"Currency: {engagement_fm.get('currency', '')}")
    print(f"Retainers: {len(retainers)}")
    print(f"Invoices: {len(invoices)}")
    print(f"Payments: {len(payments)}")
    print(f"Retainer Value: {normalize_amount(total_retainers)}")
    print(f"Total Invoiced: {normalize_amount(total_invoiced)}")
    print(f"Total Received: {normalize_amount(total_received)}")
    print(f"Outstanding: {normalize_amount(outstanding)}")
    print(f"Overdue Invoices: {len(overdue)}")
    print("Recommended Next Action:")
    if not retainers and engagement_fm.get("commercial-model") == "retainer":
        print("- create the first retainer record for this engagement")
    elif not invoices:
        print("- issue the first invoice or confirm billing is intentionally deferred")
    elif overdue:
        print("- follow up the overdue invoice and reconcile payment state")
    elif outstanding > 0:
        print("- track the remaining receivable against issued invoices")
    else:
        print("- keep finance records current as new billing events occur")
    if verbose:
        for _file_path, frontmatter, _body in invoices:
            print(f"- invoice: {frontmatter.get('invoice-number', '')} | {frontmatter.get('status', '')} | {frontmatter.get('amount', 0)}")


def review_invoice(reference, verbose=False):
    invoice_path, invoice_fm, invoice_body = load_invoice(reference)
    paid_total, derived_status, payments = reconcile_invoice_status(invoice_path, invoice_fm, invoice_body, persist=False)
    amount = float(invoice_fm.get("amount") or 0)
    outstanding = round(max(amount - paid_total, 0), 2)

    print(f"Invoice: {invoice_fm.get('invoice-name', load_display_name(invoice_path))}")
    print(f"Path: {invoice_path}")
    print(f"Invoice Number: {invoice_fm.get('invoice-number', '')}")
    print(f"Engagement: {invoice_fm.get('engagement', '')}")
    print(f"Workstream: {invoice_fm.get('workstream', '') or 'none'}")
    print(f"Retainer: {invoice_fm.get('retainer', '') or 'none'}")
    print(f"Amount: {invoice_fm.get('amount', 0)} {invoice_fm.get('currency', '')}".strip())
    print(f"Paid Total: {normalize_amount(paid_total)}")
    print(f"Outstanding: {normalize_amount(outstanding)}")
    print(f"Status: {derived_status}")
    print(f"Due Date: {invoice_fm.get('due-date', '')}")
    print(f"Payments: {len(payments)}")
    print("Recommended Next Action:")
    if derived_status == "draft":
        print("- issue the invoice or void it if it should not be sent")
    elif derived_status == "overdue":
        print("- follow up payment and confirm whether funds have already landed")
    elif derived_status == "partially-paid":
        print("- reconcile the remaining balance against the client remittance")
    elif derived_status == "paid":
        print("- confirm final reconciliation and close any follow-up tasks")
    else:
        print("- monitor receivables and payment timing")
    if verbose:
        for _file_path, frontmatter, _body in payments:
            print(f"- payment: {frontmatter.get('payment-name', '')} | {frontmatter.get('status', '')} | {frontmatter.get('amount', 0)}")


def review_retainer(reference, verbose=False):
    retainer_path, retainer_fm, _retainer_body = load_retainer(reference)
    retainer_link = link_for_path(retainer_path, CRM_DATA_PATH)
    invoices = []
    for file_path in iter_markdown_files(INVOICES_DIR):
        frontmatter, body = load_frontmatter_file(file_path)
        if normalize_reference(frontmatter.get("retainer")) == normalize_reference(retainer_link):
            invoices.append((file_path, frontmatter, body))
    total_invoiced = round(sum(float(item[1].get("amount") or 0) for item in invoices if item[1].get("status") != "void"), 2)
    total_received = 0.0
    for file_path, _frontmatter, _body in invoices:
        total_received += payments_total(find_payments_for_invoice(link_for_path(file_path, CRM_DATA_PATH)))
    total_received = round(total_received, 2)

    print(f"Retainer: {retainer_fm.get('retainer-name', load_display_name(retainer_path))}")
    print(f"Path: {retainer_path}")
    print(f"Engagement: {retainer_fm.get('engagement', '')}")
    print(f"Amount: {retainer_fm.get('amount', 0)} {retainer_fm.get('currency', '')}".strip())
    print(f"Cadence: {retainer_fm.get('cadence', '')}")
    print(f"Period: {retainer_fm.get('period-start', '')} to {retainer_fm.get('period-end', '') or 'open'}")
    print(f"Status: {retainer_fm.get('status', '')}")
    print(f"Linked Invoices: {len(invoices)}")
    print(f"Invoiced Total: {normalize_amount(total_invoiced)}")
    print(f"Received Total: {normalize_amount(total_received)}")
    print("Recommended Next Action:")
    if not invoices and retainer_fm.get("status") == "active":
        print("- create the next invoice tied to this active retainer")
    elif total_invoiced > total_received:
        print("- reconcile the unpaid retainer balance against issued invoices")
    else:
        print("- keep the next billing period and coverage dates current")
    if verbose:
        for _file_path, frontmatter, _body in invoices:
            print(f"- invoice: {frontmatter.get('invoice-number', '')} | {frontmatter.get('status', '')} | {frontmatter.get('amount', 0)}")


def cmd_review(args):
    if args.scope == "engagement":
        review_engagement(args.reference, verbose=args.verbose)
    elif args.scope == "invoice":
        review_invoice(args.reference, verbose=args.verbose)
    else:
        review_retainer(args.reference, verbose=args.verbose)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage finance workflows for engagements, retainers, invoices, and payments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    retainer_parser = subparsers.add_parser("create-retainer", help="Create a canonical retainer under an engagement.")
    retainer_parser.add_argument("--engagement", required=True)
    retainer_parser.add_argument("--name")
    retainer_parser.add_argument("--amount", required=True, type=float)
    retainer_parser.add_argument("--currency", default="USD")
    retainer_parser.add_argument("--cadence", default="monthly")
    retainer_parser.add_argument("--period-start")
    retainer_parser.add_argument("--period-end")
    retainer_parser.add_argument("--status", default="planned")
    retainer_parser.add_argument("--summary")
    retainer_parser.add_argument("--coverage")
    retainer_parser.add_argument("--owner")
    retainer_parser.add_argument("--source", default="manual")
    retainer_parser.add_argument("--source-ref")
    retainer_parser.set_defaults(func=cmd_create_retainer)

    invoice_parser = subparsers.add_parser("create-invoice", help="Create a canonical invoice under an engagement.")
    invoice_parser.add_argument("--engagement", required=True)
    invoice_parser.add_argument("--workstream")
    invoice_parser.add_argument("--retainer")
    invoice_parser.add_argument("--name")
    invoice_parser.add_argument("--invoice-number")
    invoice_parser.add_argument("--amount", required=True, type=float)
    invoice_parser.add_argument("--currency", default="USD")
    invoice_parser.add_argument("--issue-date")
    invoice_parser.add_argument("--due-date", required=True)
    invoice_parser.add_argument("--status", default="draft")
    invoice_parser.add_argument("--billing-context")
    invoice_parser.add_argument("--notes")
    invoice_parser.add_argument("--owner")
    invoice_parser.add_argument("--source", default="manual")
    invoice_parser.add_argument("--source-ref")
    invoice_parser.set_defaults(func=cmd_create_invoice)

    payment_parser = subparsers.add_parser("record-payment", help="Record a payment against an invoice.")
    payment_parser.add_argument("--invoice", required=True)
    payment_parser.add_argument("--name")
    payment_parser.add_argument("--amount", required=True, type=float)
    payment_parser.add_argument("--currency")
    payment_parser.add_argument("--received-date")
    payment_parser.add_argument("--payment-method", default="bank-transfer")
    payment_parser.add_argument("--status", default="received")
    payment_parser.add_argument("--receipt-context")
    payment_parser.add_argument("--verification-notes")
    payment_parser.add_argument("--owner")
    payment_parser.add_argument("--source", default="manual")
    payment_parser.add_argument("--source-ref")
    payment_parser.set_defaults(func=cmd_record_payment)

    status_parser = subparsers.add_parser("set-status", help="Update the status of a retainer, invoice, or payment.")
    status_parser.add_argument("entity_type", choices=sorted(VALID_ENTITY_TYPES))
    status_parser.add_argument("record")
    status_parser.add_argument("--status", required=True)
    status_parser.add_argument("--period-end")
    status_parser.add_argument("--due-date")
    status_parser.add_argument("--received-date")
    status_parser.set_defaults(func=cmd_set_status)

    review_parser = subparsers.add_parser("review", help="Review finance state for an engagement, invoice, or retainer.")
    review_parser.add_argument("scope", choices=["engagement", "invoice", "retainer"])
    review_parser.add_argument("reference")
    review_parser.add_argument("--verbose", action="store_true")
    review_parser.set_defaults(func=cmd_review)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
