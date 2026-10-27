PRAGMA foreign_keys = ON;

-- Locations
CREATE TABLE countries (
  country_code TEXT PRIMARY KEY CHECK(length(country_code) = 2), name TEXT NOT NULL UNIQUE
);
CREATE TABLE cities (
  city_id INTEGER PRIMARY KEY, country_code TEXT NOT NULL REFERENCES countries(country_code),
  name TEXT NOT NULL, UNIQUE(country_code, name)
);
CREATE TABLE delivery_zones (
  delivery_zone_id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL REFERENCES cities(city_id),
  name TEXT NOT NULL, UNIQUE(city_id, name)
);
CREATE TABLE pickup_points (
  pickup_point_id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL REFERENCES cities(city_id),
  name TEXT NOT NULL, opening_hours TEXT NOT NULL
);
CREATE TABLE tax_rates (
  tax_rate_id INTEGER PRIMARY KEY, country_code TEXT NOT NULL REFERENCES countries(country_code),
  name TEXT NOT NULL, rate_percent REAL NOT NULL CHECK(rate_percent BETWEEN 0 AND 100),
  UNIQUE(country_code, name)
);

-- People and sellers
-- ISA: accounts is specialized into customers, staff, and couriers.
-- Overlap is not allowed (one role per account); covering holds (role is mandatory).
CREATE TABLE accounts (
  account_id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('customer','staff','courier'))
);
CREATE TABLE loyalty_tiers (
  tier_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  min_points INTEGER NOT NULL CHECK(min_points >= 0),
  discount_percent INTEGER NOT NULL CHECK(discount_percent BETWEEN 0 AND 50)
);
CREATE TABLE customers (
  account_id INTEGER PRIMARY KEY REFERENCES accounts(account_id),
  joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  loyalty_points INTEGER NOT NULL DEFAULT 0 CHECK(loyalty_points >= 0),
  tier_id INTEGER REFERENCES loyalty_tiers(tier_id)
);
-- departments.manager_id refers forward to staff; SQLite checks it when rows are written.
CREATE TABLE departments (
  department_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  budget_cents INTEGER NOT NULL DEFAULT 0 CHECK(budget_cents >= 0),
  manager_id INTEGER REFERENCES staff(account_id)
);
CREATE TABLE staff (
  account_id INTEGER PRIMARY KEY REFERENCES accounts(account_id),
  title TEXT NOT NULL,
  department_id INTEGER NOT NULL REFERENCES departments(department_id)
);
CREATE TABLE vehicles (
  vehicle_id INTEGER PRIMARY KEY, fleet_code TEXT NOT NULL UNIQUE,
  vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('bicycle','motorbike','van')),
  capacity_kg INTEGER NOT NULL CHECK(capacity_kg > 0)
);
CREATE TABLE couriers (
  account_id INTEGER PRIMARY KEY REFERENCES accounts(account_id),
  license_no TEXT NOT NULL UNIQUE,
  vehicle_id INTEGER UNIQUE REFERENCES vehicles(vehicle_id)
);
CREATE TABLE courier_zones (
  courier_id INTEGER NOT NULL REFERENCES couriers(account_id),
  delivery_zone_id INTEGER NOT NULL REFERENCES delivery_zones(delivery_zone_id),
  since TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (courier_id, delivery_zone_id)
);
-- The subtype row must match the role stored on the account (no overlap).
CREATE TRIGGER customers_role BEFORE INSERT ON customers
WHEN (SELECT role FROM accounts WHERE account_id = NEW.account_id) IS NOT 'customer'
BEGIN SELECT RAISE(ABORT, 'account role is not customer'); END;
CREATE TRIGGER staff_role BEFORE INSERT ON staff
WHEN (SELECT role FROM accounts WHERE account_id = NEW.account_id) IS NOT 'staff'
BEGIN SELECT RAISE(ABORT, 'account role is not staff'); END;
CREATE TRIGGER couriers_role BEFORE INSERT ON couriers
WHEN (SELECT role FROM accounts WHERE account_id = NEW.account_id) IS NOT 'courier'
BEGIN SELECT RAISE(ABORT, 'account role is not courier'); END;
CREATE TABLE commission_plans (
  plan_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  rate_percent REAL NOT NULL CHECK(rate_percent BETWEEN 0 AND 50)
);
CREATE TABLE seller_organizations (
  seller_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
  owner_account_id INTEGER NOT NULL REFERENCES accounts(account_id),
  plan_id INTEGER NOT NULL REFERENCES commission_plans(plan_id)
);
CREATE TABLE seller_staff (
  seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  staff_account_id INTEGER NOT NULL REFERENCES staff(account_id),
  assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (seller_id, staff_account_id)
);
CREATE TABLE addresses (
  address_id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(account_id),
  city_id INTEGER NOT NULL REFERENCES cities(city_id),
  label TEXT NOT NULL, street TEXT NOT NULL, postal_code TEXT NOT NULL
);
CREATE TABLE seller_verifications (
  verification_id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
  checked_by INTEGER REFERENCES staff(account_id), checked_at TEXT
);
CREATE TABLE seller_policies (
  policy_id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  policy_type TEXT NOT NULL, body TEXT NOT NULL, effective_at TEXT NOT NULL
);
CREATE TABLE seller_payout_accounts (
  payout_account_id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  masked_iban TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','verified','disabled'))
);
CREATE TABLE seller_payouts (
  payout_id INTEGER PRIMARY KEY,
  payout_account_id INTEGER NOT NULL REFERENCES seller_payout_accounts(payout_account_id),
  period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
  status TEXT NOT NULL CHECK(status IN ('scheduled','paid','failed')), paid_at TEXT,
  CHECK(period_end >= period_start)
);
CREATE TABLE customer_notifications (
  notification_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  read_at TEXT
);

