import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.web.crm_frontend.app import app


class CrmFrontendAppTests(unittest.TestCase):
    def test_dashboard_and_detail_routes_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / "Leads/Example-Lead.md",
                """---
lead-name: "Example Lead"
status: qualified
priority: high
---
# Lead

## Summary
Useful lead context.
""",
            )
            with patch.dict(os.environ, {"CRM_DATA_PATH": str(root)}):
                client = TestClient(app)
                response = client.get("/")
                self.assertEqual(response.status_code, 200)
                self.assertIn("Pipeline Command Center", response.text)
                self.assertIn("Example Lead", response.text)
                self.assertIn("drawer empty is-collapsed", response.text)
                self.assertIn("data-drawer-toggle", response.text)

                pipeline = client.get("/pipeline?record_type=lead&stage=Qualified&active_only=false")
                self.assertEqual(pipeline.status_code, 200)
                self.assertIn("Example Lead", pipeline.text)

                detail_key = pipeline.text.split('/records/', 1)[1].split('"', 1)[0]
                drawer = client.get(f"/records/{detail_key}")
                self.assertEqual(drawer.status_code, 200)
                self.assertIn('class="drawer-close"', drawer.text)

    def test_missing_crm_data_path_returns_error_page(self):
        with patch.dict(os.environ, {"CRM_DATA_PATH": "/tmp/not-a-real-crm-vault-for-test"}):
            client = TestClient(app)
            response = client.get("/")
            self.assertEqual(response.status_code, 500)
            self.assertIn("CRM data path is unavailable", response.text)

    def _write(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
