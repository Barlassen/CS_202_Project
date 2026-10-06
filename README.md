# MarketLab — CS202 two-person database project

**Proposed e-sheet title:** Multi-Vendor Marketplace and Order Fulfillment Management System

MarketLab is a local, database-backed web demo for a multi-vendor marketplace. It has a **70-table connected SQLite relational model**, a browser interface, sample data, and working order, stock, shipment, return, and SQL reporting flows. The code uses Python's standard library only; there is no package installation, external API, or GitHub dependency.

**Course-fit status:** This is a working draft. Read [`docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md`](docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md) before treating it as a submission. The team confirmed that the project-specific AI allowance applies to two-person projects; all generated work must still be checked and understood. PostgreSQL and the exact required SQL queries still need confirmation.

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
| `schema.sql` | All 70 tables, keys, constraints, and foreign keys |
| `seed.py` | Repeatable initial sample data |
| `app.py` | HTTP routes, SQL queries, and transaction logic |
| `static/style.css` | Responsive interface styling |
| `docs/DESIGN.md` | Conceptual ER design and the four required concepts |
| `docs/ENTITIES.md` | Part 1 of report: every entity and its key |
| `docs/RELATIONSHIPS.md` | Part 2 of report: relationship meanings and cardinalities |
| `docs/REPORT.md` | Combined two-part draft report for submission review |
| `docs/FOREIGN_KEYS.md` | Exact list of all 102 foreign-key relationships |
| `docs/SQL_QUERIES.md` | Query explanations and SQL examples |
| `docs/ANLATIM_TR.md` | Step-by-step Turkish explanation and oral-exam questions |
| `docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md` | Detailed Turkish course comparison, walkthrough, and remaining work |
| `docs/er_full.svg` | Zoomable full relational relationship diagram |
| `docs/er_conceptual.svg` | Diagram of the four required ER concepts |
| `docs/er_conceptual_full.svg` | Complete connected conceptual ER **draft**: 59 entity candidates and 11 relationship sets |
| `docs/CONCEPTUAL_ER.md` | Conceptual classification, notation, and review checklist |
| `tests/test_workflow.py` | End-to-end database workflow checks |

## What is implemented, and what remains

The database schema models the complete domain. The web interface implements the **core vertical slice**: browse listings, cart, checkout, inventory allocation, invoice/payment records, fulfillment, shipment, delivery, returns, and reports. Several modeled areas, such as coupons, supplier purchasing, gift cards, staff permissions, and support tickets, have schema and relationships but **do not yet have full UI workflows**. Do not present those as finished features.

This is a **local academic demo**. It uses a fixed demo customer and a shared seller panel. It has no authentication, real payment gateway, real carrier integration, or production security controls. Payment and refund rows are explicitly simulated. The return approval records a refund but does not put returned goods back into sellable stock; inspection and restocking would be a later step.

The PDF gives no exact list of required SQL queries or delivery dates. Check the course page for later query specifications and adapt `docs/SQL_QUERIES.md` and the Reports page to them.

## How to explain it in an oral examination

Start with the four ER concepts in `docs/DESIGN.md`, then walk through a two-seller order. Show why `orders` and `order_lines` are separate, how the three-column key of `stock_positions` represents one seller stocking one variant at one warehouse, and how `stock_reservations` links the order line to that stock relationship. Explain that `BEGIN IMMEDIATE` plus rollback keeps stock, reservations, and payment records consistent if checkout fails. Run the tests and `PRAGMA foreign_key_check` as evidence.

Both students should read and be able to modify `schema.sql` and `app.py`. The guidelines explicitly require the team to check, understand, and verify AI-generated work.
