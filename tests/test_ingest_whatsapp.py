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
    def test_wacli_doctor_connected_detects_existing_live_sync(self):
        self.assertTrue(ingest.wacli_doctor_connected({"data": {"connected": True}}))
        self.assertTrue(ingest.wacli_doctor_connected({"data": {"connection_state": "connected"}}))
        self.assertFalse(ingest.wacli_doctor_connected({"data": {"connected": False}}))

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

    def test_entity_resolver_soft_matches_unique_whatsapp_direct_chat_by_name(self):
        index = ingest.CRMIndex()
        contact = {
            "type": "Contact",
            "file_path": "/tmp/contact.md",
            "rel_path": "Contacts/paolo-picazo.md",
            "link": "[[Contacts/paolo-picazo]]",
            "frontmatter": {"full-name": "Paolo Picazo"},
            "body": "",
            "name": "Paolo Picazo",
        }
        index.contacts_by_name["paolo picazo"] = [contact]
        resolver = ingest.EntityResolver(index, set(), set(), [])

        result = resolver.resolve_participant(
            {
                "email": "",
                "name": "Paolo Picazo",
                "phone": "",
                "jid": "85290881000@s.whatsapp.net",
                "role": "chat",
                "source_type": "whatsapp",
                "chat_kind": "direct",
            }
        )

        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["match_type"], "contact")
        self.assertEqual(result["record"]["name"], "Paolo Picazo")

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

                def sync_once(self):
                    raise AssertionError("sync should not run when doctor fails")

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
        fetch_calls = []
        sync_calls = []

        class FakeAdapter:
            def __init__(self, account="", store_dir=""):
                self.account = account
                self.store_dir = store_dir or "/tmp/fake-wacli"

            def doctor(self):
                return {"store": {"path": self.store_dir}}

            def sync_once(self, **kwargs):
                sync_calls.append(kwargs)
                return {"status": "ok"}

            def prune_messages(self, retain_count):
                return {"status": "ok", "retain_count": retain_count, "deleted": 0}

            def fetch_messages(self, min_rowid, since_timestamp, limit=500):
                fetch_calls.append((min_rowid, since_timestamp, limit))
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
            ), patch.object(ingest, "whatsapp_sync_max_db_size", return_value="500MB"), patch.object(
                ingest, "whatsapp_archive_max_messages", return_value=5000
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
        self.assertEqual(sync_calls, [{"max_db_size": "500MB"}])
        self.assertEqual(len(captured_events), 1)
        self.assertEqual(captured_events[0]["source_type"], "whatsapp")
        self.assertIn('"messages_scanned": 1', updates_text)
        self.assertEqual(fetch_calls[0][0], 0)
        self.assertEqual(fetch_calls[0][1], 0)
        self.assertIn('"bootstrap_full_history": true', updates_text)
        self.assertIn('"sync": {', updates_text)
        self.assertIn('"status": "ok"', updates_text)
        self.assertEqual(updates[0]["status"], "staged_or_written")

    def test_process_whatsapp_post_ingest_uses_rowid_for_delayed_messages_and_fails_open_on_sync_error(self):
        args = types.SimpleNamespace(since=None, skip_whatsapp=False, autonomous=False, auto_tier=0)
        state = {"whatsapp_last_sync_at": "2026-06-22T23:00:00Z", "whatsapp_last_rowid": 41}
        fetch_calls = []

        class FakeAdapter:
            def __init__(self, account="", store_dir=""):
                self.account = account
                self.store_dir = store_dir or "/tmp/fake-wacli"

            def doctor(self):
                return {"store": {"path": self.store_dir}}

            def sync_once(self, **kwargs):
                return {"status": "error", "reason": "not authenticated"}

            def prune_messages(self, retain_count):
                return {"status": "ok", "retain_count": retain_count, "deleted": 0}

            def fetch_messages(self, min_rowid, since_timestamp, limit=500):
                fetch_calls.append((min_rowid, since_timestamp, limit))
                return []

        with tempfile.TemporaryDirectory() as tmp:
            updates_path = Path(tmp) / "whatsapp_updates.json"
            with patch.object(ingest, "WHATSAPP_UPDATES_PATH", str(updates_path)), patch.object(
                ingest, "whatsapp_post_ingest_enabled", return_value=True
            ), patch.object(ingest, "WacliAdapter", FakeAdapter):
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
            payload = updates_path.read_text(encoding="utf-8")

        self.assertTrue(ran)
        self.assertEqual(updates, [])
        self.assertEqual(fetch_calls[0][0], 41)
        self.assertEqual(fetch_calls[0][1], 0)
        self.assertIn('"status": "error"', payload)
        self.assertIn("not authenticated", payload)

    def test_wacli_sync_once_applies_database_storage_limit(self):
        adapter = ingest.WacliAdapter(store_dir="/tmp/fake-wacli")
        completed = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(ingest.shutil, "which", return_value="/usr/local/bin/wacli"), patch.object(
            ingest.subprocess, "run", return_value=completed
        ) as run:
            result = adapter.sync_once(max_db_size="500MB")

        command = run.call_args.args[0]
        self.assertIn("--max-db-size", command)
        self.assertIn("500MB", command)
        self.assertEqual(result["max_db_size"], "500MB")

    def test_wacli_prune_messages_keeps_most_recent_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "wacli.db"
            conn = ingest.sqlite3.connect(db_path)
            conn.execute("CREATE TABLE messages (rowid INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, text TEXT)")
            conn.executemany("INSERT INTO messages(ts, text) VALUES (?, ?)", [(30, "newest"), (10, "oldest"), (20, "middle")])
            conn.commit()
            conn.close()

            result = ingest.WacliAdapter(store_dir=tmp).prune_messages(2)
            conn = ingest.sqlite3.connect(db_path)
            remaining = conn.execute("SELECT ts, text FROM messages ORDER BY ts ASC").fetchall()
            conn.close()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["deleted"], 1)
        self.assertEqual(remaining, [(20, "middle"), (30, "newest")])


if __name__ == "__main__":
    unittest.main()
