import importlib.util
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def load_ingest_module():
    module_path = Path(__file__).resolve().parents[1] / ".gemini/skills/crm-ingest-gws/scripts/ingest.py"
    spec = importlib.util.spec_from_file_location("crm_ingest_gws_ingest", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ingest = load_ingest_module()


class WhatsappIngestTests(unittest.TestCase):
    def test_entity_resolver_matches_whatsapp_participant_by_phone(self):
        index = ingest.CRMIndex()
        contact = {
            "type": "Contact",
            "file_path": "/tmp/contact.md",
            "rel_path": "Contacts/jane-doe.md",
            "link": "[[Contacts/jane-doe]]",
            "frontmatter": {"full-name": "Jane Doe"},
            "body": "",
            "name": "Jane Doe",
        }
        index.contacts_by_phone["15551234567"] = contact
        resolver = ingest.EntityResolver(index, set(), set(), [])

        result = resolver.resolve_participant(
            {
                "email": "",
                "name": "Jane",
                "phone": "+1 (555) 123-4567",
                "jid": "15551234567@s.whatsapp.net",
                "role": "sender",
            }
        )

        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["match_type"], "contact")
        self.assertEqual(result["record"]["name"], "Jane Doe")

    def test_process_whatsapp_post_ingest_fails_open_when_wacli_unavailable(self):
        args = types.SimpleNamespace(since=None, skip_whatsapp=False, autonomous=False, auto_tier=0)
        state = {}
        with tempfile.TemporaryDirectory() as tmp:
            updates_path = Path(tmp) / "whatsapp_updates.json"

            class FailingAdapter:
                def __init__(self, account="", store_dir=""):
                    self.account = account
                    self.store_dir = store_dir

                def doctor(self):
                    raise RuntimeError("wacli binary not found on PATH")

            with patch.object(ingest, "WHATSAPP_UPDATES_PATH", str(updates_path)), patch.object(
                ingest, "whatsapp_post_ingest_enabled", return_value=True
            ), patch.object(ingest, "WacliAdapter", FailingAdapter):
                updates, ran = ingest.process_whatsapp_post_ingest(
                    args,
                    ingest.CRMIndex(),
                    state,
                    resolver=None,
                    inferrer=None,
                    task_analyzer=None,
                    meeting_notes_resolver=None,
                    activity_updates=[],
                    contact_discoveries=[],
                    lead_decisions=[],
                    opportunity_suggestions=[],
                    task_suggestions=[],
                    noise_review=[],
                    audit_log={"scanned": 0, "ignored": 0, "actions": []},
                    interactions={},
                )

            self.assertFalse(ran)
            self.assertEqual(updates[0]["status"], "unavailable")
            self.assertIn("wacli", updates_path.read_text(encoding="utf-8"))

    def test_process_whatsapp_post_ingest_updates_cursor_on_success(self):
        args = types.SimpleNamespace(since=None, skip_whatsapp=False, autonomous=False, auto_tier=0)
        state = {}
        captured_events = []

        class FakeAdapter:
            def __init__(self, account="", store_dir=""):
                self.account = account
                self.store_dir = store_dir or "/tmp/fake-wacli"

            def doctor(self):
                return {"store": {"path": self.store_dir}}

            def fetch_messages(self, min_rowid, since_timestamp, limit=500):
                if min_rowid > 0:
                    return []
                return [
                    {
                        "rowid": 41,
                        "chat_jid": "15551234567@s.whatsapp.net",
                        "chat_name": "Jane Doe",
                        "msg_id": "ABC123",
                        "sender_jid": "15551234567@s.whatsapp.net",
                        "sender_name": "Jane Doe",
                        "ts": 1760000000,
                        "text": "Can we review the proposal tomorrow?",
                        "media_caption": "",
                        "media_type": "",
                        "from_me": 0,
                    }
                ]

        def fake_process_event(*call_args, **call_kwargs):
            event = call_args[0]
            call_args[7].append({"source_event_id": event["source_id"], "status": "pending_review"})
            captured_events.append(event)

        with tempfile.TemporaryDirectory() as tmp:
            updates_path = Path(tmp) / "whatsapp_updates.json"
            with patch.object(ingest, "WHATSAPP_UPDATES_PATH", str(updates_path)), patch.object(
                ingest, "whatsapp_post_ingest_enabled", return_value=True
            ), patch.object(ingest, "whatsapp_account_name", return_value="work"), patch.object(
                ingest, "whatsapp_store_dir", return_value="/tmp/fake-wacli"
            ), patch.object(ingest, "WacliAdapter", FakeAdapter), patch.object(
                ingest, "process_ingest_event", side_effect=fake_process_event
            ):
                updates, ran = ingest.process_whatsapp_post_ingest(
                    args,
                    ingest.CRMIndex(),
                    state,
                    resolver=None,
                    inferrer=None,
                    task_analyzer=None,
                    meeting_notes_resolver=None,
                    activity_updates=[],
                    contact_discoveries=[],
                    lead_decisions=[],
                    opportunity_suggestions=[],
                    task_suggestions=[],
                    noise_review=[],
                    audit_log={"scanned": 0, "ignored": 0, "actions": []},
                    interactions={},
                )
            updates_text = updates_path.read_text(encoding="utf-8")

        self.assertTrue(ran)
        self.assertEqual(state["whatsapp_last_rowid"], 41)
        self.assertEqual(len(captured_events), 1)
        self.assertEqual(captured_events[0]["source_type"], "whatsapp")
        self.assertIn('"messages_scanned": 1', updates_text)
        self.assertEqual(updates[0]["status"], "staged_or_written")


if __name__ == "__main__":
    unittest.main()
