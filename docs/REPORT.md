# MarketLab project report — draft

## Part 1 — Entities

Each row below defines one of the **59 proposed conceptual entity/subtype sets** and its key. `PK` means primary key; composite keys are shown with `+`. The 11 relationship sets are described in part 2 and [`CONCEPTUAL_ER.md`](CONCEPTUAL_ER.md). The instructor must review whether all 59 candidates satisfy the course's entity definition.

## Identity and organisations (10)

| Entity | Key | Meaning |
| --- | --- | --- |
| `accounts` | `account_id` | Login identity and common name/email for a person. |
| `customers` | `account_id` | Customer specialization of an account; owns carts and orders. |
| `staff` | `account_id` | Staff specialization; works for sellers and answers questions. |
| `couriers` | `account_id` | Courier specialization; records delivery attempts. |
| `seller_organizations` | `seller_id` | Independent business that owns listings and procurement. |
| `addresses` | `address_id` | Saved delivery address belonging to an account. |
| `seller_verifications` | `verification_id` | Review outcome for a seller's onboarding. |
| `seller_policies` | `policy_id` | Versioned seller policy such as returns or shipping. |
| `seller_payout_accounts` | `payout_account_id` | Seller's masked payout destination and verification state. |
| `customer_notifications` | `notification_id` | Message delivered to a customer with read state. |

## Catalogue (12)

| Entity | Key | Meaning |
| --- | --- | --- |
| `categories` | `category_id` | Product classification; may have a parent category. |
| `brands` | `brand_id` | Manufacturer or brand name. |
| `products` | `product_id` | Shared product description, category, and brand. |
| `variants` | `variant_id` | Specific sellable version of a product, identified by SKU. |
| `product_images` | `image_id` | Display image for a product. |
| `attributes` | `attribute_id` | Reusable variant dimension such as color or size. |
| `listings` | `listing_id` | One seller's priced offer of a variant. |
| `price_history` | `price_history_id` | Audit record of a listing price change. |
| `product_questions` | `question_id` | Customer question about a product. |
| `product_answers` | `answer_id` | Staff answer to a product question. |
| `product_documents` | `document_id` | Manual, warranty, or other product document. |
| `seller_reviews` | `seller_review_id` | Customer rating and text about a seller. |

## Shopping and marketing (7)

| Entity | Key | Meaning |
| --- | --- | --- |
| `carts` | `cart_id` | Current shopping basket of one customer. |
| `wishlists` | `wishlist_id` | Named collection saved by a customer. |
| `promotions` | `promotion_id` | Seller-funded timed discount campaign. |
| `coupons` | `coupon_id` | Code that exposes a promotion with a usage limit. |
| `reviews` | `review_id` | Customer rating and text about a product. |
| `review_images` | `review_image_id` | Image attached to a product review. |
| `gift_cards` | `gift_card_id` | Prepaid card with initial and remaining balance. |

## Inventory and procurement (11)

| Entity | Key | Meaning |
| --- | --- | --- |
| `warehouses` | `warehouse_id` | Physical fulfillment location, potentially shared by sellers. |
| `storage_zones` | `zone_id` | Named area within a warehouse. |
| `storage_bins` | `bin_id` | Small storage location within a zone. |
| `stock_batches` | `batch_id` | Received stock batch kept in a storage bin. |
| `stock_movements` | `movement_id` | Signed stock change and its reason. |
| `suppliers` | `supplier_id` | Supplier used by a seller to obtain variants. |
| `purchase_orders` | `purchase_order_id` | Seller's order to a supplier for delivery to a warehouse. |
| `purchase_order_lines` | `purchase_order_id + line_no` | Variant, quantity, and unit cost on a purchase order. |
| `goods_receipts` | `receipt_id` | Evidence that a purchase order shipment arrived. |
| `warehouse_inspections` | `inspection_id` | Staff inspection of a warehouse. |
| `inventory_adjustments` | `adjustment_id` | Authorized correction of a stock batch after a count. |

## Orders, payment, and reservations (7)

| Entity | Key | Meaning |
| --- | --- | --- |
| `orders` | `order_id` | Customer purchase with address, status, and total. |
| `order_lines` | `order_id + line_no` | Weak entity: ordered listing, quantity, and captured unit price. |
| `order_status_events` | `event_id` | Append-only history of an order's status. |
| `payments` | `payment_id` | Payment summary belonging to one order. |
| `payment_transactions` | `transaction_id` | Capture or refund event under a payment. |
| `invoices` | `invoice_id` | Invoice header for an order. |
| `invoice_lines` | `invoice_id + line_no` | Invoice amount corresponding to an order line. |

## Fulfillment and delivery (7)

| Entity | Key | Meaning |
| --- | --- | --- |
| `fulfillments` | `fulfillment_id` | Seller/warehouse processing group for an order. |
| `packages` | `package_id` | Physical package created for a fulfillment. |
| `carriers` | `carrier_id` | Shipping company. |
| `shipments` | `shipment_id` | Carrier movement of one package with tracking code. |
| `tracking_events` | `tracking_event_id` | Time-stamped tracking update for a shipment. |
| `delivery_attempts` | `attempt_id` | Courier visit and outcome for a shipment. |
| `proof_of_delivery` | `proof_id` | Recipient and evidence for a delivery attempt. |

## After-sales and support (5)

| Entity | Key | Meaning |
| --- | --- | --- |
| `return_requests` | `return_id` | Customer request to return delivered goods. |
| `refunds` | `refund_id` | Money returned against a return and payment. |
| `support_tickets` | `ticket_id` | Customer support case, optionally about an order. |
| `ticket_messages` | `message_id` | Message within a support ticket, authored by an account. |
| `return_inspections` | `return_inspection_id` | Staff evaluation of returned goods before restocking. |

**Total: 59 proposed entity/subtype sets.** The other 11 SQL tables implement relationship sets, so the relational schema still has 70 tables. Each proposed entity has a declared primary key.

## Part 2 — Relationships

The 11 relationship sets implemented as SQL tables are `seller_staff`, `variant_values`, `cart_lines`, `wishlist_items`, `stock_positions`, `coupon_redemptions`, `gift_card_uses`, `stock_reservations`, `fulfillment_lines`, `return_lines`, and `goods_receipt_lines`. Their participants and relationship attributes are listed in [`CONCEPTUAL_ER.md`](CONCEPTUAL_ER.md). The following sections explain these and the named relationships among entity sets.

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
