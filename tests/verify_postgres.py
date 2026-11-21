from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

import psycopg
from psycopg import sql


DDL = Path(__file__).resolve().parents[1] / "marketlab_postgres.sql"

FIXTURE = """
INSERT INTO accounts(account_id,email,full_name,role)
VALUES (1,'buyer@example.test','Buyer','customer'), (2,'owner@example.test','Owner','staff'),
       (3,'race@example.test','Race','customer');
INSERT INTO customers(account_id) VALUES(1);
INSERT INTO departments(department_id,name) VALUES(1,'Operations');
INSERT INTO staff(account_id,title,department_id) VALUES(2,'Manager',1);
INSERT INTO countries VALUES('TR','Türkiye');
INSERT INTO cities(city_id,country_code,name) VALUES(1,'TR','Istanbul');
INSERT INTO addresses(address_id,account_id,city_id,label,street,postal_code)
VALUES(1,1,1,'Home','Street','34000');
INSERT INTO orders(order_id,customer_id,address_id,shipping_address_id,status,total_cents)
VALUES(1,1,1,1,'placed',500), (2,1,1,1,'placed',100);
INSERT INTO commission_plans(plan_id,name,rate_percent) VALUES(1,'Standard',2);
INSERT INTO seller_organizations(seller_id,name,owner_account_id,plan_id)
VALUES(1,'Seller A',2,1), (2,'Seller B',2,1);
INSERT INTO categories(category_id,name) VALUES(1,'Books');
INSERT INTO brands(brand_id,name) VALUES(1,'Publisher');
INSERT INTO products(product_id,category_id,brand_id,name,description) VALUES(1,1,1,'Book','Book');
INSERT INTO variants(variant_id,product_id,sku,variant_name) VALUES(1,1,'A','Paper'),(2,1,'B','Hardback');
INSERT INTO listings(listing_id,seller_id,variant_id,price_cents) VALUES(1,1,1,100);
INSERT INTO warehouses(warehouse_id,name,city_id) VALUES(1,'First',1),(2,'Second',1),(3,'Empty',1);
INSERT INTO stock_positions VALUES(1,1,1,10,0),(1,1,2,10,0),(1,1,3,0,0),(2,1,1,10,0),(1,2,1,10,0);
INSERT INTO order_lines VALUES(1,1,1,5,100),(2,1,1,1,100);
INSERT INTO stock_reservations VALUES(1,1,1,1,1,3),(1,1,1,1,2,2),(2,1,1,1,1,1);
INSERT INTO fulfillments(fulfillment_id,order_id,seller_id,warehouse_id) VALUES(1,1,1,1),(2,1,1,1);
INSERT INTO return_requests(return_id,order_id,reason,status) VALUES(1,1,'One','requested'),(2,1,'Two','requested');
INSERT INTO return_lines VALUES(1,1,1,1),(2,1,1,1);
"""


def connect(schema):
    conn = psycopg.connect(autocommit=True, connect_timeout=5)
    conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    conn.execute("SET statement_timeout TO '15s'")
    return conn


def reject(conn, statement, state):
    try:
        with conn.transaction():
            conn.execute(statement)
    except psycopg.Error as error:
        if error.sqlstate == state:
            return
        raise
    raise AssertionError(f"Expected {state} for {statement}")


def race(observer, schema, first, second, state, isolation="READ COMMITTED"):
    with connect(schema) as a, connect(schema) as b, ThreadPoolExecutor(1) as pool:
        a.execute("BEGIN ISOLATION LEVEL " + isolation)
        b.execute("BEGIN ISOLATION LEVEL " + isolation)
        b.execute("SELECT count(*) FROM orders")
        a.execute(first)
        a.execute("SET CONSTRAINTS ALL IMMEDIATE")

        def compete():
            try:
                b.execute(second)
                b.execute("COMMIT")
            except psycopg.Error as error:
                b.execute("ROLLBACK")
                return error.sqlstate
            return "committed"

        pending = pool.submit(compete)
        try:
            deadline = monotonic() + 10
            while monotonic() < deadline:
                blocked = observer.execute(
                    "SELECT %s = ANY(pg_blocking_pids(%s))", (a.info.backend_pid, b.info.backend_pid)
                ).fetchone()[0]
                if blocked:
                    break
                if pending.done():
                    raise AssertionError(f"Second transaction finished early: {pending.result()}")
                sleep(0.025)
            else:
                raise AssertionError("Second transaction never waited for the first")
        finally:
            a.execute("COMMIT")
        result = pending.result()
        if result != state:
            raise AssertionError(f"Expected {state}, got {result}")


