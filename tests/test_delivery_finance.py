import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from frontmatter_utils import load_frontmatter_file, serialize_frontmatter


_MODULE_COUNTER = 0


def load_module(module_path: Path, base_name: str):
    global _MODULE_COUNTER
    _MODULE_COUNTER += 1
    module_name = f"{base_name}_{_MODULE_COUNTER}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_record(file_path: Path, frontmatter: dict, body: str = "# Record\n"):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(serialize_frontmatter(frontmatter) + body, encoding="utf-8")


class DeliveryFinanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.crm_data_path = Path(self.temp_dir.name)
        for directory in [
            "Engagements",
            "Workstreams",
            "Retainers",
            "Invoices",
            "Payments",
            "Source-Artifacts",
            "Tasks",
            "Activities",
            "Notes",
            "Leads",
            "Organizations",
            "Accounts",
            "Contacts",
        ]:
            (self.crm_data_path / directory).mkdir(parents=True, exist_ok=True)

    def load_finance_manager(self):
        with patch.dict(os.environ, {"CRM_DATA_PATH": str(self.crm_data_path)}, clear=False):
            return load_module(
                REPO_ROOT / ".gemini/skills/crm-finance-manager/scripts/finance_manager.py",
                "crm_finance_manager_test",
            )

    def load_dashboard_module(self):
        with patch.dict(os.environ, {"CRM_DATA_PATH": str(self.crm_data_path)}, clear=False):
            return load_module(
                REPO_ROOT / ".gemini/skills/update-dashboard/scripts/update-dashboard.py",
                "crm_update_dashboard_test",
            )

    def write_engagement(self, slug: str, name: str, *, status: str = "active", commercial_model: str = "retainer", currency: str = "USD"):
        write_record(
            self.crm_data_path / "Engagements" / f"{slug}.md",
            {
                "id": f"eng-{slug}",
                "engagement-name": name,
                "owner": "john",
                "organization": "[[Organizations/acme-holdings]]",
                "account": "[[Accounts/acme-holdings]]",
                "engagement-type": "advisory",
                "status": status,
                "start-date": "2026-06-01",
                "commercial-model": commercial_model,
                "currency": currency,
                "contracted-value": 12000,
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

    def write_workstream(self, slug: str, name: str, engagement_slug: str, *, status: str = "active"):
        write_record(
            self.crm_data_path / "Workstreams" / f"{slug}.md",
            {
                "id": f"ws-{slug}",
                "workstream-name": name,
                "owner": "john",
                "engagement": f"[[Engagements/{engagement_slug}]]",
                "organization": "[[Organizations/acme-holdings]]",
                "account": "[[Accounts/acme-holdings]]",
                "workstream-type": "research",
                "status": status,
                "priority": "high",
                "start-date": "2026-06-01",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

    def write_source_artifact(self, slug: str, parent_link: str):
        write_record(
            self.crm_data_path / "Source-Artifacts" / f"{slug}.md",
            {
                "id": f"src-{slug}",
                "title": slug.replace("-", " ").title(),
                "owner": "john",
                "primary-parent-type": "workstream",
                "primary-parent": parent_link,
                "secondary-links": [parent_link],
                "source-system": "google-drive",
                "source-type": "doc",
                "confidentiality": "internal-only",
                "status": "active",
                "source": "manual",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

    def test_create_invoice_rejects_workstream_from_different_engagement(self):
        self.write_engagement("alpha-engagement", "Alpha Engagement")
        self.write_engagement("beta-engagement", "Beta Engagement")
        self.write_workstream("beta-workstream", "Beta Workstream", "beta-engagement")
        finance = self.load_finance_manager()

        args = types.SimpleNamespace(
            engagement="Engagements/alpha-engagement",
            workstream="Workstreams/beta-workstream",
            retainer=None,
            name=None,
            invoice_number="INV-ALPHA-001",
            amount=1000,
            currency="USD",
            issue_date="2026-06-10",
            due_date="2026-06-30",
            status="issued",
            billing_context=None,
            notes=None,
            owner=None,
            source="manual",
            source_ref=None,
        )

        with self.assertRaisesRegex(ValueError, "Workstream does not belong to the specified engagement"):
            finance.cmd_create_invoice(args)

    def test_record_payment_reconciles_invoice_from_partial_to_paid(self):
        self.write_engagement("alpha-engagement", "Alpha Engagement")
        self.write_workstream("alpha-workstream", "Alpha Workstream", "alpha-engagement")
        finance = self.load_finance_manager()

        with contextlib.redirect_stdout(io.StringIO()):
            finance.cmd_create_invoice(
                types.SimpleNamespace(
                    engagement="Engagements/alpha-engagement",
                    workstream="Workstreams/alpha-workstream",
                    retainer=None,
                    name="Alpha June Invoice",
                    invoice_number="INV-ALPHA-001",
                    amount=1000,
                    currency="USD",
                    issue_date="2026-06-10",
                    due_date="2026-06-30",
                    status="issued",
                    billing_context="June advisory work",
                    notes="",
                    owner=None,
                    source="manual",
                    source_ref=None,
                )
            )

        invoice_path = self.crm_data_path / "Invoices" / "alpha-june-invoice.md"
        invoice_fm, _body = load_frontmatter_file(str(invoice_path))
        self.assertEqual(invoice_fm["status"], "issued")

        with contextlib.redirect_stdout(io.StringIO()):
            finance.cmd_record_payment(
                types.SimpleNamespace(
                    invoice="Invoices/alpha-june-invoice",
                    name="Alpha Part Payment",
                    amount=400,
                    currency="USD",
                    received_date="2026-06-15",
                    payment_method="wire",
                    status="received",
                    receipt_context="Initial transfer",
                    verification_notes="Matched to statement",
                    owner=None,
                    source="manual",
                    source_ref=None,
                )
            )

        invoice_fm, _body = load_frontmatter_file(str(invoice_path))
        self.assertEqual(invoice_fm["status"], "partially-paid")

        with contextlib.redirect_stdout(io.StringIO()):
            finance.cmd_record_payment(
                types.SimpleNamespace(
                    invoice="Invoices/alpha-june-invoice",
                    name="Alpha Final Payment",
                    amount=600,
                    currency="USD",
                    received_date="2026-06-20",
                    payment_method="wire",
                    status="reconciled",
                    receipt_context="Balance transfer",
                    verification_notes="Final amount confirmed",
                    owner=None,
                    source="manual",
                    source_ref=None,
                )
            )

        invoice_fm, _body = load_frontmatter_file(str(invoice_path))
        self.assertEqual(invoice_fm["status"], "paid")

        payments = sorted((self.crm_data_path / "Payments").glob("*.md"))
        self.assertEqual(len(payments), 2)

    def test_review_invoice_is_read_only_even_when_overdue(self):
        self.write_engagement("alpha-engagement", "Alpha Engagement")
        write_record(
            self.crm_data_path / "Invoices" / "alpha-overdue-invoice.md",
            {
                "id": "inv-alpha-overdue-invoice",
                "invoice-name": "Alpha Overdue Invoice",
                "owner": "john",
                "engagement": "[[Engagements/alpha-engagement]]",
                "workstream": "",
                "retainer": "",
                "invoice-number": "INV-ALPHA-OVERDUE",
                "currency": "USD",
                "amount": 1000,
                "issue-date": "2026-06-01",
                "due-date": "2026-06-10",
                "status": "issued",
                "source": "manual",
                "source-ref": "",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )
        finance = self.load_finance_manager()

        before = (self.crm_data_path / "Invoices" / "alpha-overdue-invoice.md").read_text(encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            finance.review_invoice("Invoices/alpha-overdue-invoice", verbose=False)
        after = (self.crm_data_path / "Invoices" / "alpha-overdue-invoice.md").read_text(encoding="utf-8")

        self.assertEqual(before, after)
        self.assertIn("Status: overdue", stdout.getvalue())

    def test_dashboard_engagement_finance_section_rolls_up_outstanding(self):
        self.write_engagement("alpha-engagement", "Alpha Engagement")
        self.write_workstream("alpha-workstream", "Alpha Workstream", "alpha-engagement")
        self.write_source_artifact("alpha-brief", "[[Workstreams/alpha-workstream]]")
        write_record(
            self.crm_data_path / "Invoices" / "alpha-june-invoice.md",
            {
                "id": "inv-alpha-june-invoice",
                "invoice-name": "Alpha June Invoice",
                "owner": "john",
                "engagement": "[[Engagements/alpha-engagement]]",
                "workstream": "[[Workstreams/alpha-workstream]]",
                "retainer": "",
                "invoice-number": "INV-ALPHA-001",
                "currency": "USD",
                "amount": 1000,
                "issue-date": "2026-06-01",
                "due-date": "2026-06-15",
                "status": "issued",
                "source": "manual",
                "source-ref": "",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )
        write_record(
            self.crm_data_path / "Payments" / "alpha-part-payment.md",
            {
                "id": "pay-alpha-part-payment",
                "payment-name": "Alpha Part Payment",
                "owner": "john",
                "invoice": "[[Invoices/alpha-june-invoice]]",
                "engagement": "[[Engagements/alpha-engagement]]",
                "currency": "USD",
                "amount": 250,
                "received-date": "2026-06-12",
                "payment-method": "wire",
                "status": "received",
                "source": "manual",
                "source-ref": "",
                "date-created": "2026-06-12",
                "date-modified": "2026-06-12",
            },
        )

        dashboard = self.load_dashboard_module()
        with patch.object(sys, "argv", ["update-dashboard.py", "--skip-followups", "--skip-commit"]):
            dashboard.main()

        dashboard_text = (self.crm_data_path / "DASHBOARD.md").read_text(encoding="utf-8")
        self.assertIn("## Engagement Finance", dashboard_text)
        self.assertIn("[[Engagements/alpha-engagement]]", dashboard_text)
        self.assertIn("750 USD", dashboard_text)
        self.assertIn("| 1 | 1 |", dashboard_text)


if __name__ == "__main__":
    unittest.main()
