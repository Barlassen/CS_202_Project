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


class IsaOverlapTest(unittest.TestCase):
    """No statement may put one account into two subclasses (overlap is not allowed)."""

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        self.db.executescript("""
            INSERT INTO accounts VALUES (1,'c@example.test','C','customer'), (2,'s@example.test','S','staff'),
                                        (3,'n@example.test','N','customer');
            INSERT INTO departments(department_id,name) VALUES (1,'Ops');
            INSERT INTO customers(account_id) VALUES (1);
            INSERT INTO staff VALUES (2,'Clerk',1);
        """)

    def tearDown(self):
        self.assertEqual(self.db.execute("""SELECT account_id FROM (
            SELECT account_id FROM customers UNION ALL SELECT account_id FROM staff
            UNION ALL SELECT account_id FROM couriers) GROUP BY account_id HAVING COUNT(*) > 1""").fetchall(), [])
        self.db.close()

    def assert_rejected(self, sql, message="subtype row|role is not|FOREIGN KEY"):
        with self.assertRaisesRegex(sqlite3.IntegrityError, message):
            self.db.execute(sql)

    def test_update_of_role_is_rejected(self):
        self.assert_rejected("UPDATE accounts SET role='staff' WHERE account_id=1")

    def test_insert_or_replace_of_account_is_rejected(self):
        self.assert_rejected("INSERT OR REPLACE INTO accounts VALUES (1,'c@example.test','C','staff')")

    def test_replace_into_account_is_rejected(self):
        self.assert_rejected("REPLACE INTO accounts VALUES (1,'c@example.test','C','staff')")

    def test_upsert_of_role_is_rejected(self):
        self.assert_rejected("""INSERT INTO accounts VALUES (1,'c@example.test','C','staff')
            ON CONFLICT(account_id) DO UPDATE SET role=excluded.role""")

    def test_replace_through_email_conflict_is_rejected(self):
        # Replacing account 1 through its e-mail would leave the customers row without its account.
        self.assert_rejected("INSERT OR REPLACE INTO accounts VALUES (9,'c@example.test','C','staff')")

    def test_moving_subtype_row_to_other_role_is_rejected(self):
        self.assert_rejected("UPDATE customers SET account_id=2 WHERE account_id=1")

    def test_second_subtype_row_is_rejected(self):
        self.assert_rejected("INSERT OR REPLACE INTO staff VALUES (1,'Clerk',1)")

    def test_allowed_changes_still_work(self):
        self.db.execute("UPDATE accounts SET full_name='C2' WHERE account_id=1")
        self.db.execute("INSERT OR REPLACE INTO accounts VALUES (1,'c@example.test','C3','customer')")
        self.db.execute("UPDATE accounts SET role='courier' WHERE account_id=3")  # no subtype row yet
        self.assertEqual(self.db.execute("SELECT full_name, role FROM accounts WHERE account_id=1").fetchone(), ("C3", "customer"))


if __name__ == "__main__":
    unittest.main()
