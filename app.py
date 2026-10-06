"""Local CS202 marketplace demo: Python standard library + SQLite."""
from __future__ import annotations

from contextlib import closing
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import os
import sqlite3
import uuid

from seed import db_path, initialize

ROOT = Path(__file__).resolve().parent
CUSTOMER_ID = 1  # Explicit demo identity; there is no login or real payment gateway.


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(db_path(), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def money(cents: int) -> str:
    return f"₺{cents / 100:,.2f}"


def h(value: object) -> str:
    return escape(str(value), quote=True)


def page(title: str, body: str) -> bytes:
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{h(title)} · MarketLab</title><link rel="stylesheet" href="/static/style.css"></head>
    <body><header><div class="wrap nav"><a class="brand" href="/">MarketLab<span> CS202</span></a>
    <nav><a href="/catalog">Catalog</a><a href="/cart">Cart</a><a href="/orders">Orders</a>
    <a href="/seller">Seller panel</a><a href="/reports">Reports</a></nav></div></header>
    <main class="wrap"><div class="eyebrow">DATABASE SYSTEM DEMO</div><h1>{h(title)}</h1>{body}</main>
    <footer class="wrap">Local demo · Customer: Deniz Yılmaz · Payments and shipping are simulated.</footer></body></html>"""
    return html.encode("utf-8")


def notice(message: str, kind: str = "info") -> str:
    return f'<div class="notice {h(kind)}">{h(message)}</div>'


def dashboard(db: sqlite3.Connection) -> str:
    counts = {
        "products": db.execute("SELECT COUNT(*) FROM listings WHERE active=1").fetchone()[0],
        "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "sellers": db.execute("SELECT COUNT(*) FROM seller_organizations").fetchone()[0],
        "tables": db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0],
    }
    cards = "".join(f'<div class="metric"><strong>{v}</strong><span>{h(k)}</span></div>' for k, v in counts.items())
    return f"""<p class="lead">A multi-vendor marketplace built around a connected ER model. Try a full order lifecycle to see the database change.</p>
    <div class="metrics">{cards}</div><div class="grid two">
    <a class="feature" href="/catalog"><b>1. Shop the catalog →</b><p>Search products and add listings from different sellers.</p></a>
    <a class="feature" href="/cart"><b>2. Place an order →</b><p>Checkout reserves stock, records payment, and creates an invoice in one transaction.</p></a>
    <a class="feature" href="/seller"><b>3. Fulfill and deliver →</b><p>Create grouped shipments and tracking events.</p></a>
    <a class="feature" href="/reports"><b>4. Inspect SQL reports →</b><p>See sales, stock alerts, and return activity.</p></a></div>"""


def catalog(db: sqlite3.Connection, query: str) -> str:
    rows = db.execute("""
      SELECT l.listing_id, p.name, v.variant_name, s.name AS seller,
             l.price_cents, COALESCE(SUM(sp.available_qty),0) AS stock
      FROM listings l JOIN variants v ON v.variant_id=l.variant_id
      JOIN products p ON p.product_id=v.product_id
      JOIN seller_organizations s ON s.seller_id=l.seller_id
      LEFT JOIN stock_positions sp ON sp.seller_id=l.seller_id AND sp.variant_id=l.variant_id
      WHERE l.active=1 AND (p.name LIKE ? OR s.name LIKE ?)
      GROUP BY l.listing_id ORDER BY p.name, s.name
    """, (f"%{query}%", f"%{query}%")).fetchall()
    cards = []
    for row in rows:
        action = (f'<form method="post" action="/cart/add"><input type="hidden" name="listing_id" value="{row["listing_id"]}">'
                  '<label>Qty <input type="number" name="quantity" min="1" value="1" required></label>'
                  '<button>Add to cart</button></form>') if row["stock"] else '<span class="muted">Out of stock</span>'
        cards.append(f'<article class="product"><div class="product-art">{h(row["name"][0])}</div>'
                     f'<div class="pill">{h(row["seller"])}</div><h2>{h(row["name"])}</h2>'
                     f'<p>{h(row["variant_name"])} · {row["stock"]} available</p>'
                     f'<div class="price">{money(row["price_cents"])}</div>{action}</article>')
    return (f'<form class="search" action="/catalog"><input name="q" value="{h(query)}" placeholder="Search products or sellers">'
            '<button>Search</button></form><div class="grid products">' + ("".join(cards) or '<p>No products found.</p>') + '</div>')


def cart_rows(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute("""
      SELECT cl.listing_id, cl.quantity, l.price_cents, l.seller_id, l.variant_id,
             p.name, v.variant_name, s.name AS seller
      FROM carts c JOIN cart_lines cl ON cl.cart_id=c.cart_id
      JOIN listings l ON l.listing_id=cl.listing_id
      JOIN variants v ON v.variant_id=l.variant_id
      JOIN products p ON p.product_id=v.product_id
      JOIN seller_organizations s ON s.seller_id=l.seller_id
      WHERE c.customer_id=? ORDER BY cl.listing_id
    """, (CUSTOMER_ID,)).fetchall()


def cart_view(db: sqlite3.Connection) -> str:
    rows = cart_rows(db)
    if not rows:
        return notice("Your cart is empty.") + '<a class="button" href="/catalog">Browse catalog</a>'
    lines = "".join(f'<tr><td>{h(r["name"])} <small>{h(r["variant_name"])} · {h(r["seller"])}</small></td>'
                    f'<td>{r["quantity"]}</td><td>{money(r["price_cents"])}</td>'
                    f'<td>{money(r["price_cents"]*r["quantity"])}</td></tr>' for r in rows)
    total = sum(r["price_cents"] * r["quantity"] for r in rows)
    return (f'<div class="panel"><table><thead><tr><th>Listing</th><th>Qty</th><th>Unit</th><th>Total</th></tr></thead>'
            f'<tbody>{lines}</tbody></table><div class="total">Total: {money(total)}</div>'
            '<form method="post" action="/checkout"><button>Place demo order</button></form></div>'
            '<p class="muted">Checkout uses a simulated payment. No card information is collected.</p>')


def add_to_cart(db: sqlite3.Connection, fields: dict[str, list[str]]) -> None:
    listing_id = int(fields.get("listing_id", [""])[0])
    quantity = int(fields.get("quantity", [""])[0])
    if not 1 <= quantity <= 100:
        raise ValueError("Quantity must be between 1 and 100.")
    listing = db.execute("SELECT 1 FROM listings WHERE listing_id=? AND active=1", (listing_id,)).fetchone()
    if not listing:
        raise ValueError("Listing not found.")
    with db:
        cart_id = db.execute("SELECT cart_id FROM carts WHERE customer_id=?", (CUSTOMER_ID,)).fetchone()[0]
        db.execute("""INSERT INTO cart_lines(cart_id,listing_id,quantity) VALUES(?,?,?)
          ON CONFLICT(cart_id,listing_id) DO UPDATE SET quantity=quantity+excluded.quantity""",
          (cart_id, listing_id, quantity))


def checkout(db: sqlite3.Connection) -> int:
    db.execute("BEGIN IMMEDIATE")
    try:
        rows = cart_rows(db)
        if not rows:
            raise ValueError("The cart is empty.")
        allocations = []
        for r in rows:
            positions = db.execute("""SELECT warehouse_id,available_qty FROM stock_positions
              WHERE seller_id=? AND variant_id=? AND available_qty>0
              ORDER BY available_qty DESC,warehouse_id""", (r["seller_id"], r["variant_id"])).fetchall()
            remaining = r["quantity"]
            line_allocations = []
            for position in positions:
                take = min(remaining, position["available_qty"])
                if take:
                    line_allocations.append((position["warehouse_id"], take))
                    remaining -= take
                if remaining == 0:
                    break
            if remaining:
                raise ValueError(f"Insufficient stock for {r['name']}. Reduce the cart quantity.")
            allocations.append(line_allocations)
        address = db.execute("SELECT address_id FROM addresses WHERE account_id=? ORDER BY address_id LIMIT 1", (CUSTOMER_ID,)).fetchone()
        total = sum(r["price_cents"] * r["quantity"] for r in rows)
        order_id = db.execute("INSERT INTO orders(customer_id,address_id,status,total_cents) VALUES(?,?,'placed',?)",
                              (CUSTOMER_ID, address[0], total)).lastrowid
        for line_no, (r, positions) in enumerate(zip(rows, allocations), 1):
            db.execute("INSERT INTO order_lines VALUES(?,?,?,?,?)",
                       (order_id, line_no, r["listing_id"], r["quantity"], r["price_cents"]))
            for warehouse_id, take in positions:
                result = db.execute("""UPDATE stock_positions SET available_qty=available_qty-?
                  WHERE seller_id=? AND variant_id=? AND warehouse_id=? AND available_qty>=?""",
                  (take, r["seller_id"], r["variant_id"], warehouse_id, take))
                if result.rowcount != 1:
                    raise ValueError("Stock changed during checkout. Please retry.")
                db.execute("""INSERT INTO stock_reservations
                  (order_id,line_no,seller_id,variant_id,warehouse_id,quantity) VALUES(?,?,?,?,?,?)""",
                  (order_id, line_no, r["seller_id"], r["variant_id"], warehouse_id, take))
                batch_remaining = take
                batches = db.execute("""SELECT batch_id,quantity FROM stock_batches
                  WHERE seller_id=? AND variant_id=? AND warehouse_id=? AND quantity>0
                  ORDER BY received_at,batch_id""", (r["seller_id"], r["variant_id"], warehouse_id)).fetchall()
                for batch in batches:
                    used = min(batch_remaining, batch["quantity"])
                    db.execute("UPDATE stock_batches SET quantity=quantity-? WHERE batch_id=?", (used, batch["batch_id"]))
                    db.execute("INSERT INTO stock_movements(batch_id,quantity_delta,reason) VALUES(?,?,'order reservation')",
                               (batch["batch_id"], -used))
                    batch_remaining -= used
                    if not batch_remaining:
                        break
                if batch_remaining:
                    raise ValueError("Batch ledger and stock position disagree; checkout was rolled back.")
        db.execute("INSERT INTO order_status_events(order_id,status) VALUES(?,'placed')", (order_id,))
        payment_id = db.execute("""INSERT INTO payments(order_id,method,status,amount_cents)
          VALUES(?,'demo','paid',?)""", (order_id, total)).lastrowid
        db.execute("""INSERT INTO payment_transactions(payment_id,kind,status,amount_cents)
          VALUES(?,'capture','approved',?)""", (payment_id, total))
        invoice_id = db.execute("INSERT INTO invoices(order_id,total_cents) VALUES(?,?)", (order_id, total)).lastrowid
        for line_no, r in enumerate(rows, 1):
            db.execute("INSERT INTO invoice_lines VALUES(?,?,?,?,?)",
                       (invoice_id, line_no, order_id, line_no, r["price_cents"] * r["quantity"]))
        db.execute("DELETE FROM cart_lines WHERE cart_id=(SELECT cart_id FROM carts WHERE customer_id=?)", (CUSTOMER_ID,))
        db.commit()
        return order_id
    except Exception:
        db.rollback()
        raise


def orders_view(db: sqlite3.Connection) -> str:
    rows = db.execute("SELECT * FROM orders WHERE customer_id=? ORDER BY order_id DESC", (CUSTOMER_ID,)).fetchall()
    if not rows:
        return notice("No orders yet. Place an order from the catalog.")
    return '<div class="panel"><table><thead><tr><th>Order</th><th>Date</th><th>Status</th><th>Total</th></tr></thead><tbody>' + "".join(
        f'<tr><td><a href="/orders/{r["order_id"]}">#{r["order_id"]}</a></td><td>{h(r["placed_at"])}</td>'
        f'<td><span class="pill">{h(r["status"])}</span></td><td>{money(r["total_cents"])}</td></tr>' for r in rows) + '</tbody></table></div>'


def order_view(db: sqlite3.Connection, order_id: int) -> str:
    order = db.execute("SELECT * FROM orders WHERE order_id=? AND customer_id=?", (order_id, CUSTOMER_ID)).fetchone()
    if not order:
        raise ValueError("Order not found.")
    lines = db.execute("""SELECT ol.*,p.name,v.variant_name,s.name AS seller FROM order_lines ol
      JOIN listings l ON l.listing_id=ol.listing_id JOIN seller_organizations s ON s.seller_id=l.seller_id
      JOIN variants v ON v.variant_id=l.variant_id JOIN products p ON p.product_id=v.product_id
      WHERE ol.order_id=? ORDER BY ol.line_no""", (order_id,)).fetchall()
    events = db.execute("SELECT status,event_at FROM order_status_events WHERE order_id=? ORDER BY event_id", (order_id,)).fetchall()
    shipments = db.execute("""SELECT sh.tracking_code,sh.status,c.name AS carrier FROM shipments sh
      JOIN carriers c ON c.carrier_id=sh.carrier_id JOIN packages pa ON pa.package_id=sh.package_id
      JOIN fulfillments f ON f.fulfillment_id=pa.fulfillment_id WHERE f.order_id=?""", (order_id,)).fetchall()
    rows = "".join(f'<tr><td>{h(r["name"])} <small>{h(r["variant_name"])} · {h(r["seller"])}</small></td>'
                   f'<td>{r["quantity"]}</td><td>{money(r["unit_price_cents"]*r["quantity"])}</td></tr>' for r in lines)
    shipment_html = "".join(f'<li>{h(s["carrier"])} · {h(s["tracking_code"])} · {h(s["status"])}</li>' for s in shipments) or '<li>Pending fulfillment</li>'
    return_forms = ""
    if order["status"] == "delivered":
        return_forms = '<h2>Request a return</h2>' + "".join(
            f'<form class="inline-form" method="post" action="/orders/{order_id}/return">'
            f'<input type="hidden" name="line_no" value="{r["line_no"]}"><span>{h(r["name"])}</span>'
            f'<input type="number" name="quantity" min="1" max="{r["quantity"]}" value="1" required>'
            '<input name="reason" maxlength="200" placeholder="Reason" required><button>Request</button></form>' for r in lines)
    returns = db.execute("SELECT return_id,status,reason FROM return_requests WHERE order_id=?", (order_id,)).fetchall()
    return_list = '<h2>Returns</h2><ul>' + "".join(f'<li>#{r["return_id"]} · {h(r["status"])} · {h(r["reason"])}</li>' for r in returns) + '</ul>' if returns else ''
    return (f'<p class="lead">Status: <b>{h(order["status"])}</b> · Total: <b>{money(order["total_cents"])}</b></p>'
            f'<div class="panel"><table><thead><tr><th>Item</th><th>Qty</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table></div>'
            '<div class="grid two"><section class="panel"><h2>History</h2><ul>' + "".join(f'<li>{h(e["status"])} · {h(e["event_at"])}</li>' for e in events)
            + '</ul></section><section class="panel"><h2>Shipments</h2><ul>' + shipment_html + '</ul></section></div>' + return_forms + return_list)


def seller_view(db: sqlite3.Connection) -> str:
    rows = db.execute("""SELECT o.order_id,o.status,o.placed_at,COUNT(DISTINCT l.seller_id) AS sellers
      FROM orders o JOIN order_lines ol ON ol.order_id=o.order_id
      JOIN listings l ON l.listing_id=ol.listing_id
      GROUP BY o.order_id ORDER BY o.order_id DESC""").fetchall()
    stock = db.execute("""SELECT s.name AS seller,p.name AS product,SUM(sp.available_qty) AS available
      FROM stock_positions sp JOIN seller_organizations s ON s.seller_id=sp.seller_id
      JOIN variants v ON v.variant_id=sp.variant_id JOIN products p ON p.product_id=v.product_id
      GROUP BY sp.seller_id,sp.variant_id ORDER BY s.name,p.name""").fetchall()
    order_cards = []
    for r in rows:
        action = (f'<form method="post" action="/seller/fulfill"><input type="hidden" name="order_id" value="{r["order_id"]}">'
                  '<button>Fulfill & ship</button></form>') if r["status"] == "placed" else (
                  f'<form method="post" action="/seller/deliver"><input type="hidden" name="order_id" value="{r["order_id"]}">'
                  '<button>Mark delivered</button></form>' if r["status"] == "shipped" else '')
        order_cards.append(f'<div class="list-item"><div><b>Order #{r["order_id"]}</b><small>{h(r["status"])} · {r["sellers"]} seller(s)</small></div>{action}</div>')
    stock_rows = "".join(f'<tr><td>{h(r["seller"])}</td><td>{h(r["product"])}</td><td>{r["available"]}</td></tr>' for r in stock)
    returns = db.execute("""SELECT rr.return_id,rr.order_id,rr.reason,rr.status
      FROM return_requests rr ORDER BY rr.return_id DESC""").fetchall()
    return_cards = "".join(
        f'<div class="list-item"><div><b>Return #{r["return_id"]}</b><small>Order #{r["order_id"]} · {h(r["status"])} · {h(r["reason"])}</small></div>'
        + (f'<form method="post" action="/seller/return/approve"><input type="hidden" name="return_id" value="{r["return_id"]}">'
           '<button>Approve & refund</button></form>' if r["status"] == "requested" else '') + '</div>' for r in returns)
    return ('<p class="muted">Shared demo seller panel. Actions are simulated and require no external carrier.</p>'
            '<div class="grid two"><section class="panel"><h2>Orders</h2>' + ("".join(order_cards) or '<p>No orders yet.</p>') +
            '</section><section class="panel"><h2>Current stock</h2><table><thead><tr><th>Seller</th><th>Product</th><th>Qty</th></tr></thead><tbody>'
            + stock_rows + '</tbody></table></section></div><section class="panel"><h2>Return requests</h2>'
            + (return_cards or '<p>No return requests yet.</p>') + '</section>')


def fulfill(db: sqlite3.Connection, order_id: int) -> None:
    db.execute("BEGIN IMMEDIATE")
    try:
        order = db.execute("SELECT status FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if not order or order["status"] != "placed":
            raise ValueError("Only placed orders can be fulfilled.")
        groups = db.execute("""SELECT seller_id,warehouse_id,order_id,line_no,SUM(quantity) AS quantity
          FROM stock_reservations WHERE order_id=?
          GROUP BY seller_id,warehouse_id,order_id,line_no ORDER BY seller_id,warehouse_id,line_no""", (order_id,)).fetchall()
        if not groups:
            raise ValueError("Order has no stock reservations.")
        grouped: dict[tuple[int, int], list[sqlite3.Row]] = {}
        for row in groups:
            grouped.setdefault((row["seller_id"], row["warehouse_id"]), []).append(row)
        for (seller_id, warehouse_id), lines in grouped.items():
            fulfillment_id = db.execute("INSERT INTO fulfillments(order_id,seller_id,warehouse_id) VALUES(?,?,?)",
                                        (order_id, seller_id, warehouse_id)).lastrowid
            for line in lines:
                db.execute("INSERT INTO fulfillment_lines VALUES(?,?,?,?)",
                           (fulfillment_id, order_id, line["line_no"], line["quantity"]))
            weight = 500 * sum(line["quantity"] for line in lines)
            package_id = db.execute("INSERT INTO packages(fulfillment_id,weight_grams) VALUES(?,?)",
                                    (fulfillment_id, weight)).lastrowid
            code = "DEMO-" + uuid.uuid4().hex[:10].upper()
            shipment_id = db.execute("""INSERT INTO shipments(package_id,carrier_id,tracking_code,status)
              VALUES(?,1,?,'shipped')""", (package_id, code)).lastrowid
            db.execute("INSERT INTO tracking_events(shipment_id,status,location) VALUES(?,'shipped','Warehouse')", (shipment_id,))
        db.execute("UPDATE orders SET status='shipped' WHERE order_id=?", (order_id,))
        db.execute("INSERT INTO order_status_events(order_id,status) VALUES(?,'shipped')", (order_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def deliver(db: sqlite3.Connection, order_id: int) -> None:
    db.execute("BEGIN IMMEDIATE")
    try:
        order = db.execute("SELECT status FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if not order or order["status"] != "shipped":
            raise ValueError("Only shipped orders can be delivered.")
        shipments = db.execute("""SELECT sh.shipment_id FROM shipments sh
          JOIN packages p ON p.package_id=sh.package_id JOIN fulfillments f ON f.fulfillment_id=p.fulfillment_id
          WHERE f.order_id=?""", (order_id,)).fetchall()
        for shipment in shipments:
            db.execute("UPDATE shipments SET status='delivered',delivered_at=CURRENT_TIMESTAMP WHERE shipment_id=?", (shipment[0],))
            db.execute("INSERT INTO tracking_events(shipment_id,status,location) VALUES(?,'delivered','Customer address')", (shipment[0],))
        db.execute("UPDATE orders SET status='delivered' WHERE order_id=?", (order_id,))
        db.execute("INSERT INTO order_status_events(order_id,status) VALUES(?,'delivered')", (order_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def request_return(db: sqlite3.Connection, order_id: int, line_no: int, quantity: int, reason: str) -> None:
    if not reason.strip() or len(reason) > 200 or quantity < 1:
        raise ValueError("Provide a reason and a positive quantity.")
    db.execute("BEGIN IMMEDIATE")
    try:
        order = db.execute("SELECT status FROM orders WHERE order_id=? AND customer_id=?", (order_id, CUSTOMER_ID)).fetchone()
        line = db.execute("SELECT quantity FROM order_lines WHERE order_id=? AND line_no=?", (order_id, line_no)).fetchone()
        used = db.execute("""SELECT COALESCE(SUM(rl.quantity),0) FROM return_lines rl
          JOIN return_requests rr ON rr.return_id=rl.return_id
          WHERE rl.order_id=? AND rl.line_no=? AND rr.status!='rejected'""", (order_id, line_no)).fetchone()[0]
        if not order or order["status"] != "delivered" or not line or used + quantity > line["quantity"]:
            raise ValueError("Return quantity exceeds the delivered quantity available.")
        return_id = db.execute("""INSERT INTO return_requests(order_id,customer_id,reason,status)
          VALUES(?,?,?,'requested')""", (order_id, CUSTOMER_ID, reason.strip())).lastrowid
        db.execute("INSERT INTO return_lines VALUES(?,?,?,?)", (return_id, order_id, line_no, quantity))
        db.commit()
    except Exception:
        db.rollback()
        raise


def approve_return(db: sqlite3.Connection, return_id: int) -> None:
    db.execute("BEGIN IMMEDIATE")
    try:
        request = db.execute("SELECT order_id,status FROM return_requests WHERE return_id=?", (return_id,)).fetchone()
        if not request or request["status"] != "requested":
            raise ValueError("Only requested returns can be approved.")
        amount = db.execute("""SELECT SUM(rl.quantity * ol.unit_price_cents) FROM return_lines rl
          JOIN order_lines ol ON ol.order_id=rl.order_id AND ol.line_no=rl.line_no
          WHERE rl.return_id=?""", (return_id,)).fetchone()[0]
        payment = db.execute("SELECT payment_id FROM payments WHERE order_id=?", (request["order_id"],)).fetchone()
        if not amount or not payment:
            raise ValueError("Return has no refundable payment line.")
        db.execute("INSERT INTO refunds(return_id,payment_id,amount_cents,status) VALUES(?,?,?,'completed')",
                   (return_id, payment["payment_id"], amount))
        db.execute("""INSERT INTO payment_transactions(payment_id,kind,status,amount_cents)
          VALUES(?,'refund','approved',?)""", (payment["payment_id"], amount))
        db.execute("UPDATE return_requests SET status='approved' WHERE return_id=?", (return_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def reports(db: sqlite3.Connection) -> str:
    sales = db.execute("""SELECT s.name AS seller,COUNT(DISTINCT o.order_id) AS orders,
      SUM(ol.quantity*ol.unit_price_cents) AS revenue_cents
      FROM order_lines ol JOIN orders o ON o.order_id=ol.order_id
      JOIN listings l ON l.listing_id=ol.listing_id JOIN seller_organizations s ON s.seller_id=l.seller_id
      WHERE o.status!='cancelled' GROUP BY s.seller_id ORDER BY revenue_cents DESC""").fetchall()
    low = db.execute("""SELECT s.name AS seller,p.name AS product,sp.available_qty,sp.reorder_point
      FROM stock_positions sp JOIN seller_organizations s ON s.seller_id=sp.seller_id
      JOIN variants v ON v.variant_id=sp.variant_id JOIN products p ON p.product_id=v.product_id
      WHERE sp.available_qty<=sp.reorder_point ORDER BY sp.available_qty""").fetchall()
    top = db.execute("""SELECT p.name,SUM(ol.quantity) AS units FROM order_lines ol
      JOIN listings l ON l.listing_id=ol.listing_id JOIN variants v ON v.variant_id=l.variant_id
      JOIN products p ON p.product_id=v.product_id GROUP BY p.product_id ORDER BY units DESC LIMIT 5""").fetchall()
    returns = db.execute("""SELECT status,COUNT(*) AS count FROM return_requests
      GROUP BY status ORDER BY status""").fetchall()
    sales_rows = "".join(f'<tr><td>{h(r["seller"])}</td><td>{r["orders"]}</td><td>{money(r["revenue_cents"])}</td></tr>' for r in sales) or '<tr><td colspan="3">No sales yet.</td></tr>'
    low_rows = "".join(f'<tr><td>{h(r["seller"])}</td><td>{h(r["product"])}</td><td>{r["available_qty"]} / {r["reorder_point"]}</td></tr>' for r in low) or '<tr><td colspan="3">No low stock.</td></tr>'
    top_rows = "".join(f'<li>{h(r["name"])} · {r["units"]} units</li>' for r in top) or '<li>No orders yet.</li>'
    return_rows = "".join(f'<li>{h(r["status"])} · {r["count"]}</li>' for r in returns) or '<li>No returns yet.</li>'
    return (f'<div class="grid two"><section class="panel"><h2>Revenue by seller</h2><table><tr><th>Seller</th><th>Orders</th><th>Revenue</th></tr>{sales_rows}</table></section>'
            f'<section class="panel"><h2>Low stock</h2><table><tr><th>Seller</th><th>Product</th><th>Qty / reorder</th></tr>{low_rows}</table></section>'
            f'<section class="panel"><h2>Top products</h2><ol>{top_rows}</ol></section>'
            f'<section class="panel"><h2>Return requests</h2><ul>{return_rows}</ul></section></div>'
            '<p class="muted">These reports use SQL JOIN, GROUP BY, SUM, COUNT, filtering, and ordering. See docs/SQL_QUERIES.md.</p>')


class Handler(BaseHTTPRequestHandler):
    def respond(self, body: bytes, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/static/style.css":
            return self.respond((ROOT / "static" / "style.css").read_bytes(), content_type="text/css; charset=utf-8")
        try:
            with closing(connect()) as db:
                if url.path == "/":
                    title, body = "Marketplace dashboard", dashboard(db)
                elif url.path == "/catalog":
                    title, body = "Catalog", catalog(db, parse_qs(url.query).get("q", [""])[0][:100])
                elif url.path == "/cart":
                    title, body = "Your cart", cart_view(db)
                elif url.path == "/orders":
                    title, body = "Your orders", orders_view(db)
                elif url.path.startswith("/orders/") and url.path.count("/") == 2:
                    order_id = int(url.path.split("/")[2])
                    title, body = f"Order #{order_id}", order_view(db, order_id)
                elif url.path == "/seller":
                    title, body = "Seller panel", seller_view(db)
                elif url.path == "/reports":
                    title, body = "SQL reports", reports(db)
                else:
                    return self.respond(page("Not found", notice("Page not found.", "error")), 404)
            self.respond(page(title, body))
        except (ValueError, sqlite3.Error) as exc:
            self.respond(page("Request error", notice(str(exc), "error")), 400)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 8192:
                raise ValueError("Form is too large.")
            fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            with closing(connect()) as db:
                if path == "/cart/add":
                    add_to_cart(db, fields)
                    target = "/cart"
                elif path == "/checkout":
                    target = f"/orders/{checkout(db)}"
                elif path == "/seller/fulfill":
                    fulfill(db, int(fields.get("order_id", [""])[0]))
                    target = "/seller"
                elif path == "/seller/deliver":
                    deliver(db, int(fields.get("order_id", [""])[0]))
                    target = "/seller"
                elif path == "/seller/return/approve":
                    approve_return(db, int(fields.get("return_id", [""])[0]))
                    target = "/seller"
                elif path.startswith("/orders/") and path.endswith("/return"):
                    order_id = int(path.split("/")[2])
                    request_return(db, order_id, int(fields.get("line_no", [""])[0]),
                                   int(fields.get("quantity", [""])[0]), fields.get("reason", [""])[0])
                    target = f"/orders/{order_id}"
                else:
                    return self.respond(page("Not found", notice("Page not found.", "error")), 404)
            self.redirect(target)
        except (ValueError, sqlite3.Error) as exc:
            self.respond(page("Request error", notice(str(exc), "error")), 400)


if __name__ == "__main__":
    initialize()
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "8000"))
    print(f"MarketLab running at http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
