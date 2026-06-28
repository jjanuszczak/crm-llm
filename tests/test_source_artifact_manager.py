import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess


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


class SourceArtifactManagerTests(unittest.TestCase):
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
            "Notes",
        ]:
            (self.crm_data_path / directory).mkdir(parents=True, exist_ok=True)

    def load_manager(self):
        return load_module(
            REPO_ROOT / ".gemini/skills/crm-source-artifact-manager/scripts/source_artifact_manager.py",
            "crm_source_artifact_manager_test",
            self.crm_data_path,
        )

    def write_workstream(self):
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

    def test_create_readwise_maps_payload_to_source_artifact(self):
        self.write_workstream()
        manager = self.load_manager()
        payload = {
            "id": "rw-123",
            "title": "Scaling Climate Market Entry",
            "category": "article",
            "url": "https://example.com/climate-entry",
            "summary": "Useful market entry framing for climate infrastructure clients.",
            "highlights": [
                {"text": "The local distribution chain matters more than global brand recognition."},
                {"text": "Market entry fails when the commercial champion lacks local operating depth."},
            ],
        }
        payload_path = self.crm_data_path / "readwise-item.json"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")

        with contextlib.redirect_stdout(io.StringIO()):
            manager.cmd_create_readwise(
                types.SimpleNamespace(
                    primary_parent_type="workstream",
                    primary_parent="Workstreams/board-deck-refresh",
                    json_path=str(payload_path),
                    json=None,
                    title=None,
                    secondary_links=[],
                    source_type=None,
                    url=None,
                    source_ref=None,
                    confidentiality="internal-only",
                    status="active",
                    summary_note=None,
                    summary=None,
                    usage_context=None,
                    review_notes=None,
                    owner="john",
                    last_reviewed="2026-06-28",
                )
            )

        artifact_path = self.crm_data_path / "Source-Artifacts" / "scaling-climate-market-entry.md"
        self.assertTrue(artifact_path.exists())
        frontmatter, body = load_frontmatter_file(str(artifact_path))
        self.assertEqual(frontmatter["source-system"], "readwise")
        self.assertEqual(frontmatter["source-type"], "article")
        self.assertEqual(frontmatter["external-id"], "rw-123")
        self.assertEqual(frontmatter["source"], "readwise-sync")
        self.assertEqual(frontmatter["source-ref"], "rw-123")
        self.assertEqual(frontmatter["primary-parent"], "[[Workstreams/board-deck-refresh]]")
        self.assertIn("Useful market entry framing", body)
        self.assertIn("Highlights:", body)
        self.assertIn("# **Source Artifact: Scaling Climate Market Entry**", body)

    def test_create_readwise_rejects_duplicate_external_id(self):
        self.write_workstream()
        manager = self.load_manager()
        payload = {
            "id": "rw-123",
            "title": "Scaling Climate Market Entry",
            "category": "article",
            "url": "https://example.com/climate-entry",
        }
        first_payload_path = self.crm_data_path / "readwise-item-1.json"
        first_payload_path.write_text(json.dumps(payload), encoding="utf-8")

        duplicate_payload = {
            "id": "rw-123",
            "title": "Different Packaging Same Readwise Item",
            "category": "article",
            "url": "https://example.com/climate-entry-duplicate",
        }
        duplicate_payload_path = self.crm_data_path / "readwise-item-2.json"
        duplicate_payload_path.write_text(json.dumps(duplicate_payload), encoding="utf-8")

        args = types.SimpleNamespace(
            primary_parent_type="workstream",
            primary_parent="Workstreams/board-deck-refresh",
            json_path=str(first_payload_path),
            json=None,
            title=None,
            secondary_links=[],
            source_type=None,
            url=None,
            source_ref=None,
            confidentiality="internal-only",
            status="active",
            summary_note=None,
            summary=None,
            usage_context=None,
            review_notes=None,
            owner="john",
            last_reviewed="2026-06-28",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            manager.cmd_create_readwise(args)

        duplicate_args = types.SimpleNamespace(**{**args.__dict__, "json_path": str(duplicate_payload_path)})
        with self.assertRaisesRegex(FileExistsError, "matching external-id slug already exists"):
            manager.cmd_create_readwise(duplicate_args)

    def test_create_readwise_from_cli_document_id_fetches_reader_document(self):
        self.write_workstream()
        manager = self.load_manager()
        cli_payload = {
            "id": "rw-doc-789",
            "title": "SEA Distribution Notes",
            "category": "article",
            "summary": "Practical notes on local channel leverage.",
            "content": "# SEA Distribution Notes\n\nWarm channels beat cold entry.",
        }

        with patch.object(
            manager.subprocess,
            "run",
            return_value=CompletedProcess(
                args=["readwise", "--json", "reader-get-document-details", "--document-id", "rw-doc-789"],
                returncode=0,
                stdout=json.dumps(cli_payload),
                stderr="",
            ),
        ) as mocked_run:
            with contextlib.redirect_stdout(io.StringIO()):
                manager.cmd_create_readwise(
                    types.SimpleNamespace(
                        primary_parent_type="workstream",
                        primary_parent="Workstreams/board-deck-refresh",
                        document_id="rw-doc-789",
                        json_path=None,
                        json=None,
                        title=None,
                        secondary_links=[],
                        source_type=None,
                        url=None,
                        source_ref=None,
                        confidentiality="internal-only",
                        status="active",
                        summary_note=None,
                        summary=None,
                        usage_context=None,
                        review_notes=None,
                        owner="john",
                        last_reviewed="2026-06-28",
                    )
                )

        mocked_run.assert_called_once_with(
            ["readwise", "--json", "reader-get-document-details", "--document-id", "rw-doc-789"],
            capture_output=True,
            text=True,
            check=False,
        )
        artifact_path = self.crm_data_path / "Source-Artifacts" / "sea-distribution-notes.md"
        self.assertTrue(artifact_path.exists())
        frontmatter, body = load_frontmatter_file(str(artifact_path))
        self.assertEqual(frontmatter["external-id"], "rw-doc-789")
        self.assertEqual(frontmatter["source-system"], "readwise")
        self.assertEqual(frontmatter["source"], "readwise-sync")
        self.assertEqual(frontmatter["url"], "https://read.readwise.io/read/rw-doc-789")
        self.assertIn("Practical notes on local channel leverage.", body)
        self.assertIn("# **Source Artifact: SEA Distribution Notes**", body)

    def test_create_readwise_from_cli_raises_on_cli_error(self):
        self.write_workstream()
        manager = self.load_manager()

        with patch.object(
            manager.subprocess,
            "run",
            return_value=CompletedProcess(
                args=["readwise", "--json", "reader-get-document-details", "--document-id", "missing"],
                returncode=1,
                stdout="",
                stderr="document not found",
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "Readwise CLI failed: document not found"):
                manager.cmd_create_readwise(
                    types.SimpleNamespace(
                        primary_parent_type="workstream",
                        primary_parent="Workstreams/board-deck-refresh",
                        document_id="missing",
                        json_path=None,
                        json=None,
                        title=None,
                        secondary_links=[],
                        source_type=None,
                        url=None,
                        source_ref=None,
                        confidentiality="internal-only",
                        status="active",
                        summary_note=None,
                        summary=None,
                        usage_context=None,
                        review_notes=None,
                        owner="john",
                        last_reviewed="2026-06-28",
                    )
                )


if __name__ == "__main__":
    unittest.main()
