import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.crm_api.app import app


class CrmApiAppTests(unittest.TestCase):
    def test_pipeline_api_returns_json_for_standalone_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / "Opportunities/Example-Opp.md",
                """---
opportunity-name: "Example Opportunity"
stage: proposal
is-active: true
probability: 75
---
# Opportunity
""",
            )
            with patch.dict(os.environ, {"CRM_DATA_PATH": str(root)}):
                client = TestClient(app)
                response = client.get("/pipeline?active_only=false")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["counts"]["opportunities"], 1)
            self.assertEqual(payload["columns"]["Proposal"][0]["title"], "Example Opportunity")
            self.assertEqual(payload["columns"]["Proposal"][0]["next_motion"], "Advance to negotiation")

    def _write(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
