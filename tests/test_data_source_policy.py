import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_data_sources import validate_policy  # noqa: E402


class DataSourcePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "config" / "data-sources.json").read_text(encoding="utf-8"))

    def test_repository_policy_is_valid(self):
        self.assertEqual(validate_policy(self.policy), [])

    def test_blocked_source_cannot_enable_collection(self):
        policy = copy.deepcopy(self.policy)
        source = next(item for item in policy["sources"] if item["id"] == "kis-open-api")
        source["status"] = "blocked"
        source["allowed"]["collect"] = True
        self.assertTrue(any("blocked but allows" in error for error in validate_policy(policy)))

    def test_enabled_use_requires_official_document(self):
        policy = copy.deepcopy(self.policy)
        source = next(item for item in policy["sources"] if item["id"] == "open-dart")
        source["official_documents"] = []
        self.assertTrue(any("official document" in error for error in validate_policy(policy)))

    def test_kcif_retry_schedule_is_fixed(self):
        source = next(item for item in self.policy["sources"] if item["id"] == "kcif")
        schedule = source["collection_schedule"]
        self.assertEqual(schedule["timezone"], "Asia/Seoul")
        self.assertEqual(schedule["times"], ["06:00", "07:00", "07:30", "08:00", "08:30"])
        self.assertEqual(schedule["retry_policy"], "retry_only_after_failure")
        self.assertTrue(schedule["skip_after_success_for_business_date"])


if __name__ == "__main__":
    unittest.main()
