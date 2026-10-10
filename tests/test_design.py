"""Run with: python3 -m unittest discover -s tests -v"""
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_er  # noqa: E402


class ConceptualModelTest(unittest.TestCase):
    def test_model_matches_schema_and_guidelines(self):
        entities, relationships, problems = build_er.build_model(build_er.read_schema())
        self.assertEqual(problems, [])
        for requirement, ok, evidence in build_er.check_guidelines(entities, relationships):
            self.assertTrue(ok, f"{requirement}: {evidence}")


class IsaTriggerTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript((ROOT / "schema.sql").read_text())
        self.db.execute("INSERT INTO accounts VALUES (1,'a@example.test','A','staff')")

    def tearDown(self):
        self.db.close()

    def test_subtype_must_match_account_role(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "not customer"):
            self.db.execute("INSERT INTO customers(account_id) VALUES (1)")

    def test_matching_subtype_is_accepted(self):
        self.db.execute("INSERT INTO departments(department_id,name) VALUES (1,'Ops')")
        self.db.execute("INSERT INTO staff VALUES (1,'Manager',1)")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM staff").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
