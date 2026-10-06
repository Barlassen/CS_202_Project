# Complete foreign-key relationship appendix

Generated from `schema.sql`: **70 tables**, **102 foreign-key relationships**, **one connected component**.

Each row explains which child record points to which parent. `Required` means the child must have exactly one parent; `Optional` means zero or one. The final column is the maximum number of children one parent can have under declared uniqueness constraints. A parent may have zero children in all cases.

| Child | Parent | Key mapping | Child participation | Parent can have |
| --- | --- | --- | --- | --- |
| `addresses` | `accounts` | `account_id` → `account_id` | Required | many |
| `cart_lines` | `carts` | `cart_id` → `cart_id` | Required | many |
| `cart_lines` | `listings` | `listing_id` → `listing_id` | Required | many |
| `carts` | `customers` | `customer_id` → `account_id` | Required | one |
| `categories` | `categories` | `parent_id` → `category_id` | Optional | many |
| `coupon_redemptions` | `coupons` | `coupon_id` → `coupon_id` | Required | many |
| `coupon_redemptions` | `customers` | `customer_id` → `account_id` | Required | many |
| `coupon_redemptions` | `orders` | `order_id` → `order_id` | Required | many |
| `coupons` | `promotions` | `promotion_id` → `promotion_id` | Required | many |
| `couriers` | `accounts` | `account_id` → `account_id` | Required | one |
| `customer_notifications` | `customers` | `customer_id` → `account_id` | Required | many |
| `customers` | `accounts` | `account_id` → `account_id` | Required | one |
| `delivery_attempts` | `couriers` | `courier_id` → `account_id` | Required | many |
| `delivery_attempts` | `shipments` | `shipment_id` → `shipment_id` | Required | many |
| `fulfillment_lines` | `fulfillments` | `fulfillment_id` → `fulfillment_id` | Required | many |
| `fulfillment_lines` | `order_lines` | `order_id` → `order_id`, `line_no` → `line_no` | Required | many |
| `fulfillments` | `orders` | `order_id` → `order_id` | Required | many |
| `fulfillments` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `fulfillments` | `warehouses` | `warehouse_id` → `warehouse_id` | Required | many |
| `gift_card_uses` | `gift_cards` | `gift_card_id` → `gift_card_id` | Required | many |
| `gift_card_uses` | `orders` | `order_id` → `order_id` | Required | many |
| `gift_cards` | `customers` | `buyer_customer_id` → `account_id` | Required | many |
| `goods_receipt_lines` | `goods_receipts` | `receipt_id` → `receipt_id` | Required | many |
| `goods_receipt_lines` | `purchase_order_lines` | `purchase_order_id` → `purchase_order_id`, `line_no` → `line_no` | Required | many |
| `goods_receipts` | `purchase_orders` | `purchase_order_id` → `purchase_order_id` | Required | many |
| `inventory_adjustments` | `staff` | `staff_id` → `account_id` | Required | many |
| `inventory_adjustments` | `stock_batches` | `batch_id` → `batch_id` | Required | many |
| `invoice_lines` | `invoices` | `invoice_id` → `invoice_id` | Required | many |
| `invoice_lines` | `order_lines` | `order_id` → `order_id`, `order_line_no` → `line_no` | Required | many |
| `invoices` | `orders` | `order_id` → `order_id` | Required | one |
| `listings` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `listings` | `variants` | `variant_id` → `variant_id` | Required | many |
| `order_lines` | `listings` | `listing_id` → `listing_id` | Required | many |
| `order_lines` | `orders` | `order_id` → `order_id` | Required | many |
| `order_status_events` | `orders` | `order_id` → `order_id` | Required | many |
| `orders` | `addresses` | `address_id` → `address_id` | Required | many |
| `orders` | `customers` | `customer_id` → `account_id` | Required | many |
| `packages` | `fulfillments` | `fulfillment_id` → `fulfillment_id` | Required | many |
| `payment_transactions` | `payments` | `payment_id` → `payment_id` | Required | many |
| `payments` | `orders` | `order_id` → `order_id` | Required | one |
| `price_history` | `listings` | `listing_id` → `listing_id` | Required | many |
| `product_answers` | `product_questions` | `question_id` → `question_id` | Required | many |
| `product_answers` | `staff` | `staff_id` → `account_id` | Required | many |
| `product_documents` | `products` | `product_id` → `product_id` | Required | many |
| `product_images` | `products` | `product_id` → `product_id` | Required | many |
| `product_questions` | `customers` | `customer_id` → `account_id` | Required | many |
| `product_questions` | `products` | `product_id` → `product_id` | Required | many |
| `products` | `brands` | `brand_id` → `brand_id` | Required | many |
| `products` | `categories` | `category_id` → `category_id` | Required | many |
| `promotions` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `proof_of_delivery` | `delivery_attempts` | `attempt_id` → `attempt_id` | Required | one |
| `purchase_order_lines` | `purchase_orders` | `purchase_order_id` → `purchase_order_id` | Required | many |
| `purchase_order_lines` | `variants` | `variant_id` → `variant_id` | Required | many |
| `purchase_orders` | `suppliers` | `supplier_id` → `supplier_id` | Required | many |
| `purchase_orders` | `warehouses` | `warehouse_id` → `warehouse_id` | Required | many |
| `refunds` | `payments` | `payment_id` → `payment_id` | Required | many |
| `refunds` | `return_requests` | `return_id` → `return_id` | Required | many |
| `return_inspections` | `return_requests` | `return_id` → `return_id` | Required | many |
| `return_inspections` | `staff` | `staff_id` → `account_id` | Required | many |
| `return_lines` | `order_lines` | `order_id` → `order_id`, `line_no` → `line_no` | Required | many |
| `return_lines` | `return_requests` | `return_id` → `return_id` | Required | many |
| `return_requests` | `customers` | `customer_id` → `account_id` | Required | many |
| `return_requests` | `orders` | `order_id` → `order_id` | Required | many |
| `review_images` | `reviews` | `review_id` → `review_id` | Required | many |
| `reviews` | `customers` | `customer_id` → `account_id` | Required | many |
| `reviews` | `products` | `product_id` → `product_id` | Required | many |
| `seller_organizations` | `accounts` | `owner_account_id` → `account_id` | Required | many |
| `seller_payout_accounts` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `seller_policies` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `seller_reviews` | `customers` | `customer_id` → `account_id` | Required | many |
| `seller_reviews` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `seller_staff` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `seller_staff` | `staff` | `staff_account_id` → `account_id` | Required | many |
| `seller_verifications` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `seller_verifications` | `staff` | `checked_by` → `account_id` | Optional | many |
| `shipments` | `carriers` | `carrier_id` → `carrier_id` | Required | many |
| `shipments` | `packages` | `package_id` → `package_id` | Required | one |
| `staff` | `accounts` | `account_id` → `account_id` | Required | one |
| `stock_batches` | `stock_positions` | `seller_id` → `seller_id`, `variant_id` → `variant_id`, `warehouse_id` → `warehouse_id` | Required | many |
| `stock_batches` | `storage_bins` | `bin_id` → `bin_id` | Required | many |
| `stock_movements` | `stock_batches` | `batch_id` → `batch_id` | Required | many |
| `stock_positions` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `stock_positions` | `variants` | `variant_id` → `variant_id` | Required | many |
| `stock_positions` | `warehouses` | `warehouse_id` → `warehouse_id` | Required | many |
| `stock_reservations` | `order_lines` | `order_id` → `order_id`, `line_no` → `line_no` | Required | many |
| `stock_reservations` | `stock_positions` | `seller_id` → `seller_id`, `variant_id` → `variant_id`, `warehouse_id` → `warehouse_id` | Required | many |
| `storage_bins` | `storage_zones` | `zone_id` → `zone_id` | Required | many |
| `storage_zones` | `warehouses` | `warehouse_id` → `warehouse_id` | Required | many |
| `suppliers` | `seller_organizations` | `seller_id` → `seller_id` | Required | many |
| `support_tickets` | `customers` | `customer_id` → `account_id` | Required | many |
| `support_tickets` | `orders` | `order_id` → `order_id` | Optional | many |
| `ticket_messages` | `accounts` | `author_account_id` → `account_id` | Required | many |
| `ticket_messages` | `support_tickets` | `ticket_id` → `ticket_id` | Required | many |
| `tracking_events` | `shipments` | `shipment_id` → `shipment_id` | Required | many |
| `variant_values` | `attributes` | `attribute_id` → `attribute_id` | Required | many |
| `variant_values` | `variants` | `variant_id` → `variant_id` | Required | many |
| `variants` | `products` | `product_id` → `product_id` | Required | many |
| `warehouse_inspections` | `staff` | `staff_id` → `account_id` | Required | many |
| `warehouse_inspections` | `warehouses` | `warehouse_id` → `warehouse_id` | Required | many |
| `wishlist_items` | `listings` | `listing_id` → `listing_id` | Required | many |
| `wishlist_items` | `wishlists` | `wishlist_id` → `wishlist_id` | Required | many |
| `wishlists` | `customers` | `customer_id` → `account_id` | Required | many |
