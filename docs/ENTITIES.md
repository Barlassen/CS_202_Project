# Report part 1 — entities

Each row below defines one modeled object and its key. `PK` means primary key. Composite keys are shown with `+`. Foreign-key details are in `RELATIONSHIPS.md` and `schema.sql`. Weak and relationship tables are included here for completeness; `DESIGN.md` explains the conservative ER entity count.

## Identity and organisations (11)

| Entity | Key | Meaning |
| --- | --- | --- |
| `accounts` | `account_id` | Login identity and common name/email for a person. |
| `customers` | `account_id` | Customer specialization of an account; owns carts and orders. |
| `staff` | `account_id` | Staff specialization; works for sellers and answers questions. |
| `couriers` | `account_id` | Courier specialization; records delivery attempts. |
| `seller_organizations` | `seller_id` | Independent business that owns listings and procurement. |
| `seller_staff` | `seller_id + staff_account_id` | Assignment of a staff member to a seller. |
| `addresses` | `address_id` | Saved delivery address belonging to an account. |
| `seller_verifications` | `verification_id` | Review outcome for a seller's onboarding. |
| `seller_policies` | `policy_id` | Versioned seller policy such as returns or shipping. |
| `seller_payout_accounts` | `payout_account_id` | Seller's masked payout destination and verification state. |
| `customer_notifications` | `notification_id` | Message delivered to a customer with read state. |

## Catalogue (13)

| Entity | Key | Meaning |
| --- | --- | --- |
| `categories` | `category_id` | Product classification; may have a parent category. |
| `brands` | `brand_id` | Manufacturer or brand name. |
| `products` | `product_id` | Shared product description, category, and brand. |
| `variants` | `variant_id` | Specific sellable version of a product, identified by SKU. |
| `product_images` | `image_id` | Display image for a product. |
| `attributes` | `attribute_id` | Reusable variant dimension such as color or size. |
| `variant_values` | `variant_id + attribute_id` | A variant's value for one attribute. |
| `listings` | `listing_id` | One seller's priced offer of a variant. |
| `price_history` | `price_history_id` | Audit record of a listing price change. |
| `product_questions` | `question_id` | Customer question about a product. |
| `product_answers` | `answer_id` | Staff answer to a product question. |
| `product_documents` | `document_id` | Manual, warranty, or other product document. |
| `seller_reviews` | `seller_review_id` | Customer rating and text about a seller. |

## Shopping and marketing (9)

| Entity | Key | Meaning |
| --- | --- | --- |
| `carts` | `cart_id` | Current shopping basket of one customer. |
| `cart_lines` | `cart_id + listing_id` | Quantity of a listing in a basket. |
| `wishlists` | `wishlist_id` | Named collection saved by a customer. |
| `wishlist_items` | `wishlist_id + listing_id` | Listing saved to a wishlist. |
| `promotions` | `promotion_id` | Seller-funded timed discount campaign. |
| `coupons` | `coupon_id` | Code that exposes a promotion with a usage limit. |
| `reviews` | `review_id` | Customer rating and text about a product. |
| `review_images` | `review_image_id` | Image attached to a product review. |
| `gift_cards` | `gift_card_id` | Prepaid card with initial and remaining balance. |

## Inventory and procurement (13)

| Entity | Key | Meaning |
| --- | --- | --- |
| `warehouses` | `warehouse_id` | Physical fulfillment location, potentially shared by sellers. |
| `storage_zones` | `zone_id` | Named area within a warehouse. |
| `storage_bins` | `bin_id` | Small storage location within a zone. |
| `stock_positions` | `seller_id + variant_id + warehouse_id` | Stock quantity for one seller–variant–warehouse triple. |
| `stock_batches` | `batch_id` | Received stock batch kept in a storage bin. |
| `stock_movements` | `movement_id` | Signed stock change and its reason. |
| `suppliers` | `supplier_id` | Supplier used by a seller to obtain variants. |
| `purchase_orders` | `purchase_order_id` | Seller's order to a supplier for delivery to a warehouse. |
| `purchase_order_lines` | `purchase_order_id + line_no` | Variant, quantity, and unit cost on a purchase order. |
| `goods_receipts` | `receipt_id` | Evidence that a purchase order shipment arrived. |
| `goods_receipt_lines` | `receipt_id + purchase_order_id + line_no` | Received quantity against a purchase order line. |
| `warehouse_inspections` | `inspection_id` | Staff inspection of a warehouse. |
| `inventory_adjustments` | `adjustment_id` | Authorized correction of a stock batch after a count. |

## Orders, payment, and reservations (10)

| Entity | Key | Meaning |
| --- | --- | --- |
| `orders` | `order_id` | Customer purchase with address, status, and total. |
| `order_lines` | `order_id + line_no` | Weak entity: ordered listing, quantity, and captured unit price. |
| `order_status_events` | `event_id` | Append-only history of an order's status. |
| `payments` | `payment_id` | Payment summary belonging to one order. |
| `payment_transactions` | `transaction_id` | Capture or refund event under a payment. |
| `invoices` | `invoice_id` | Invoice header for an order. |
| `invoice_lines` | `invoice_id + line_no` | Invoice amount corresponding to an order line. |
| `coupon_redemptions` | `redemption_id` | Coupon use by a customer on an order. |
| `gift_card_uses` | `gift_card_use_id` | Amount of a gift card applied to an order. |
| `stock_reservations` | `reservation_id` | Amount of a stock position reserved for an order line. |

## Fulfillment and delivery (8)

| Entity | Key | Meaning |
| --- | --- | --- |
| `fulfillments` | `fulfillment_id` | Seller/warehouse processing group for an order. |
| `fulfillment_lines` | `fulfillment_id + order_id + line_no` | Ordered quantity included in a fulfillment. |
| `packages` | `package_id` | Physical package created for a fulfillment. |
| `carriers` | `carrier_id` | Shipping company. |
| `shipments` | `shipment_id` | Carrier movement of one package with tracking code. |
| `tracking_events` | `tracking_event_id` | Time-stamped tracking update for a shipment. |
| `delivery_attempts` | `attempt_id` | Courier visit and outcome for a shipment. |
| `proof_of_delivery` | `proof_id` | Recipient and evidence for a delivery attempt. |

## After-sales and support (6)

| Entity | Key | Meaning |
| --- | --- | --- |
| `return_requests` | `return_id` | Customer request to return delivered goods. |
| `return_lines` | `return_id + order_id + line_no` | Ordered line and quantity included in a return. |
| `refunds` | `refund_id` | Money returned against a return and payment. |
| `support_tickets` | `ticket_id` | Customer support case, optionally about an order. |
| `ticket_messages` | `message_id` | Message within a support ticket, authored by an account. |
| `return_inspections` | `return_inspection_id` | Staff evaluation of returned goods before restocking. |

**Total: 70 tables.** The 70 names here match the tables in `schema.sql`. Each has a declared primary key.
