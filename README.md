# MarketLab — CS202 two-person database project

**Proposed e-sheet title:** Multi-Vendor Marketplace and Order Fulfillment Management System

MarketLab is a local, database-backed web demo for a multi-vendor marketplace. Its conceptual ER model has **71 entity sets and 103 relationship sets** in one connected diagram, implemented as an **83-table SQLite schema**. It has a browser interface, sample data, and working order, stock, shipment, return, and SQL reporting flows. The code uses Python's standard library only; there is no package installation, external API, or GitHub dependency.

**Course-fit status:** This is a working draft. Read [`docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md`](docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md) before treating it as a submission. The team confirmed that the project-specific AI allowance applies to two-person projects; all generated work must still be checked and understood. PostgreSQL and the exact required SQL queries still need confirmation.

**ER design (Part 1 deliverable):** [`docs/REPORT.md`](docs/REPORT.md) starts with the guideline checklist and the four required concepts, followed by Part 1 (every entity) and Part 2 (every relationship). The diagrams in [`docs/er/`](docs/er/) use the notation of the course slides.

## Run

Requires Python 3.10 or newer.

```bash
cd CS_202_Project
python3 app.py
```

Open <http://127.0.0.1:8000>. The first run creates `marketplace.db` and inserts sample data. To reset the demo, stop the server, delete `marketplace.db`, and run it again. To keep a separate database, set `PROJECT_DB=/path/to/demo.db` before running. Set `PORT` to change the port.

## Try the complete workflow

1. Open **Catalog** and add products from both sellers to the cart.
2. Open **Cart** and place a demo order. Checkout atomically creates order lines, stock reservations, stock movements, a simulated payment, and an invoice.
3. Open **Seller panel** and select **Fulfill & ship**. The app creates one fulfillment and shipment per seller/warehouse group.
4. Select **Mark delivered**. The customer order now offers a return form.
5. Submit a return request, then approve/refund it in **Seller panel**.
6. Open **Reports** to see aggregate SQL results.

## Files

| File | Purpose |
| --- | --- |
| `schema.sql` | All 83 tables, keys, constraints, foreign keys and ISA triggers |
| `seed.py` | Repeatable initial sample data |
| `app.py` | HTTP routes, SQL queries, and transaction logic |
| `static/style.css` | Responsive interface styling |
| `tools/er_model.py` | The conceptual ER model: which table is an entity or a relationship, names, explanations, weak entities, ISA, aggregation |
| `tools/build_er.py` | Checks the model against `schema.sql` and the guidelines, then generates the diagrams and the report |
| `docs/REPORT.md` | Generated report: guideline checklist, the four concepts, Part 1 entities, Part 2 relationships |
| `docs/er/full.svg` | Generated complete ER diagram (large; zoom in) |
| `docs/er/area-*.svg` | Generated ER diagram per business area |
| `docs/er/legend.svg` | The notation used in the diagrams |
| `docs/DESIGN.md` | Implementation decisions: cardinalities, transactions, integrity rules |
| `docs/SQL_QUERIES.md` | Query explanations and SQL examples |
| `docs/ANLATIM_TR.md` | Step-by-step Turkish explanation and oral-exam questions |
| `docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md` | Detailed Turkish course comparison, walkthrough, and remaining work |
| `tests/test_workflow.py` | End-to-end database workflow checks |

## Regenerate the ER diagrams and report

Edit `tools/er_model.py` or `schema.sql`, never the generated files. Then:

```bash
python3 tools/build_er.py --check     # model vs schema + guideline checks only
cd tools/render && npm install && cd ../..   # once, for SVG rendering (Graphviz as WebAssembly)
python3 tools/build_er.py             # checks, DOT, SVG and docs/REPORT.md
```

## What is implemented, and what remains

The database schema models the complete domain. The web interface implements the **core vertical slice**: browse listings, cart, checkout, inventory allocation, invoice/payment records, fulfillment, shipment, delivery, returns, and reports. Several modeled areas, such as coupons, supplier purchasing, gift cards, staff permissions, and support tickets, have schema and relationships but **do not yet have full UI workflows**. Do not present those as finished features.

This is a **local academic demo**. It uses a fixed demo customer and a shared seller panel. It has no authentication, real payment gateway, real carrier integration, or production security controls. Payment and refund rows are explicitly simulated. The return approval records a refund but does not put returned goods back into sellable stock; inspection and restocking would be a later step.

The PDF gives no exact list of required SQL queries or delivery dates. Check the course page for later query specifications and adapt `docs/SQL_QUERIES.md` and the Reports page to them.

## How to explain it in an oral examination

Start with the four ER concepts in `docs/DESIGN.md`, then walk through a two-seller order. Show why `orders` and `order_lines` are separate, how the three-column key of `stock_positions` represents one seller stocking one variant at one warehouse, and how `stock_reservations` links the order line to that stock relationship. Explain that `BEGIN IMMEDIATE` plus rollback keeps stock, reservations, and payment records consistent if checkout fails. Run the tests and `PRAGMA foreign_key_check` as evidence.

Both students should read and be able to modify `schema.sql` and `app.py`. The guidelines explicitly require the team to check, understand, and verify AI-generated work.
