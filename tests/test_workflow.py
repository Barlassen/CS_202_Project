"""Run with: python3 -m unittest discover -s tests -v"""
import os
import tempfile
import unittest
from pathlib import Path

import app
import seed


class MarketplaceWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_path = os.environ.get("PROJECT_DB")
        os.environ["PROJECT_DB"] = str(Path(self.directory.name) / "test.db")
        seed.initialize()

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop("PROJECT_DB", None)
        else:
            os.environ["PROJECT_DB"] = self.old_path
        self.directory.cleanup()

    def test_multi_seller_order_delivery_and_refund(self):
        with app.connect() as db:
            app.add_to_cart(db, {"listing_id": ["1"], "quantity": ["2"]})
            app.add_to_cart(db, {"listing_id": ["3"], "quantity": ["1"]})
            order_id = app.checkout(db)
            self.assertEqual(db.execute("SELECT total_cents FROM orders WHERE order_id=?", (order_id,)).fetchone()[0], 534700)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM stock_reservations WHERE order_id=?", (order_id,)).fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT available_qty FROM stock_positions WHERE seller_id=1 AND variant_id=1").fetchone()[0], 6)
            self.assertEqual(db.execute("SELECT quantity FROM stock_batches WHERE batch_id=1").fetchone()[0], 6)
            app.fulfill(db, order_id)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM fulfillments WHERE order_id=?", (order_id,)).fetchone()[0], 2)
            app.deliver(db, order_id)
            app.request_return(db, order_id, 1, 1, "Damaged")
            return_id = db.execute("SELECT return_id FROM return_requests").fetchone()[0]
            app.approve_return(db, return_id)
            self.assertEqual(db.execute("SELECT amount_cents FROM refunds WHERE return_id=?", (return_id,)).fetchone()[0], 249900)
            self.assertEqual(db.execute("SELECT status FROM orders WHERE order_id=?", (order_id,)).fetchone()[0], "delivered")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_insufficient_stock_rolls_back_whole_checkout(self):
        with app.connect() as db:
            app.add_to_cart(db, {"listing_id": ["1"], "quantity": ["100"]})
            with self.assertRaisesRegex(ValueError, "Insufficient stock"):
                app.checkout(db)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM stock_reservations").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT available_qty FROM stock_positions WHERE seller_id=1 AND variant_id=1").fetchone()[0], 8)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM cart_lines").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