-- Catalogue
CREATE TABLE categories (
  category_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  parent_id INTEGER REFERENCES categories(category_id)
);
CREATE TABLE brands (brand_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE products (
  product_id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL REFERENCES categories(category_id),
  brand_id INTEGER NOT NULL REFERENCES brands(brand_id),
  name TEXT NOT NULL, description TEXT NOT NULL
);
CREATE TABLE variants (
  variant_id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(product_id),
  sku TEXT NOT NULL UNIQUE, variant_name TEXT NOT NULL
);
CREATE TABLE product_images (
  image_id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(product_id),
  image_url TEXT NOT NULL, alt_text TEXT NOT NULL, display_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE attributes (attribute_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE variant_values (
  variant_id INTEGER NOT NULL REFERENCES variants(variant_id),
  attribute_id INTEGER NOT NULL REFERENCES attributes(attribute_id),
  value TEXT NOT NULL, PRIMARY KEY (variant_id, attribute_id)
);
CREATE TABLE listings (
  listing_id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  variant_id INTEGER NOT NULL REFERENCES variants(variant_id),
  price_cents INTEGER NOT NULL CHECK(price_cents > 0),
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  UNIQUE(seller_id, variant_id)
);
CREATE TABLE price_history (
  price_history_id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(listing_id),
  old_price_cents INTEGER NOT NULL, new_price_cents INTEGER NOT NULL,
  changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE product_questions (
  question_id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(product_id),
  customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  body TEXT NOT NULL, asked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE product_answers (
  answer_id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES product_questions(question_id),
  staff_id INTEGER NOT NULL REFERENCES staff(account_id), body TEXT NOT NULL,
  answered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE product_documents (
  document_id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(product_id),
  document_type TEXT NOT NULL, file_url TEXT NOT NULL
);
CREATE TABLE seller_reviews (
  seller_review_id INTEGER PRIMARY KEY,
  seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5), body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(seller_id, customer_id)
);

-- Shopping and marketing
CREATE TABLE carts (
  cart_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL UNIQUE REFERENCES customers(account_id),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE cart_lines (
  cart_id INTEGER NOT NULL REFERENCES carts(cart_id) ON DELETE CASCADE,
  listing_id INTEGER NOT NULL REFERENCES listings(listing_id),
  quantity INTEGER NOT NULL CHECK(quantity > 0), PRIMARY KEY(cart_id, listing_id)
);
CREATE TABLE wishlists (
  wishlist_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  name TEXT NOT NULL
);
CREATE TABLE wishlist_items (
  wishlist_id INTEGER NOT NULL REFERENCES wishlists(wishlist_id),
  listing_id INTEGER NOT NULL REFERENCES listings(listing_id),
  PRIMARY KEY(wishlist_id, listing_id)
);
CREATE TABLE promotions (
  promotion_id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  name TEXT NOT NULL, starts_at TEXT NOT NULL, ends_at TEXT NOT NULL,
  discount_percent INTEGER NOT NULL CHECK(discount_percent BETWEEN 1 AND 100)
);
CREATE TABLE coupons (
  coupon_id INTEGER PRIMARY KEY, promotion_id INTEGER NOT NULL REFERENCES promotions(promotion_id),
  code TEXT NOT NULL UNIQUE, max_uses INTEGER NOT NULL CHECK(max_uses > 0)
);
CREATE TABLE reviews (
  review_id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(product_id),
  customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5), body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(product_id, customer_id)
);
CREATE TABLE review_images (
  review_image_id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL REFERENCES reviews(review_id),
  image_url TEXT NOT NULL
);
CREATE TABLE gift_cards (
  gift_card_id INTEGER PRIMARY KEY, buyer_customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  code TEXT NOT NULL UNIQUE, initial_cents INTEGER NOT NULL CHECK(initial_cents > 0),
  balance_cents INTEGER NOT NULL CHECK(balance_cents >= 0)
);

-- Inventory and procurement
CREATE TABLE warehouses (
  warehouse_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
  city_id INTEGER NOT NULL REFERENCES cities(city_id)
);
CREATE TABLE storage_bins (
  bin_id INTEGER PRIMARY KEY, warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  zone_code TEXT NOT NULL, code TEXT NOT NULL,
  UNIQUE(warehouse_id, zone_code, code), UNIQUE(bin_id, warehouse_id)
);
-- This is the ternary Seller × Variant × Warehouse stock relationship.
CREATE TABLE stock_positions (
  seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  variant_id INTEGER NOT NULL REFERENCES variants(variant_id),
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  available_qty INTEGER NOT NULL DEFAULT 0 CHECK(available_qty >= 0),
  reorder_point INTEGER NOT NULL DEFAULT 0 CHECK(reorder_point >= 0),
  PRIMARY KEY(seller_id, variant_id, warehouse_id)
);
CREATE TABLE stock_batches (
  batch_id INTEGER PRIMARY KEY,
  seller_id INTEGER NOT NULL, variant_id INTEGER NOT NULL, warehouse_id INTEGER NOT NULL,
  bin_id INTEGER NOT NULL,
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  quantity INTEGER NOT NULL CHECK(quantity >= 0),
  FOREIGN KEY(seller_id, variant_id, warehouse_id)
    REFERENCES stock_positions(seller_id, variant_id, warehouse_id),
  -- The bin must be in the batch's own warehouse.
  FOREIGN KEY(bin_id, warehouse_id) REFERENCES storage_bins(bin_id, warehouse_id)
);
CREATE TABLE stock_movements (
  movement_id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES stock_batches(batch_id),
  staff_id INTEGER REFERENCES staff(account_id),
  quantity_delta INTEGER NOT NULL CHECK(quantity_delta <> 0), reason TEXT NOT NULL,
  moved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE suppliers (
  supplier_id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  name TEXT NOT NULL, contact_email TEXT NOT NULL
);
CREATE TABLE purchase_orders (
  purchase_order_id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id),
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  ordered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL
);
CREATE TABLE purchase_order_lines (
  purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(purchase_order_id),
  line_no INTEGER NOT NULL, variant_id INTEGER NOT NULL REFERENCES variants(variant_id),
  quantity INTEGER NOT NULL CHECK(quantity > 0), unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents >= 0),
  PRIMARY KEY(purchase_order_id, line_no)
);
CREATE TABLE goods_receipts (
  receipt_id INTEGER PRIMARY KEY,
  purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(purchase_order_id),
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(receipt_id, purchase_order_id)
);
CREATE TABLE goods_receipt_lines (
  receipt_id INTEGER NOT NULL,
  purchase_order_id INTEGER NOT NULL, line_no INTEGER NOT NULL,
  received_qty INTEGER NOT NULL CHECK(received_qty > 0),
  PRIMARY KEY(receipt_id, purchase_order_id, line_no),
  -- The received line must belong to the receipt's own purchase order.
  FOREIGN KEY(receipt_id, purchase_order_id)
    REFERENCES goods_receipts(receipt_id, purchase_order_id),
  FOREIGN KEY(purchase_order_id, line_no)
    REFERENCES purchase_order_lines(purchase_order_id, line_no)
);
CREATE TABLE warehouse_inspections (
  inspection_id INTEGER PRIMARY KEY, warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  staff_id INTEGER NOT NULL REFERENCES staff(account_id),
  result TEXT NOT NULL, inspected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Orders and payment
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  address_id INTEGER NOT NULL REFERENCES addresses(address_id),
  pickup_point_id INTEGER REFERENCES pickup_points(pickup_point_id),
  placed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL CHECK(status IN ('placed','shipped','delivered','cancelled')),
  total_cents INTEGER NOT NULL CHECK(total_cents >= 0)
);
-- Weak entity: line_no only identifies an order line within its parent order.
CREATE TABLE order_lines (
  order_id INTEGER NOT NULL REFERENCES orders(order_id), line_no INTEGER NOT NULL,
  listing_id INTEGER NOT NULL REFERENCES listings(listing_id),
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents > 0),
  PRIMARY KEY(order_id, line_no)
);
CREATE TABLE order_status_events (
  event_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id),
  status TEXT NOT NULL, event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE payment_methods (
  payment_method_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  method_type TEXT NOT NULL CHECK(method_type IN ('card','wallet','bank_transfer')),
  masked_number TEXT NOT NULL, expires_on TEXT
);
CREATE TABLE payments (
  payment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE REFERENCES orders(order_id),
  payment_method_id INTEGER NOT NULL REFERENCES payment_methods(payment_method_id),
  status TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
  UNIQUE(payment_id, order_id)
);
CREATE TABLE payment_transactions (
  transaction_id INTEGER PRIMARY KEY, payment_id INTEGER NOT NULL,
  -- order_id adds no information of its own: it ties both foreign keys below to one order,
  -- so a refund is paid back from the payment of the order that was returned.
  order_id INTEGER NOT NULL, return_id INTEGER,
  kind TEXT NOT NULL CHECK(kind IN ('capture','refund')),
  status TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK((kind = 'refund') = (return_id IS NOT NULL)),
  FOREIGN KEY(payment_id, order_id) REFERENCES payments(payment_id, order_id),
  FOREIGN KEY(return_id, order_id) REFERENCES return_requests(return_id, order_id)
);
CREATE TABLE invoices (
  invoice_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE REFERENCES orders(order_id),
  issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, total_cents INTEGER NOT NULL CHECK(total_cents >= 0)
);
CREATE TABLE invoice_lines (
  invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id), line_no INTEGER NOT NULL,
  order_id INTEGER NOT NULL, order_line_no INTEGER NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
  tax_rate_id INTEGER REFERENCES tax_rates(tax_rate_id),
  PRIMARY KEY(invoice_id, line_no),
  FOREIGN KEY(order_id, order_line_no) REFERENCES order_lines(order_id, line_no)
);
-- The customer of a redemption is the customer of the order, so it is not stored again.
CREATE TABLE coupon_redemptions (
  coupon_id INTEGER NOT NULL REFERENCES coupons(coupon_id),
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  redeemed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(coupon_id, order_id)
);
CREATE TABLE gift_card_uses (
  gift_card_id INTEGER NOT NULL REFERENCES gift_cards(gift_card_id),
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  PRIMARY KEY(gift_card_id, order_id)
);

-- Aggregation: an order line reserves the Seller × Variant × Warehouse relationship.
CREATE TABLE stock_reservations (
  order_id INTEGER NOT NULL, line_no INTEGER NOT NULL,
  seller_id INTEGER NOT NULL, variant_id INTEGER NOT NULL, warehouse_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  PRIMARY KEY(order_id, line_no, seller_id, variant_id, warehouse_id),
  FOREIGN KEY(order_id, line_no) REFERENCES order_lines(order_id, line_no),
  FOREIGN KEY(seller_id, variant_id, warehouse_id)
    REFERENCES stock_positions(seller_id, variant_id, warehouse_id)
);

-- Fulfillment
CREATE TABLE fulfillments (
  fulfillment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id),
  seller_id INTEGER NOT NULL REFERENCES seller_organizations(seller_id),
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE fulfillment_lines (
  fulfillment_id INTEGER NOT NULL REFERENCES fulfillments(fulfillment_id),
  order_id INTEGER NOT NULL, line_no INTEGER NOT NULL,
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  PRIMARY KEY(fulfillment_id, order_id, line_no),
  FOREIGN KEY(order_id, line_no) REFERENCES order_lines(order_id, line_no)
);
CREATE TABLE packages (
  package_id INTEGER PRIMARY KEY, fulfillment_id INTEGER NOT NULL REFERENCES fulfillments(fulfillment_id),
  weight_grams INTEGER NOT NULL CHECK(weight_grams > 0)
);
CREATE TABLE carriers (carrier_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
-- Weak entity: service_code only identifies a service within its carrier.
CREATE TABLE carrier_services (
  carrier_id INTEGER NOT NULL REFERENCES carriers(carrier_id), service_code TEXT NOT NULL,
  name TEXT NOT NULL, max_delivery_days INTEGER NOT NULL CHECK(max_delivery_days > 0),
  PRIMARY KEY(carrier_id, service_code)
);
CREATE TABLE shipments (
  shipment_id INTEGER PRIMARY KEY, package_id INTEGER NOT NULL UNIQUE REFERENCES packages(package_id),
  carrier_id INTEGER NOT NULL, service_code TEXT NOT NULL,
  tracking_code TEXT NOT NULL UNIQUE, status TEXT NOT NULL CHECK(status IN ('shipped','delivered')),
  shipped_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  delivered_at TEXT,
  FOREIGN KEY(carrier_id, service_code) REFERENCES carrier_services(carrier_id, service_code)
);
CREATE TABLE tracking_events (
  tracking_event_id INTEGER PRIMARY KEY, shipment_id INTEGER NOT NULL REFERENCES shipments(shipment_id),
  status TEXT NOT NULL, location TEXT NOT NULL,
  event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE delivery_attempts (
  attempt_id INTEGER PRIMARY KEY, shipment_id INTEGER NOT NULL REFERENCES shipments(shipment_id),
  courier_id INTEGER NOT NULL REFERENCES couriers(account_id),
  attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  outcome TEXT NOT NULL CHECK(outcome IN ('delivered','failed')),
  recipient_name TEXT, evidence_url TEXT,
  notes TEXT,
  CHECK((outcome = 'delivered') = (recipient_name IS NOT NULL)),
  CHECK(outcome = 'delivered' OR evidence_url IS NULL)
);
-- A shipment is delivered at most once; failed attempts may repeat.
CREATE UNIQUE INDEX one_delivered_attempt_per_shipment
  ON delivery_attempts(shipment_id) WHERE outcome = 'delivered';

-- After-sales and support
CREATE TABLE return_requests (
  return_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id),
  reason TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('requested','approved','rejected')),
  requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(return_id, order_id)
);
CREATE TABLE return_lines (
  return_id INTEGER NOT NULL,
  order_id INTEGER NOT NULL, line_no INTEGER NOT NULL,
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  PRIMARY KEY(return_id, order_id, line_no),
  -- The returned line must belong to the return request's own order.
  FOREIGN KEY(return_id, order_id) REFERENCES return_requests(return_id, order_id),
  FOREIGN KEY(order_id, line_no) REFERENCES order_lines(order_id, line_no)
);
CREATE TABLE support_tickets (
  ticket_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(account_id),
  order_id INTEGER REFERENCES orders(order_id),
  subject TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('open','closed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE ticket_messages (
  message_id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES support_tickets(ticket_id),
  author_account_id INTEGER NOT NULL REFERENCES accounts(account_id),
  body TEXT NOT NULL, sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE return_inspections (
  return_inspection_id INTEGER PRIMARY KEY,
  return_id INTEGER NOT NULL REFERENCES return_requests(return_id),
  staff_id INTEGER NOT NULL REFERENCES staff(account_id),
  condition TEXT NOT NULL, inspected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_listings_variant ON listings(variant_id);
CREATE INDEX idx_stock_positions_variant ON stock_positions(variant_id);
CREATE INDEX idx_orders_customer ON orders(customer_id, placed_at);
CREATE INDEX idx_order_lines_listing ON order_lines(listing_id);
CREATE INDEX idx_tracking_shipment ON tracking_events(shipment_id);
