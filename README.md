# MarketLab — CS202 two-person database project

**Proposed e-sheet title:** Multi-Vendor Marketplace and Order Fulfillment Management System

MarketLab is a local, database-backed web demo for a multi-vendor marketplace. Its conceptual ER model has **67 entity sets and 99 relationship sets** in one connected diagram, implemented as an **79-table SQLite schema**. It has a browser interface, sample data, and working order, stock, shipment, return, and SQL reporting flows. The application uses Python's standard library only; there is no package installation, external API, or GitHub dependency. Only re-rendering the ER diagrams needs Node.js (see below).

**Course-fit status:** This is a working draft. Read [`docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md`](docs/DERS_UYUMU_VE_ADIM_ADIM_ANLATIM.md) before treating it as a submission. The team confirmed that the project-specific AI allowance applies to two-person projects; all generated work must still be checked and understood. PostgreSQL and the exact required SQL queries still need confirmation.

**ER design (Part 1 deliverable):** [`docs/REPORT.md`](docs/REPORT.md) starts with the guideline checklist and the four required concepts, followed by Part 1 (every entity) and Part 2 (every relationship). The diagrams in [`docs/er/`](docs/er/) use the notation of the course slides.

## Changes in the `project_changes` branch

**After the instructor's feedback (27 October 2026): 71 → 67 entities, 103 → 99 relationships.** Four entity sets that repeated information were merged:

| Removed | Merged into | Why |
| --- | --- | --- |
| Inventory_Adjustments | Stock_Movements (optional `staff_id`, relationship *Authorizes*) | Both stored a signed quantity change of a batch with its reason and time. |
| Refunds | Payment_Transactions (`return_id`, relationship *Refund_For*) | A refund was stored twice: as a Refunds row and as a transaction of kind `refund`. |
| Proof_Of_Delivery | Delivery_Attempts (`recipient_name`, `evidence_url`) | One-to-one with a successful attempt, with no relationships of its own. |
| Storage_Zones | Storage_Bins (`zone_code`, relationship *Located_In* to Warehouses) | A zone had only a code. Bins now reference their warehouse directly, and a composite foreign key keeps each batch's bin in the batch's own warehouse. |

