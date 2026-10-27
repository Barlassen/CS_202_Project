"""Conceptual ER model of MarketLab, written in the notation of the course slides
(Ramakrishnan & Gehrke, Chapter 2).

`schema.sql` is the relational implementation of this model. `build_er.py` reads both,
checks that they agree, and generates the ER diagrams and the two-part report.

Only modelling decisions live here: which table is an entity and which is a
relationship, names, explanations, weak entities, the ISA hierarchy, the
aggregation, and business rules that SQL alone does not show. Attributes, keys,
domains, key constraints and participation implied by NOT NULL / UNIQUE are read
from the schema, so the diagram cannot drift from the database.
"""

# Areas only group the report and the per-area diagrams; the full diagram is one graph.
AREAS = {
    "people": "People and accounts",
    "sellers": "Sellers",
    "locations": "Locations and tax",
    "catalogue": "Catalogue",
    "shopping": "Shopping and marketing",
    "inventory": "Inventory and procurement",
    "orders": "Orders and payment",
    "delivery": "Fulfilment and delivery",
    "aftersales": "After-sales and support",
}

# table -> (area, explanation). `WHY_ENTITY` below adds the entity-vs-attribute
# argument for the sets that a reader might otherwise expect to be attributes.
ENTITIES = {
    # People and accounts (sellers follow)
    "accounts": ("people", "A person who can sign in to the marketplace. Every account is exactly one of a customer, a staff member or a courier (see the ISA hierarchy)."),
    "customers": ("people", "An account that shops: it owns a cart, wishlists, saved payment methods and orders, and collects loyalty points."),
    "staff": ("people", "An account that works for the marketplace or for sellers: verifies sellers, answers questions, inspects warehouses and returns. Every staff member belongs to one department."),
    "couriers": ("people", "An account that delivers shipments. A courier holds a licence, may be assigned one vehicle and serves one or more delivery zones."),
    "departments": ("people", "An internal unit of the marketplace (for example Seller Operations). It has a budget and at most one managing staff member."),
    "loyalty_tiers": ("people", "A level of the customer loyalty programme (Bronze, Silver, ...). A customer reaches a tier at a points threshold and receives its discount."),
    "vehicles": ("people", "A fleet vehicle (bicycle, motorbike or van) with a carrying capacity. A vehicle is assigned to at most one courier at a time."),
    "seller_organizations": ("sellers", "An independent business that sells on the marketplace. It is owned by one account, pays commission under one plan and lists products."),
    "commission_plans": ("sellers", "A pricing plan that sets the commission percentage the marketplace keeps from a seller's sales."),
    "seller_verifications": ("sellers", "One onboarding check of a seller (identity, tax documents) with its outcome. A seller can be checked several times."),
    "seller_policies": ("sellers", "A versioned seller rule shown to buyers, such as a return or shipping policy, with the date it takes effect."),
    "seller_payout_accounts": ("sellers", "A bank account (stored masked) into which a seller receives its earnings, with a verification status."),
    "seller_payouts": ("sellers", "One transfer of a seller's earnings for a settlement period into one payout account."),
    "customer_notifications": ("people", "A message sent to a customer (order shipped, price dropped) together with when it was read."),
    # Locations and tax
    "countries": ("locations", "A country the marketplace operates in, identified by its two-letter ISO code."),
    "cities": ("locations", "A city inside a country. Addresses, warehouses, delivery zones and pickup points are located in cities."),
    "addresses": ("locations", "A delivery address saved by an account, located in one city."),
    "delivery_zones": ("locations", "A district of a city that couriers are assigned to serve."),
    "pickup_points": ("locations", "A parcel locker or partner shop in a city where a customer may collect an order instead of home delivery."),
    "tax_rates": ("locations", "A named sales-tax rate (for example Standard VAT 20%) defined by one country and applied to invoice lines."),
    # Catalogue
    "categories": ("catalogue", "A product classification. Categories form a tree: a category may have a parent category."),
    "brands": ("catalogue", "A manufacturer or brand name that labels products."),
    "products": ("catalogue", "A shared catalogue description of a product (name, text) that belongs to one category and one brand. Sellers sell its variants."),
    "variants": ("catalogue", "A concrete, stock-keeping version of a product (for example the black headphones), identified by its SKU."),
    "product_images": ("catalogue", "A picture of a product with alternative text and a display position."),
    "attributes": ("catalogue", "A dimension along which variants differ, such as Color or Size."),
    "listings": ("catalogue", "One seller's priced offer of one variant. A seller can list a variant at most once."),
    "price_history": ("catalogue", "One recorded price change of a listing: the old price, the new price and when it changed."),
    "product_questions": ("catalogue", "A public question that a customer asks about a product."),
    "product_answers": ("catalogue", "A staff member's answer to a product question."),
    "product_documents": ("catalogue", "A downloadable file for a product, such as a manual or a warranty certificate."),
    "seller_reviews": ("catalogue", "A customer's star rating and comment about a seller (at most one per customer and seller)."),
    # Shopping and marketing
    "carts": ("shopping", "The single shopping cart that a customer is currently filling."),
    "wishlists": ("shopping", "A named list in which a customer saves listings for later."),
    "promotions": ("shopping", "A time-limited discount campaign run by a seller."),
    "coupons": ("shopping", "A code issued under a promotion that can be redeemed a limited number of times."),
    "reviews": ("shopping", "A customer's star rating and comment about a product (at most one per customer and product)."),
    "review_images": ("shopping", "A photo attached to a product review."),
    "gift_cards": ("shopping", "A prepaid card bought by a customer, with a code, an initial value and a remaining balance."),
    # Inventory and procurement
    "warehouses": ("inventory", "A fulfilment centre in a city where sellers keep stock."),
    "storage_bins": ("inventory", "A shelf location in a warehouse where stock batches are placed. Its address is a zone code and a shelf code (for example zone A, shelf A-01), unique within the warehouse."),
    "stock_batches": ("inventory", "A physical quantity of one stock position received at one time and stored in one bin. Batches let the system issue the oldest stock first."),
    "stock_movements": ("inventory", "A signed change of a batch's quantity with its reason: made by the system (an order reservation) or entered by hand after a count or damage, then authorised by a staff member."),
    "suppliers": ("inventory", "A wholesaler from which a seller buys goods."),
    "purchase_orders": ("inventory", "An order a seller places with a supplier for delivery to one warehouse."),
    "purchase_order_lines": ("inventory", "One line of a purchase order: which variant, how many and at what unit cost. Numbered within its purchase order."),
    "goods_receipts": ("inventory", "The record of a delivery arriving at the warehouse against a purchase order. One purchase order may arrive in several deliveries."),
    "warehouse_inspections": ("inventory", "A safety or quality inspection of a warehouse performed by a staff member, with its result."),
    # Orders and payment
    "orders": ("orders", "A customer's purchase of one or more listings, delivered to an address or a pickup point, with its status and total."),
    "order_lines": ("orders", "One line of an order: which listing, how many and the unit price at checkout. Numbered within its order."),
    "order_status_events": ("orders", "One step in an order's history (placed, shipped, delivered) with its time."),
    "payment_methods": ("orders", "A card, wallet or bank account a customer has saved for paying (stored masked)."),
    "payments": ("orders", "The payment of one order, made with one payment method, with its amount and status."),
    "payment_transactions": ("orders", "One money movement of a payment: the capture, or a refund paid back for an approved return request."),
    "invoices": ("orders", "The legal invoice issued for an order."),
    "invoice_lines": ("orders", "One line of an invoice: the billed amount for one order line and the tax rate applied. Numbered within its invoice."),
    # Fulfilment and delivery
    "fulfillments": ("delivery", "The part of an order that one seller prepares from one warehouse. A multi-seller order is split into several fulfilments."),
    "packages": ("delivery", "A physical parcel packed for a fulfilment, with its weight."),
    "carriers": ("delivery", "A shipping company that transports packages."),
    "carrier_services": ("delivery", "A delivery service offered by a carrier (Standard, Express) with its maximum delivery time. The service code is only unique within its carrier."),
    "shipments": ("delivery", "The transport of one package with one carrier service, identified by a tracking code."),
    "tracking_events": ("delivery", "One scan of a shipment along its route: status, location and time."),
    "delivery_attempts": ("delivery", "One try by a courier to hand over a shipment, with its outcome. A successful attempt also records the proof of delivery: who received the parcel and, optionally, a photo or signature link; these attributes stay empty on failed attempts. A shipment can fail several times but is delivered at most once."),
    # After-sales and support
    "return_requests": ("aftersales", "A customer's request to send back items of a delivered order, with the reason and its status."),
    "return_inspections": ("aftersales", "The check of returned goods by a staff member before they may be restocked."),
    "support_tickets": ("aftersales", "A help request opened by a customer, optionally about a specific order."),
    "ticket_messages": ("aftersales", "One message in a support ticket's conversation, written by an account."),
}

