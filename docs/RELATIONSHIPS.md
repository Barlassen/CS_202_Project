# Report part 2 — relationships

This document explains the relationships by business process. [`FOREIGN_KEYS.md`](FOREIGN_KEYS.md) is the complete, generated list of **all 102 foreign-key relationships**, their exact key columns, required/optional participation, and maximum child cardinality. The diagram in [`er_full.svg`](er_full.svg) shows all 70 tables in one connected component.

## Identity and sellers

An `account` may be specialized as one `customer`, one `staff` member, or one `courier`. Each subtype must share the exact account key. A seller organisation has one owner account and may assign many staff members through `seller_staff`; a staff member may work for more than one seller. An account may save many addresses. A seller may have many verification decisions, policy versions, and payout accounts. A staff member may check a verification. A customer may receive many notifications. The seller owner and staff assignments connect people to marketplace operations.

## Catalogue and offers

A category may contain child categories and classify many products. A brand may label many products. Each product has one category and one brand; it may have many variants, images, questions, and documents. An attribute can be given a value for many variants through `variant_values`. A seller offers a variant through a `listing`: many listings can refer to one variant, while a seller and variant combination is unique. A listing can have many price-history records. A customer asks product questions; staff provide answers. Customers may review products and sellers, and a product review may have images.

## Shopping and marketing

A customer owns one current cart and may own many named wishlists. Each cart line or wishlist item points to one listing. A seller creates promotions; a promotion can issue coupons. A coupon redemption connects a coupon, a customer, and the resulting order, so usage can be audited. A customer buys a gift card, and each use of it connects the gift card to an order. These relationships keep promotional activity attached to actual shoppers and purchases.

## Inventory and procurement

A warehouse contains zones; a zone contains bins. The **ternary** `stock_positions` relationship connects one seller, one variant, and one warehouse, and stores their available quantity. A position can have many received batches; each batch is stored in one bin. Stock movements and inventory adjustments explain changes to batches, with staff responsible for adjustments. A seller uses suppliers. A purchase order connects one supplier to one destination warehouse and contains variant lines. A goods receipt belongs to a purchase order; its receipt lines refer back to particular purchase-order lines. Staff inspect warehouses and record outcomes.

## Orders and aggregation

A customer places many orders, each sent to one saved address. An order owns one or more `order_lines`; the pair `(order_id, line_no)` identifies a line. Each line purchases one listing, capturing the price at checkout even if the listing price changes later. An order has status events, one payment, and one invoice. Payment transactions record capture and refund events; invoice lines map invoice amounts to order lines.

The **aggregation** is explicit in `stock_reservations`: each reservation links one order line to the single seller–variant–warehouse stock relationship it consumes. An order line may create multiple reservations if different warehouses supply it. This is why a reservation stores both `(order_id, line_no)` and `(seller_id, variant_id, warehouse_id)` as foreign keys.

## Fulfillment and delivery

An order can have several fulfillments, grouped by seller and warehouse. A fulfillment has lines tied to original order lines and may contain packages. A package is shipped once via one carrier; a carrier may handle many shipments. Each shipment has tracking events and may have several courier delivery attempts. A successful attempt may have one proof-of-delivery record. This structure allows one customer order to become multiple seller shipments.

## Returns and support

A customer can request returns for an order. Each return line identifies the original order line and return quantity. An approved return can produce a refund against the original payment. Staff can inspect returned goods before any later restocking. A customer may open support tickets, optionally linked to an order; each ticket has messages authored by accounts. Thus after-sales records trace back to the customer, order, line, and payment.

## Design cautions to discuss with the instructor

The SQL model permits some cross-row combinations that a production database would constrain further with triggers or composite foreign keys. For example, it does not prove that an `orders.address_id` belongs to the same customer, or that a `stock_batches.bin_id` is inside its `warehouse_id`. The demo writes only coherent combinations. For an assessed submission, these are useful examples of invariants beyond basic foreign keys. The role discriminator in `accounts` likewise relies on application convention. We have documented these limits so they can be improved deliberately.
