# SQL queries and how to explain them

The course announcement calls for a web interface that uses SQL queries. The supplied guideline PDF does **not** list the exact queries. These queries are implemented in `app.py`; replace or extend them when the course publishes a specific query list.

## 1. Catalog search with stock aggregation

`catalog()` joins listing → variant → product → seller and left-joins stock positions. `GROUP BY listing_id` combines stock from warehouses. `LEFT JOIN` keeps an active listing visible even if its stock is zero. The search term is bound as a parameter, not concatenated into SQL.

```sql
SELECT l.listing_id, p.name, s.name AS seller,
       COALESCE(SUM(sp.available_qty), 0) AS stock
FROM listings l
JOIN variants v ON v.variant_id = l.variant_id
JOIN products p ON p.product_id = v.product_id
JOIN seller_organizations s ON s.seller_id = l.seller_id
LEFT JOIN stock_positions sp
  ON sp.seller_id = l.seller_id AND sp.variant_id = l.variant_id
WHERE l.active = 1 AND (p.name LIKE ? OR s.name LIKE ?)
GROUP BY l.listing_id;
```

## 2. Checkout stock allocation and transaction

`checkout()` starts `BEGIN IMMEDIATE`, which reserves SQLite's write lock before checking inventory. For each cart line it reads matching stock positions, allocates from warehouses, updates quantities only if enough remains, and inserts `stock_reservations`. It also reduces batch quantities and writes stock movement rows. Order, payment, invoice, and cart clearing are committed together. Any error rolls back all changes, preventing a paid order without stock.

The conditional update is the last defense against negative stock:

```sql
UPDATE stock_positions
SET available_qty = available_qty - ?
WHERE seller_id = ? AND variant_id = ? AND warehouse_id = ?
  AND available_qty >= ?;
```

## 3. Revenue by seller

`reports()` joins order lines through listings to sellers. It sums the **captured** order-line price, not today's listing price. `COUNT(DISTINCT order_id)` avoids counting a multi-line order repeatedly.

```sql
SELECT s.name, COUNT(DISTINCT o.order_id) AS orders,
       SUM(ol.quantity * ol.unit_price_cents) AS revenue_cents
FROM order_lines ol
JOIN orders o ON o.order_id = ol.order_id
JOIN listings l ON l.listing_id = ol.listing_id
JOIN seller_organizations s ON s.seller_id = l.seller_id
WHERE o.status != 'cancelled'
GROUP BY s.seller_id
ORDER BY revenue_cents DESC;
```

This is gross booked revenue in the demo. It does not subtract refunds or calculate fees/tax.

## 4. Low-stock alert

`reports()` compares each seller–variant–warehouse's available quantity to its reorder point. That threshold belongs to the ternary stock relationship, because the same variant may have different thresholds at different warehouses.

```sql
SELECT s.name, p.name, sp.available_qty, sp.reorder_point
FROM stock_positions sp
JOIN seller_organizations s ON s.seller_id = sp.seller_id
JOIN variants v ON v.variant_id = sp.variant_id
JOIN products p ON p.product_id = v.product_id
WHERE sp.available_qty <= sp.reorder_point;
```

## 5. Return quantity guard

`request_return()` sums all non-rejected return quantities for one order line. A new request is accepted only when `used + requested <= originally ordered`. The check and insertion run under `BEGIN IMMEDIATE`, so two requests cannot both pass against the same available quantity.

```sql
SELECT COALESCE(SUM(rl.quantity), 0)
FROM return_lines rl
JOIN return_requests rr ON rr.return_id = rl.return_id
WHERE rl.order_id = ? AND rl.line_no = ? AND rr.status != 'rejected';
```

## More query categories available for assessment

`app.py` also uses filtering, sorting, `COUNT`, `SUM`, grouping across multiple tables, conditional writes, and status history queries. A course-specific requirement for nested subqueries, views, triggers, or stored procedures is not stated in the supplied PDF; add those only after checking the actual assignment page.