# Slide "Entity vs. Attribute": a concept must be an entity when an entity can have
# several values of it (attributes cannot be set-valued) or when its structure matters.
WHY_ENTITY = {
    "product_images": "A product has many images, each with its own URL, text and position. Attributes cannot be set-valued, so images are an entity set.",
    "review_images": "A review can carry several photos, so the photos cannot be a single-valued attribute of the review.",
    "price_history": "A listing changes price many times and each change has its own old price, new price and time. Storing only the current price would lose the history.",
    "order_status_events": "An order passes through several statuses and we want the time of each. A single status attribute keeps only the latest one.",
    "tracking_events": "A shipment is scanned many times, each scan with a location and time.",
    "ticket_messages": "A ticket holds a conversation of many messages, each with its own author, which is itself a relationship to Accounts.",
    "customer_notifications": "A customer receives many notifications, each with its own read time.",
    "product_documents": "A product may have several documents of different types.",
    "payment_transactions": "One payment produces several money movements over time (capture, later refunds).",
    "stock_movements": "A batch changes many times and each change must be auditable with its reason and time.",
    "cities": "Addresses, warehouses, zones and pickup points all refer to cities, and we want to search by city. As the slide on addresses says, when the structure matters it must be an entity.",
    "countries": "Cities and tax rates both depend on the country; a separate entity stores the country name once.",
}