def check_rules(conn, schema):
    reject(conn, "UPDATE stock_reservations SET seller_id=2 WHERE order_id=1 AND warehouse_id=1", "23503")
    reject(conn, "UPDATE stock_reservations SET variant_id=2 WHERE order_id=1 AND warehouse_id=1", "23503")
    reject(conn, "DELETE FROM stock_reservations WHERE order_id=1 AND warehouse_id=2", "23514")
    reject(conn, "UPDATE stock_reservations SET quantity=4 WHERE order_id=1 AND warehouse_id=1", "23514")
    reject(conn, "INSERT INTO fulfillment_lines VALUES(1,1,1,4)", "23514")
    reject(conn, "UPDATE return_lines SET quantity=5 WHERE return_id=1", "23514")
    reject(conn, "TRUNCATE stock_reservations", "23514")
    race(conn, schema, "INSERT INTO customers(account_id) VALUES(3)",
         "UPDATE accounts SET role='staff' WHERE account_id=3", "23503")
    conn.execute("DELETE FROM customers WHERE account_id=3")
    race(conn, schema, "UPDATE accounts SET role='staff' WHERE account_id=3",
         "INSERT INTO customers(account_id) VALUES(3)", "23503")
    for isolation, expected in (("READ COMMITTED", "23514"), ("REPEATABLE READ", "40001")):
        race(conn, schema, "INSERT INTO fulfillment_lines VALUES(1,1,1,2)",
             "INSERT INTO fulfillment_lines VALUES(2,1,1,2)", expected, isolation)
        conn.execute("DELETE FROM fulfillment_lines WHERE fulfillment_id=1")
        race(conn, schema, "UPDATE return_lines SET quantity=3 WHERE return_id=1",
             "UPDATE return_lines SET quantity=3 WHERE return_id=2", expected, isolation)
        conn.execute("UPDATE return_lines SET quantity=1 WHERE return_id=1")
    print("PASS: allocation, shipment, return and concurrent writes")


def observations(conn):
    probes = {
        "Reservation from an empty warehouse": """
            UPDATE stock_reservations SET warehouse_id=3 WHERE order_id=2;
        """,
        "Return before shipment": """
            INSERT INTO return_requests(return_id,order_id,reason,status) VALUES(3,2,'Early','requested');
            INSERT INTO return_lines VALUES(3,2,1,1);
        """,
        "200-cent refund on a rejected return after a 100-cent capture": """
            UPDATE orders SET status='delivered' WHERE order_id=2;
            INSERT INTO return_requests(return_id,order_id,reason,status) VALUES(3,2,'Closed','rejected');
            INSERT INTO return_lines VALUES(3,2,1,1);
            INSERT INTO payment_methods(payment_method_id,customer_id,method_type,masked_number)
            VALUES(1,1,'card','1234');
            INSERT INTO payments(payment_id,order_id,payment_method_id,customer_id,status,amount_cents)
            VALUES(1,2,1,1,'approved',100);
            INSERT INTO payment_transactions(payment_id,order_id,kind,status,amount_cents)
            VALUES(1,2,'capture','approved',100);
            INSERT INTO payment_transactions(payment_id,order_id,return_id,kind,status,amount_cents)
            VALUES(1,2,3,'refund','approved',200);
        """,
        "Two orders redeem a single-use coupon": """
            INSERT INTO promotions(promotion_id,seller_id,name,starts_at,ends_at,discount_percent)
            VALUES(1,1,'Promo',CURRENT_TIMESTAMP-INTERVAL '1 day',CURRENT_TIMESTAMP+INTERVAL '1 day',5);
            INSERT INTO coupons(coupon_id,promotion_id,code,max_uses) VALUES(1,1,'ONE',1);
            INSERT INTO coupon_redemptions(coupon_id,order_id) VALUES(1,1),(1,2);
        """,
    }
    for name, statement in probes.items():
        try:
            with conn.transaction(force_rollback=True):
                conn.execute(statement)
                conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
        except psycopg.IntegrityError as error:
            print(f"REJECTED ({error.sqlstate}): {name}")
        else:
            print(f"ACCEPTED: {name}")


def main():
    schema = "marketlab_test_" + uuid4().hex
    with psycopg.connect(autocommit=True, connect_timeout=5) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with connect(schema) as conn:
                ddl = DDL.read_text(encoding="utf-8-sig")
                conn.execute(ddl)
                conn.execute(ddl)
                counts = conn.execute("""
                    SELECT (SELECT count(*) FROM pg_tables WHERE schemaname=current_schema()),
                           count(*) FILTER (WHERE contype='p'), count(*) FILTER (WHERE contype='f')
                    FROM pg_constraint WHERE connamespace=current_schema()::regnamespace
                """).fetchone()
                if counts != (79, 79, 117):
                    raise AssertionError(f"Unexpected schema counts: {counts}")
                with conn.transaction():
                    conn.execute(FIXTURE)
                print("PASS: two installations, 79 tables, 79 primary keys, 117 foreign keys, split 3+2")
                check_rules(conn, schema)
                observations(conn)
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
