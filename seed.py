"""Create a local demo database. No external services or packages are required."""
from pathlib import Path
import os
import sqlite3

ROOT = Path(__file__).resolve().parent


def db_path() -> Path:
    return Path(os.environ.get("PROJECT_DB", ROOT / "marketplace.db"))


def initialize(path: Path | None = None) -> Path:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys = ON")
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts'").fetchone()
        if exists:
            count = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
            if count != 70:
                raise RuntimeError(f"Existing database has {count} tables; expected 70. Back it up and recreate it.")
            return path
        db.executescript((ROOT / "schema.sql").read_text())
        db.executescript("""
        INSERT INTO accounts VALUES
          (1,'customer@example.test','Deniz Yılmaz','customer'),
          (2,'tech@example.test','Ece Demir','staff'),
          (3,'home@example.test','Mert Kaya','staff'),
          (4,'courier@example.test','Aslı Çelik','courier');
        INSERT INTO customers(account_id) VALUES (1);
        INSERT INTO staff VALUES (2,'Store manager'),(3,'Store manager');
        INSERT INTO couriers VALUES (4,'Bicycle');
        INSERT INTO seller_organizations VALUES
          (1,'Nova Teknoloji',2),(2,'Ev & Yaşam',3);
        INSERT INTO seller_staff(seller_id,staff_account_id) VALUES (1,2),(2,3);
        INSERT INTO addresses VALUES
          (1,1,'Home','Istanbul','Örnek Sokak 12','34000');
        INSERT INTO seller_verifications(seller_id,status,checked_by) VALUES
          (1,'approved',2),(2,'approved',3);
        INSERT INTO categories(category_id,name) VALUES
          (1,'Electronics'),(2,'Home'),(3,'Stationery');
        INSERT INTO brands VALUES (1,'Nova'),(2,'Rota'),(3,'Masa');
        INSERT INTO products VALUES
          (1,1,1,'Wireless Headphones','Over-ear Bluetooth headphones.'),
          (2,1,1,'USB-C Hub','Six-port laptop hub.'),
          (3,3,2,'Notebook Set','Three recycled-paper notebooks.'),
          (4,2,3,'Desk Lamp','Adjustable LED desk lamp.'),
          (5,2,3,'Ceramic Mug','Handmade ceramic mug.'),
          (6,3,2,'Pen Set','Five refillable pens.');
        INSERT INTO variants VALUES
          (1,1,'HEAD-BLK','Black'),(2,2,'HUB-SLV','Silver'),
          (3,3,'NOTE-A5','A5'),(4,4,'LAMP-WHT','White'),
          (5,5,'MUG-BLU','Blue'),(6,6,'PEN-5','Five pack');
        INSERT INTO attributes VALUES (1,'Color'),(2,'Size');
        INSERT INTO variant_values VALUES
          (1,1,'Black'),(2,1,'Silver'),(3,2,'A5'),
          (4,1,'White'),(5,1,'Blue'),(6,2,'Five pack');
        INSERT INTO listings VALUES
          (1,1,1,249900,1),(2,1,2,89900,1),
          (3,2,3,34900,1),(4,2,4,129900,1),
          (5,2,5,44900,1),(6,2,6,29900,1);
        INSERT INTO carts(customer_id) VALUES (1);
        INSERT INTO wishlists(customer_id,name) VALUES (1,'Favorites');
        INSERT INTO warehouses VALUES (1,'Istanbul Fulfillment Center','Istanbul'),
                                      (2,'Ankara Fulfillment Center','Ankara');
        INSERT INTO storage_zones VALUES (1,1,'A'),(2,2,'A');
        INSERT INTO storage_bins VALUES (1,1,'A-01'),(2,2,'A-01');
        INSERT INTO stock_positions VALUES
          (1,1,1,8,3),(1,2,1,12,4),
          (2,3,2,20,5),(2,4,2,6,3),
          (2,5,2,9,3),(2,6,2,16,4);
        INSERT INTO stock_batches(batch_id,seller_id,variant_id,warehouse_id,bin_id,quantity) VALUES
          (1,1,1,1,1,8),(2,1,2,1,1,12),
          (3,2,3,2,2,20),(4,2,4,2,2,6),
          (5,2,5,2,2,9),(6,2,6,2,2,16);
        INSERT INTO carriers VALUES (1,'Demo Carrier');
        INSERT INTO suppliers(seller_id,name,contact_email) VALUES
          (1,'Nova Wholesale','supply@nova.example.test'),
          (2,'Home Goods Supply','supply@home.example.test');
        """)
    return path


if __name__ == "__main__":
    print(f"Database ready: {initialize()}")