# Weak entities: table -> owner table. The identifying relationship is the FK to the owner;
# the partial key is the rest of the primary key.
WEAK_ENTITIES = {
    "order_lines": "orders",
    "purchase_order_lines": "purchase_orders",
    "invoice_lines": "invoices",
    "carrier_services": "carriers",
}

ISA = {
    "parent": "accounts",
    "children": ["customers", "staff", "couriers"],
    "overlap": False,
    "covering": True,
    "explanation": (
        "Customers, staff and couriers share the attributes of an account (e-mail, name) and inherit its key "
        "account_id, but each has its own attributes and takes part in different relationships. "
        "Overlap is not allowed: an account has exactly one role, and triggers reject a subtype row whose "
        "account has a different role. Covering holds: role is mandatory, so every account is one of the three."
    ),
}

# Relationship sets that the schema implements as their own table (many-to-many or n-ary).
# table -> (area, name, explanation)
RELATIONSHIP_TABLES = {
    "seller_staff": ("sellers", "Employs", "A seller employs staff members to run its shop; a staff member may work for several sellers. The relationship records when the assignment started."),
    "courier_zones": ("locations", "Serves", "A courier serves one or more delivery zones and a zone is served by several couriers, each since a given date."),
    "variant_values": ("catalogue", "Has_Value", "A variant has a value for an attribute (Color = Black). The value belongs to the pair, not to either side alone."),
    "cart_lines": ("shopping", "In_Cart", "A cart contains listings, each with a quantity. A listing can be in many customers' carts."),
    "wishlist_items": ("shopping", "Saved_In", "A wishlist holds listings, and the same listing may be saved in many wishlists."),
    "coupon_redemptions": ("shopping", "Redeems", "An order redeems coupons. A coupon can be used by several orders up to its limit, and an order may use several coupons. The customer is not stored again because it is the customer of the order."),
    "gift_card_uses": ("shopping", "Pays_With", "An order is partly paid with gift cards; the relationship records how much of each card was spent."),
    "stock_positions": ("inventory", "Stocks", "TERNARY. A seller stocks a variant in a warehouse, with the available quantity and a reorder point. The quantity belongs to the triple: knowing that a seller sells a variant, that the seller uses a warehouse and that the warehouse holds the variant does not tell how many units of that seller's variant are in that warehouse (the Contracts argument on the Binary vs. Ternary slide)."),
    "goods_receipt_lines": ("inventory", "Receives", "A goods receipt receives some quantity of purchase-order lines. A line can arrive across several receipts."),
    "stock_reservations": ("orders", "Reserves", "AGGREGATION. An order line reserves a quantity from a stock position, that is, from a Stocks relationship (seller, variant, warehouse) treated as one object. One line may be served from several warehouses; the reserved quantities of a line add up to its ordered quantity."),
    "fulfillment_lines": ("delivery", "Includes", "A fulfilment includes some quantity of order lines; a line split across warehouses appears in several fulfilments."),
    "return_lines": ("aftersales", "Returns", "A return request returns some quantity of order lines."),
}

