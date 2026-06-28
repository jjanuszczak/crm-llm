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


def load_module(module_path: Path, base_name: str, crm_data_path: Path):
    global _MODULE_COUNTER
    _MODULE_COUNTER += 1
    module_name = f"{base_name}_{_MODULE_COUNTER}"
    with patch.dict(os.environ, {"CRM_DATA_PATH": str(crm_data_path)}, clear=False):
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


def write_record(file_path: Path, frontmatter: dict, body: str = "# Record\n"):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(serialize_frontmatter(frontmatter) + body, encoding="utf-8")


class OpportunityHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.crm_data_path = Path(self.temp_dir.name)
        for directory in [
            "Organizations",
            "Accounts",
            "Contacts",
            "Opportunities",
            "Engagements",
            "Workstreams",
            "Tasks",
            "Activities",
            "Notes",
        ]:
            (self.crm_data_path / directory).mkdir(parents=True, exist_ok=True)

    def load_opportunity_manager(self):
        return load_module(
            REPO_ROOT / ".gemini/skills/crm-opportunity-manager/scripts/opportunity_manager.py",
            "crm_opportunity_manager_test",
            self.crm_data_path,
        )

    def write_core_records(self):
        write_record(
            self.crm_data_path / "Organizations" / "acme-holdings.md",
            {
                "id": "org-acme-holdings",
                "organization-name": "Acme Holdings",
            },
        )
        write_record(
            self.crm_data_path / "Accounts" / "acme-holdings.md",
            {
                "id": "acct-acme-holdings",
                "account-name": "Acme Holdings",
                "organization": "[[Organizations/acme-holdings]]",
                "owner": "john",
            },
        )
        write_record(
            self.crm_data_path / "Contacts" / "jane-doe.md",
            {
                "id": "ct-jane-doe",
                "full-name": "Jane Doe",
                "account": "[[Accounts/acme-holdings]]",
            },
        )
        write_record(
            self.crm_data_path / "Opportunities" / "acme-sea-advisory-2026.md",
            {
                "id": "acme-sea-advisory-2026",
                "opportunity-name": "Acme SEA Advisory 2026",
                "owner": "john",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
                "account": "[[Accounts/acme-holdings]]",
                "deal": "",
                "primary-contact": "[[Contacts/jane-doe]]",
                "source-lead": "",
                "organization": "[[Organizations/acme-holdings]]",
                "opportunity-type": "advisory",
                "is-active": True,
                "stage": "proposal",
                "commercial-value": 15000,
                "close-date": "2026-06-30",
                "probability": 70,
                "product-service": "SEA Advisory",
                "influencers": [],
                "source": "manual",
                "source-ref": "",
                "lost-at-stage": "",
                "lost-reason": "",
                "lost-date": "",
            },
            body=(
                "# Opportunity\n\n"
                "## **Executive Summary**\n"
                "SEA market entry advisory mandate for Acme.\n\n"
                "## **Next Steps**\n"
                "1. Confirm scope.\n"
            ),
        )

    def test_mark_won_with_handoff_creates_engagement_and_workstream(self):
        self.write_core_records()
        manager = self.load_opportunity_manager()

        with contextlib.redirect_stdout(io.StringIO()):
            manager.cmd_mark_won(
                types.SimpleNamespace(
                    opportunity="Opportunities/acme-sea-advisory-2026",
                    close_date="2026-06-28",
                    create_engagement=True,
                    engagement_name="Acme Advisory Engagement",
                    engagement_type="advisory",
                    engagement_status="active",
                    engagement_start_date=None,
                    engagement_target_end_date="2026-09-30",
                    engagement_end_date=None,
                    commercial_model="retainer",
                    currency="USD",
                    contracted_value=None,
                    engagement_success_definition="Deliver a board-ready SEA entry plan.",
                    engagement_summary=None,
                    engagement_commercial_notes="Monthly strategic advisory support.",
                    engagement_owner=None,
                    create_workstream=True,
                    workstream_name="Board Deck Refresh",
                    workstream_type="research",
                    workstream_status="active",
                    workstream_start_date=None,
                    workstream_target_end_date="2026-07-31",
                    workstream_end_date=None,
                    workstream_priority="high",
                    workstream_success_definition=None,
                    workstream_objective="Turn strategy into a board-ready narrative.",
                    workstream_scope="Deck outline, messaging, and evidence pack.",
                    workstream_current_state="Kickoff complete.",
                    workstream_outputs=["Board deck", "Key talking points"],
                    workstream_owner=None,
                )
            )

        opportunity_fm, _ = load_frontmatter_file(str(self.crm_data_path / "Opportunities" / "acme-sea-advisory-2026.md"))
        self.assertEqual(opportunity_fm["stage"], "closed-won")
        self.assertFalse(opportunity_fm["is-active"])
        self.assertEqual(opportunity_fm["probability"], 100)
        self.assertEqual(str(opportunity_fm["close-date"]), "2026-06-28")

        engagement_path = self.crm_data_path / "Engagements" / "Acme-Advisory-Engagement.md"
        self.assertTrue(engagement_path.exists())
        engagement_fm, engagement_body = load_frontmatter_file(str(engagement_path))
        self.assertEqual(engagement_fm["source-opportunity"], "[[Opportunities/acme-sea-advisory-2026]]")
        self.assertEqual(engagement_fm["commercial-model"], "retainer")
        self.assertEqual(engagement_fm["contracted-value"], 15000)
        self.assertEqual(str(engagement_fm["start-date"]), "2026-06-28")
        self.assertIn("SEA market entry advisory mandate for Acme.", engagement_body)

        workstream_path = self.crm_data_path / "Workstreams" / "board-deck-refresh.md"
        self.assertTrue(workstream_path.exists())
        workstream_fm, workstream_body = load_frontmatter_file(str(workstream_path))
        self.assertEqual(workstream_fm["engagement"], "[[Engagements/Acme-Advisory-Engagement]]")
        self.assertEqual(workstream_fm["workstream-type"], "research")
        self.assertEqual(workstream_fm["priority"], "high")
        self.assertIn("Deck outline, messaging, and evidence pack.", workstream_body)

    def test_mark_won_rejects_workstream_without_engagement_handoff(self):
        self.write_core_records()
        manager = self.load_opportunity_manager()

        with self.assertRaisesRegex(ValueError, "create-workstream requires create-engagement"):
            manager.cmd_mark_won(
                types.SimpleNamespace(
                    opportunity="Opportunities/acme-sea-advisory-2026",
                    close_date="2026-06-28",
                    create_engagement=False,
                    engagement_name=None,
                    engagement_type=None,
                    engagement_status="active",
                    engagement_start_date=None,
                    engagement_target_end_date=None,
                    engagement_end_date=None,
                    commercial_model="other",
                    currency="USD",
                    contracted_value=None,
                    engagement_success_definition=None,
                    engagement_summary=None,
                    engagement_commercial_notes=None,
                    engagement_owner=None,
                    create_workstream=True,
                    workstream_name=None,
                    workstream_type="advisory",
                    workstream_status="active",
                    workstream_start_date=None,
                    workstream_target_end_date=None,
                    workstream_end_date=None,
                    workstream_priority="medium",
                    workstream_success_definition=None,
                    workstream_objective=None,
                    workstream_scope=None,
                    workstream_current_state=None,
                    workstream_outputs=[],
                    workstream_owner=None,
                )
            )

    def test_review_flags_closed_won_opportunity_without_engagement_handoff(self):
        self.write_core_records()
        manager = self.load_opportunity_manager()
        opportunity_path = self.crm_data_path / "Opportunities" / "acme-sea-advisory-2026.md"
        fm, body = load_frontmatter_file(str(opportunity_path))
        fm["stage"] = "closed-won"
        fm["is-active"] = False
        fm["probability"] = 100
        fm["close-date"] = "2026-06-28"
        opportunity_path.write_text(serialize_frontmatter(fm) + body, encoding="utf-8")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            manager.cmd_review(types.SimpleNamespace(opportunity="Opportunities/acme-sea-advisory-2026"))

        rendered = output.getvalue()
        self.assertIn("Linked Engagements: 0", rendered)
        self.assertIn("- no-engagement-handoff", rendered)
        self.assertIn("- create the post-close engagement handoff and first workstream", rendered)


if __name__ == "__main__":
    unittest.main()
