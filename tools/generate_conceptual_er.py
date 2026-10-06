"""Build an auditable conceptual ER draft from the SQL schema and explicit modeling choices.

The output distinguishes entities from relationship tables and marks the required
weak entity, ISA, ternary relationship, and aggregation. It is still a model for
student/instructor review, not evidence that table count equals entity count.
"""
from collections import defaultdict, deque
from pathlib import Path
import sqlite3
import subprocess

from generate_design_artifacts import GROUPS, COLORS

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# These are modeled as relationships, rather than counted as entity sets.
RELATIONSHIP_TABLES = {
    "seller_staff": ("works for", "assigned_at"),
    "variant_values": ("has attribute", "value"),
    "cart_lines": ("contains", "quantity"),
    "wishlist_items": ("saves", ""),
    "stock_positions": ("STOCKS", "available_qty, reorder_point"),
    "coupon_redemptions": ("redeems", ""),
    "gift_card_uses": ("applies card", "amount_cents"),
    "stock_reservations": ("RESERVES", "quantity"),
    "fulfillment_lines": ("includes line", "quantity"),
    "return_lines": ("returns line", "quantity"),
    "goods_receipt_lines": ("receives line", "received_qty"),
}
ISA_CHILDREN = {"customers", "staff", "couriers"}
WEAK_ENTITIES = {"order_lines", "purchase_order_lines", "invoice_lines"}

# Conceptual names for foreign-key relationships that are not represented by
# a relationship table. Every such FK is required to have an explicit name.
RELATION_NAMES = {
    ("addresses", "accounts"): "saved by",
    ("carts", "customers"): "owned by",
    ("categories", "categories"): "subcategory of",
    ("coupons", "promotions"): "issued by",
    ("customer_notifications", "customers"): "received by",
    ("delivery_attempts", "couriers"): "performed by",
    ("delivery_attempts", "shipments"): "attempts delivery of",
    ("fulfillments", "orders"): "fulfills",
    ("fulfillments", "seller_organizations"): "handled by",
    ("fulfillments", "warehouses"): "picked from",
    ("gift_cards", "customers"): "purchased by",
    ("goods_receipts", "purchase_orders"): "receives",
    ("inventory_adjustments", "staff"): "authorized by",
    ("inventory_adjustments", "stock_batches"): "adjusts",
    ("invoice_lines", "invoices"): "part of invoice",
    ("invoice_lines", "order_lines"): "bills",
    ("invoices", "orders"): "issued for",
    ("listings", "seller_organizations"): "offered by",
    ("listings", "variants"): "offers variant",
    ("order_lines", "listings"): "purchases listing",
    ("order_lines", "orders"): "contains (identifying)",
    ("order_status_events", "orders"): "status of",
    ("orders", "addresses"): "shipped to",
    ("orders", "customers"): "placed by",
    ("packages", "fulfillments"): "packs",
    ("payment_transactions", "payments"): "recorded under",
    ("payments", "orders"): "pays for",
    ("price_history", "listings"): "tracks price of",
    ("product_answers", "product_questions"): "answers",
    ("product_answers", "staff"): "written by",
    ("product_documents", "products"): "documents",
    ("product_images", "products"): "depicts",
    ("product_questions", "customers"): "asked by",
    ("product_questions", "products"): "about product",
    ("products", "brands"): "branded as",
    ("products", "categories"): "classified in",
    ("promotions", "seller_organizations"): "funded by",
    ("proof_of_delivery", "delivery_attempts"): "proves",
    ("purchase_order_lines", "purchase_orders"): "contains (identifying)",
    ("purchase_order_lines", "variants"): "orders variant",
    ("purchase_orders", "suppliers"): "sent to",
    ("purchase_orders", "warehouses"): "delivered to",
    ("refunds", "payments"): "refunded against",
    ("refunds", "return_requests"): "resolves return",
    ("return_inspections", "return_requests"): "inspects return",
    ("return_inspections", "staff"): "performed by",
    ("return_requests", "customers"): "requested by",
    ("return_requests", "orders"): "for order",
    ("review_images", "reviews"): "illustrates review",
    ("reviews", "customers"): "written by",
    ("reviews", "products"): "rates product",
    ("seller_organizations", "accounts"): "owned by",
    ("seller_payout_accounts", "seller_organizations"): "belongs to seller",
    ("seller_policies", "seller_organizations"): "defined by",
    ("seller_reviews", "customers"): "written by",
    ("seller_reviews", "seller_organizations"): "rates seller",
    ("seller_verifications", "seller_organizations"): "verifies seller",
    ("seller_verifications", "staff"): "checked by",
    ("shipments", "carriers"): "carried by",
    ("shipments", "packages"): "ships package",
    ("stock_batches", "stock_positions"): "batch of stock",
    ("stock_batches", "storage_bins"): "stored in",
    ("stock_movements", "stock_batches"): "changes batch",
    ("storage_bins", "storage_zones"): "located in zone",
    ("storage_zones", "warehouses"): "located in warehouse",
    ("suppliers", "seller_organizations"): "supplies seller",
    ("support_tickets", "customers"): "opened by",
    ("support_tickets", "orders"): "about order",
    ("ticket_messages", "accounts"): "authored by",
    ("ticket_messages", "support_tickets"): "message in",
    ("tracking_events", "shipments"): "tracks shipment",
    ("variants", "products"): "variant of",
    ("warehouse_inspections", "staff"): "performed by",
    ("warehouse_inspections", "warehouses"): "inspects warehouse",
    ("wishlists", "customers"): "owned by",
}


