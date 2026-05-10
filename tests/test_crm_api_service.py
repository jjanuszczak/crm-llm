import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.api.crm_api.service import load_item_detail, load_pipeline


class CrmFrontendDataTests(unittest.TestCase):
    def test_load_pipeline_projects_leads_and_opportunities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / "Leads/Example-Lead.md",
                """---
lead-name: "Example Lead"
status: qualified
person-name: "Jane Doe"
company-name: "Example Co"
priority: high
---
# Lead

## Summary
Qualified lead summary.
""",
            )
            self._write(
                root / "Opportunities/Example-Opp.md",
                """---
opportunity-name: "Example Opportunity"
stage: proposal
is-active: true
probability: 75
organization: "[[Organizations/Example-Co]]"
primary-contact: "[[Contacts/Jane-Doe]]"
---
# Opportunity

## Executive Summary
Proposal-stage opportunity summary.
""",
            )
            self._write(root / "Organizations/Example-Co.md", "---\norganization-name: \"Example Co\"\n---\n")
            self._write(root / "Contacts/Jane-Doe.md", "---\nfull-name: \"Jane Doe\"\n---\n")
            self._write(
                root / "Tasks/2026/01/Follow-up.md",
                """---
task-name: "Follow up"
status: todo
due-date: "2026-01-01"
primary-parent: "[[Opportunities/Example-Opp]]"
---
""",
            )
            self._write(
                root / "Tasks/2026/01/Completed.md",
                """---
task-name: "Completed task"
status: completed
due-date: "2026-01-01"
primary-parent: "[[Opportunities/Example-Opp]]"
---
""",
            )

            with patch.dict(os.environ, {"CRM_DATA_PATH": str(root)}):
                pipeline = load_pipeline(active_only=False)

            self.assertEqual(pipeline.stage_counts["Qualified"], 1)
            self.assertEqual(pipeline.stage_counts["Proposal"], 1)
            opportunity = next(item for item in pipeline.items if item.record_type == "opportunity")
            self.assertEqual(opportunity.overdue_count, 1)
            self.assertEqual(opportunity.organization_or_account, "Example Co")

            with patch.dict(os.environ, {"CRM_DATA_PATH": str(root)}):
                detail = load_item_detail(opportunity.key)
            self.assertEqual([task.frontmatter["task-name"] for task in detail["tasks"]], ["Follow up"])

    def test_detail_drawer_context_uses_encoded_record_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / "Leads/Example-Lead.md",
                """---
lead-name: "Example Lead"
status: engaged
priority: medium
---
# Lead

## Summary
Useful lead context.
""",
            )
            with patch.dict(os.environ, {"CRM_DATA_PATH": str(root)}):
                pipeline = load_pipeline(active_only=False)
                detail = load_item_detail(pipeline.items[0].key)

            self.assertEqual(detail["item"].title, "Example Lead")
            self.assertIn("Useful lead context", detail["summary"])

    def test_malformed_frontmatter_does_not_crash_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root / "Leads/Broken.md", "---\nnot: [valid\n---\n# Broken")
            with patch.dict(os.environ, {"CRM_DATA_PATH": str(root)}):
                pipeline = load_pipeline(active_only=False)
            self.assertEqual(pipeline.counts["total"], 0)

    def _write(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