The three major consistency issues in the feedback (a goods receipt receiving another purchase order's lines, a return covering another order's lines, a refund charged to another order's payment) are now prevented in the schema with composite foreign keys. A final check found five more rules of the same kind (an order's billing address and payment method belong to its customer; invoice and fulfilment lines belong to their own order; a support ticket is about its customer's own order), enforced the same way. The report lists these rules under *Design choices → Consistency across relationships* and under each relationship involved.

Minor items: Couriers in Serves, Order_Lines in Reserves, Fulfillments in Includes and Return_Requests in Returns now have total participation (the application already guaranteed it). *Ships_To* is renamed *Billed_To*: the order's address is its billing address and sets the VAT rate, also for pickup orders. The zone-code uniqueness item is closed by the Storage_Zones merge.

Numbers in the report changed; [`docs/NUMBERING_OLD_NEW.md`](docs/NUMBERING_OLD_NEW.md) maps the old E/R numbers used in the feedback to the new ones.


This branch reworks the ER design against `Guidelines.pdf` and the instructor's Chapter 2 slides. Compared with `main`:

**Entities: 59 → 71.** Twelve new entity sets, each with its own attributes and relationships:

| Area | New entity sets |
| --- | --- |
| Locations and tax | Countries, Cities, Delivery_Zones, Pickup_Points, Tax_Rates |
| People and sellers | Departments, Loyalty_Tiers, Vehicles, Commission_Plans, Seller_Payouts |
| Orders and payment | Payment_Methods |
| Delivery | Carrier_Services (a second weak entity: the service code is unique only within its carrier) |

Entity sets that could look like attributes (images, price history, status events, ...) now carry an explicit *entity vs. attribute* justification in the report. Even if all 12 of them were rejected, 55 entities would remain.

**Diagrams in course notation** ([`docs/er/`](docs/er/)): attributes as ovals with the key underlined; arrows for key constraints, bold lines for total participation; weak entities and identifying relationships drawn bold with a dashed partial key; ISA triangle with its overlap and covering decisions; aggregation as a dashed box. There is one complete diagram (`full.svg`), one per business area (`area-*.svg`) and a legend.

**Two corrected constructs:**
- *Weak entity:* `Order_Lines` shows only its partial key `line_no`; the owner's key comes from the bold identifying relationship `Contains`, not from the entity box.
- *Aggregation:* `Reserves` now connects to the dashed aggregation box around `Stocks`, not to the `Stocks` diamond. `Batch_Of` (each stock batch belongs to exactly one stock position) is a second relationship on the aggregation.

**ISA decided:** overlap not allowed, covering holds. Overlap is enforced by triggers: a `customers`/`staff`/`couriers` row must match its account's role, and an account cannot change its role once it has a subtype row. Covering cannot be required in SQL (the account row must exist first); the application creates every account together with its subtype row.

**Submission files:** [`docs/MarketLab_Project_Description.docx`](docs/MarketLab_Project_Description.docx) (introduction, Part 1, Part 2, generated from the same model) and [`docs/MarketLab_ER_Diagram.pdf`](docs/MarketLab_ER_Diagram.pdf) (the complete diagram).

**Report rewritten** ([`docs/REPORT.md`](docs/REPORT.md)): guideline checklist, the four required concepts, design choices, Part 1 with every entity (key, attributes with domains, justification) and Part 2 with every relationship (participants, key constraint, participation, attributes, SQL implementation).

**Single source of truth:** the report and diagrams are generated from [`tools/er_model.py`](tools/er_model.py) by [`tools/build_er.py`](tools/build_er.py), which also checks the model against `schema.sql` and guideline items 1–4. `tests/test_design.py` runs those checks.

**Schema clean-ups:**
- The customer is no longer stored again in `coupon_redemptions` and `return_requests`, because the order already determines it.
- Relationship tables (`coupon_redemptions`, `gift_card_uses`, `stock_reservations`) are keyed by their participants instead of a surrogate id.
- `addresses` and `warehouses` refer to `cities`; `payments` refer to `payment_methods`; `shipments` refer to `carrier_services`.

**Removed** (superseded, still in git history): `docs/CONCEPTUAL_ER.md`, `ENTITIES.md`, `RELATIONSHIPS.md`, `FOREIGN_KEYS.md`, `GUIDELINE_STATUS.md`, the old `er_*.svg/dot/png` files and the two old generator scripts.

**If you ran `main` before:** delete your old `marketplace.db`. The schema changed from 70 to 79 tables, and the app refuses to open the old database.

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
| `schema.sql` | All 79 tables, keys, constraints, foreign keys and ISA triggers |
| `seed.py` | Repeatable initial sample data |
| `app.py` | HTTP routes, SQL queries, and transaction logic |
| `static/style.css` | Responsive interface styling |
| `tools/er_model.py` | The conceptual ER model: which table is an entity or a relationship, names, explanations, weak entities, ISA, aggregation |
| `tools/build_er.py` | Checks the model against `schema.sql` and the guidelines, then generates the diagrams and the report |
| `docs/MarketLab_Project_Description.docx` | Generated submission report (Word), as item 5 of the guidelines asks: a short introduction, Part 1 (every entity) and Part 2 (every relationship). Team names and student IDs are filled in. |
| `docs/MarketLab_ER_Diagram.pdf` | The complete ER diagram with a legend of the notation, as a one-page vector PDF, submitted next to the report (made from `docs/er/full.svg`; printing the SVG to PDF from a browser gives the same result). |
| `docs/REPORT.md` | Generated report: guideline checklist, the four concepts, Part 1 entities, Part 2 relationships |
| `docs/er/full.svg` | Generated complete ER diagram (large; zoom in) |
| `docs/er/area-*.svg`, `concept-*.svg` | Generated ER diagram per business area, and one small figure per required construct (PNG copies are used in the Word document) |
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
python3 tools/build_er.py             # checks, DOT, SVG/PNG, docs/REPORT.md and docs/er/model.json
node tools/render/report_docx.mjs     # Word document from model.json and the PNG figures
```

## What is implemented, and what remains

The database schema models the complete domain. The web interface implements the **core vertical slice**: browse listings, cart, checkout, inventory allocation, invoice/payment records, fulfillment, shipment, delivery, returns, and reports. Several modeled areas, such as coupons, supplier purchasing, gift cards, staff permissions, and support tickets, have schema and relationships but **do not yet have full UI workflows**. Do not present those as finished features.

This is a **local academic demo**. It uses a fixed demo customer and a shared seller panel. It has no authentication, real payment gateway, real carrier integration, or production security controls. Payment and refund rows are explicitly simulated. On delivery the demo records the customer as the recipient; it is not real proof of who received the parcel. The return approval records a refund but does not put returned goods back into sellable stock; inspection and restocking would be a later step.

The PDF gives no exact list of required SQL queries or delivery dates. Check the course page for later query specifications and adapt `docs/SQL_QUERIES.md` and the Reports page to them.

## How to explain it in an oral examination

Start with the four ER concepts in `docs/DESIGN.md`, then walk through a two-seller order. Show why `orders` and `order_lines` are separate, how the three-column key of `stock_positions` represents one seller stocking one variant at one warehouse, and how `stock_reservations` links the order line to that stock relationship. Explain that `BEGIN IMMEDIATE` plus rollback keeps stock, reservations, and payment records consistent if checkout fails. Run the tests and `PRAGMA foreign_key_check` as evidence.

Both students should read and be able to modify `schema.sql` and `app.py`. The guidelines explicitly require the team to check, understand, and verify AI-generated work.