# The ternary relationship set that is aggregated (treated as an entity for participation).
AGGREGATED = "stock_positions"

# Binary relationships implemented as a foreign key in an entity table.
# (child table, first FK column) -> (name, explanation, optional role labels (child role, parent role)).
FK_RELATIONSHIPS = {
    ("cities", "country_code"): ("Part_Of", "Each city is part of exactly one country; a country has many cities."),
    ("delivery_zones", "city_id"): ("Zone_Of", "Each delivery zone lies in exactly one city; a city may be divided into several zones."),
    ("pickup_points", "city_id"): ("Placed_In", "Each pickup point is in exactly one city."),
    ("tax_rates", "country_code"): ("Levied_By", "Each tax rate is defined by exactly one country; a country defines several rates."),
    ("customers", "tier_id"): ("Belongs_To", "A customer belongs to at most one loyalty tier (none before the first purchase); a tier has many customers."),
    ("departments", "manager_id"): ("Manages", "A department is managed by at most one staff member (the same Manages example as the Key Constraints slide). Not every department needs a manager, so participation is partial.", ("managed dept", "manager")),
    ("staff", "department_id"): ("Works_In", "Every staff member works in exactly one department; a department has many staff."),
    ("couriers", "vehicle_id"): ("Drives", "One-to-one: a courier drives at most one vehicle and a vehicle is assigned to at most one courier. Both sides are optional."),
    ("seller_organizations", "owner_account_id"): ("Owns", "Every seller is owned by exactly one account; one person may own several sellers."),
    ("seller_organizations", "plan_id"): ("Subscribes_To", "Every seller is on exactly one commission plan; a plan has many sellers."),
    ("addresses", "account_id"): ("Saves_Address", "Each address is saved by exactly one account; an account can save many addresses."),
    ("addresses", "city_id"): ("Lies_In", "Each address lies in exactly one city."),
    ("seller_verifications", "seller_id"): ("Verification_Of", "Each verification is about exactly one seller; a seller can be verified several times."),
    ("seller_verifications", "checked_by"): ("Checks", "A staff member checks verifications. A verification that is still pending has no checker yet, so the Verification side is partial."),
    ("seller_policies", "seller_id"): ("Publishes", "Each policy is published by exactly one seller."),
    ("seller_payout_accounts", "seller_id"): ("Paid_Into", "Each payout account belongs to exactly one seller; a seller may register several."),
    ("seller_payouts", "payout_account_id"): ("Pays_To", "Each payout is transferred to exactly one payout account."),
    ("customer_notifications", "customer_id"): ("Notifies", "Each notification is sent to exactly one customer."),
    ("categories", "parent_id"): ("Subcategory_Of", "A category may have one parent category; a parent has many subcategories. The same entity set appears in two roles, as in the Reports_To example.", ("child", "parent")),
    ("products", "category_id"): ("Classified_As", "Every product is classified under exactly one category."),
    ("products", "brand_id"): ("Made_By", "Every product is made by exactly one brand."),
    ("variants", "product_id"): ("Variant_Of", "Every variant is a version of exactly one product; a product has at least one variant."),
    ("product_images", "product_id"): ("Illustrates", "Each image illustrates exactly one product."),
    ("listings", "seller_id"): ("Offers", "Each listing is offered by exactly one seller."),
    ("listings", "variant_id"): ("Lists", "Each listing sells exactly one variant; a variant can be listed by several sellers."),
    ("price_history", "listing_id"): ("Price_Change_Of", "Each price change belongs to exactly one listing."),
    ("product_questions", "product_id"): ("Asked_About", "Each question is about exactly one product."),
    ("product_questions", "customer_id"): ("Asks", "Each question is asked by exactly one customer."),
    ("product_answers", "question_id"): ("Answers", "Each answer replies to exactly one question; a question may get several answers."),
    ("product_answers", "staff_id"): ("Writes_Answer", "Each answer is written by exactly one staff member."),
    ("product_documents", "product_id"): ("Documents", "Each document belongs to exactly one product."),
    ("seller_reviews", "seller_id"): ("Reviews_Seller", "Each seller review is about exactly one seller."),
    ("seller_reviews", "customer_id"): ("Writes_Seller_Review", "Each seller review is written by exactly one customer."),
    ("carts", "customer_id"): ("Has_Cart", "One-to-one: every cart belongs to exactly one customer and a customer has at most one cart."),
    ("wishlists", "customer_id"): ("Keeps", "Each wishlist is kept by exactly one customer."),
    ("promotions", "seller_id"): ("Runs", "Each promotion is run by exactly one seller."),
    ("coupons", "promotion_id"): ("Issues", "Each coupon is issued under exactly one promotion."),
    ("reviews", "product_id"): ("Reviews_Product", "Each review is about exactly one product."),
    ("reviews", "customer_id"): ("Writes_Review", "Each review is written by exactly one customer."),
    ("review_images", "review_id"): ("Attached_To", "Each review image is attached to exactly one review."),
    ("gift_cards", "buyer_customer_id"): ("Buys_Gift_Card", "Each gift card is bought by exactly one customer."),
    ("warehouses", "city_id"): ("Sited_In", "Each warehouse is sited in exactly one city."),
    ("storage_bins", "warehouse_id"): ("Located_In", "Each bin is in exactly one warehouse; a warehouse has many bins."),
    ("stock_batches", "seller_id"): ("Batch_Of", "Each batch belongs to exactly one stock position, that is, to one Stocks relationship (aggregation). A stock position consists of many batches."),
    ("stock_batches", "bin_id"): ("Stored_In", "Each batch is stored in exactly one bin, and the bin must be in the batch's own warehouse."),
    ("stock_movements", "batch_id"): ("Moves", "Each movement changes exactly one batch."),
    ("suppliers", "seller_id"): ("Uses_Supplier", "Each supplier record belongs to exactly one seller."),
    ("purchase_orders", "supplier_id"): ("Ordered_From", "Each purchase order is placed with exactly one supplier."),
    ("purchase_orders", "warehouse_id"): ("Delivered_To", "Each purchase order is delivered to exactly one warehouse."),
    ("purchase_order_lines", "purchase_order_id"): ("PO_Has_Line", "IDENTIFYING. A purchase-order line exists only inside its purchase order and is numbered within it."),
    ("purchase_order_lines", "variant_id"): ("Orders_Variant", "Each purchase-order line orders exactly one variant."),
    ("goods_receipts", "purchase_order_id"): ("Receipt_For", "Each goods receipt is for exactly one purchase order."),
    ("warehouse_inspections", "warehouse_id"): ("Inspects", "Each inspection is of exactly one warehouse."),
    ("warehouse_inspections", "staff_id"): ("Conducts", "Each inspection is conducted by exactly one staff member."),
    ("stock_movements", "staff_id"): ("Authorizes", "A manual movement (a count correction or damage) is authorised by one staff member; movements made by the system, such as order reservations, have none."),
    ("orders", "customer_id"): ("Places", "Every order is placed by exactly one customer."),
    ("orders", "address_id"): ("Billed_To", "Every order has exactly one billing address, and the VAT rate comes from its country. A home-delivery order is also shipped to this address; a pickup order is collected at its pickup point (Collect_At)."),
    ("orders", "pickup_point_id"): ("Collect_At", "An order may be collected at one pickup point instead of being delivered to its address."),
    ("order_lines", "order_id"): ("Contains", "IDENTIFYING. An order line exists only inside its order and is numbered within it. Every order has at least one line."),
    ("order_lines", "listing_id"): ("Buys", "Each order line buys exactly one listing."),
    ("order_status_events", "order_id"): ("Status_Of", "Each status event belongs to exactly one order."),
    ("payment_methods", "customer_id"): ("Saves_Method", "Each payment method is saved by exactly one customer."),
    ("payments", "order_id"): ("Paid_By", "One-to-one: every payment is for exactly one order and an order has at most one payment."),
    ("payments", "payment_method_id"): ("Uses_Method", "Every payment uses exactly one saved payment method."),
    ("payment_transactions", "payment_id"): ("Transaction_Of", "Each transaction belongs to exactly one payment."),
    ("invoices", "order_id"): ("Invoiced_As", "One-to-one: every invoice is for exactly one order and an order has at most one invoice."),
    ("invoice_lines", "invoice_id"): ("Invoice_Has_Line", "IDENTIFYING. An invoice line exists only inside its invoice and is numbered within it."),
    ("invoice_lines", "order_id"): ("Bills", "Each invoice line bills exactly one order line."),
    ("invoice_lines", "tax_rate_id"): ("Taxed_At", "An invoice line is taxed at most at one tax rate (none for tax-exempt lines)."),
    ("fulfillments", "order_id"): ("Fulfills", "Each fulfilment fulfils exactly one order."),
    ("fulfillments", "seller_id"): ("Handled_By", "Each fulfilment is handled by exactly one seller."),
    ("fulfillments", "warehouse_id"): ("Picked_From", "Each fulfilment is picked from exactly one warehouse."),
    ("packages", "fulfillment_id"): ("Packed_For", "Each package is packed for exactly one fulfilment."),
    ("carrier_services", "carrier_id"): ("Offers_Service", "IDENTIFYING. A carrier service exists only for its carrier; the service code (STD, EXP) is unique only within the carrier. Every carrier offers at least one service."),
    ("shipments", "package_id"): ("Ships", "One-to-one: every shipment carries exactly one package and a package is shipped at most once."),
    ("shipments", "carrier_id"): ("Ships_Via", "Every shipment travels with exactly one carrier service."),
    ("tracking_events", "shipment_id"): ("Tracks", "Each tracking event is for exactly one shipment."),
    ("delivery_attempts", "shipment_id"): ("Attempts", "Each delivery attempt is for exactly one shipment."),
    ("delivery_attempts", "courier_id"): ("Makes_Attempt", "Each delivery attempt is made by exactly one courier."),
    ("return_requests", "order_id"): ("Return_Of", "Each return request is for exactly one order. The customer is reached through the order."),
    ("payment_transactions", "return_id"): ("Refund_For", "A refund transaction pays back exactly one return request; capture transactions belong to no return."),
    ("support_tickets", "customer_id"): ("Opens", "Each ticket is opened by exactly one customer."),
    ("support_tickets", "order_id"): ("About_Order", "A ticket may be about one order."),
    ("ticket_messages", "ticket_id"): ("Message_In", "Each message belongs to exactly one ticket."),
    ("ticket_messages", "author_account_id"): ("Writes_Message", "Each message is written by exactly one account (customer or staff)."),
    ("return_inspections", "return_id"): ("Inspection_Of", "Each inspection checks exactly one return request."),
    ("return_inspections", "staff_id"): ("Inspects_Return", "Each return inspection is done by exactly one staff member."),
}

