"""Generate the complete FK appendix and zoomable diagram from schema.sql."""
from collections import defaultdict, deque
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

GROUPS = {
    "Identity and organisations": "accounts customers staff couriers seller_organizations seller_staff addresses seller_verifications seller_policies seller_payout_accounts customer_notifications".split(),
    "Catalogue": "categories brands products variants product_images attributes variant_values listings price_history product_questions product_answers product_documents seller_reviews".split(),
    "Shopping and marketing": "carts cart_lines wishlists wishlist_items promotions coupons reviews review_images gift_cards".split(),
    "Inventory and procurement": "warehouses storage_zones storage_bins stock_positions stock_batches stock_movements suppliers purchase_orders purchase_order_lines goods_receipts goods_receipt_lines warehouse_inspections inventory_adjustments".split(),
    "Orders and payment": "orders order_lines order_status_events payments payment_transactions invoices invoice_lines coupon_redemptions gift_card_uses stock_reservations".split(),
    "Fulfillment": "fulfillments fulfillment_lines packages carriers shipments tracking_events delivery_attempts proof_of_delivery".split(),
    "After-sales and support": "return_requests return_lines refunds support_tickets ticket_messages return_inspections".split(),
}
COLORS = ["#e8efff", "#e9f7f0", "#fff2e5", "#e9f4f8", "#f1eafa", "#fff0f3", "#f4f1e8"]


def main() -> None:
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript((ROOT / "schema.sql").read_text())
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    grouped_names = [name for names in GROUPS.values() for name in names]
    assert len(tables) == 70 and set(tables) == set(grouped_names) and len(grouped_names) == len(set(grouped_names))

    links = []
    graph = defaultdict(set)
    for table in tables:
        info = {r[1]: r for r in db.execute(f"PRAGMA table_info({table})")}
        fks = defaultdict(list)
        for row in db.execute(f"PRAGMA foreign_key_list({table})"):
            fks[row[0]].append(row)
        unique_sets = []
        for idx in db.execute(f"PRAGMA index_list({table})"):
            if idx[2]:
                unique_sets.append({r[2] for r in db.execute(f"PRAGMA index_info({idx[1]})")})
        primary = {name for name, row in info.items() if row[5]}
        if primary:
            unique_sets.append(primary)
        for rows in fks.values():
            rows.sort(key=lambda row: row[1])
            parent = rows[0][2]
            child_columns = [row[3] for row in rows]
            parent_columns = [row[4] for row in rows]
            mandatory = all(info[name][3] or name in primary for name in child_columns)
            parent_max = "one" if set(child_columns) in unique_sets else "many"
            links.append((table, parent, child_columns, parent_columns, mandatory, parent_max))
            graph[table].add(parent)
            graph[parent].add(table)

    seen = {tables[0]}
    queue = deque(seen)
    while queue:
        for neighbor in graph[queue.popleft()]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    assert len(seen) == len(tables), f"Disconnected tables: {set(tables) - seen}"

    lines = ["# Complete foreign-key relationship appendix", "",
             f"Generated from `schema.sql`: **{len(tables)} tables**, **{len(links)} foreign-key relationships**, **one connected component**.", "",
             "Each row explains which child record points to which parent. `Required` means the child must have exactly one parent; `Optional` means zero or one. The final column is the maximum number of children one parent can have under declared uniqueness constraints. A parent may have zero children in all cases.", "",
             "| Child | Parent | Key mapping | Child participation | Parent can have |", "| --- | --- | --- | --- | --- |"]
    for child, parent, child_cols, parent_cols, mandatory, maximum in sorted(links):
        mapping = ", ".join(f"`{a}` → `{b}`" for a, b in zip(child_cols, parent_cols))
        lines.append(f"| `{child}` | `{parent}` | {mapping} | {'Required' if mandatory else 'Optional'} | {maximum} |")
    (DOCS / "FOREIGN_KEYS.md").write_text("\n".join(lines) + "\n")

    dot = ["digraph ER {", 'graph [rankdir=LR, bgcolor="white", nodesep="0.25", ranksep="0.75", splines=polyline, fontname="Helvetica", label="MarketLab relational diagram · 70 tables", labelloc=t, fontsize=22];',
           'node [shape=box, style="rounded,filled", color="#a8b7ce", fontname="Helvetica", fontsize=10, margin="0.08,0.05"];',
           'edge [color="#899bb3", arrowsize=0.5, penwidth=0.8];']
    for i, (label, names) in enumerate(GROUPS.items()):
        dot.append(f'subgraph cluster_{i} {{ label="{label}"; color="#c8d3e1"; style="rounded";')
        for name in names:
            color = COLORS[i]
            if name == "order_lines":
                color = "#ffd09a"
            if name == "stock_positions":
                color = "#b9e4ff"
            if name == "stock_reservations":
                color = "#f6c8ec"
            dot.append(f'"{name}" [fillcolor="{color}"];')
        dot.append("}")
    for child, parent, _, _, _, _ in links:
        dot.append(f'"{child}" -> "{parent}";')
    dot.append("}")
    (DOCS / "er_full.dot").write_text("\n".join(dot) + "\n")
    subprocess.run(["dot", "-Tsvg", str(DOCS / "er_full.dot"), "-o", str(DOCS / "er_full.svg")], check=True)
    print(f"Verified {len(tables)} tables, {len(links)} FKs, one connected component.")


if __name__ == "__main__":
    main()