def quote(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def inspect_schema(db: sqlite3.Connection):
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    keys = {}
    links = []
    for table in tables:
        columns = list(db.execute(f"PRAGMA table_info({table})"))
        keys[table] = [r[1] for r in sorted(columns, key=lambda r: r[5]) if r[5]]
        assert keys[table], f"Missing key: {table}"
        mandatory_columns = {r[1] for r in columns if r[3] or r[5]}
        unique_sets = [set(keys[table])]
        for idx in db.execute(f"PRAGMA index_list({table})"):
            if idx[2]:
                unique_sets.append({r[2] for r in db.execute(f"PRAGMA index_info({idx[1]})")})
        grouped = defaultdict(list)
        for row in db.execute(f"PRAGMA foreign_key_list({table})"):
            grouped[row[0]].append(row)
        for group in grouped.values():
            group.sort(key=lambda r: r[1])
            parent = group[0][2]
            child_columns = [r[3] for r in group]
            required = all(c in mandatory_columns for c in child_columns)
            unique = set(child_columns) in unique_sets
            links.append((table, parent, child_columns, required, unique))
    return tables, keys, links


def main() -> None:
    db = sqlite3.connect(":memory:")
    db.executescript((ROOT / "schema.sql").read_text())
    tables, keys, links = inspect_schema(db)
    entities = set(tables) - set(RELATIONSHIP_TABLES)
    assert len(tables) == 70 and len(entities) == 59 and len(RELATIONSHIP_TABLES) == 11
    assert len(links) == 102
    assert ISA_CHILDREN <= entities and WEAK_ENTITIES <= entities
    assert all(parent in entities or parent == "stock_positions" for _, parent, *_ in links)

    # Every schema FK must be accounted for in the conceptual model. A relation
    # table is a diamond; ISA links share one triangle; all others get a named
    # relationship diamond.
    ordinary = {(child, parent) for child, parent, *_ in links
                if child in entities and not (child in ISA_CHILDREN and parent == "accounts")}
    assert ordinary == set(RELATION_NAMES), (ordinary - set(RELATION_NAMES), set(RELATION_NAMES) - ordinary)

    graph = defaultdict(set)
    for child, parent, *_ in links:
        graph[child].add(parent)
        graph[parent].add(child)
    seen = {tables[0]}
    queue = deque(seen)
    while queue:
        for neighbor in graph[queue.popleft()]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    assert len(seen) == 70, f"Disconnected model objects: {set(tables) - seen}"

    color = {name: COLORS[i] for i, names in enumerate(GROUPS.values()) for name in names}
    dot = [
        "graph ConceptualER {",
        'graph [rankdir=LR, bgcolor="white", outputorder=edgesfirst, overlap=false, splines=polyline, nodesep=0.18, ranksep=0.45, fontname="Helvetica", fontsize=19, label="MarketLab · complete conceptual ER draft · 59 entity candidates · 11 relationship sets", labelloc=t];',
        'node [fontname="Helvetica", fontsize=9, color="#60728c", style=filled, margin="0.07,0.04"];',
        'edge [fontname="Helvetica", fontsize=7, color="#899bb3", penwidth=0.8];',
    ]
    for table in sorted(entities):
        key = ", ".join(keys[table])
        shape = "box" if table not in WEAK_ENTITIES else "box"
        peripheries = 2 if table in WEAK_ENTITIES else 1
        dot.append(f'{quote(table)} [shape={shape}, peripheries={peripheries}, fillcolor={quote(color[table])}, label={quote(table + chr(10) + "PK: " + key)}];')
    for table, (name, attribute) in RELATIONSHIP_TABLES.items():
        label = name + ("\n" + attribute if attribute else "")
        fill = "#cceeff" if table == "stock_positions" else "#f8d9ed" if table == "stock_reservations" else "#fff4dd"
        dot.append(f'{quote(table)} [shape=diamond, fillcolor={quote(fill)}, label={quote(label)}, tooltip={quote(table)}];')
    dot.append('"isa_accounts" [shape=triangle, fillcolor="#f3e8ff", label="ISA"];')
    dot.append('"accounts" -- "isa_accounts";')
    for child in sorted(ISA_CHILDREN):
        dot.append(f'"isa_accounts" -- {quote(child)};')

    # The aggregation encloses all three participants and their ternary Stocks
    # relationship. Reserves connects an order line to the aggregated Stocks.
    dot.append('subgraph cluster_aggregation { label="Aggregation: Seller × Variant × Warehouse STOCKS"; color="#af89b7"; style="rounded,dashed"; bgcolor="#fdf8ff"; "seller_organizations"; "variants"; "warehouses"; "stock_positions"; }')

    relation_count = 0
    for child, parent, columns, required, unique in sorted(links):
        if child in RELATIONSHIP_TABLES:
            dot.append(f'{quote(child)} -- {quote(parent)};')
            continue
        if child in ISA_CHILDREN and parent == "accounts":
            continue
        relation_count += 1
        relation_id = f"R{relation_count:03d}"
        name = RELATION_NAMES[(child, parent)]
        identifying = child in WEAK_ENTITIES and parent in {"orders", "purchase_orders", "invoices"}
        dot.append(f'{quote(relation_id)} [shape=diamond, peripheries={2 if identifying else 1}, fillcolor="#f0f4fa", label={quote(name)}, tooltip={quote(child + "." + ",".join(columns) + " → " + parent)}];')
        # Endpoint ranges describe participation in the relationship. The
        # child has one parent when required; a parent may have zero children.
        child_range = "1..1" if required else "0..1"
        parent_range = "0..1" if unique else "0..N"
        dot.append(f'{quote(child)} -- {quote(relation_id)} [taillabel={quote(child_range)}];')
        dot.append(f'{quote(relation_id)} -- {quote(parent)} [headlabel={quote(parent_range)}];')
    dot.append("}")
    dot_path = DOCS / "er_conceptual_full.dot"
    svg_path = DOCS / "er_conceptual_full.svg"
    dot_path.write_text("\n".join(dot) + "\n")
    subprocess.run(["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)
    print(f"Conceptual draft: {len(entities)} entity candidates, {len(RELATIONSHIP_TABLES)} relationship sets, {relation_count} named FK relationships, one connected model.")


if __name__ == "__main__":
    main()