# Total participation of the "one" side that SQL cannot declare (it would need a
# check across tables). The application guarantees these. (relationship name, table) -> reason
TOTAL_PARTICIPATION = {
    ("Contains", "orders"): "checkout always creates at least one order line",
    ("PO_Has_Line", "purchase_orders"): "a purchase order is created together with its lines",
    ("Invoice_Has_Line", "invoices"): "an invoice is issued with one line per order line",
    ("Variant_Of", "products"): "a product is only published with at least one variant",
    ("Offers_Service", "carriers"): "a carrier is only usable with at least one service",
    ("Serves", "couriers"): "a courier is registered together with at least one delivery zone",
    ("Reserves", "order_lines"): "checkout reserves stock for every order line and creates no order when stock is short",
    ("Includes", "fulfillments"): "a fulfilment is created together with the order lines it ships",
    ("Returns", "return_requests"): "a return request is created together with the order lines it returns",
}

# Rules that span two relationships. An ER diagram draws each relationship on its own,
# so it cannot say that two paths must reach the same entity. The schema enforces each
# rule with a composite foreign key through the shared column.
# (relationships, rule, how the schema enforces it)
CROSS_RULES = [
    (("Receipt_For", "Receives"),
     "a goods receipt only receives lines of its own purchase order",
     "`goods_receipt_lines(receipt_id, purchase_order_id)` references `goods_receipts(receipt_id, purchase_order_id)`, "
     "and `(purchase_order_id, line_no)` references the purchase-order line, so both must name the same purchase order"),
    (("Return_Of", "Returns"),
     "a return request only returns lines of its own order",
     "`return_lines(return_id, order_id)` references `return_requests(return_id, order_id)`, "
     "and `(order_id, line_no)` references the order line, so both must name the same order"),
    (("Transaction_Of", "Refund_For"),
     "a refund is paid back from the payment of the order that was returned",
     "`payment_transactions` carries `order_id` only for this: `(payment_id, order_id)` references `payments` "
     "and `(return_id, order_id)` references `return_requests`, so the payment and the return belong to the same order"),
    (("Batch_Of", "Stored_In"),
     "a stock batch is stored in a bin of its own warehouse",
     "`stock_batches(bin_id, warehouse_id)` references `storage_bins(bin_id, warehouse_id)`, "
     "and `warehouse_id` is also part of the batch's stock position"),
]
