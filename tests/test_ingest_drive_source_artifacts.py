import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from frontmatter_utils import load_frontmatter_file, serialize_frontmatter


_MODULE_COUNTER = 0


def load_ingest_module(crm_data_path: Path):
    global _MODULE_COUNTER
    _MODULE_COUNTER += 1
    module_name = f"crm_ingest_drive_source_artifacts_{_MODULE_COUNTER}"
    module_path = REPO_ROOT / ".gemini/skills/crm-ingest-gws/scripts/ingest.py"
    with patch.dict(os.environ, {"CRM_DATA_PATH": str(crm_data_path)}, clear=False):
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


def write_record(file_path: Path, frontmatter: dict, body: str = "# Record\n"):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(serialize_frontmatter(frontmatter) + body, encoding="utf-8")


class DriveSourceArtifactIngestTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.crm_data_path = Path(self.temp_dir.name)
        for directory in [
            "Organizations",
            "Accounts",
            "Contacts",
            "Leads",
            "Opportunities",
            "Engagements",
            "Workstreams",
            "Source-Artifacts",
            "Tasks",
            "Activities",
            "Notes",
            "staging",
        ]:
            (self.crm_data_path / directory).mkdir(parents=True, exist_ok=True)

    def test_infer_anchor_from_text_prefers_workstream(self):
        write_record(
            self.crm_data_path / "Engagements" / "acme-growth-engagement.md",
            {
                "id": "eng-acme-growth-engagement",
                "engagement-name": "Acme Growth Engagement",
                "owner": "john",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "engagement-type": "advisory",
                "status": "active",
                "commercial-model": "retainer",
                "currency": "USD",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )
        write_record(
            self.crm_data_path / "Workstreams" / "board-deck-refresh.md",
            {
                "id": "ws-board-deck-refresh",
                "workstream-name": "Board Deck Refresh",
                "owner": "john",
                "engagement": "[[Engagements/acme-growth-engagement]]",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "workstream-type": "research",
                "status": "active",
                "priority": "high",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

        ingest = load_ingest_module(self.crm_data_path)
        crm_index = ingest.get_crm_index()
        anchor = ingest.infer_anchor_from_text(
            "Board Deck Refresh notes",
            "Updated talking points and board deck refresh decisions for the Acme Growth Engagement.",
            crm_index,
        )

        self.assertIsNotNone(anchor)
        self.assertEqual(anchor["type"], "workstream")
        self.assertEqual(anchor["record"]["link"], "[[Workstreams/board-deck-refresh]]")

    def test_infer_anchor_from_text_prefers_engagement_for_general_doc_title(self):
        write_record(
            self.crm_data_path / "Engagements" / "acme-growth-engagement.md",
            {
                "id": "eng-acme-growth-engagement",
                "engagement-name": "Acme Growth Engagement",
                "owner": "john",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "engagement-type": "advisory",
                "status": "active",
                "commercial-model": "retainer",
                "currency": "USD",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )
        write_record(
            self.crm_data_path / "Workstreams" / "board-deck-refresh.md",
            {
                "id": "ws-board-deck-refresh",
                "workstream-name": "Board Deck Refresh",
                "owner": "john",
                "engagement": "[[Engagements/acme-growth-engagement]]",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "workstream-type": "research",
                "status": "active",
                "priority": "high",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

        ingest = load_ingest_module(self.crm_data_path)
        crm_index = ingest.get_crm_index()
        anchor = ingest.infer_anchor_from_text(
            "Acme Growth Engagement weekly update",
            "General engagement summary, including a short status line on the board deck refresh workstream.",
            crm_index,
        )

        self.assertIsNotNone(anchor)
        self.assertEqual(anchor["type"], "engagement")
        self.assertEqual(anchor["record"]["link"], "[[Engagements/acme-growth-engagement]]")

    def test_google_doc_creates_source_artifact_and_dedupes_on_rerun(self):
        write_record(
            self.crm_data_path / "Engagements" / "acme-growth-engagement.md",
            {
                "id": "eng-acme-growth-engagement",
                "engagement-name": "Acme Growth Engagement",
                "owner": "john",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "engagement-type": "advisory",
                "status": "active",
                "commercial-model": "retainer",
                "currency": "USD",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )
        write_record(
            self.crm_data_path / "Workstreams" / "board-deck-refresh.md",
            {
                "id": "ws-board-deck-refresh",
                "workstream-name": "Board Deck Refresh",
                "owner": "john",
                "engagement": "[[Engagements/acme-growth-engagement]]",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "workstream-type": "research",
                "status": "active",
                "priority": "high",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

        ingest = load_ingest_module(self.crm_data_path)
        crm_index = ingest.get_crm_index()
        primary_anchor = {
            "type": "workstream",
            "record": crm_index.linked_records["workstreams/board-deck-refresh"],
        }
        event = {
            "source_type": "drive",
            "source_id": "doc1234567890",
            "source_link": "https://docs.google.com/document/d/doc1234567890/edit",
            "event_time": "2026-06-28T08:00:00Z",
            "subject_or_title": "Board Deck Refresh",
            "body_text": "Board deck refresh notes and next steps for the workstream.",
            "snippet": "Board deck refresh notes",
        }
        file_item = {
            "id": "doc1234567890",
            "name": "Board Deck Refresh",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/document/d/doc1234567890/edit",
            "modifiedTime": "2026-06-28T08:00:00Z",
        }

        result = ingest.maybe_write_source_artifact(event, file_item, primary_anchor, [], crm_index)

        self.assertTrue(result["written"])
        artifact_path = self.crm_data_path / "Source-Artifacts" / "board-deck-refresh-doc12345.md"
        self.assertTrue(artifact_path.exists())
        artifact_fm, _body = load_frontmatter_file(str(artifact_path))
        self.assertEqual(artifact_fm["primary-parent"], "[[Workstreams/board-deck-refresh]]")
        self.assertEqual(artifact_fm["source-system"], "google-drive")
        self.assertEqual(artifact_fm["source-type"], "meeting-note")
        self.assertEqual(artifact_fm["external-id"], "doc1234567890")

        duplicate = ingest.maybe_write_source_artifact(event, file_item, primary_anchor, [], crm_index)
        self.assertTrue(duplicate["duplicate"])

    def test_anchor_ambiguity_context_flags_close_engagement_and_workstream_match(self):
        write_record(
            self.crm_data_path / "Engagements" / "acme-growth-engagement.md",
            {
                "id": "eng-acme-growth-engagement",
                "engagement-name": "Acme Growth Engagement",
                "owner": "john",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "engagement-type": "advisory",
                "status": "active",
                "commercial-model": "retainer",
                "currency": "USD",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )
        write_record(
            self.crm_data_path / "Workstreams" / "growth-engagement.md",
            {
                "id": "ws-growth-engagement",
                "workstream-name": "Growth Engagement",
                "owner": "john",
                "engagement": "[[Engagements/acme-growth-engagement]]",
                "organization": "[[Organizations/acme]]",
                "account": "[[Accounts/acme]]",
                "workstream-type": "research",
                "status": "active",
                "priority": "high",
                "date-created": "2026-06-01",
                "date-modified": "2026-06-01",
            },
        )

        ingest = load_ingest_module(self.crm_data_path)
        crm_index = ingest.get_crm_index()
        context = ingest.anchor_ambiguity_context(
            "Growth Engagement update",
            "General growth engagement summary for the client.",
            crm_index,
        )

        self.assertTrue(context["ambiguous"])
        self.assertEqual(context["anchor"]["record"]["link"], "[[Workstreams/growth-engagement]]")
        self.assertEqual(
            [item["record"]["link"] for item in context["candidates"][:2]],
            ["[[Workstreams/growth-engagement]]", "[[Engagements/acme-growth-engagement]]"],
        )


if __name__ == "__main__":
    unittest.main()
