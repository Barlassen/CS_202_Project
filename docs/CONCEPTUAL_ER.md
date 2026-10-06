# Complete conceptual ER draft and review guide

This document accompanies [`er_conceptual_full.svg`](er_conceptual_full.svg). The SVG is a **single connected conceptual-model draft** covering all 70 modeled objects. It distinguishes **59 entity/subtype candidates** (rectangles) from **11 relationship sets** (diamonds). A separate [`er_full.svg`](er_full.svg) shows the relational foreign-key graph. The two diagrams answer different questions.

The model is generated from `schema.sql` plus explicit modeling choices in `tools/generate_conceptual_er.py`. The generator checks that all 70 SQL tables are classified, all 102 foreign keys are accounted for, all entity candidates have keys, and the graph is one connected component. This is an auditable proposed interpretation of the course's “50 entities” rule; the instructor decides whether each proposed entity is acceptable.

## Legend

| Symbol | Meaning |
| --- | --- |
| Rectangle with `PK` | Candidate strong entity or subtype and its key. Color identifies its business area. |
| Double rectangle | Weak/dependent entity: `order_lines`, `purchase_order_lines`, or `invoice_lines`. |
| Diamond | Conceptual relationship. An ordinary foreign-key relationship has a semantic verb label. |
| Double diamond | Identifying relationship between a weak entity and its owner. |
| Triangle | `accounts` ISA into `customers`, `staff`, and `couriers`. |
| Blue diamond with three participants | `STOCKS`: seller × variant × warehouse, with quantity and reorder point. |
| Dashed aggregation box | Seller, variant, warehouse, and the `STOCKS` relationship treated together as one stock position. |
| Pink diamond | `RESERVES`: an order line reserves a quantity from that aggregated stock position. |

On ordinary foreign-key relationships, `1..1` or `0..1` near the child indicates required/optional reference to a parent. `0..1` or `0..N` near the parent indicates the number of children permitted by the database constraints. These are **schema-derived bounds**, not a claim that every business minimum is enforced by SQL. For example, checkout creates at least one order line, but the schema alone does not require every order to have one.

## The 59 proposed entity/subtype sets

The rectangles in the SVG are precisely the 70 tables in `schema.sql` **except** the 11 relationship sets listed below:

| Domain | Count | Candidate entity/subtype sets |
| --- | ---: | --- |
| Identity and organisations | 10 | `accounts`, `customers`, `staff`, `couriers`, `seller_organizations`, `addresses`, `seller_verifications`, `seller_policies`, `seller_payout_accounts`, `customer_notifications` |
| Catalogue | 12 | `categories`, `brands`, `products`, `variants`, `product_images`, `attributes`, `listings`, `price_history`, `product_questions`, `product_answers`, `product_documents`, `seller_reviews` |
| Shopping and marketing | 7 | `carts`, `wishlists`, `promotions`, `coupons`, `reviews`, `review_images`, `gift_cards` |
| Inventory and procurement | 11 | `warehouses`, `storage_zones`, `storage_bins`, `stock_batches`, `stock_movements`, `suppliers`, `purchase_orders`, `purchase_order_lines`, `goods_receipts`, `warehouse_inspections`, `inventory_adjustments` |
| Orders and payment | 7 | `orders`, `order_lines`, `order_status_events`, `payments`, `payment_transactions`, `invoices`, `invoice_lines` |
| Fulfillment and delivery | 7 | `fulfillments`, `packages`, `carriers`, `shipments`, `tracking_events`, `delivery_attempts`, `proof_of_delivery` |
| After-sales and support | 5 | `return_requests`, `refunds`, `support_tickets`, `ticket_messages`, `return_inspections` |
| **Total** | **59** | |

[`ENTITIES.md`](ENTITIES.md) gives the meaning and key of every named object. Some candidates are event or dependent entity sets (for example `order_status_events`, `payment_transactions`, and `purchase_order_lines`). Their status as distinct conceptual entities should be checked with the course's ER criteria, rather than assumed from the existence of a table.

## The 11 relationship sets excluded from the entity count

| SQL representation | Conceptual relationship | Participants | Relationship attributes |
| --- | --- | --- | --- |
| `seller_staff` | works for | Seller, Staff | assignment time |
| `variant_values` | has attribute | Variant, Attribute | value |
| `cart_lines` | contains | Cart, Listing | quantity |
| `wishlist_items` | saves | Wishlist, Listing | none |
| `stock_positions` | STOCKS (ternary) | Seller, Variant, Warehouse | available quantity, reorder point |
| `coupon_redemptions` | redeems | Coupon, Customer, Order | none |
| `gift_card_uses` | applies card | Gift Card, Order | amount |
| `stock_reservations` | RESERVES (aggregation) | Order Line, aggregated STOCKS | quantity |
| `fulfillment_lines` | includes line | Fulfillment, Order Line | quantity |
| `return_lines` | returns line | Return Request, Order Line | quantity |
| `goods_receipt_lines` | receives line | Goods Receipt, Purchase Order Line | received quantity |

The other 75 named relationship diamonds come from explicit foreign keys between entity sets, such as a customer *places* an order, a seller *offers* a listing, and a shipment is *carried by* a carrier. The exact key columns and database-enforced multiplicities are listed in [`FOREIGN_KEYS.md`](FOREIGN_KEYS.md); the business explanation is in [`RELATIONSHIPS.md`](RELATIONSHIPS.md).

## Four required constructs

1. **Weak entity:** `order_lines` is identified by `orders.order_id` plus partial key `line_no`; the `contains (identifying)` diamond is drawn with a double border. `purchase_order_lines` and `invoice_lines` are also dependent on their owning headers.
2. **ISA:** one `accounts` identity is specialized into customer, staff, or courier. The intended roles are disjoint, but the database does not yet enforce role/subtype agreement or total participation. The final report must state whether the specialization is total or partial.
3. **Ternary:** `STOCKS` is a relationship of Seller × Variant × Warehouse. The quantity belongs to the complete triple; three independent binary relations would lose that assignment.
4. **Aggregation:** `RESERVES` relates an order line to the `STOCKS` triple considered as one object. The boxed region makes the relationship-of-relationship explicit.

## Review before treating this as the final ER submission

1. Open the SVG at full zoom. Follow every group of rectangles and diamonds, and check that each conceptual name matches the meaning of the related rows in `schema.sql`.
2. Review whether all 59 proposed entity/subtype sets meet the instructor's definition of an entity. If fewer than 50 are accepted, remodel the domain with genuinely distinct entities and associated relationships; adding empty tables solely to raise the number is not a valid fix.
3. Confirm the instructor's expected ER notation for keys, cardinality, participation, ISA completeness/disjointness, weak identifying links, and aggregation. Adjust the drawing and report together.
4. Decide and enforce any missing business constraints needed for the submission, such as `accounts.role` matching the subtype and an order's address belonging to the same customer.
5. Re-run `python3 tools/generate_conceptual_er.py` after schema/model changes; review the regenerated SVG rather than editing generated output by hand.

**Current status:** a complete and connected *draft* exists. The formal “at least 50 entities” acceptance and notation review still require a human check against the actual course submission criteria.
